"""
Streaming routes: /chat/stream - SSE endpoint for real-time chat responses

Supports live thinking display (like ChatGPT) with real-time reasoning steps
streamed before the actual response.
"""
import json
import os
import uuid
import time
from datetime import datetime
from pathlib import Path
import sys
from flask import Blueprint, request, session, Response
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import MEMORY_DIR
from core.extensions import MONGODB_ENABLED, logger
from core.chatbot_v2 import get_chatbot
from core.stream_metrics import (
    get_stream_metrics_snapshot,
    record_stream_complete,
    record_stream_error,
    record_stream_start,
)
from core.streaming import StreamingChatHandler, StreamEvent
from core.stream_contract import STREAM_CONTRACT_VERSION, build_complete_event_payload, with_request_id
from core.thinking_generator import (
    ThinkTagParser, detect_category,
    generate_thinking_summary, REASONING_PREFIX
)

# Check MCP availability
MCP_AVAILABLE = False
try:
    from src.handlers.mcp_handler import inject_code_context, get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    pass

stream_bp = Blueprint('stream', __name__)


# ── Auto web-search detection ────────────────────────────────────────

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


def _build_complete_event_payload(
    *,
    full_response: str,
    model: str,
    context: str,
    deep_thinking: bool,
    thinking_mode: str,
    chunk_count: int,
    thinking_summary: str,
    thinking_steps_text: list,
    thinking_duration: int,
    elapsed_time: float,
    tokens: int,
    max_tokens: int,
    request_id: str | None = None,
) -> dict:
    """Compatibility wrapper around shared contract helper."""
    return build_complete_event_payload(
        full_response=full_response,
        model=model,
        context=context,
        deep_thinking=deep_thinking,
        thinking_mode=thinking_mode,
        chunk_count=chunk_count,
        thinking_summary=thinking_summary,
        thinking_steps_text=thinking_steps_text,
        thinking_duration=thinking_duration,
        elapsed_time=elapsed_time,
        tokens=tokens,
        max_tokens=max_tokens,
        request_id=request_id,
    )


def _needs_web_search(message: str, tools: list) -> bool:
    """Detect if the message needs web search for accurate real-time data."""
    if "google-search" in tools or "deep-research" in tools:
        return True
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in _SEARCH_KEYWORDS):
        return True
    if any(p in msg_lower for p in _REALTIME_PATTERNS_VI + _REALTIME_PATTERNS_EN):
        return True
    return False


def _run_web_search(query: str, engine: str = "google") -> str:
    """
    Web search. Uses SerpAPI when SERPAPI_API_KEY is set; falls back to Google CSE.
    engine: 'google' (default), 'bing', 'baidu'
    """
    import requests as _req
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    serpapi_key = os.getenv("SERPAPI_API_KEY", "")

    # ── SerpAPI (primary) ──────────────────────────────────────────────
    if serpapi_key:
        try:
            resp = _req.get("https://serpapi.com/search.json", params={
                "engine": engine,
                "q": query,
                "api_key": serpapi_key,
                "num": 5,
            }, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("organic_results", [])
                if items:
                    label = {"google": "Google", "bing": "Bing", "baidu": "Baidu"}.get(engine, engine.title())
                    parts = []
                    for item in items[:5]:
                        title = item.get("title", "")
                        snippet = item.get("snippet", item.get("description", ""))
                        link = item.get("link", "")
                        parts.append(f"**{title}**\n{snippet}\n🔗 {link}")
                    return f"🔍 **{label} Search — Kết quả thực tế:**\n\n" + "\n\n---\n\n".join(parts)
        except Exception as e:
            logger.warning(f"[WebSearch:SerpAPI] Error: {e}")

    # ── Google Custom Search (fallback) ────────────────────────────────
    api_key_1 = os.getenv("GOOGLE_SEARCH_API_KEY_1", "")
    api_key_2 = os.getenv("GOOGLE_SEARCH_API_KEY_2", "")
    cse_id = os.getenv("GOOGLE_CSE_ID", "")

    if not api_key_1 or not cse_id:
        logger.warning("[WebSearch] Missing all search credentials")
        return ""

    url = "https://www.googleapis.com/customsearch/v1"
    s = _req.Session()
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503])
    s.mount("https://", HTTPAdapter(max_retries=retry))

    for api_key in [api_key_1, api_key_2]:
        if not api_key:
            continue
        try:
            resp = s.get(url, params={
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
                continue
            else:
                logger.warning(f"[WebSearch] HTTP {resp.status_code}")
                return ""
        except Exception as e:
            logger.warning(f"[WebSearch] Error: {e}")
            continue

    return ""


@stream_bp.route('/chat/stream', methods=['POST', 'GET'])
def chat_stream():
    """
    Streaming chat endpoint using Server-Sent Events (SSE)
    
    Supports both POST (preferred) and GET (for simple testing)
    
    Request Body (POST) or Query Params (GET):
        - message: User message (required)
        - model: AI model to use (default: 'grok')
        - context: Conversation context (default: 'casual')
        - deep_thinking: Enable detailed reasoning (default: false)
        - language: Response language (default: 'vi')
        - custom_prompt: Custom system prompt (optional)
        - memory_ids: List of memory IDs to include (optional)
    
    Returns:
        SSE stream with events:
        - metadata: Initial metadata about the request
        - chunk: Response chunks as they arrive
        - complete: Final event with full response
        - error: Error event if something fails
    """
    try:
        request_id = uuid.uuid4().hex[:12]
        stream_backend = "flask"
        stream_contract_version = STREAM_CONTRACT_VERSION
        record_stream_start(backend=stream_backend, request_id=request_id)
        logger.info(f"[SSE:{request_id}] Incoming stream request")

        # Parse request
        if request.method == 'POST':
            if request.content_type and 'application/json' in request.content_type:
                data = request.json or {}
            else:
                data = request.form.to_dict()
                # Parse JSON fields
                for key in ['memory_ids', 'history', 'mcp_selected_files']:
                    if key in data:
                        try:
                            data[key] = json.loads(data[key])
                        except:
                            data[key] = []
        else:
            # GET request
            data = request.args.to_dict()
        
        message = data.get('message', '')
        model = data.get('model', 'grok')
        context = data.get('context', 'casual')
        deep_thinking = str(data.get('deep_thinking', 'false')).lower() == 'true'
        language = data.get('language', 'vi')
        custom_prompt = data.get('custom_prompt', '')
        memory_ids = data.get('memory_ids', [])
        mcp_selected_files = data.get('mcp_selected_files', [])
        history = data.get('history')

        # Map thinking_mode (from frontend) to backend behavior
        thinking_mode = data.get('thinking_mode', 'auto')
        if thinking_mode in ('thinking', 'deep', 'multi-thinking'):
            deep_thinking = True
        elif thinking_mode in ('instant', 'auto'):
            # auto: parse <think> tags if model produces them, but don't force
            # instant: no thinking at all
            deep_thinking = False
        
        # Extract images for vision models (base64 data URLs from frontend)
        images = data.get('images', [])
        if images and not isinstance(images, list):
            images = []
        # Validate and cap images (max 5 images, each max ~10MB base64)
        MAX_IMAGES = 5
        MAX_IMAGE_LEN = 15 * 1024 * 1024  # ~10MB raw ≈ 14MB base64
        validated_images = []
        for img in (images or [])[:MAX_IMAGES]:
            if isinstance(img, str) and img.startswith('data:image/') and len(img) <= MAX_IMAGE_LEN:
                validated_images.append(img)
        images = validated_images if validated_images else None
        
        if images:
            logger.info(f"[STREAM] {len(images)} image(s) attached for vision")
        
        if not message:
            return Response(
                StreamEvent(
                    event="error",
                    data=json.dumps(with_request_id({"error": "Empty message"}, request_id), ensure_ascii=False)
                ).format(),
                mimetype='text/event-stream',
                status=400
            )
        
        # Ensure session
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        # MCP Integration
        if MCP_AVAILABLE:
            try:
                mcp_client = get_mcp_client()
                if mcp_client and mcp_client.enabled:
                    message = inject_code_context(message, mcp_client, mcp_selected_files)
            except Exception as e:
                logger.warning(f"[MCP] Error injecting context: {e}")
        
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        
        # Load memories
        memories = []
        if memory_ids:
            for mem_id in memory_ids:
                memory_file = MEMORY_DIR / f"{mem_id}.json"
                if memory_file.exists():
                    try:
                        with open(memory_file, 'r', encoding='utf-8') as f:
                            memories.append(json.load(f))
                    except Exception as e:
                        logger.error(f"Error loading memory {mem_id}: {e}")
        
        # ── Tool execution (auto web search) ──────────────────────────
        tools = data.get('tools', [])
        if isinstance(tools, str):
            try:
                tools = json.loads(tools)
            except Exception:
                tools = []
        _search_performed = False

        if _needs_web_search(data.get('message', message), tools):
            try:
                search_results = _run_web_search(data.get('message', message))
                if search_results:
                    _search_performed = True
                    message = (
                        f"{message}\n\n"
                        f"---\n"
                        f"📋 DỮ LIỆU THỰC TẾ TỪ WEB (sử dụng thông tin này để trả lời chính xác):\n"
                        f"{search_results}\n"
                        f"---\n"
                        f"Hãy trả lời dựa trên dữ liệu web ở trên. Nếu dữ liệu có ngày/giờ cụ thể, hãy trích dẫn."
                    )
                    logger.info(f"[Stream] Auto web search triggered for: {data.get('message', '')[:60]}")
            except Exception as e:
                logger.warning(f"[Stream] Web search failed: {e}")

        # ── SauceNAO reverse image search ──
        if 'saucenao' in tools:
            import re as _re
            _img_urls = _re.findall(r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)\S*', data.get('message', ''), _re.IGNORECASE)
            try:
                from core.tools import saucenao_search_tool
                if _img_urls:
                    _sauce = saucenao_search_tool(image_url=_img_urls[0])
                elif images:
                    import base64 as _b64
                    _first = images[0]
                    if ',' in _first:
                        _first = _first.split(',', 1)[1]
                    _sauce = saucenao_search_tool(image_data=_b64.b64decode(_first))
                else:
                    _sauce = ""
                if _sauce:
                    message = f"{message}\n\n---\n{_sauce}\n---\nHãy tổng hợp kết quả tìm kiếm ảnh ở trên để trả lời."
                    logger.info("[Stream] SauceNAO search completed")
            except Exception as e:
                logger.warning(f"[Stream] SauceNAO failed: {e}")

        # ── SerpAPI — Google Lens / Reverse Image ──
        if 'serpapi-reverse-image' in tools:
            import re as _re
            _img_urls = _re.findall(r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)\S*', data.get('message', ''), _re.IGNORECASE)
            try:
                from core.tools import serpapi_reverse_image
                if _img_urls:
                    _lens_result = serpapi_reverse_image(_img_urls[0])
                elif images:
                    _lens_result = "❌ Google Lens cần URL ảnh (http/https). Vui lòng paste URL ảnh vào tin nhắn."
                else:
                    _lens_result = ""
                if _lens_result:
                    message = f"{message}\n\n---\n{_lens_result}\n---\nHãy phân tích và tổng hợp kết quả tìm kiếm ảnh trên."
                    logger.info("[Stream] Google Lens search completed")
            except Exception as e:
                logger.warning(f"[Stream] SerpAPI reverse image failed: {e}")

        # ── SerpAPI — Bing Search ──
        if 'serpapi-bing' in tools:
            try:
                _bing_results = _run_web_search(data.get('message', message), engine='bing')
                if _bing_results:
                    _search_performed = True
                    message = (
                        f"{message}\n\n---\n"
                        f"📋 KẾT QUẢ BING SEARCH:\n{_bing_results}\n---\n"
                        f"Hãy trả lời dựa trên dữ liệu Bing ở trên."
                    )
                    logger.info("[Stream] Bing search completed")
            except Exception as e:
                logger.warning(f"[Stream] Bing search failed: {e}")

        # ── SerpAPI — Baidu Search ──
        if 'serpapi-baidu' in tools:
            try:
                _baidu_results = _run_web_search(data.get('message', message), engine='baidu')
                if _baidu_results:
                    _search_performed = True
                    message = (
                        f"{message}\n\n---\n"
                        f"📋 KẾT QUẢ BAIDU SEARCH:\n{_baidu_results}\n---\n"
                        f"Hãy trả lời dựa trên dữ liệu Baidu ở trên."
                    )
                    logger.info("[Stream] Baidu search completed")
            except Exception as e:
                logger.warning(f"[Stream] Baidu search failed: {e}")

        # ── SerpAPI — Image Search ──
        if 'serpapi-images' in tools:
            try:
                from core.tools import serpapi_image_search
                _img_search_result = serpapi_image_search(data.get('message', message))
                if _img_search_result:
                    message = (
                        f"{message}\n\n---\n"
                        f"📋 KẾT QUẢ IMAGE SEARCH:\n{_img_search_result}\n---\n"
                        f"Hãy liệt kê và mô tả các ảnh tìm được."
                    )
                    logger.info("[Stream] SerpAPI image search completed")
            except Exception as e:
                logger.warning(f"[Stream] SerpAPI image search failed: {e}")

        # ── Auto reverse-image search when images attached + search intent ──
        _IMAGE_SEARCH_PATTERNS = [
            'tìm nguồn', 'tìm ảnh', 'nguồn ảnh', 'tìm gốc', 'reverse image',
            'find source', 'image source', 'where is this', 'tìm tác giả',
            'ai vẽ', 'tác giả', 'author', 'original', 'find this image',
            'ảnh này từ đâu', 'ảnh gốc', 'tìm kiếm ảnh',
        ]
        _raw_msg = data.get('message', '').lower()
        _wants_image_search = images and any(p in _raw_msg for p in _IMAGE_SEARCH_PATTERNS)

        if _wants_image_search:
            try:
                from core.tools import reverse_image_search
                _ris = reverse_image_search(image_data_url=images[0])
                if _ris.get("summary"):
                    message = (
                        f"{message}\n\n---\n"
                        f"📋 KẾT QUẢ TÌM KIẾM ẢNH (reverse image search):\n{_ris['summary']}\n---\n"
                        f"Hãy phân tích kết quả tìm kiếm ảnh ở trên. Đưa ra nguồn gốc, tác giả (nếu có), "
                        f"và các thông tin chi tiết. Kèm link ảnh gốc nếu tìm được."
                    )
                    _search_performed = True
                    logger.info("[Stream] Auto reverse-image search completed")
            except Exception as e:
                logger.warning(f"[Stream] Auto reverse-image search failed: {e}")

        # Create streaming generator
        def generate_stream():
            try:
                thinking_start = time.time()

                def _emit(event: str, payload: dict) -> str:
                    return StreamEvent(
                        event=event,
                        data=json.dumps(with_request_id(payload, request_id), ensure_ascii=False)
                    ).format()
                
                # Send metadata
                yield _emit("metadata", {
                    "model": model,
                    "context": context,
                    "deep_thinking": deep_thinking,
                    "thinking_mode": thinking_mode,
                    "stream_backend": stream_backend,
                    "stream_contract_version": stream_contract_version,
                    "web_search": _search_performed,
                    "streaming": True,
                    "timestamp": datetime.now().isoformat()
                })
                
                # ── Thinking Phase ──
                # Real AI reasoning via <think> tags or native reasoning_content
                category = detect_category(message)
                thinking_steps_text = []
                thinking_summary = ""
                thinking_duration = 0
                thinking_started = False
                thinking_ended = False

                # For instant mode, skip thinking entirely
                use_thinking = thinking_mode != 'instant'
                is_multi_thinking = thinking_mode == 'multi-thinking'
                
                # ── Response Phase (with integrated thinking) ──
                full_response = ""
                chunk_count = 0
                has_model_reasoning = False
                fallback_used = False

                # ── 4-Agents Coordinated Reasoning ──
                if is_multi_thinking:
                    yield _emit("thinking_start", {
                        "mode": "multi-thinking",
                        "label": "4-Agents Reasoning",
                        "category": category,
                        "timestamp": datetime.now().isoformat()
                    })

                    try:
                        import queue as _queue
                        import threading as _threading

                        from app.services.reasoning_service import get_reasoning_service
                        from app.services.ai_service import AIService
                        reasoning_svc = get_reasoning_service(ai_service=AIService())

                        # Use thread + queue so progress events stream in real-time
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
                                item = _progress_q.get(timeout=15)
                            except _queue.Empty:
                                # SSE keepalive comment to prevent connection timeout
                                yield ": keepalive\n\n"
                                continue

                            if isinstance(item, tuple) and len(item) == 2:
                                if item[0] == _DONE:
                                    result = item[1]
                                    break
                                elif item[0] == _ERROR:
                                    raise item[1]

                            # Real progress event from reasoning service
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
                                    thinking_steps_text.append(step_text)
                                    yield _emit("thinking", {
                                        "step": step_text,
                                        "step_index": step_idx,
                                        "is_reasoning_chunk": False,
                                    })

                        # Ensure thread is joined
                        _t.join(timeout=5)

                        if result is None:
                            raise RuntimeError("Reasoning returned no result")

                        thinking_duration = round(result.reasoning_time * 1000)
                        yield _emit("thinking_end", {
                            "summary": f"{result.total_rounds} rounds · {result.total_trajectories} trajectories · {result.reasoning_time:.1f}s",
                            "duration_ms": thinking_duration,
                            "rounds": result.total_rounds,
                            "trajectories": result.total_trajectories,
                            "steps": thinking_steps_text,
                            "category": category,
                        })

                        full_response = result.final_answer
                        _est_tokens = result.total_tokens or max(1, int(len(full_response) * 0.75))

                        # Stream the final answer in chunks for progressive rendering
                        chunk_size = 80
                        for i in range(0, len(full_response), chunk_size):
                            text = full_response[i:i + chunk_size]
                            chunk_count += 1
                            yield _emit("chunk", {"content": text, "chunk_index": chunk_count})

                    except Exception as e:
                        logger.error(f"[SSE:{request_id}] 4-Agents reasoning failed, fallback: {e}")
                        fallback_used = True
                        yield _emit("thinking_end", {
                            "summary": "Fallback to standard",
                            "duration_ms": 0,
                            "steps": [],
                            "category": category,
                        })
                        # Fallback to standard deep-thinking stream below
                        is_multi_thinking = False

                if not is_multi_thinking:
                    # ── Standard streaming (instant or thinking) ──
                    think_parser = ThinkTagParser() if use_thinking else None

                    # Get streaming response from chatbot
                    for chunk in chatbot.chat_stream(
                        message=message,
                        model=model,
                        context=context,
                        deep_thinking=deep_thinking,
                        history=history,
                        memories=memories if memories else None,
                        language=language,
                        custom_prompt=custom_prompt,
                        images=images
                    ):
                        if not chunk:
                            continue
                        
                        # Handle native reasoning_content (DeepSeek R1, etc.)
                        if chunk.startswith(REASONING_PREFIX):
                            reasoning_text = chunk[len(REASONING_PREFIX):]
                            if reasoning_text and use_thinking:
                                if not thinking_started:
                                    thinking_started = True
                                    has_model_reasoning = True
                                    yield _emit("thinking_start", {
                                        "category": category,
                                        "timestamp": datetime.now().isoformat()
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
                                    # This is reasoning content inside <think>
                                    if not thinking_started:
                                        thinking_started = True
                                        yield _emit("thinking_start", {
                                            "category": category,
                                            "timestamp": datetime.now().isoformat()
                                        })
                                    thinking_steps_text.append(text)
                                    yield _emit("thinking", {
                                        "step": text,
                                        "category": category,
                                        "is_reasoning_chunk": True,
                                    })
                                else:
                                    # Regular response content — end thinking if active
                                    if thinking_started and not thinking_ended:
                                        thinking_ended = True
                                        thinking_duration = round((time.time() - thinking_start) * 1000)
                                        thinking_summary = generate_thinking_summary(message, category, language)
                                        yield _emit("thinking_end", {
                                            "summary": thinking_summary,
                                            "steps": thinking_steps_text,
                                            "category": category,
                                            "duration_ms": thinking_duration,
                                        })
                                    
                                    full_response += text
                                    chunk_count += 1
                                    yield _emit("chunk", {
                                        "content": text,
                                        "chunk_index": chunk_count
                                    })
                        else:
                            # No thinking parser (instant mode) — pass through
                            full_response += chunk
                            chunk_count += 1
                            yield _emit("chunk", {
                                "content": chunk,
                                "chunk_index": chunk_count
                            })
                    
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
                                yield _emit("chunk", {
                                    "content": text,
                                    "chunk_index": chunk_count
                                })
                    
                    # Close thinking if still open (model didn't close </think>)
                    if thinking_started and not thinking_ended:
                        thinking_duration = round((time.time() - thinking_start) * 1000)
                        thinking_summary = generate_thinking_summary(message, category, language)
                        yield _emit("thinking_end", {
                            "summary": thinking_summary,
                            "steps": thinking_steps_text,
                            "category": category,
                            "duration_ms": thinking_duration,
                        })
                
                # Send complete event
                _elapsed = time.time() - thinking_start
                _est_tokens = max(1, int(len(full_response) * 0.75))
                if is_multi_thinking:
                    _max_tokens = 4096
                else:
                    _mc = chatbot.registry.get_config(model) if chatbot.registry else None
                    _max_tokens = (_mc.max_tokens_deep if deep_thinking else _mc.max_tokens) if _mc else 2000
                yield StreamEvent(
                    event="complete",
                    data=json.dumps(_build_complete_event_payload(
                        full_response=full_response,
                        model=model,
                        context=context,
                        deep_thinking=deep_thinking,
                        thinking_mode=thinking_mode,
                        chunk_count=chunk_count,
                        thinking_summary=thinking_summary,
                        thinking_steps_text=thinking_steps_text,
                        thinking_duration=thinking_duration,
                        elapsed_time=_elapsed,
                        tokens=_est_tokens,
                        max_tokens=_max_tokens,
                        request_id=request_id,
                    ))
                ).format()
                record_stream_complete(
                    backend=stream_backend,
                    request_id=request_id,
                    elapsed_s=_elapsed,
                    chunk_count=chunk_count,
                    tokens=_est_tokens,
                    max_tokens=_max_tokens,
                    fallback_used=fallback_used,
                    time_to_first_chunk_s=None,
                )
                logger.info(
                    f"[SSE:{request_id}] complete model={model} chunks={chunk_count} "
                    f"tokens={_est_tokens}/{_max_tokens} elapsed={_elapsed:.3f}s"
                )
                
            except GeneratorExit:
                logger.info(f"[SSE:{request_id}] Client disconnected")
            except Exception as e:
                logger.error(f"[SSE:{request_id}] Streaming error: {e}")
                record_stream_error(backend=stream_backend, request_id=request_id, error=str(e))
                yield StreamEvent(
                    event="error",
                    data=json.dumps(with_request_id({"error": str(e)}, request_id), ensure_ascii=False)
                ).format()
        
        return Response(
            generate_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': '*',
            }
        )
        
    except Exception as e:
        logger.error(f"[SSE] Error before stream init: {e}")
        return Response(
            StreamEvent(event="error", data=json.dumps({"error": str(e)}, ensure_ascii=False)).format(),
            mimetype='text/event-stream',
            status=500
        )


@stream_bp.route('/chat/stream/models', methods=['GET'])
def list_streaming_models():
    """List models that support streaming"""
    from core.chatbot_v2 import get_model_registry
    
    registry = get_model_registry()
    models = []
    
    for name in registry.list_available():
        config = registry.get_config(name)
        if config:
            models.append({
                'name': name,
                'supports_streaming': config.supports_streaming,
                'provider': config.provider.value
            })
    
    return {
        'models': models,
        'streaming_supported': [m['name'] for m in models if m['supports_streaming']]
    }


@stream_bp.route('/chat/stream/metrics', methods=['GET'])
def stream_metrics():
    """Return in-memory stream telemetry snapshot."""
    return get_stream_metrics_snapshot()
