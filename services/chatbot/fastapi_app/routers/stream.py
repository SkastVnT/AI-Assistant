"""
SSE Streaming router — /chat/stream
"""
import json
import logging
import os
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from fastapi_app.dependencies import get_chatbot_for_session, get_session_id
from fastapi_app.models import StreamRequest
from fastapi_app.rag_helpers import retrieve_rag_context
from core.config import MEMORY_DIR
from core.extensions import logger

router = APIRouter()

# MCP
MCP_AVAILABLE = False
try:
    from src.handlers.mcp_handler import inject_code_context, get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    pass


def _sse(event: str, data: dict | str) -> str:
    """Format a single Server-Sent Event."""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _generate_suggestions(user_msg: str, response: str, language: str = "vi") -> list[str]:
    """Generate 2-3 follow-up question suggestions based on the conversation."""
    # Use rule-based extraction for speed (no extra LLM call)
    suggestions = []
    resp_lower = response.lower()
    msg_lower = user_msg.lower()

    # Detect topic categories for smart suggestions
    is_code = any(k in resp_lower for k in ("```", "def ", "function ", "class ", "import "))
    is_explain = any(k in msg_lower for k in ("là gì", "what is", "giải thích", "explain", "how does"))
    is_list = resp_lower.count("\n- ") >= 3 or resp_lower.count("\n1.") >= 2
    is_error = any(k in msg_lower for k in ("lỗi", "error", "bug", "fix", "sửa"))

    vi = language.startswith("vi")

    if is_code:
        suggestions.append("Giải thích chi tiết đoạn code này" if vi else "Explain this code in detail")
        suggestions.append("Tối ưu hiệu suất được không?" if vi else "Can this be optimized?")
        if is_error:
            suggestions.append("Còn cách nào khác để fix không?" if vi else "Any alternative fix?")
    elif is_explain:
        suggestions.append("Cho ví dụ thực tế được không?" if vi else "Can you give a real example?")
        suggestions.append("So sánh với các giải pháp khác" if vi else "Compare with alternatives")
    elif is_list:
        suggestions.append("Phân tích chi tiết hơn từng mục" if vi else "Analyze each item in detail")
        suggestions.append("Cái nào quan trọng nhất?" if vi else "Which one is most important?")
    else:
        suggestions.append("Giải thích thêm chi tiết" if vi else "Explain in more detail")
        suggestions.append("Có ví dụ cụ thể không?" if vi else "Any specific examples?")

    # Always add a "go deeper" suggestion
    if len(suggestions) < 3:
        suggestions.append("Tóm tắt ngắn gọn hơn" if vi else "Summarize more concisely")

    return suggestions[:3]


# ── Auto web-search detection ────────────────────────────────────────

# Patterns that very likely need real-time / factual data from the web
_REALTIME_PATTERNS_VI = [
    "giá", "tỷ giá", "thời tiết", "tin tức", "mới nhất", "hiện tại",
    "hôm nay", "bây giờ", "mấy giờ", "ngày bao nhiêu",
    "lịch", "kết quả", "tỉ số", "xổ số", "chứng khoán",
    "cổ phiếu", "bitcoin", "crypto", "coin", "vàng", "USD",
    "bao nhiêu tiền", "review", "đánh giá", "so sánh",
    "nên mua", "mua ở đâu", "ở đâu", "địa chỉ", "số điện thoại",
    "sự kiện", "lịch trình", "cập nhật", "phiên bản mới",
    "ra mắt", "release", "công bố", "thông báo",
]
_REALTIME_PATTERNS_EN = [
    "price", "weather", "news", "latest", "current", "today",
    "right now", "stock", "bitcoin", "crypto", "gold price",
    "exchange rate", "how much", "review", "compare",
    "where to buy", "address", "phone number", "schedule",
    "update", "new version", "release", "announcement",
    "score", "result", "ranking", "trending",
]
_SEARCH_KEYWORDS = [
    "tìm", "search", "tra cứu", "look up", "google",
    "tìm kiếm", "find", "tìm giúp", "check",
]


def _needs_web_search(message: str, tools: list[str]) -> bool:
    """Detect if the message needs web search for accurate real-time data.
    
    Returns True if:
    - User explicitly has google-search / deep-research tool active, OR
    - Message contains real-time patterns (prices, weather, news, etc.), OR
    - User explicitly asks to search/look up something
    """
    if "google-search" in tools or "deep-research" in tools:
        return True

    msg_lower = message.lower()

    # Explicit search request
    if any(kw in msg_lower for kw in _SEARCH_KEYWORDS):
        return True

    # Real-time data patterns
    if any(p in msg_lower for p in _REALTIME_PATTERNS_VI + _REALTIME_PATTERNS_EN):
        return True

    return False


def _run_web_search(query: str) -> str:
    """Run Google Custom Search and return formatted results.
    Reuses the same API as chatbot_main.google_search_tool but standalone.
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    api_key_1 = os.getenv("GOOGLE_SEARCH_API_KEY_1", "")
    api_key_2 = os.getenv("GOOGLE_SEARCH_API_KEY_2", "")
    cse_id = os.getenv("GOOGLE_CSE_ID", "")

    if not api_key_1 or not cse_id:
        return ""

    url = "https://www.googleapis.com/customsearch/v1"
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503])
    session.mount("https://", HTTPAdapter(max_retries=retry))

    for api_key in [api_key_1, api_key_2]:
        if not api_key:
            continue
        try:
            resp = session.get(url, params={
                "key": api_key, "cx": cse_id, "q": query, "num": 5,
            }, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                if items:
                    parts = []
                    for item in items[:5]:
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        link = item.get("link", "")
                        parts.append(f"**{title}**\n{snippet}\n🔗 {link}")
                    return "🔍 **Kết quả tìm kiếm web (real-time):**\n\n" + "\n\n---\n\n".join(parts)
            elif resp.status_code in (429, 403):
                continue  # try next key
            else:
                logger.warning(f"[WebSearch] HTTP {resp.status_code}")
                return ""
        except Exception as e:
            logger.warning(f"[WebSearch] Error: {e}")
            continue

    return ""


@router.post("/chat/stream")
async def chat_stream(body: StreamRequest, request: Request):
    """Streaming chat via Server-Sent Events."""
    message = body.message
    model = body.model
    context = body.context
    deep_thinking = body.deep_thinking
    thinking_mode = body.thinking_mode
    language = body.language
    custom_prompt = body.custom_prompt
    memory_ids = body.memory_ids
    mcp_selected_files = body.mcp_selected_files
    history = body.history

    if not message:
        return StreamingResponse(
            iter([_sse("error", {"error": "Empty message"})]),
            media_type="text/event-stream",
            status_code=400,
        )

    # MCP integration
    if MCP_AVAILABLE:
        try:
            mcp_client = get_mcp_client()
            if mcp_client and mcp_client.enabled:
                message = inject_code_context(message, mcp_client, mcp_selected_files)
        except Exception as e:
            logger.warning(f"[MCP] Stream context error: {e}")

    chatbot = get_chatbot_for_session(request)

    # Load memories
    memories = []
    for mid in memory_ids:
        path = MEMORY_DIR / f"{mid}.json"
        if path.exists():
            try:
                memories.append(json.loads(path.read_text("utf-8")))
            except Exception:
                pass

    # RAG retrieval — shared helper (no logic duplication with chat.py)
    rag_collection_ids = getattr(body, "rag_collection_ids", [])
    rag_top_k = getattr(body, "rag_top_k", 5)
    rag = await retrieve_rag_context(
        message=message,
        custom_prompt=custom_prompt,
        language=language,
        tenant_id=get_session_id(request),
        rag_collection_ids=rag_collection_ids,
        rag_top_k=rag_top_k,
    )
    message = rag.message
    custom_prompt = rag.custom_prompt

    # ── Tool execution (web search, etc.) ──────────────────────────
    tools = body.tools or []
    tool_context = ""
    _search_performed = False

    if _needs_web_search(body.message, tools):
        try:
            search_results = _run_web_search(body.message)
            if search_results:
                tool_context = search_results
                _search_performed = True
                logger.info(f"[Stream] Auto web search triggered for: {body.message[:60]}")
        except Exception as e:
            logger.warning(f"[Stream] Web search failed: {e}")

    # Inject tool results into the message context for the LLM
    if tool_context:
        message = (
            f"{message}\n\n"
            f"---\n"
            f"📋 DỮ LIỆU THỰC TẾ TỪ WEB (sử dụng thông tin này để trả lời chính xác):\n"
            f"{tool_context}\n"
            f"---\n"
            f"Hãy trả lời dựa trên dữ liệu web ở trên. Nếu dữ liệu có ngày/giờ cụ thể, hãy trích dẫn."
        )

    # ── 4-Agents (multi-thinking) mode ──
    is_multi_thinking = thinking_mode == "multi-thinking"

    async def event_generator() -> AsyncGenerator[str, None]:
        import time as _time
        try:
            # ── Early RAG metadata event (before any tokens) ──
            if rag.chunk_count > 0:
                yield _sse("rag_context", {
                    "chunk_count": rag.chunk_count,
                    "citations": rag.citations,
                })

            _stream_start = _time.monotonic()

            yield _sse("metadata", {
                "model": model,
                "context": context,
                "deep_thinking": deep_thinking or is_multi_thinking,
                "thinking_mode": thinking_mode,
                "web_search": _search_performed,
                "streaming": True,
                "timestamp": datetime.now().isoformat(),
            })

            full_response = ""
            chunk_count = 0
            _first_chunk_time = None
            _est_tokens = 0

            if is_multi_thinking:
                # ── 4-Agents Coordinated Reasoning (streamed via SSE) ──
                yield _sse("thinking_start", {"mode": "multi-thinking", "label": "4-Agents Reasoning"})

                try:
                    from app.services.reasoning_service import get_reasoning_service
                    from app.services.ai_service import AIService
                    reasoning_svc = get_reasoning_service(ai_service=AIService())

                    # Run coordinated reasoning (async)
                    result = await reasoning_svc.coordinate_reasoning(
                        message=message,
                        context=context,
                        max_rounds=3,
                    )

                    # Stream thinking process as steps
                    if result.thinking_process:
                        for i, part in enumerate(result.thinking_process.split("\n\n")):
                            part = part.strip()
                            if part:
                                yield _sse("thinking", {"step": part, "step_index": i})

                    yield _sse("thinking_end", {
                        "summary": f"{result.total_rounds} rounds · {result.total_trajectories} trajectories · {result.reasoning_time:.1f}s",
                        "duration_ms": int(result.reasoning_time * 1000),
                        "rounds": result.total_rounds,
                        "trajectories": result.total_trajectories,
                    })

                    full_response = result.final_answer
                    _est_tokens = result.total_tokens or max(1, int(len(full_response) * 0.75))
                    _first_chunk_time = _time.monotonic()

                    # Stream the final answer in chunks for progressive rendering
                    chunk_size = 80
                    for i in range(0, len(full_response), chunk_size):
                        chunk = full_response[i:i + chunk_size]
                        chunk_count += 1
                        yield _sse("chunk", {"content": chunk, "chunk_index": chunk_count})

                except Exception as e:
                    logger.error(f"[4-Agents] Coordinated reasoning failed, fallback: {e}")
                    yield _sse("thinking_end", {"summary": "Fallback to standard", "duration_ms": 0})
                    # Fallback to standard deep-thinking stream
                    for chunk in chatbot.chat_stream(
                        message=message, model=model, context=context,
                        deep_thinking=True, history=history,
                        memories=memories or None, language=language,
                        custom_prompt=custom_prompt,
                    ):
                        if chunk:
                            if _first_chunk_time is None:
                                _first_chunk_time = _time.monotonic()
                            full_response += chunk
                            chunk_count += 1
                            yield _sse("chunk", {"content": chunk, "chunk_index": chunk_count})
                    _est_tokens = max(1, int(len(full_response) * 0.75))
            else:
                # ── Standard streaming ──
                for chunk in chatbot.chat_stream(
                    message=message,
                    model=model,
                    context=context,
                    deep_thinking=deep_thinking,
                    history=history,
                    memories=memories or None,
                    language=language,
                    custom_prompt=custom_prompt,
                ):
                    if chunk:
                        if _first_chunk_time is None:
                            _first_chunk_time = _time.monotonic()
                        full_response += chunk
                        chunk_count += 1
                        yield _sse("chunk", {"content": chunk, "chunk_index": chunk_count})
                _est_tokens = max(1, int(len(full_response) * 0.75))

            _elapsed = _time.monotonic() - _stream_start
            _ttfc = (_first_chunk_time - _stream_start) if _first_chunk_time else _elapsed

            yield _sse("complete", {
                "response": full_response,
                "model": model,
                "context": context,
                "deep_thinking": deep_thinking or is_multi_thinking,
                "thinking_mode": thinking_mode,
                "total_chunks": chunk_count,
                "timestamp": datetime.now().isoformat(),
                "elapsed_time": round(_elapsed, 3),
                "time_to_first_chunk": round(_ttfc, 3),
                "tokens": _est_tokens,
            })

            # Generate follow-up suggestions (lightweight, non-blocking)
            try:
                suggestions = _generate_suggestions(message, full_response, language)
                if suggestions:
                    yield _sse("suggestions", {"items": suggestions})
            except Exception:
                pass  # Non-critical, skip silently

            if rag.citations:
                yield _sse("citations", {"citations": rag.citations})

        except GeneratorExit:
            logger.info("[SSE] Client disconnected")
        except Exception as e:
            logger.error(f"[SSE] Streaming error: {e}")
            yield _sse("error", {"error": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/stream/models")
async def list_streaming_models():
    """List models that support streaming."""
    from core.chatbot_v2 import get_model_registry

    registry = get_model_registry()
    models = []
    for name in registry.list_available():
        config = registry.get_config(name)
        if config:
            models.append({
                "name": name,
                "supports_streaming": config.supports_streaming,
                "provider": config.provider.value,
            })
    return {
        "models": models,
        "streaming_supported": [m["name"] for m in models if m["supports_streaming"]],
    }
