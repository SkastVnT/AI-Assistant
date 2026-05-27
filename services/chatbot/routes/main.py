"""
Main routes: /, /new, /chat, /clear, /history
"""

import json
import logging
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, session

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from app.middleware.auth import require_login

# NOTE: routes/main.py uses the LEGACY V1 ChatbotAgent. The streaming path
# (routes/stream.py) uses V2 (core.chatbot_v2). Consolidation onto V2 is
# deliberately out of scope for the current drift-reduction step — see the
# LEGACY V1 marker in core/chatbot.py.
from core.chatbot import get_chatbot
from core.config import MEMORY_DIR
from core.extensions import logger
from core.private_logger import log_chat, log_interaction
from core.request_normalizer import normalize_chat_request
from core.skills.applicator import apply_skill_overrides
from core.skills.resolver import resolve_skill
from core.tools import github_search_tool, google_search_tool

# Check MCP availability
MCP_AVAILABLE = False
try:
    from src.handlers.mcp_handler import get_mcp_client, inject_code_context

    MCP_AVAILABLE = True
except ImportError:
    pass

main_bp = Blueprint("main", __name__)


# ── DB monitoring helpers ──────────────────────────────────────────────────


def _log_chat_event(event: str, data: dict) -> None:
    """Fire-and-forget: write a chat event to MongoDB + Firebase RTDB.

    Runs in a daemon background thread so it never blocks the response.
    event: "input" | "output"
    data: dict with message, response, model, session_id, etc.
    """

    def _worker():
        try:
            from datetime import datetime as _dt

            payload = {
                **data,
                "event": event,
                "timestamp": _dt.utcnow().isoformat() + "Z",
                "collection": "chat_logs",
            }
            # MongoDB
            try:
                from core.image_storage import mongo_db as _mdb

                if _mdb is not None:
                    _mdb["chat_logs"].insert_one(payload.copy())
            except Exception as me:
                logger.debug(f"[monitor] mongo write skipped: {me}")
            # Firebase RTDB
            try:
                from core.image_storage import rtdb_push

                sid = data.get("session_id", "unknown")
                rtdb_push(
                    f"chat_logs/{sid}", {k: v for k, v in payload.items() if k != "_id"}
                )

                # New normalized conversation stream for Firebase (v2 schema)
                if event == "input":
                    convo_item = {
                        "session_id": sid,
                        "role": "user",
                        "content": data.get("message", ""),
                        "model": data.get("model", ""),
                        "context": data.get("context", ""),
                        "timestamp": payload["timestamp"],
                        "schema_version": 2,
                    }
                else:
                    convo_item = {
                        "session_id": sid,
                        "role": "assistant",
                        "content": data.get("response", ""),
                        "user_content": data.get("message", ""),
                        "model": data.get("model", ""),
                        "context": data.get("context", ""),
                        "latency_ms": data.get("latency_ms"),
                        "timestamp": payload["timestamp"],
                        "schema_version": 2,
                    }
                rtdb_push(f"conversations_v2/{sid}/messages", convo_item)
            except Exception as fe:
                logger.debug(f"[monitor] rtdb write skipped: {fe}")
        except Exception as e:
            logger.debug(f"[monitor] _log_chat_event error: {e}")

    threading.Thread(target=_worker, daemon=True).start()


@main_bp.route("/", methods=["GET", "POST"])
@require_login
def index():
    """Home page - Original beautiful UI with full SDXL support"""
    if request.method == "POST":
        body_preview = request.get_data(as_text=True)[:300]
        logger.debug(
            "[POST /] Unexpected POST at root — body=%r ct=%r",
            body_preview,
            request.content_type,
        )
        return jsonify({"status": "ok"}), 200
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")


@main_bp.route("/new")
@require_login
def index_new():
    """New Tailwind version (experimental)"""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index_tailwind.html")


@main_bp.route("/chat", methods=["POST"])
@require_login
def chat():
    """Chat endpoint - handles both JSON and FormData (with files)"""
    try:
        logger.info(f"[CHAT] Received request - Content-Type: {request.content_type}")

        # Check if request has files (FormData) or is JSON
        if request.content_type and "multipart/form-data" in request.content_type:
            # FormData with files
            data = request.form
            message = data.get("message", "")
            model = data.get("model", "grok")
            context = data.get("context", "casual")
            deep_thinking = data.get("deep_thinking", "false").lower() == "true"
            language = data.get("language", "vi")
            custom_prompt = data.get("custom_prompt", "")

            # Safe JSON parsing
            try:
                tools = json.loads(data.get("tools", "[]")) if data.get("tools") else []
            except:
                tools = []

            try:
                history_str = data.get("history", "null")
                history = (
                    json.loads(history_str)
                    if history_str and history_str != "null"
                    else None
                )
            except:
                history = None

            try:
                memory_ids = (
                    json.loads(data.get("memory_ids", "[]"))
                    if data.get("memory_ids")
                    else []
                )
            except:
                memory_ids = []

            try:
                mcp_selected_files = (
                    json.loads(data.get("mcp_selected_files", "[]"))
                    if data.get("mcp_selected_files")
                    else []
                )
            except:
                mcp_selected_files = []

            # Handle uploaded files
            files = request.files.getlist("files")

            # Process uploaded files: extract text content and inject into message
            if files:
                file_parts = []
                for f in files:
                    try:
                        fname = f.filename or "unknown"
                        content_type = f.content_type or ""
                        raw = f.read()
                        # Skip empty files
                        if not raw:
                            continue
                        # Cap at 10MB per file to prevent OOM
                        if len(raw) > 10 * 1024 * 1024:
                            file_parts.append(f"**{fname}**: (file too large, skipped)")
                            continue
                        # Text-like files: decode and inject content
                        if (
                            content_type.startswith("text/")
                            or content_type == "application/json"
                            or fname.endswith(
                                (
                                    ".py",
                                    ".js",
                                    ".html",
                                    ".css",
                                    ".csv",
                                    ".md",
                                    ".txt",
                                    ".json",
                                )
                            )
                        ):
                            text = raw.decode("utf-8", errors="replace")
                            # Truncate very long text
                            if len(text) > 30000:
                                text = text[:30000] + "\n...(truncated)"
                            file_parts.append(f"**File: {fname}**\n```\n{text}\n```")
                        else:
                            # Binary/image files: note metadata only (images handled client-side via base64)
                            size_kb = len(raw) / 1024
                            file_parts.append(
                                f"**File: {fname}** ({content_type}, {size_kb:.0f} KB)"
                            )
                    except Exception as fe:
                        logger.warning(
                            f"[CHAT] Error processing file {f.filename}: {fe}"
                        )

                if file_parts:
                    file_context = (
                        "📎 **Uploaded Files:**\n\n"
                        + "\n\n---\n\n".join(file_parts)
                        + "\n\n---\n\n"
                    )
                    message = file_context + message
                    logger.info(
                        f"[CHAT] Injected {len(file_parts)} file(s) into message"
                    )
        else:
            # JSON request
            data = request.json
            message = data.get("message", "")
            model = data.get("model", "grok")
            context = data.get("context", "casual")
            deep_thinking = data.get("deep_thinking", False)
            language = data.get("language", "vi")
            custom_prompt = data.get("custom_prompt", "")
            tools = data.get("tools", [])
            history = data.get("history", None)
            memory_ids = data.get("memory_ids", [])
            mcp_selected_files = data.get("mcp_selected_files", [])

        if not message:
            return jsonify({"error": "Tin nháº¯n trá»‘ng"}), 400

        # ── Shared request normalization ──────────────────────────────
        # Same contract enforced by /chat/stream so the two endpoints agree
        # on conversation_id binding, image-context injection, and history
        # bounds. See core/request_normalizer.py.
        _norm_data = data if hasattr(data, "get") else {}
        _normalized = normalize_chat_request(
            _norm_data,
            session,
            message=message,
        )
        message = _normalized["message"]
        history = (
            _normalized["history"] if _normalized["history"] is not None else history
        )
        if _normalized["conversation_id_bound"]:
            logger.info(f"[CHAT] conversation_id={_normalized['conversation_id']}")
        if _normalized["image_context_count"]:
            logger.info(
                f"[CHAT] Injected {_normalized['image_context_count']} image asset(s) into context"
            )

        # ── Runtime Skill Resolution + Application ────────────────────
        skill_overrides = resolve_skill(
            message=message,
            explicit_skill_id=data.get("skill") if hasattr(data, "get") else None,
            session_id=session.get("session_id"),
            auto_route=True,
        )
        applied = apply_skill_overrides(
            data=dict(data) if hasattr(data, "to_dict") else (data or {}),
            skill_overrides=skill_overrides,
            language=language,
        )
        model = applied.model
        context = applied.context
        deep_thinking = applied.deep_thinking
        custom_prompt = applied.custom_prompt
        tools = applied.tools

        if applied.was_applied:
            logger.info(f"[CHAT] Skill applied: {applied.skill_id}")

        # MCP Integration: Inject code context
        if MCP_AVAILABLE:
            try:
                mcp_client = get_mcp_client()
                if mcp_client and mcp_client.enabled:
                    # Pre-warm memory cache by inferred domain to stabilize long/complex responses.
                    if hasattr(mcp_client, "warm_memory_cache_by_question"):
                        try:
                            mcp_client.warm_memory_cache_by_question(
                                question=message,
                                force_refresh=False,
                                cache_ttl_seconds=900,
                                limit=20,
                                min_importance=4,
                                max_chars=12000,
                            )
                            logger.info("[MCP] Memory cache pre-warm completed")
                        except Exception as warm_error:
                            logger.warning(
                                f"[MCP] Memory cache pre-warm skipped: {warm_error}"
                            )

                    logger.info("[MCP] Injecting code context")
                    message = inject_code_context(
                        message, mcp_client, mcp_selected_files
                    )
                elif applied.prefer_mcp and mcp_client:
                    message = inject_code_context(
                        message, mcp_client, mcp_selected_files
                    )
                    logger.info(
                        f"[MCP] Skill '{applied.skill_id}' triggered MCP context injection"
                    )
            except Exception as e:
                logger.warning(f"[MCP] Error injecting context: {e}")

        session_id = session.get("session_id")
        chatbot = get_chatbot(session_id)

        # Handle tools
        tool_results = []
        if tools and len(tools) > 0:
            logger.info(f"[TOOLS] Active tools: {tools}")

            if "google-search" in tools:
                search_result = google_search_tool(message)
                tool_results.append(f"## ðŸ” Google Search Results\n\n{search_result}")

            if "github" in tools:
                github_result = github_search_tool(message)
                tool_results.append(f"## ðŸ™ GitHub Search Results\n\n{github_result}")

            if "image-generation" in tools:
                # Handle AI image generation via tools
                tool_results.append(
                    _handle_image_generation_tool(chatbot, message, model)
                )

        # Return tool results if any
        if tool_results:
            combined_results = "\n\n---\n\n".join(tool_results)
            # Private log for tool interactions
            log_chat(
                session_id=session.get("session_id", ""),
                user_message=message,
                assistant_response=combined_results[:2000],
                model="tools",
                context=context,
                language=language,
                tools=tools,
            )
            log_interaction(
                "tool_call",
                {
                    "tools": tools,
                    "message": message[:300],
                    "result_length": len(combined_results),
                },
                session_id=session.get("session_id", ""),
            )
            return jsonify(
                {
                    "response": combined_results,
                    "model": "tools",
                    "context": context,
                    "deep_thinking": False,
                    "tools": tools,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Load selected memories
        memories = []
        if memory_ids:
            for mem_id in memory_ids:
                memory_file = MEMORY_DIR / f"{mem_id}.json"
                if memory_file.exists():
                    try:
                        with open(memory_file, encoding="utf-8") as f:
                            memories.append(json.load(f))
                    except Exception as e:
                        logger.error(f"Error loading memory {mem_id}: {e}")

        # Process chat
        _t0 = time.time()
        # Log input event (non-blocking)
        _log_chat_event(
            "input",
            {
                "session_id": session.get("session_id", ""),
                "message": message[:500],  # cap length
                "model": model,
                "context": context,
            },
        )

        if history:
            original_history = chatbot.conversation_history.copy()
            result = chatbot.chat(
                message,
                model,
                context,
                deep_thinking,
                history,
                memories,
                language,
                custom_prompt,
            )
            chatbot.conversation_history = original_history
        else:
            result = chatbot.chat(
                message,
                model,
                context,
                deep_thinking,
                None,
                memories,
                language,
                custom_prompt,
            )

        # Extract response
        if isinstance(result, dict):
            response = result.get("response", "")
            thinking_process = result.get("thinking_process", None)
        else:
            response = result
            thinking_process = None

        # Log output event (non-blocking)
        _log_chat_event(
            "output",
            {
                "session_id": session.get("session_id", ""),
                "message": message[:500],
                "response": response[:1000],  # cap length
                "model": model,
                "context": context,
                "latency_ms": round((time.time() - _t0) * 1000, 1),
            },
        )

        # ── Private local log (non-blocking) ──
        log_chat(
            session_id=session.get("session_id", ""),
            user_message=message,
            assistant_response=response,
            model=model,
            context=context,
            language=language,
            tools=tools,
            latency_ms=round((time.time() - _t0) * 1000, 1),
            thinking_process=thinking_process,
        )

        return jsonify(
            {
                "response": response,
                "model": model,
                "context": context,
                "deep_thinking": deep_thinking,
                "thinking_process": thinking_process,
                "tools": tools,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"[CHAT] Error: {e}")
        return jsonify({"error": "An internal error occurred"}), 500


@main_bp.route("/clear", methods=["POST"])
def clear():
    """Clear chat history"""
    try:
        session_id = session.get("session_id")
        chatbot = get_chatbot(session_id)
        chatbot.clear_history()

        return jsonify({"message": "ÄÃ£ xÃ³a lá»‹ch sá»­ chat"})

    except Exception as e:
        logger.error(f"[Clear History] Error: {str(e)}")
        return jsonify({"error": "Failed to clear chat history"}), 500


@main_bp.route("/history", methods=["GET"])
def history():
    """Get chat history"""
    try:
        session_id = session.get("session_id")
        chatbot = get_chatbot(session_id)

        return jsonify({"history": chatbot.conversation_history})

    except Exception as e:
        logger.error(f"[History] Error: {str(e)}")
        return jsonify({"error": "Failed to retrieve chat history"}), 500


@main_bp.route("/api/health/databases", methods=["GET"])
def health_databases():
    """Check MongoDB + Firebase RTDB connectivity."""
    from datetime import datetime as _dt

    result = {"timestamp": _dt.utcnow().isoformat() + "Z"}

    # MongoDB
    try:
        from core.image_storage import mongo_client as _mc

        if _mc is not None:
            _mc.admin.command("ping")
            result["mongodb"] = {"ok": True}
        else:
            result["mongodb"] = {"ok": False, "error": "not configured"}
    except Exception:
        result["mongodb"] = {"ok": False, "error": "connection failed"}

    # Firebase RTDB
    try:
        from core.image_storage import rtdb_health

        result["firebase_rtdb"] = rtdb_health()
    except Exception:
        result["firebase_rtdb"] = {"ok": False, "error": "connection failed"}

    overall_ok = result["mongodb"]["ok"] and result["firebase_rtdb"]["ok"]
    return jsonify({"ok": overall_ok, **result}), (200 if overall_ok else 503)


@main_bp.route("/api/generate-title", methods=["POST"])
def generate_title():
    """Generate a concise conversation title using Ollama qwen2.5:0.5b (lightest local model)."""
    import requests as _req

    data = request.get_json(silent=True) or {}
    raw_message = data.get("message", "")
    if not isinstance(raw_message, str):
        raw_message = ""
    # Sanitize and truncate input
    user_message = raw_message.strip()[:200]
    language = str(data.get("language", "vi")).strip()

    if not user_message:
        return jsonify({"error": "message is required"}), 400

    if language == "en":
        prompt = (
            "Generate a concise 3-5 word English title for this conversation. "
            "Return ONLY the title text, no quotes, no explanation:\n"
            f'"{user_message}"'
        )
    else:
        prompt = (
            "Tạo tiêu đề ngắn gọn 3-7 từ tiếng Việt cho cuộc trò chuyện này. "
            "Chỉ trả về tiêu đề, không giải thích, không ngoặc kép:\n"
            f'"{user_message}"'
        )

    try:
        resp = _req.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:0.5b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 20},
            },
            timeout=10,
        )
        resp.raise_for_status()
        title = (
            resp.json()
            .get("response", "")
            .strip()
            .replace('"', "")
            .replace("'", "")
            .strip()
        )
        if title:
            return jsonify({"title": title})
    except Exception as e:
        logger.warning(f"[generate-title] Ollama unavailable: {e}")

    # Fallback 1: xAI Grok (cloud) — uses GROK_API_KEY if available
    try:
        from core.config import GROK_API_KEY

        if GROK_API_KEY:
            r = _req.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "grok-2-latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 30,
                },
                timeout=12,
            )
            r.raise_for_status()
            content = (
                (r.json().get("choices") or [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            title = content.strip().replace('"', "").replace("'", "").strip()
            # Trim to first line and cap length.
            title = title.split("\n", 1)[0][:60]
            if title:
                return jsonify({"title": title})
    except Exception as e:
        logger.warning(f"[generate-title] xAI fallback failed: {e}")

    # Fallback 2: truncate the raw message
    fallback = user_message[:40] + ("..." if len(user_message) > 40 else "")
    return jsonify({"title": fallback})


@main_bp.route("/api/chat/suggestions", methods=["POST"])
def chat_suggestions():
    """Generate 3 context-aware follow-up suggestions using the AI model.

    Request body:
        message  (str) — the user's original question (max 500 chars)
        response (str) — the AI's reply (max 1000 chars)
        model    (str, optional) — model to use; defaults to chatbot default
        language (str, optional) — 'vi' or 'en'; defaults to 'vi'

    Returns:
        {"suggestions": ["...", "...", "..."]}
    """
    data = request.get_json(silent=True) or {}
    user_msg = str(data.get("message", "")).strip()[:500]
    bot_resp = str(data.get("response", "")).strip()[:1000]
    language = str(data.get("language", "vi")).strip()
    model = str(data.get("model", "")).strip() or None

    if not user_msg or not bot_resp:
        return jsonify({"suggestions": []}), 400

    vi = language != "en"
    if vi:
        prompt = (
            "Dựa trên cuộc trò chuyện dưới đây, hãy tạo ra ĐÚNG 3 câu hỏi tiếp theo "
            "mà người dùng có thể muốn hỏi. Mỗi câu hỏi phải:\n"
            "- Cụ thể, liên quan trực tiếp đến nội dung vừa trả lời\n"
            "- Ngắn gọn (tối đa 12 từ)\n"
            "- Khác nhau về góc nhìn (ví dụ: chi tiết hơn / ứng dụng thực tế / so sánh)\n"
            "Chỉ trả về 3 câu, mỗi câu 1 dòng, không đánh số, không giải thích.\n\n"
            f"Người dùng hỏi: {user_msg}\n"
            f"AI trả lời: {bot_resp}"
        )
    else:
        prompt = (
            "Based on the conversation below, generate EXACTLY 3 follow-up questions "
            "the user might want to ask. Each question must be:\n"
            "- Specific and directly related to the answer\n"
            "- Concise (max 12 words)\n"
            "- Different angles (e.g. deeper detail / practical use / comparison)\n"
            "Return only 3 questions, one per line, no numbering, no explanation.\n\n"
            f"User asked: {user_msg}\n"
            f"AI replied: {bot_resp}"
        )

    try:
        chatbot = get_chatbot()
        response = chatbot.chat(
            message=prompt,
            model=model,
            context="casual",
            deep_thinking=False,
        )
        raw = response.get("text", "") if isinstance(response, dict) else str(response)
        lines = [
            ln.strip().lstrip("•-–—").strip()
            for ln in raw.strip().splitlines()
            if ln.strip()
        ]
        # Filter out lines that look like meta-commentary rather than questions
        suggestions = [ln for ln in lines if len(ln) > 5 and len(ln) < 150][:3]
        if suggestions:
            return jsonify({"suggestions": suggestions})
    except Exception as e:
        logger.warning("[chat/suggestions] AI call failed: %s", e)

    return jsonify({"suggestions": []})


@main_bp.route("/api/extract-file-text", methods=["POST"])
def extract_file_text():
    """Extract readable text from a base64-encoded file (PDF, DOCX, XLSX, image, etc.)."""
    import base64 as _b64

    data = request.get_json(silent=True) or {}
    file_b64 = data.get("file_b64", "")
    filename = str(data.get("filename", "file")).strip()

    if not file_b64 or not filename:
        return (
            jsonify({"success": False, "error": "file_b64 and filename required"}),
            400,
        )

    # Strip data URL prefix if present (e.g. "data:application/pdf;base64,...")
    if "," in file_b64:
        file_b64 = file_b64.split(",", 1)[1]

    try:
        file_bytes = _b64.b64decode(file_b64)
    except Exception as e:
        return jsonify({"success": False, "error": f"Invalid base64: {e}"}), 400

    try:
        from src.ocr_integration import extract_file_content

        success, text = extract_file_content(file_bytes, filename)
    except Exception as e:
        logger.error(f"[extract-file-text] OCR error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    if success and text and text.strip():
        return jsonify({"success": True, "text": text.strip(), "filename": filename})
    return jsonify(
        {"success": False, "text": "", "error": "Could not extract text from file"}
    )

    """Handle AI-powered image generation tool"""
    import json
    import re

    prompt_request = f"""Báº¡n lÃ  chuyÃªn gia táº¡o prompt cho Stable Diffusion.

NHIá»†M Vá»¤: Chuyá»ƒn Ä‘á»•i mÃ´ táº£ cá»§a ngÆ°á»i dÃ¹ng thÃ nh prompt CHÃNH XÃC.

âš ï¸ QUY Táº®C:
1. CHá»ˆ mÃ´ táº£ ÄÃšNG nhá»¯ng gÃ¬ user yÃªu cáº§u
2. NSFW Protection: Táº¤T Cáº¢ áº£nh pháº£i SFW
3. Negative PHáº¢I CÃ“: nsfw, nude, naked, explicit, sexual

MÃ” Táº¢: "{message}"

Tráº£ vá» JSON:
{{
    "prompt": "prompt mÃ´ táº£",
    "negative_prompt": "bad quality, blurry, nsfw, nude, naked, explicit",
    "explanation": "giáº£i thÃ­ch ngáº¯n",
    "has_people": false
}}

CHá»ˆ tráº£ JSON."""

    try:
        import os

        from src.utils.sd_client import get_sd_client

        ai_response = chatbot.chat(
            prompt_request, model=model, context="programming", language="vi"
        )
        response_text = (
            ai_response.get("response", ai_response)
            if isinstance(ai_response, dict)
            else ai_response
        )

        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            prompt_data = json.loads(json_match.group())
            generated_prompt = prompt_data.get("prompt", "")
            generated_neg = prompt_data.get("negative_prompt", "")
            prompt_data.get("explanation", "")

            # Add NSFW filters
            nsfw_filters = "nsfw, nude, naked, explicit, sexual, porn"
            if "nsfw" not in generated_neg.lower():
                generated_neg = f"{generated_neg}, {nsfw_filters}"

            sd_api_url = os.getenv("SD_API_URL", "http://127.0.0.1:7861")
            sd_client = get_sd_client(sd_api_url)

            image_params = {
                "prompt": generated_prompt,
                "negative_prompt": generated_neg,
                "width": 512,
                "height": 512,
                "steps": 30,
                "cfg_scale": 7.0,
                "sampler_name": "DPM++ 2M Karras",
                "seed": -1,
                "save_images": False,
            }

            sd_result = sd_client.txt2img(**image_params)

            if sd_result.get("images"):
                image_base64 = sd_result["images"][0]

                return f"""## ðŸŽ¨ áº¢nh Ä‘Ã£ Ä‘Æ°á»£c táº¡o thÃ nh cÃ´ng!

**MÃ´ táº£ gá»‘c:** {message}

**Generated Prompt:**
```
{generated_prompt}
```

**áº¢nh Ä‘Æ°á»£c táº¡o:**
<img src="data:image/png;base64,{image_base64}" alt="Generated Image" style="max-width: 100%; border-radius: 8px;">

---
ðŸŽ¯ **ThÃ´ng sá»‘:** {image_params["width"]}x{image_params["height"]} | Steps: {image_params["steps"]}"""
            else:
                return f"## ðŸŽ¨ Image Generation\n\nâš ï¸ KhÃ´ng thá»ƒ táº¡o áº£nh. SD Response: {sd_result}"
        else:
            return "## ðŸŽ¨ Image Generation\n\nKhÃ´ng thá»ƒ táº¡o prompt tá»± Ä‘á»™ng."

    except Exception as e:
        logging.error(f"[TOOLS] Error in image generation: {e}")
        return f"## ðŸŽ¨ Image Generation\n\nLá»—i: {str(e)}"
