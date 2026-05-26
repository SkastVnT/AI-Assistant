import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.chatbot.core.central_router import route_request
from services.chatbot.core.request_trace import RequestTrace, RequestTraceStore


def test_router_pipeline_selection():
    assert route_request("please search web latest ai news").pipeline == "xai_native"
    assert route_request("hãy tạo ảnh anime waifu").pipeline == "anime_pipeline"
    assert route_request("hãy đọc file và chạy git status").pipeline == "mcp_tool_flow"


def test_request_trace_lifecycle():
    tr = RequestTrace(
        request_id="r1",
        conversation_id="c1",
        message_id="m1",
        selected_pipeline="hermes",
        selected_model="hermes3",
    )
    tr.mark_tool("web_search", status="completed")
    tr.mark_step("planner", status="done")
    tr.finish()
    store = RequestTraceStore(max_items=5)
    assert store.save(tr) is True
    rec = store.latest(1)[0]
    assert rec["selected_pipeline"] == "hermes"
    assert rec["latency_ms"] is not None
