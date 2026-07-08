"""
Streaming routes: /chat/stream - SSE endpoint for real-time chat responses

Supports live thinking display (like ChatGPT) with real-time reasoning steps
streamed before the actual response.
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, request, session

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core import mongo_store
from core.central_router import route_request
from core.central_trace import InMemoryTraceStore, RequestTrace
from core.chatbot_v2 import get_chatbot
from core.config import MEMORY_DIR
from core.config import get_system_prompts as _get_system_prompts
from core.extensions import logger
from core.request_normalizer import normalize_chat_request
from core.skills.applicator import apply_skill_overrides
from core.skills.resolver import resolve_skill
from core.stream_contract import (
    STREAM_CONTRACT_VERSION,
    build_complete_event_payload,
    with_request_id,
)
from core.stream_metrics import (
    get_stream_metrics_snapshot,
    record_stream_complete,
    record_stream_error,
    record_stream_start,
)
from core.streaming import StreamEvent
from core.thinking_generator import (
    REASONING_PREFIX,
    USAGE_SENTINEL,
    ThinkTagParser,
    detect_category,
    generate_thinking_summary,
)

# Check MCP availability
MCP_AVAILABLE = False
try:
    from src.handlers.mcp_handler import get_mcp_client, inject_code_context

    MCP_AVAILABLE = True
except ImportError:
    pass

stream_bp = Blueprint("stream", __name__)
TRACE_STORE = InMemoryTraceStore(max_items=2000)


# ── Auto web-search detection ────────────────────────────────────────

_REALTIME_PATTERNS_VI = [
    "giá",
    "tỷ giá",
    "thời tiết",
    "tin tức",
    "mới nhất",
    "hiện tại",
    "hôm nay",
    "bây giờ",
    "mấy giờ",
    "ngày bao nhiêu",
    "lịch",
    "kết quả",
    "tỉ số",
    "xổ số",
    "chứng khoán",
    "cổ phiếu",
    "bitcoin",
    "crypto",
    "coin",
    "vàng",
    "USD",
    "bao nhiêu tiền",
    "review",
    "đánh giá",
    "so sánh",
    "nên mua",
    "mua ở đâu",
    "ở đâu",
    "địa chỉ",
    "số điện thoại",
    "sự kiện",
    "lịch trình",
    "cập nhật",
    "phiên bản mới",
    "ra mắt",
    "release",
    "công bố",
    "thông báo",
    "biểu đồ",
    "chart",
    "benchmark",
    "xếp hạng model",
    "so sánh model",
    "hiệu năng model",
]
_REALTIME_PATTERNS_EN = [
    "price",
    "weather",
    "news",
    "latest",
    "current",
    "today",
    "right now",
    "stock",
    "bitcoin",
    "crypto",
    "gold price",
    "exchange rate",
    "how much",
    "review",
    "compare",
    "where to buy",
    "address",
    "phone number",
    "schedule",
    "update",
    "new version",
    "release",
    "announcement",
    "score",
    "result",
    "ranking",
    "trending",
    "chart",
    "graph",
    "benchmark",
    "model comparison",
    "leaderboard",
]

# Chart intent detection — triggers chart output instruction when search results injected
_CHART_PATTERNS_VI = [
    "biểu đồ", "chart", "vẽ chart", "tạo chart", "vẽ biểu đồ", "tạo biểu đồ",
    "bar chart", "line chart", "pie chart", "so sánh.*chart", "chart.*so sánh",
]
_CHART_PATTERNS_EN = [
    "chart", "graph", "plot", "bar chart", "line chart", "pie chart",
    "create chart", "make a chart", "draw chart", "visualize", "visualization",
]


def _wants_chart(message: str) -> bool:
    """Return True when the user explicitly asked for a chart/graph."""
    msg_lower = message.lower()
    return any(p in msg_lower for p in _CHART_PATTERNS_VI + _CHART_PATTERNS_EN)
_SEARCH_KEYWORDS = [
    "tìm",
    "search",
    "tra cứu",
    "look up",
    "google",
    "tìm kiếm",
    "find",
    "tìm giúp",
    "check",
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
    has_image: bool | None = None,
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
        has_image=has_image,
    )


def _with_rag_citations(payload: dict, citations: list | None) -> dict:
    """Attach RAG citations to the complete-event payload when present."""
    if citations:
        payload["citations"] = citations
    return payload


def _needs_web_search(message: str, tools: list) -> bool:
    """Detect if the message needs web search for accurate real-time data."""
    if "google-search" in tools or "deep-research" in tools:
        return True
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in _SEARCH_KEYWORDS):
        return True
    return bool(
        any(p in msg_lower for p in _REALTIME_PATTERNS_VI + _REALTIME_PATTERNS_EN)
    )


def _run_web_search(query: str, engine: str = "google") -> str:
    """
    Web search. Uses SerpAPI when SERPAPI_API_KEY is set; falls back to Google CSE.
    engine: 'google' (default), 'bing', 'baidu'
    """
    import requests as _req
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    serpapi_key = os.getenv("SERPAPI_API_KEY", "")

    # 2026-04-29: track which providers we tried so the user sees the
    # actual cascade in the rendered tool result ("SerpAPI → Google CSE").
    _attempted: list[str] = []

    # ── SerpAPI (primary) ───────────────────────────────────────
    if serpapi_key:
        _attempted.append(f"SerpAPI:{engine}")
        try:
            resp = _req.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": engine,
                    "q": query,
                    "api_key": serpapi_key,
                    "num": 5,
                },
                timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("organic_results", [])
                if items:
                    label = {"google": "Google", "bing": "Bing", "baidu": "Baidu"}.get(
                        engine, engine.title()
                    )
                    parts = []
                    for item in items[:5]:
                        title = item.get("title", "")
                        snippet = item.get("snippet", item.get("description", ""))
                        link = item.get("link", "")
                        parts.append(f"**{title}**\n{snippet}\n🔗 {link}")
                    return (
                        f"🪜 _Cascade: SerpAPI:{engine} ✅_\n\n🔍 **{label} Search — Kết quả thực tế:**\n\n"
                        + "\n\n---\n\n".join(parts)
                    )
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
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503])

    with _req.Session() as s:
        s.mount("https://", HTTPAdapter(max_retries=retry))
        for api_key in [api_key_1, api_key_2]:
            if not api_key:
                continue
            _attempted.append("GoogleCSE")
            try:
                resp = s.get(
                    url,
                    params={
                        "key": api_key,
                        "cx": cse_id,
                        "q": query,
                        "num": 5,
                    },
                    timeout=15,
                )
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
                        _trail = " → ".join(_attempted)
                        return (
                            f"🪜 _Cascade: {_trail}_\n\n🔍 **Kết quả tìm kiếm web (real-time):**\n\n"
                            + "\n\n---\n\n".join(parts)
                        )
                elif resp.status_code in (429, 403):
                    continue
                else:
                    logger.warning(f"[WebSearch] HTTP {resp.status_code}")
                    return ""
            except Exception as e:
                logger.warning(f"[WebSearch] Error: {e}")
                continue

    return ""


@stream_bp.route("/chat/stream", methods=["POST", "GET"])
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
        if request.method == "POST":
            if request.content_type and "application/json" in request.content_type:
                data = request.json or {}
            else:
                data = request.form.to_dict()
                # Parse JSON fields
                for key in ["memory_ids", "history", "mcp_selected_files"]:
                    if key in data:
                        try:
                            data[key] = json.loads(data[key])
                        except Exception:
                            data[key] = []
        else:
            # GET request
            data = request.args.to_dict()

        message = data.get("message", "")
        language = data.get("language", "vi")
        memory_ids = data.get("memory_ids", [])
        mcp_selected_files = data.get("mcp_selected_files", [])
        history = data.get("history")

        # ── RAG collection selection (opt-in; default empty) ──────────
        rag_collection_ids = data.get("rag_collection_ids") or []
        if isinstance(rag_collection_ids, str):
            try:
                rag_collection_ids = json.loads(rag_collection_ids)
            except (ValueError, TypeError):
                rag_collection_ids = [
                    c.strip() for c in rag_collection_ids.split(",") if c.strip()
                ]
        if not isinstance(rag_collection_ids, list):
            rag_collection_ids = []
        rag_tenant_id = str(data.get("rag_tenant_id") or "default")

        # Preserve the raw user message before normalization appends
        # asset-context (previously generated images). route_request() must
        # classify the user's actual words, not the augmented string.
        raw_message = message

        # ── Shared request normalization ──────────────────────────────
        # Conversation id extract+validate+bind, image context injection,
        # and history bounding live in core/request_normalizer.py so that
        # /chat (routes/main.py) applies the exact same contract.
        _normalized = normalize_chat_request(data, session, message=message)
        conversation_id = _normalized["conversation_id"]
        if _normalized["conversation_id_bound"]:
            logger.info(f"[SSE:{request_id}] conversation_id={conversation_id}")
        # generated_images / image-context were applied to message in-place.
        message = _normalized["message"]
        if _normalized["image_context_count"]:
            logger.info(
                f"[SSE:{request_id}] Injected {_normalized['image_context_count']} image asset(s) into context"
            )
        # Defensive history cap (frontend already caps; this is depth-in-defense).
        if _normalized["history"] is not None:
            history = _normalized["history"]
        _normalized["generated_images"]

        # ── Runtime Skill Resolution + Application ────────────────────
        skill_overrides = resolve_skill(
            message=message,
            explicit_skill_id=data.get("skill"),
            session_id=session.get("session_id"),
            auto_route=str(data.get("skill_auto_route", "true")).lower() != "false",
        )
        applied = apply_skill_overrides(
            data=data,
            skill_overrides=skill_overrides,
            language=language,
        )
        model = applied.model
        context = applied.context
        thinking_mode = applied.thinking_mode
        deep_thinking = applied.deep_thinking
        custom_prompt = applied.custom_prompt
        tools = applied.tools

        if applied.was_applied:
            logger.info(f"[SSE:{request_id}] Skill applied: {applied.skill_id}")

        route_decision = route_request(raw_message)
        trace = RequestTrace(
            conversation_id=conversation_id or "",
            message_id=(data.get("message_id") or "").strip()
            or f"msg-{uuid.uuid4().hex[:12]}",
            user_input=message,
            selected_pipeline=route_decision.pipeline,
            selected_model=model,
            router_confidence=route_decision.confidence,
        )
        logger.info(
            "[SSE:%s] router decision intent=%s pipeline=%s confidence=%.2f",
            request_id,
            route_decision.intent,
            route_decision.pipeline,
            route_decision.confidence,
        )

        # ── Mongo activity logging (schema v2) ────────────────────────
        # Log the inbound user message + ensure parent conversation exists.
        # Fail-safe: every call returns disabled when Mongo is unavailable
        # and never raises. We do not block streaming on this.
        user_message_id = (
            data.get("message_id") or ""
        ).strip() or f"msg-{uuid.uuid4().hex[:12]}"
        try:
            if conversation_id:
                mongo_store.save_conversation(
                    {
                        "conversation_id": conversation_id,
                        "user_id": session.get("user_id")
                        or session.get("username")
                        or "",
                        "session_id": session.get("session_id") or "",
                    }
                )
            mongo_store.save_message(
                {
                    "message_id": user_message_id,
                    "conversation_id": conversation_id or "",
                    "role": "user",
                    "message_type": "chat",
                    "content": message,
                    "metadata": {
                        "model": model,
                        "context": context,
                        "thinking_mode": thinking_mode,
                        "skill_id": applied.skill_id,
                        "request_id": request_id,
                        "language": language,
                    },
                }
            )
        except Exception as _me:  # noqa: BLE001 — never block streaming
            logger.warning(f"[SSE:{request_id}] mongo log (user message) failed: {_me}")

        # Extract images for vision models (base64 data URLs from frontend)
        images = data.get("images", [])
        if images and not isinstance(images, list):
            images = []
        # Validate and cap images (max 5 images, each max ~10MB base64)
        MAX_IMAGES = 5
        MAX_IMAGE_LEN = 15 * 1024 * 1024  # ~10MB raw ≈ 14MB base64
        validated_images = []
        for img in (images or [])[:MAX_IMAGES]:
            if (
                isinstance(img, str)
                and img.startswith("data:image/")
                and len(img) <= MAX_IMAGE_LEN
            ):
                validated_images.append(img)
        images = validated_images if validated_images else None

        if images:
            logger.info(f"[STREAM] {len(images)} image(s) attached for vision")

        # Extract per-request model parameter overrides
        try:
            _t = data.get("temperature")
            temperature = (
                float(_t) if _t is not None and 0.0 <= float(_t) <= 2.0 else None
            )
        except (TypeError, ValueError):
            temperature = None
        try:
            _td = data.get("temperature_deep")
            temperature_deep = (
                float(_td) if _td is not None and 0.0 <= float(_td) <= 2.0 else None
            )
        except (TypeError, ValueError):
            temperature_deep = None
        try:
            _mt = data.get("max_tokens_deep")
            max_tokens_deep = (
                int(_mt) if _mt is not None and 1 <= int(_mt) <= 131072 else None
            )
        except (TypeError, ValueError):
            max_tokens_deep = None
        try:
            _tp = data.get("top_p")
            top_p = float(_tp) if _tp is not None and 0.0 <= float(_tp) <= 1.0 else None
        except (TypeError, ValueError):
            top_p = None

        if not message:
            return Response(
                StreamEvent(
                    event="error",
                    data=json.dumps(
                        with_request_id({"error": "Empty message"}, request_id),
                        ensure_ascii=False,
                    ),
                ).format(),
                mimetype="text/event-stream",
                status=400,
            )

        # Ensure session
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())

        # MCP Integration
        if MCP_AVAILABLE:
            try:
                mcp_client = get_mcp_client()
                if mcp_client and mcp_client.enabled:
                    message = inject_code_context(
                        message, mcp_client, mcp_selected_files
                    )
                elif applied.prefer_mcp and mcp_client:
                    # Skill prefers MCP context — inject even without user toggle
                    message = inject_code_context(
                        message, mcp_client, mcp_selected_files
                    )
                    logger.info(
                        f"[MCP] Skill '{applied.skill_id}' triggered MCP context injection"
                    )
            except Exception as e:
                logger.warning(f"[MCP] Error injecting context: {e}")

        # ── RAG retrieval (opt-in; gated by RAG_ENABLED + collections) ─
        rag_citations = None
        if rag_collection_ids:
            try:
                from src.rag.service.orchestrator import RAGOrchestrator

                from core.rag_runner import run_rag_coro

                _rag_result = run_rag_coro(
                    RAGOrchestrator().retrieve_for_chat(
                        message=message,
                        custom_prompt=custom_prompt,
                        language=language,
                        tenant_id=rag_tenant_id,
                        collection_ids=[str(c) for c in rag_collection_ids],
                    )
                )
                message = _rag_result.message
                custom_prompt = _rag_result.custom_prompt
                rag_citations = _rag_result.citations
                if _rag_result.chunk_count:
                    logger.info(
                        f"[SSE:{request_id}] RAG injected {_rag_result.chunk_count} chunk(s)"
                    )
            except Exception as e:  # noqa: BLE001 — never block streaming
                logger.warning(f"[RAG] retrieval skipped: {e}")

        session_id = session.get("session_id")
        chatbot = get_chatbot(session_id)

        # Load memories
        memories = []
        if memory_ids:
            import re as _re
            _uuid_re = _re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
            for mem_id in memory_ids:
                if not _uuid_re.match(str(mem_id)):
                    continue
                for _f in MEMORY_DIR.iterdir():
                    if _f.is_file() and _f.suffix == ".json" and _f.stem == mem_id:
                        try:
                            with open(_f, encoding="utf-8") as f:
                                memories.append(json.load(f))
                        except Exception as e:
                            logger.error(f"Error loading memory {mem_id}: {e}")
                        break

        # ── Command detection: /last30days <topic> ──────────────────────
        _raw_text = data.get("message", "").strip()
        if _raw_text.lower().startswith("/last30days"):
            _cmd_topic = _raw_text[len("/last30days") :].strip()
            if _cmd_topic:
                tools = list(set(tools) | {"last30days-research"})
                # Use extracted topic as the message for the tool
                data["message"] = _cmd_topic
                message = _cmd_topic
                logger.info(
                    "[Stream] /last30days command detected, topic=%r", _cmd_topic
                )

        # ── Tool execution (auto web search) ──────────────────────────

        _search_performed = False

        if _needs_web_search(data.get("message", message), tools):
            try:
                _raw_user_msg = data.get("message", message)
                # For chart requests, build a more targeted search query
                _search_query = _raw_user_msg
                if _wants_chart(_raw_user_msg):
                    import re as _re_q
                    # Strip UI instruction words to get the data topic
                    _clean = _re_q.sub(
                        r'\b(tạo|vẽ|tạo ra|cho tôi|giúp tôi|create|make|draw|generate|plot)\b',
                        '', _raw_user_msg, flags=_re_q.IGNORECASE
                    ).strip()
                    _clean = _re_q.sub(r'\b(biểu đồ|chart|graph|visualization)\b', '', _clean, flags=_re_q.IGNORECASE).strip()
                    _search_query = f"{_clean} benchmark comparison 2025" if _clean else _raw_user_msg
                    logger.info("[Stream] Chart search query refined: %r", _search_query[:80])
                search_results = _run_web_search(_search_query)
                if search_results:
                    _search_performed = True
                    _chart_instruction = ""
                    _over_reviewers = bool(data.get("over_reviewers", False))
                    if _wants_chart(_raw_user_msg):
                        if _over_reviewers:
                            _chart_instruction = (
                                "\n4. OVER REVIEWERS MODE — Người dùng muốn xem 3 cách visualize tốt nhất cho dữ liệu này.\n"
                                "Phân tích dữ liệu, hiểu ngữ cảnh (benchmark, market share, trend, comparison, v.v.) rồi "
                                "output CHÍNH XÁC 3 ```chart blocks với 3 loại biểu đồ KHÁC NHAU và PHÙ HỢP NHẤT.\n\n"
                                "NGUYÊN TẮC chọn chart type (dùng đúng các type sau — Chart.js 4.x):\n"
                                "- So sánh trực tiếp → type:\"bar\"\n"
                                "- Bar nằm ngang → type:\"bar\" + options.indexAxis:\"y\"\n"
                                "- Đa chiều/nhiều metric → type:\"radar\"\n"
                                "- Phân phối tỷ lệ → type:\"pie\" hoặc type:\"doughnut\"\n"
                                "- Xu hướng/thời gian → type:\"line\"\n"
                                "- Phân phối tròn → type:\"polarArea\"\n"
                                "TUYỆT ĐỐI KHÔNG dùng type:\"horizontalBar\" (đã bị xóa trong Chart.js 4).\n\n"
                                "Mỗi chart bắt buộc:\n"
                                "- DỮ LIỆU THỰC (không được để 0 hoặc null) — dùng web data > training knowledge\n"
                                "- options.plugins.title.display:true và text mô tả rõ loại\n"
                                "- Màu sắc dark-theme (rgba với alpha 0.75–0.9)\n"
                                "- labels[] và data[] cùng độ dài\n"
                                "- Radar chart: KHÔNG set scales.y — chỉ set scales.r nếu cần\n\n"
                                "Format: 3 khối ```chart riêng biệt, mỗi khối JSON hoàn chỉnh hợp lệ.\n"
                                "Ví dụ format một khối:\n"
                                "```chart\n"
                                '{"type":"bar","data":{"labels":["A","B","C"],"datasets":[{"label":"Score",'
                                '"data":[85,90,78],"backgroundColor":["rgba(99,179,237,0.8)","rgba(154,117,234,0.8)",'
                                '"rgba(72,187,120,0.8)"],"borderWidth":1}]},'
                                '"options":{"plugins":{"title":{"display":true,"text":"Bar Chart — So sánh"}}}}\n'
                                "```\n"
                                "Sau đó là 2 khối chart khác tương tự với type khác nhau."
                            )
                        else:
                            _chart_instruction = (
                                "\n4. QUAN TRỌNG — Người dùng yêu cầu biểu đồ/chart. "
                                "Bắt buộc phải output một ```chart block với DỮ LIỆU THỰC (không được để 0 hoặc null).\n"
                                "Nếu dữ liệu web không có số liệu cụ thể → dùng kiến thức training của bạn "
                                "(benchmark scores, market share, v.v. đã biết). Ưu tiên: web data > training knowledge > ước tính có ghi chú.\n"
                                "Format bắt buộc (JSON hợp lệ, đặt trong code block ```chart):\n"
                                "```chart\n"
                                '{"type":"bar","data":{"labels":[...],"datasets":[{"label":"Benchmark","data":[87.2,88.0,83.7],'
                                '"backgroundColor":["rgba(99,179,237,0.8)","rgba(154,117,234,0.8)","rgba(72,187,120,0.8)"],'
                                '"borderColor":["rgba(99,179,237,1)","rgba(154,117,234,1)","rgba(72,187,120,1)"],"borderWidth":1}]},'
                                '"options":{"plugins":{"title":{"display":true,"text":"Tiêu đề chart"},'
                                '"legend":{"display":true}},"scales":{"y":{"beginAtZero":false,"min":70}}}}\n'
                                "```\n"
                                "Quy tắc: (a) data[] phải là số thực dương; (b) labels[] và data[] phải cùng độ dài; "
                                "(c) chỉ output đúng một ```chart block; (d) nếu có nhiều metrics → dùng nhiều datasets; "
                                "(e) KHÔNG dùng type:\"horizontalBar\" — đã bị xóa, dùng type:\"bar\"+options.indexAxis:\"y\" thay thế."
                            )
                    message = (
                        f"{message}\n\n"
                        f"---\n"
                        f"📋 DỮ LIỆU THỰC TẾ TỪ WEB (sử dụng thông tin này để trả lời chính xác):\n"
                        f"{search_results}\n"
                        f"---\n"
                        f"YÊU CẦU BẮT BUỘC khi trả lời:\n"
                        f"1. Dẫn thông tin từ dữ liệu web trên.\n"
                        f"2. Ghi rõ link nguồn (🔗 URL) ngay sau thông tin liên quan HOẶC gom lại trong mục **Nguồn:** ở cuối — KHÔNG chỉ nhắc tên site.\n"
                        f"3. Nếu dữ liệu có ngày/giờ cụ thể, hãy trích dẫn chính xác."
                        f"{_chart_instruction}"
                    )
                    logger.info(
                        "[Stream] Auto web search triggered for: %s%s",
                        _raw_user_msg[:60],
                        " [+chart×3]" if (_chart_instruction and _over_reviewers) else (" [+chart]" if _chart_instruction else ""),
                    )
            except Exception as e:
                logger.warning(f"[Stream] Web search failed: {e}")

        # ── SauceNAO reverse image search ──
        if "saucenao" in tools:
            import re as _re

            _img_urls = _re.findall(
                r"https?://\S+\.(?:jpg|jpeg|png|gif|webp)\S*",
                data.get("message", ""),
                _re.IGNORECASE,
            )
            try:
                from core.tools import saucenao_search_tool

                if _img_urls:
                    _sauce = saucenao_search_tool(image_url=_img_urls[0])
                elif images:
                    import base64 as _b64

                    _first = images[0]
                    if "," in _first:
                        _first = _first.split(",", 1)[1]
                    _sauce = saucenao_search_tool(image_data=_b64.b64decode(_first))
                else:
                    _sauce = ""
                if _sauce:
                    message = f"{message}\n\n---\n{_sauce}\n---\nHãy tổng hợp kết quả tìm kiếm ảnh ở trên để trả lời."
                    logger.info("[Stream] SauceNAO search completed")
            except Exception as e:
                logger.warning(f"[Stream] SauceNAO failed: {e}")

        # ── SerpAPI — Google Lens / Reverse Image ──
        if "serpapi-reverse-image" in tools:
            import re as _re

            _img_urls = _re.findall(
                r"https?://\S+\.(?:jpg|jpeg|png|gif|webp)\S*",
                data.get("message", ""),
                _re.IGNORECASE,
            )
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
        if "serpapi-bing" in tools:
            try:
                _bing_results = _run_web_search(
                    data.get("message", message), engine="bing"
                )
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
        if "serpapi-baidu" in tools:
            try:
                _baidu_results = _run_web_search(
                    data.get("message", message), engine="baidu"
                )
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
        if "serpapi-images" in tools:
            try:
                from core.tools import serpapi_image_search

                _img_search_result = serpapi_image_search(data.get("message", message))
                if _img_search_result:
                    message = (
                        f"{message}\n\n---\n"
                        f"📋 KẾT QUẢ IMAGE SEARCH:\n{_img_search_result}\n---\n"
                        f"Hãy liệt kê và mô tả các ảnh tìm được."
                    )
                    logger.info("[Stream] SerpAPI image search completed")
            except Exception as e:
                logger.warning(f"[Stream] SerpAPI image search failed: {e}")

        # ── last30days — Social Media Research ──
        if "last30days-research" in tools:
            try:
                from core.last30days_tool import (
                    parse_research_params,
                    run_last30days_research,
                )

                _l30d_raw = data.get("message", message)
                _l30d_params = parse_research_params(_l30d_raw)
                _l30d_topic = _l30d_params["topic"]
                _l30d_depth = _l30d_params["depth"]
                _l30d_days = _l30d_params["days"]
                _l30d_sources = _l30d_params["sources"]

                logger.info(
                    "[Stream] last30days starting: topic=%r depth=%s days=%d",
                    _l30d_topic[:60],
                    _l30d_depth,
                    _l30d_days,
                )
                _l30d_result = run_last30days_research(
                    _l30d_topic,
                    depth=_l30d_depth,
                    days=_l30d_days,
                    sources=_l30d_sources,
                )
                if _l30d_result and not _l30d_result.startswith("❌"):
                    message = (
                        f"{message}\n\n---\n"
                        f"📋 KẾT QUẢ SOCIAL RESEARCH (last30days):\n{_l30d_result}\n---\n"
                        f"Hãy phân tích kết quả nghiên cứu từ nhiều nền tảng ở trên. "
                        f"Tổng hợp các quan điểm, xu hướng, và sentiment chính."
                    )
                    _search_performed = True
                    logger.info("[Stream] last30days research completed")
                elif _l30d_result:
                    logger.warning(
                        f"[Stream] last30days research returned error: {_l30d_result[:200]}"
                    )
            except Exception as e:
                logger.warning(f"[Stream] last30days research failed: {e}")

        # ── Auto reverse-image search when images attached + search intent ──
        _IMAGE_SEARCH_PATTERNS = [
            "tìm nguồn",
            "tìm ảnh",
            "nguồn ảnh",
            "tìm gốc",
            "reverse image",
            "find source",
            "image source",
            "where is this",
            "tìm tác giả",
            "ai vẽ",
            "tác giả",
            "author",
            "original",
            "find this image",
            "ảnh này từ đâu",
            "ảnh gốc",
            "tìm kiếm ảnh",
        ]
        _raw_msg = data.get("message", "").lower()
        _wants_image_search = images and any(
            p in _raw_msg for p in _IMAGE_SEARCH_PATTERNS
        )

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
                        data=json.dumps(
                            with_request_id(payload, request_id), ensure_ascii=False
                        ),
                    ).format()

                # Send metadata
                metadata_payload = {
                    "model": model,
                    "context": context,
                    "deep_thinking": deep_thinking,
                    "thinking_mode": thinking_mode,
                    "skill": applied.skill_id,
                    "skill_name": applied.skill_name,
                    "skill_source": skill_overrides.source,
                    "stream_backend": stream_backend,
                    "stream_contract_version": stream_contract_version,
                    "web_search": _search_performed,
                    "streaming": True,
                    "timestamp": datetime.now().isoformat(),
                }
                if skill_overrides.source == "auto":
                    metadata_payload["skill_auto_score"] = (
                        skill_overrides.auto_route_score
                    )
                    metadata_payload["skill_auto_keywords"] = (
                        skill_overrides.auto_route_keywords
                    )
                yield _emit("metadata", metadata_payload)
                yield _emit("router.selected", route_decision.to_dict())

                # ── Thinking-with-Images bridge ─────────────────────────
                # When the request is an image intent and the bridge flag
                # is on, run the anime pipeline as an in-chat image
                # sub-stream INSTEAD of the LLM text path. The pipeline keeps
                # its own queue / GPU semaphore / cancel and its ap_* SSE
                # vocabulary; we forward those frames VERBATIM so the existing
                # anime-pipeline.js renderer drives the inline bubble. After
                # the image finishes we stream a short LLM caption + a real
                # `complete` so the chat turn is finalized and saved.
                #
                # NOTE: multi-thinking council is NOT re-run here — the
                # orchestrator already runs its own council internally when
                # job.thinking_mode == "multi-thinking", and we return before
                # the text-council dispatch below, so it runs exactly once.
                def _caption_with_timeout(user_prompt: str, timeout_s: float = 12.0) -> str:
                    """Short, non-blocking LLM caption. Returns "" on timeout/err."""
                    import re as _re_cap
                    import threading as _th_cap

                    _res: dict = {}

                    def _work():
                        try:
                            buf = []
                            for ch in chatbot.chat_stream(
                                message=(
                                    "Viết MỘT câu ngắn (tối đa 25 từ), thân thiện, bằng "
                                    "tiếng Việt, giới thiệu bức ảnh vừa được tạo theo yêu "
                                    "cầu sau. Chỉ trả về đúng một câu, không markdown, "
                                    f"không tiền tố.\n\nYêu cầu: {user_prompt}"
                                ),
                                model=model,
                                context=context,
                                deep_thinking=False,
                                history=[],
                                language=language,
                                custom_prompt="",
                                images=[],
                            ):
                                # Skip reasoning chunks AND the trailing usage
                                # sentinel ("\x02USAGE\x03<in>:<out>") that every
                                # provider stream yields as its last chunk — the
                                # text path strips it, so the caption must too
                                # (it leaked as "USAGE1570:20" in the chat).
                                if (
                                    ch
                                    and not ch.startswith(REASONING_PREFIX)
                                    and not ch.startswith(USAGE_SENTINEL)
                                ):
                                    buf.append(ch)
                            text = "".join(buf)
                            # Belt-and-braces: drop anything after a mid-buffer
                            # sentinel in case a provider merges chunks.
                            if USAGE_SENTINEL in text:
                                text = text.split(USAGE_SENTINEL, 1)[0]
                            _res["text"] = text.strip()
                        except Exception as exc:  # noqa: BLE001 — caption is non-fatal
                            _res["err"] = exc

                    _t_cap = _th_cap.Thread(target=_work, daemon=True)
                    _t_cap.start()
                    _t_cap.join(timeout=timeout_s)
                    txt = (_res.get("text") or "").strip()
                    if not txt:
                        return ""
                    # Strip stray <think> blocks from reasoning models.
                    txt = _re_cap.sub(
                        r"<think>.*?</think>", "", txt, flags=_re_cap.DOTALL
                    ).strip()
                    return txt[:300]

                def _image_chat_bridge():
                    """Forward anime-pipeline ap_* frames into the chat SSE,
                    then stream caption + complete. Returns True if it handled
                    the turn, False to fall back to the normal chat path."""
                    import queue as _q_ap
                    import re as _re_ap
                    import threading as _th_ap

                    from core import anime_pipeline_service as _aps

                    # Build the pipeline request from the chat body. Image
                    # options come from the chat mode-card (PR3); default
                    # safely if absent so the bridge also works pre-PR3.
                    _img_data: dict = {
                        "prompt": message,
                        "thinking_mode": thinking_mode,
                        "session_id": session_id or "",
                        "conversation_id": conversation_id or "",
                        "character_key": (data.get("character_key") or "").strip(),
                        "image_only": bool(data.get("image_only", False)),
                        "batch_size": int(data.get("batch_size") or 1),
                        "preset": data.get("preset") or "anime_quality",
                    }
                    for _k in ("width", "height"):
                        _v = data.get(_k)
                        if isinstance(_v, (int, float)) and _v:
                            _img_data[_k] = int(_v)
                    if data.get("references"):
                        _img_data["references"] = data.get("references")
                    if data.get("reference_images"):
                        _img_data["reference_images"] = data.get("reference_images")

                    # Character resolution parity with the standalone image
                    # routes (/api/anime-pipeline/stream, /api/image-gen/*):
                    # auto-derive the character from the message via NLU and/or
                    # resolve an explicit picker key against the local registry
                    # + SAA 5149-char DB, prepending a fully-qualified
                    # "Name in Series" phrase so the pipeline renders the right
                    # character. The chat bridge previously skipped this, which
                    # is why in-chat image gen was worse at characters than the
                    # modal path. Fail-safe: any error leaves _img_data as-is.
                    try:
                        from routes.anime_pipeline import _enrich_with_character

                        _img_data = _enrich_with_character(_img_data)
                    except Exception as _ce:  # pragma: no cover — defensive
                        logger.debug(
                            "[SSE:%s] character enrichment skipped: %s",
                            request_id,
                            _ce,
                        )

                    _req, _verr = _aps.validate_request(_img_data)
                    if _verr or _req is None:
                        logger.info(
                            "[SSE:%s] image bridge skipped (validate: %s)",
                            request_id,
                            _verr,
                        )
                        # When the caller forced the bridge (frontend explicitly
                        # signaled image intent), tell the user why it failed
                        # instead of silently falling through to the text path.
                        if bool(data.get("force_image_bridge")):
                            _err_msg = f"Không thể tạo ảnh: {_verr or 'pipeline không sẵn sàng'}."
                            yield _emit("chunk", {"content": _err_msg, "chunk_index": 1})
                            _ep = _build_complete_event_payload(
                                full_response=_err_msg,
                                model=model, context=context,
                                deep_thinking=False, thinking_mode=thinking_mode,
                                chunk_count=1, thinking_summary="",
                                thinking_steps_text=[], thinking_duration=0,
                                elapsed_time=0.0,
                                tokens=max(1, len(_err_msg)), max_tokens=512,
                                request_id=request_id, has_image=False,
                            )
                            yield StreamEvent(
                                event="complete",
                                data=json.dumps(_ep, ensure_ascii=False),
                            ).format()
                            return True
                        return False

                    logger.info(
                        "[SSE:%s] image bridge engaged intent=%s mode=%s",
                        request_id,
                        route_decision.intent,
                        thinking_mode,
                    )

                    # Drain stream_pipeline() in a worker thread so its
                    # blocking GPU-semaphore wait (sleep loop) never stalls
                    # the Flask SSE generator / keepalive.
                    _frame_q: _q_ap.Queue = _q_ap.Queue()
                    _AP_DONE = "__APBRIDGE_DONE__"
                    _AP_ERR = "__APBRIDGE_ERR__"

                    def _drain():
                        try:
                            for _frame in _aps.stream_pipeline(_req):
                                _frame_q.put(_frame)
                            _frame_q.put((_AP_DONE, None))
                        except BaseException as exc:  # catches KeyboardInterrupt/SystemExit too
                            _frame_q.put((_AP_ERR, exc))
                            raise

                    _worker = _th_ap.Thread(target=_drain, daemon=True)
                    _worker.start()

                    _evt_re = _re_ap.compile(r"^event:\s*(\S+)", _re_ap.MULTILINE)
                    _ok = False
                    _cancelled = False
                    _failed = False

                    # JobQueue tracking: capture job_id from first ap_status frame.
                    from core.job_queue import get_queue as _get_queue_ap

                    _jid: str = ""
                    _jq = _get_queue_ap()

                    try:
                        while True:
                            try:
                                _item = _frame_q.get(timeout=15)
                            except _q_ap.Empty:
                                yield ": keepalive\n\n"
                                continue
                            if isinstance(_item, tuple):
                                if _item[0] == _AP_DONE:
                                    break
                                if _item[0] == _AP_ERR:
                                    _failed = True
                                    logger.error(
                                        "[SSE:%s] image bridge pipeline error: %s",
                                        request_id,
                                        _item[1],
                                    )
                                    break
                            # _item is a pre-formatted SSE string; forward verbatim.
                            yield _item
                            _m = _evt_re.search(_item)
                            _name = _m.group(1) if _m else ""
                            # Parse JSON payload for job_id and queue transitions.
                            _data_j: dict = {}
                            for _ln in _item.split("\n"):
                                if _ln.startswith("data:"):
                                    try:
                                        _data_j = json.loads(_ln.split(":", 1)[1].strip())
                                    except Exception:
                                        pass
                                    break
                            if _name == "ap_status" and not _jid:
                                _jid = str(_data_j.get("job_id") or "")
                                if _jid:
                                    if _jq.get(_jid) is None:
                                        _jq.create(job_id=_jid, prompt=raw_message[:500])
                                    _jq.transition(_jid, "queued")
                                    _jq.transition(_jid, "running")
                            elif _name == "ap_result":
                                _ok = True
                                if _jid:
                                    _jq.transition(_jid, "completed", progress_pct=100.0)
                            elif _name == "ap_cancelled":
                                _cancelled = True
                                if _jid:
                                    _jq.transition(_jid, "cancelled")
                            elif _name == "ap_error":
                                _failed = True
                                if _jid:
                                    _jq.transition(
                                        _jid, "failed",
                                        error=str(_data_j.get("error", "pipeline error")),
                                    )
                    except GeneratorExit:
                        # Client disconnected: cancel job and interrupt ComfyUI GPU.
                        if _jid:
                            _rec = _jq.get(_jid)
                            if _rec and _rec.state in ("queued", "running"):
                                _jq.request_cancel(_jid)
                                try:
                                    from routes.anime_pipeline import (
                                        _interrupt_comfyui as _ic,
                                    )
                                    _ic()
                                except Exception:
                                    pass
                        _worker.join(timeout=5)
                        raise

                    _worker.join(timeout=5)

                    # ── Caption + complete (finalize the chat turn) ──
                    # Caption only on success; its failure must NOT fail the
                    # image turn (ap_done ≠ complete: chat finalizes here).
                    if _ok and not _cancelled and not _failed:
                        _caption = _caption_with_timeout(message) or "Ảnh đã được tạo xong."
                    elif _cancelled:
                        _caption = "Đã hủy tạo ảnh."
                    else:
                        _caption = "Tạo ảnh thất bại. Hãy thử lại."

                    _cc = 0
                    for _i in range(0, len(_caption), 80):
                        _cc += 1
                        yield _emit(
                            "chunk",
                            {"content": _caption[_i : _i + 80], "chunk_index": _cc},
                        )

                    _payload = _build_complete_event_payload(
                        full_response=_caption,
                        model=model,
                        context=context,
                        deep_thinking=deep_thinking,
                        thinking_mode=thinking_mode,
                        chunk_count=_cc,
                        thinking_summary="",
                        thinking_steps_text=[],
                        thinking_duration=0,
                        elapsed_time=time.time() - thinking_start,
                        tokens=max(1, len(_caption)),
                        max_tokens=512,
                        request_id=request_id,
                        has_image=_ok,
                    )
                    try:
                        trace.finish()
                        TRACE_STORE.save(trace)
                    except Exception:  # noqa: BLE001
                        pass
                    yield StreamEvent(
                        event="complete",
                        data=json.dumps(_payload, ensure_ascii=False),
                    ).format()
                    return True

                _bridge_on = (
                    os.getenv("IMAGE_PIPELINE_CHAT_BRIDGE", "false").lower() == "true"
                )
                _image_tool_active = "image-generation" in (tools or [])
                _image_intent = route_decision.intent in ("image_anime", "image_general")
                # Frontend (main.js) sets force_image_bridge when it decides a
                # prompt is an image request under bridge mode — the explicit,
                # mismatch-proof signal (its ImageGenV2 heuristic may diverge
                # from the backend keyword router).
                _force_bridge = bool(data.get("force_image_bridge"))
                if _bridge_on and (
                    _force_bridge
                    or _image_tool_active
                    or (_image_intent and route_decision.confidence >= 0.85)
                ):
                    _handled = yield from _image_chat_bridge()
                    if _handled:
                        return

                # ── Thinking Phase ──
                # Real AI reasoning via <think> tags or native reasoning_content
                category = detect_category(message)
                thinking_steps_text = []
                thinking_summary = ""
                thinking_duration = 0
                thinking_started = False
                thinking_ended = False

                # For instant mode, skip thinking entirely
                use_thinking = thinking_mode != "instant"
                is_multi_thinking = thinking_mode == "multi-thinking"

                # ── Instant mode: force concise + direct answers ──
                _eff_prompt = custom_prompt
                if thinking_mode == "instant" and not _eff_prompt:
                    _base = _get_system_prompts(language).get(
                        context, _get_system_prompts(language).get("casual", "")
                    )
                    _eff_prompt = (
                        _base
                        + "\n\n⚡ INSTANT MODE: Trả lời ngắn gọn, trực tiếp, cụ thể. "
                        "Tối đa 3-4 đoạn văn. Không dẫn nhập lan man. Không cần liệt kê hết mọi thứ. "
                        "Đi thẳng vào câu trả lời quan trọng nhất."
                    )

                # ── Response Phase (with integrated thinking) ──
                full_response = ""
                chunk_count = 0
                fallback_used = False
                _api_input_tokens = 0
                _api_output_tokens = 0

                # ── 4-Agents Coordinated Reasoning ──
                if is_multi_thinking:
                    yield _emit(
                        "thinking_start",
                        {
                            "mode": "multi-thinking",
                            "label": "4-Agents Reasoning",
                            "category": category,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    try:
                        import queue as _queue
                        import threading as _threading

                        from app.services.ai_service import AIService
                        from app.services.reasoning_service import get_reasoning_service

                        reasoning_svc = get_reasoning_service(ai_service=AIService())

                        # Use thread + queue so progress events stream in real-time
                        _progress_q = _queue.Queue()
                        _DONE = "__DONE__"
                        _ERROR = "__ERROR__"

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
                                yield _emit(
                                    "thinking",
                                    {
                                        "step": item.get("text", ""),
                                        "step_index": step_idx,
                                        "is_reasoning_chunk": True,
                                        "trajectory_id": item.get("tid", ""),
                                    },
                                )
                            else:
                                # String items = status headers / markers
                                step_text = str(item).strip()
                                if step_text:
                                    step_idx += 1
                                    thinking_steps_text.append(step_text)
                                    yield _emit(
                                        "thinking",
                                        {
                                            "step": step_text,
                                            "step_index": step_idx,
                                            "is_reasoning_chunk": False,
                                        },
                                    )

                        # Ensure thread is joined
                        _t.join(timeout=5)

                        if result is None:
                            raise RuntimeError("Reasoning returned no result")

                        thinking_duration = round(result.reasoning_time * 1000)
                        yield _emit(
                            "thinking_end",
                            {
                                "summary": f"{result.total_rounds} rounds · {result.total_trajectories} trajectories · {result.reasoning_time:.1f}s",
                                "duration_ms": thinking_duration,
                                "rounds": result.total_rounds,
                                "trajectories": result.total_trajectories,
                                "steps": thinking_steps_text,
                                "category": category,
                            },
                        )

                        full_response = result.final_answer
                        _est_tokens = result.total_tokens or max(
                            1, int(len(full_response) * 0.75)
                        )

                        # Stream the final answer in chunks for progressive rendering
                        chunk_size = 80
                        for i in range(0, len(full_response), chunk_size):
                            text = full_response[i : i + chunk_size]
                            chunk_count += 1
                            yield _emit(
                                "chunk", {"content": text, "chunk_index": chunk_count}
                            )

                    except Exception as e:
                        logger.error(
                            f"[SSE:{request_id}] 4-Agents reasoning failed, fallback: {e}"
                        )
                        fallback_used = True
                        yield _emit(
                            "thinking_end",
                            {
                                "summary": "Fallback to standard",
                                "duration_ms": 0,
                                "steps": [],
                                "category": category,
                            },
                        )
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
                        custom_prompt=_eff_prompt,
                        images=images,
                        temperature=temperature,
                        temperature_deep=temperature_deep,
                        max_tokens_deep=max_tokens_deep,
                        top_p=top_p,
                    ):
                        if not chunk:
                            continue

                        # Capture real token usage from the API layer sentinel.
                        if chunk.startswith(USAGE_SENTINEL):
                            try:
                                raw = chunk[len(USAGE_SENTINEL):]
                                _in, _out = raw.split(":", 1)
                                _api_input_tokens = int(_in)
                                _api_output_tokens = int(_out)
                            except Exception:
                                pass
                            continue

                        # Handle native reasoning_content (DeepSeek R1, etc.)
                        if chunk.startswith(REASONING_PREFIX):
                            reasoning_text = chunk[len(REASONING_PREFIX) :]
                            if reasoning_text and use_thinking:
                                if not thinking_started:
                                    thinking_started = True
                                    yield _emit(
                                        "thinking_start",
                                        {
                                            "category": category,
                                            "timestamp": datetime.now().isoformat(),
                                        },
                                    )
                                thinking_steps_text.append(reasoning_text)
                                yield _emit(
                                    "thinking",
                                    {
                                        "step": reasoning_text,
                                        "category": "model_reasoning",
                                        "is_reasoning_chunk": True,
                                    },
                                )
                            continue

                        # Parse <think> tags from model output
                        if think_parser:
                            segments = think_parser.feed(chunk)
                            for is_thinking, text in segments:
                                if is_thinking:
                                    # This is reasoning content inside <think>
                                    if not thinking_started:
                                        thinking_started = True
                                        yield _emit(
                                            "thinking_start",
                                            {
                                                "category": category,
                                                "timestamp": datetime.now().isoformat(),
                                            },
                                        )
                                    thinking_steps_text.append(text)
                                    yield _emit(
                                        "thinking",
                                        {
                                            "step": text,
                                            "category": category,
                                            "is_reasoning_chunk": True,
                                        },
                                    )
                                else:
                                    # Regular response content — end thinking if active
                                    if thinking_started and not thinking_ended:
                                        thinking_ended = True
                                        thinking_duration = round(
                                            (time.time() - thinking_start) * 1000
                                        )
                                        thinking_summary = generate_thinking_summary(
                                            message, category, language
                                        )
                                        yield _emit(
                                            "thinking_end",
                                            {
                                                "summary": thinking_summary,
                                                "steps": thinking_steps_text,
                                                "category": category,
                                                "duration_ms": thinking_duration,
                                            },
                                        )

                                    full_response += text
                                    chunk_count += 1
                                    yield _emit(
                                        "chunk",
                                        {"content": text, "chunk_index": chunk_count},
                                    )
                        else:
                            # No thinking parser (instant mode) — pass through
                            full_response += chunk
                            chunk_count += 1
                            yield _emit(
                                "chunk", {"content": chunk, "chunk_index": chunk_count}
                            )

                    # Flush remaining buffer from think parser
                    if think_parser:
                        for is_thinking, text in think_parser.flush():
                            if is_thinking:
                                thinking_steps_text.append(text)
                                yield _emit(
                                    "thinking",
                                    {
                                        "step": text,
                                        "category": category,
                                        "is_reasoning_chunk": True,
                                    },
                                )
                            else:
                                full_response += text
                                chunk_count += 1
                                yield _emit(
                                    "chunk",
                                    {"content": text, "chunk_index": chunk_count},
                                )

                    # Close thinking if still open (model didn't close </think>)
                    if thinking_started and not thinking_ended:
                        thinking_duration = round((time.time() - thinking_start) * 1000)
                        thinking_summary = generate_thinking_summary(
                            message, category, language
                        )
                        yield _emit(
                            "thinking_end",
                            {
                                "summary": thinking_summary,
                                "steps": thinking_steps_text,
                                "category": category,
                                "duration_ms": thinking_duration,
                            },
                        )

                # Send complete event
                _elapsed = time.time() - thinking_start
                # Prefer real API-reported output tokens; fall back to character estimate.
                _est_tokens = _api_output_tokens or max(1, int(len(full_response) * 0.75))
                if is_multi_thinking:
                    _max_tokens = 4096
                else:
                    _mc = (
                        chatbot.registry.get_config(model) if chatbot.registry else None
                    )
                    _max_tokens = (
                        (_mc.max_tokens_deep if deep_thinking else _mc.max_tokens)
                        if _mc
                        else 2000
                    )
                _complete_payload = _build_complete_event_payload(
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
                    has_image=False,
                )
                if _api_input_tokens:
                    _complete_payload["input_tokens"] = _api_input_tokens
                yield StreamEvent(
                    event="complete",
                    data=json.dumps(
                        _with_rag_citations(_complete_payload, rag_citations),
                        ensure_ascii=False,
                    ),
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
                trace.finish()
                TRACE_STORE.save(trace)

                # Mongo activity log: assistant message summary (fail-safe).
                try:
                    mongo_store.save_message(
                        {
                            "message_id": f"msg-{uuid.uuid4().hex[:12]}",
                            "conversation_id": conversation_id or "",
                            "role": "assistant",
                            "message_type": "chat",
                            "content": full_response,
                            "metadata": {
                                "model": model,
                                "context": context,
                                "thinking_mode": thinking_mode,
                                "deep_thinking": deep_thinking,
                                "chunk_count": chunk_count,
                                "tokens": _est_tokens,
                                "elapsed_ms": int(_elapsed * 1000),
                                "in_reply_to_message_id": user_message_id,
                                "request_id": request_id,
                            },
                        }
                    )
                except Exception as _me:  # noqa: BLE001
                    logger.warning(
                        f"[SSE:{request_id}] mongo log (assistant message) failed: {_me}"
                    )

            except GeneratorExit:
                logger.info(f"[SSE:{request_id}] Client disconnected")
            except Exception as e:
                trace.finish(error=str(e))
                TRACE_STORE.save(trace)
                logger.error(f"[SSE:{request_id}] Streaming error: {e}")
                record_stream_error(
                    backend=stream_backend, request_id=request_id, error=str(e)
                )
                yield StreamEvent(
                    event="error",
                    data=json.dumps(
                        with_request_id({"error": str(e)}, request_id),
                        ensure_ascii=False,
                    ),
                ).format()

        return Response(
            generate_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
            },
        )

    except Exception as e:
        logger.error(f"[SSE] Error before stream init: {e}")
        return Response(
            StreamEvent(
                event="error", data=json.dumps({"error": str(e)}, ensure_ascii=False)
            ).format(),
            mimetype="text/event-stream",
            status=500,
        )


@stream_bp.route("/chat/stream/models", methods=["GET"])
def list_streaming_models():
    """List models that support streaming"""
    from core.chatbot_v2 import get_model_registry

    registry = get_model_registry()
    models = []

    for name in registry.list_available():
        config = registry.get_config(name)
        if config:
            models.append(
                {
                    "name": name,
                    "supports_streaming": config.supports_streaming,
                    "provider": config.provider.value,
                }
            )

    return {
        "models": models,
        "streaming_supported": [m["name"] for m in models if m["supports_streaming"]],
    }


@stream_bp.route("/chat/stream/metrics", methods=["GET"])
def stream_metrics():
    """Return in-memory stream telemetry snapshot."""
    return get_stream_metrics_snapshot()


@stream_bp.route("/chat/stream/skills", methods=["GET"])
def list_skills():
    """Legacy alias — redirects to /api/skills. Kept for backward compat."""
    from core.skills.registry import get_skill_registry

    registry = get_skill_registry()
    skills = []
    for s in registry.list_ui_visible():
        skills.append(
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "default_model": s.default_model,
                "default_thinking_mode": s.default_thinking_mode,
                "default_context": s.default_context,
                "preferred_tools": s.preferred_tools,
                "blocked_tools": s.blocked_tools,
                "tags": s.tags,
                "enabled": s.enabled,
            }
        )
    return {"skills": skills}
