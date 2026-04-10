"""
SSE Streaming router — /chat/stream
"""
import json
import logging
import os
import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from fastapi_app.dependencies import (
    get_chatbot_for_session,
    get_session_id,
    get_image_orchestrator_for_session,
    use_new_image_orchestrator,
    get_new_orchestration_service,
)
from fastapi_app.models import StreamRequest
from fastapi_app.rag_helpers import retrieve_rag_context
from core.config import MEMORY_DIR
from core.extensions import logger
from core.stream_metrics import (
    get_stream_metrics_snapshot,
    record_stream_complete,
    record_stream_error,
    record_stream_start,
)
from core.stream_contract import STREAM_CONTRACT_VERSION, build_complete_event_payload, with_request_id
from core.thinking_generator import (
    ThinkTagParser, detect_category,
    generate_thinking_summary, REASONING_PREFIX
)

router = APIRouter()

# MCP
MCP_AVAILABLE = False
try:
    from src.handlers.mcp_handler import inject_code_context, get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    pass


def _sse(event: str, data: dict | str, request_id: str | None = None) -> str:
    """Format a single Server-Sent Event."""
    if isinstance(data, dict):
        data = with_request_id(data, request_id)
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _generate_suggestions(user_msg: str, response: str, language: str = "vi") -> list[str]:
    """Generate 2-3 contextual follow-up suggestions based on the conversation."""
    suggestions = []
    resp_lower = response.lower()
    msg_lower = user_msg.lower()

    vi = language.startswith("vi")

    # Extract key topics from the response for context-aware suggestions
    # Use heuristic topic extraction from response headings/bold text
    import re
    topics = re.findall(r'\*\*(.+?)\*\*', response[:1500])
    topics = [t.strip('*: ') for t in topics if 3 < len(t) < 60][:5]

    # Detect categories
    is_code = any(k in resp_lower for k in ("```", "def ", "function ", "class ", "import "))
    is_explain = any(k in msg_lower for k in ("là gì", "what is", "giải thích", "explain", "how does"))
    is_list = resp_lower.count("\n- ") >= 3 or resp_lower.count("\n1.") >= 2
    is_error = any(k in msg_lower for k in ("lỗi", "error", "bug", "fix", "sửa"))
    is_compare = any(k in msg_lower for k in ("so sánh", "compare", "vs ", "versus", "khác nhau"))
    is_howto = any(k in msg_lower for k in ("làm sao", "how to", "cách ", "hướng dẫn", "tutorial"))

    if is_code:
        suggestions.append("Giải thích chi tiết đoạn code này" if vi else "Explain this code in detail")
        suggestions.append("Tối ưu hiệu suất được không?" if vi else "Can this be optimized?")
        if is_error:
            suggestions.append("Còn cách nào khác để fix không?" if vi else "Any alternative fix?")
        else:
            suggestions.append("Viết unit test cho code này" if vi else "Write unit tests for this")
    elif is_compare:
        suggestions.append("Tổng hợp bảng so sánh chi tiết" if vi else "Create a detailed comparison table")
        if topics:
            suggestions.append(f"{topics[0]} phù hợp trong trường hợp nào?" if vi else f"When is {topics[0]} the best choice?")
    elif is_howto:
        suggestions.append("Cho ví dụ code/thực hành cụ thể" if vi else "Show a practical example")
        suggestions.append("Những lỗi thường gặp khi làm việc này?" if vi else "Common pitfalls to avoid?")
    elif is_explain:
        suggestions.append("Cho ví dụ thực tế được không?" if vi else "Can you give a real example?")
        suggestions.append("So sánh với các giải pháp khác" if vi else "Compare with alternatives")
    elif is_list:
        suggestions.append("Phân tích chi tiết hơn từng mục" if vi else "Analyze each item in detail")
        suggestions.append("Cái nào quan trọng nhất?" if vi else "Which one is most important?")
    else:
        # Context-aware: use extracted topics for specific follow-ups
        if topics and len(topics) >= 2:
            suggestions.append(f"{topics[0]} chi tiết hơn" if vi else f"More about {topics[0]}")
            suggestions.append(f"So sánh {topics[0]} và {topics[1]}" if vi else f"Compare {topics[0]} vs {topics[1]}")
        else:
            suggestions.append("Giải thích thêm chi tiết" if vi else "Explain in more detail")
            suggestions.append("Có ví dụ cụ thể không?" if vi else "Any specific examples?")

    # Fill up to 3
    filler = [
        ("Tóm tắt ngắn gọn hơn" if vi else "Summarize more concisely"),
        ("Áp dụng vào thực tế như thế nào?" if vi else "How to apply in practice?"),
        ("Có nguồn tham khảo nào không?" if vi else "Any references?"),
    ]
    for f in filler:
        if len(suggestions) >= 3:
            break
        if f not in suggestions:
            suggestions.append(f)

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
    - User explicitly asks to search/look up something, OR
    - Message asks a factual/knowledge question (broad match for accuracy)
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

    # Factual/knowledge questions — broad match for accuracy
    _FACTUAL_VI = [
        "là gì", "là ai", "ở đâu", "bao nhiêu", "khi nào", "tại sao",
        "như thế nào", "có bao nhiêu", "danh sách", "top ", "best ",
        "nên dùng", "nên chọn", "recommend", "gợi ý", "xu hướng",
        "công nghệ", "framework", "library", "tool", "phần mềm",
        "cách dùng", "hướng dẫn", "tutorial", "documentation",
        "lịch sử", "nguồn gốc", "thống kê", "số liệu", "data",
    ]
    _FACTUAL_EN = [
        "what is", "who is", "where is", "how many", "when did",
        "why does", "how does", "how to", "list of", "top ",
        "best ", "should i", "recommend", "trending", "technology",
        "statistics", "data ", "history of", "comparison",
    ]
    if any(p in msg_lower for p in _FACTUAL_VI + _FACTUAL_EN):
        return True

    # If message is a question (ends with ?) — likely benefits from web data
    if message.strip().endswith('?'):
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
    request_id = uuid.uuid4().hex[:12]
    stream_backend = "fastapi"
    stream_contract_version = STREAM_CONTRACT_VERSION
    record_stream_start(backend=stream_backend, request_id=request_id)
    logger.info(f"[SSE:{request_id}] Incoming stream request")

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

    # ── Validate images for vision models ──
    MAX_IMAGES = 5
    MAX_IMAGE_LEN = 15 * 1024 * 1024  # ~10MB raw ≈ 14MB base64
    images = None
    if body.images:
        validated = [
            img for img in body.images[:MAX_IMAGES]
            if isinstance(img, str) and img.startswith('data:image/') and len(img) <= MAX_IMAGE_LEN
        ]
        images = validated or None
        if images:
            logger.info(f"[STREAM] {len(images)} image(s) attached for vision")

    if not message:
        return StreamingResponse(
            iter([_sse("error", {"error": "Empty message"}, request_id=request_id)]),
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

    # ── Image orchestration (pre-compute intent before streaming) ────
    # Done OUTSIDE the async generator so we can use the sync orchestrator API.
    # If image was generated, the generator only emits image SSE events.
    _image_orch_events: list[dict] = []
    _image_orch_done = False
    _image_pipeline_used = "legacy"
    _original_message_for_orch = body.message  # pre-MCP/RAG message

    enable_image_gen = getattr(body, "enable_image_gen", True)
    if enable_image_gen and body.agent_mode == "off":
        try:
            # ── New pipeline (feature-flagged) ────────────────────────
            if use_new_image_orchestrator():
                new_svc = get_new_orchestration_service()
                if new_svc is not None:
                    _session_id = get_session_id(request)
                    for evt in new_svc.handle_stream(
                        message    = _original_message_for_orch,
                        session_id = _session_id,
                        language   = language,
                        tools      = tools,
                        quality    = getattr(body, "image_quality", "auto"),
                    ):
                        _image_orch_events.append(evt)
                    if _image_orch_events and _image_orch_events[-1]["event"] == "image_gen_result":
                        _image_orch_done = True
                        _image_pipeline_used = "new"

            # ── Legacy pipeline (default or fallback) ─────────────────
            if not _image_orch_done:
                _orch = get_image_orchestrator_for_session(request)
                if _orch is not None:
                    _image_orch_events = []  # reset if new pipeline yielded partial events
                    for evt in _orch.handle_stream(
                        message  = _original_message_for_orch,
                        language = language,
                        tools    = tools,
                    ):
                        _image_orch_events.append(evt)
                    if _image_orch_events and _image_orch_events[-1]["event"] == "image_gen_result":
                        _image_orch_done = True
                        _image_pipeline_used = "legacy"
        except Exception as _orch_stream_err:
            logger.warning(f"[Stream] Orchestrator error (fallback to LLM): {_orch_stream_err}")
            _image_orch_events = []

    async def event_generator() -> AsyncGenerator[str, None]:
        import time as _time
        try:
            def _emit(event: str, payload: dict) -> str:
                return _sse(event, payload, request_id=request_id)

            # ── Image generation path ──────────────────────────────────
            if _image_orch_done:
                # Enrich the final result event with extra metadata
                _last_data = _image_orch_events[-1]["data"]
                _provider = _last_data.get("provider", "")
                _is_local = _provider.lower() in ("comfyui", "stable-diffusion", "sd-webui")
                _last_data.setdefault("pipeline", _image_pipeline_used)
                _last_data.setdefault("request_kind", _last_data.get("intent", "generate"))
                _last_data.setdefault("provider_selected", _provider)
                _last_data.setdefault("used_local_backend", _is_local)
                _last_data.setdefault("used_remote_backend", bool(_provider) and not _is_local)
                _last_data.setdefault("used_previous_image_context",
                                      _last_data.get("intent", "") in ("edit", "followup_edit"))

                for evt in _image_orch_events:
                    yield _emit(evt["event"], evt["data"])
                # Emit a 'complete' event so the frontend knows the stream ended
                yield _emit("complete", {
                    "full_response": _last_data.get("response_text", ""),
                    "model":         model,
                    "context":       context,
                    "image_result":  _last_data,
                    "streaming":     True,
                    "stream_contract_version": stream_contract_version,
                    "request_id":    request_id,
                })
                return

            # Emit intermediate image_gen_start/status events even if we ultimately
            # fell back (so the frontend can show a "checking…" indicator)
            for evt in _image_orch_events:
                if evt["event"] in ("image_gen_start", "image_gen_status"):
                    yield _emit(evt["event"], evt["data"])

            # ── Early RAG metadata event (before any tokens) ──
            if rag.chunk_count > 0:
                yield _emit("rag_context", {
                    "chunk_count": rag.chunk_count,
                    "citations": rag.citations,
                })

            _stream_start = _time.monotonic()

            yield _emit("metadata", {
                "model": model,
                "context": context,
                "deep_thinking": deep_thinking or is_multi_thinking,
                "thinking_mode": thinking_mode,
                "stream_backend": stream_backend,
                "stream_contract_version": stream_contract_version,
                "web_search": _search_performed,
                "streaming": True,
                "timestamp": datetime.now().isoformat(),
            })

            full_response = ""
            chunk_count = 0
            _first_chunk_time = None
            _est_tokens = 0
            _fallback_used = False

            if is_multi_thinking:
                # ── 4-Agents Coordinated Reasoning (streamed via SSE) ──
                yield _emit("thinking_start", {"mode": "multi-thinking", "label": "4-Agents Reasoning"})

                try:
                    import asyncio as _asyncio
                    import queue as _queue
                    import threading as _threading

                    from app.services.reasoning_service import get_reasoning_service
                    from app.services.ai_service import AIService
                    reasoning_svc = get_reasoning_service(ai_service=AIService())

                    # Thread + queue pattern — reasoning has blocking sync API calls
                    # so asyncio.create_task would block the event loop
                    _progress_q = _queue.Queue()
                    _DONE = '__DONE__'
                    _ERROR = '__ERROR__'

                    def _run_reasoning():
                        try:
                            r = reasoning_svc.coordinate_reasoning_sync(
                                message=message,
                                context=context,
                                max_rounds=3,
                                images=images,
                                progress_callback=lambda msg: _progress_q.put(msg),
                            )
                            _progress_q.put((_DONE, r))
                        except Exception as exc:
                            _progress_q.put((_ERROR, exc))

                    _t = _threading.Thread(target=_run_reasoning, daemon=True)
                    _t.start()

                    result = None
                    step_idx = 0
                    while True:
                        try:
                            item = await _asyncio.to_thread(
                                _progress_q.get, True, 15  # block=True, timeout=15
                            )
                        except Exception:
                            # Queue.Empty or timeout → SSE keepalive
                            yield ": keepalive\n\n"
                            if not _t.is_alive() and _progress_q.empty():
                                break
                            continue

                        if isinstance(item, tuple) and len(item) == 2:
                            if item[0] == _DONE:
                                result = item[1]
                                break
                            elif item[0] == _ERROR:
                                raise item[1]

                        # Dict items = streamed tokens (with trajectory ID)
                        if isinstance(item, dict) and item.get("type") == "token":
                            yield _emit("thinking", {
                                "step": item.get("text", ""),
                                "step_index": step_idx,
                                "is_reasoning_chunk": True,
                                "trajectory_id": item.get("tid", ""),
                            })
                        else:
                            # String items = status headers / markers
                            step_text = str(item).strip()
                            if step_text:
                                step_idx += 1
                                yield _emit("thinking", {
                                    "step": step_text,
                                    "step_index": step_idx,
                                    "is_reasoning_chunk": False,
                                })

                    _t.join(timeout=5)

                    if result is None:
                        raise RuntimeError("Reasoning returned no result")

                    yield _emit("thinking_end", {
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
                        yield _emit("chunk", {"content": chunk, "chunk_index": chunk_count})

                except Exception as e:
                    logger.error(f"[SSE:{request_id}] 4-Agents reasoning failed, fallback: {e}")
                    _fallback_used = True
                    yield _emit("thinking_end", {"summary": "Fallback to standard", "duration_ms": 0})
                    # Fallback to standard deep-thinking stream
                    for chunk in chatbot.chat_stream(
                        message=message, model=model, context=context,
                        deep_thinking=True, history=history,
                        memories=memories or None, language=language,
                        custom_prompt=custom_prompt, images=images,
                    ):
                        if chunk:
                            if _first_chunk_time is None:
                                _first_chunk_time = _time.monotonic()
                            full_response += chunk
                            chunk_count += 1
                            yield _emit("chunk", {"content": chunk, "chunk_index": chunk_count})
                    _est_tokens = max(1, int(len(full_response) * 0.75))
            else:
                # ── Standard streaming (with thinking support) ──
                use_thinking = thinking_mode != 'instant'
                think_parser = ThinkTagParser() if use_thinking else None
                category = detect_category(message) if use_thinking else ""
                thinking_steps_text = []
                thinking_started = False
                thinking_ended = False
                has_model_reasoning = False

                for chunk in chatbot.chat_stream(
                    message=message,
                    model=model,
                    context=context,
                    deep_thinking=deep_thinking,
                    history=history,
                    memories=memories or None,
                    language=language,
                    custom_prompt=custom_prompt,
                    images=images,
                ):
                    if not chunk:
                        continue

                    if _first_chunk_time is None:
                        _first_chunk_time = _time.monotonic()

                    # Handle native reasoning_content (Grok, DeepSeek R1, etc.)
                    if chunk.startswith(REASONING_PREFIX):
                        reasoning_text = chunk[len(REASONING_PREFIX):]
                        if reasoning_text and use_thinking:
                            if not thinking_started:
                                thinking_started = True
                                has_model_reasoning = True
                                yield _emit("thinking_start", {
                                    "category": category,
                                    "timestamp": datetime.now().isoformat(),
                                })
                            thinking_steps_text.append(reasoning_text)
                            yield _emit("thinking", {
                                "step": reasoning_text,
                                "category": "model_reasoning",
                                "is_reasoning_chunk": True,
                            })
                        continue

                    # Parse <think> tags from model output
                    if think_parser:
                        segments = think_parser.feed(chunk)
                        for is_thinking, text in segments:
                            if is_thinking:
                                if not thinking_started:
                                    thinking_started = True
                                    yield _emit("thinking_start", {
                                        "category": category,
                                        "timestamp": datetime.now().isoformat(),
                                    })
                                thinking_steps_text.append(text)
                                yield _emit("thinking", {
                                    "step": text,
                                    "category": category,
                                    "is_reasoning_chunk": True,
                                })
                            else:
                                # Regular content — end thinking if active
                                if thinking_started and not thinking_ended:
                                    thinking_ended = True
                                    _thinking_dur = round((_time.monotonic() - _stream_start) * 1000)
                                    thinking_summary = generate_thinking_summary(message, category, language)
                                    yield _emit("thinking_end", {
                                        "summary": thinking_summary,
                                        "steps": thinking_steps_text,
                                        "category": category,
                                        "duration_ms": _thinking_dur,
                                    })

                                full_response += text
                                chunk_count += 1
                                yield _emit("chunk", {"content": text, "chunk_index": chunk_count})
                    else:
                        # No thinking parser (instant mode) — pass through
                        full_response += chunk
                        chunk_count += 1
                        yield _emit("chunk", {"content": chunk, "chunk_index": chunk_count})

                # Flush remaining buffer from think parser
                if think_parser:
                    for is_thinking, text in think_parser.flush():
                        if is_thinking:
                            thinking_steps_text.append(text)
                            yield _emit("thinking", {
                                "step": text,
                                "category": category,
                                "is_reasoning_chunk": True,
                            })
                        else:
                            full_response += text
                            chunk_count += 1
                            yield _emit("chunk", {"content": text, "chunk_index": chunk_count})

                # Close thinking if still open (model didn't close </think>)
                if thinking_started and not thinking_ended:
                    _thinking_dur = round((_time.monotonic() - _stream_start) * 1000)
                    thinking_summary = generate_thinking_summary(message, category, language)
                    yield _emit("thinking_end", {
                        "summary": thinking_summary,
                        "steps": thinking_steps_text,
                        "category": category,
                        "duration_ms": _thinking_dur,
                    })

                _est_tokens = max(1, int(len(full_response) * 0.75))

            _elapsed = _time.monotonic() - _stream_start
            _ttfc = (_first_chunk_time - _stream_start) if _first_chunk_time else _elapsed

            # Determine effective max_tokens for the final output
            if is_multi_thinking:
                _max_tokens = 4096  # synthesis step limit
            else:
                _cfg = getattr(chatbot, 'registry', None)
                if _cfg:
                    _mc = _cfg.get_config(model)
                    _max_tokens = (_mc.max_tokens_deep if deep_thinking else _mc.max_tokens) if _mc else 2000
                else:
                    _max_tokens = 2000 if deep_thinking else 1000

            yield _emit("complete", build_complete_event_payload(
                full_response=full_response,
                model=model,
                context=context,
                deep_thinking=deep_thinking or is_multi_thinking,
                thinking_mode=thinking_mode,
                chunk_count=chunk_count,
                thinking_summary="",
                thinking_steps_text=[],
                thinking_duration=0,
                elapsed_time=_elapsed,
                time_to_first_chunk=_ttfc,
                tokens=_est_tokens,
                max_tokens=_max_tokens,
                request_id=request_id,
            ))
            record_stream_complete(
                backend=stream_backend,
                request_id=request_id,
                elapsed_s=_elapsed,
                time_to_first_chunk_s=_ttfc,
                chunk_count=chunk_count,
                tokens=_est_tokens,
                max_tokens=_max_tokens,
                fallback_used=_fallback_used,
            )
            logger.info(
                f"[SSE:{request_id}] complete model={model} chunks={chunk_count} "
                f"tokens={_est_tokens}/{_max_tokens} elapsed={_elapsed:.3f}s"
            )

            # Generate follow-up suggestions (lightweight, non-blocking)
            try:
                suggestions = _generate_suggestions(message, full_response, language)
                if suggestions:
                    yield _emit("suggestions", {"items": suggestions})
            except Exception:
                pass  # Non-critical, skip silently

            if rag.citations:
                yield _emit("citations", {"citations": rag.citations})

        except GeneratorExit:
            logger.info(f"[SSE:{request_id}] Client disconnected")
        except Exception as e:
            logger.error(f"[SSE:{request_id}] Streaming error: {e}")
            record_stream_error(backend=stream_backend, request_id=request_id, error=str(e))
            yield _sse("error", {"error": str(e)}, request_id=request_id)

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


@router.get("/chat/stream/metrics")
async def stream_metrics():
    """Return in-memory stream telemetry snapshot."""
    return get_stream_metrics_snapshot()
