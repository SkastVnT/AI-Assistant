import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.chatbot.core.central_router import route_request
from services.chatbot.core.central_trace import (
    AgentStep,
    InMemoryTraceStore,
    RequestTrace,
)
from services.chatbot.core.job_queue import JobQueue


def test_router_selects_mcp_tool_flow():
    d = route_request("hãy đọc file và chạy git status")
    assert d.pipeline == "mcp_tool_flow"
    assert d.confidence > 0.8


def test_trace_lifecycle_and_store():
    trace = RequestTrace(conversation_id="c1", message_id="m1", user_input="hello")
    trace.selected_pipeline = "normal_chat"
    trace.selected_model = "default_chat"
    trace.agent_steps.append(AgentStep(agent="planner", status="done", latency_ms=5))
    trace.finish()
    store = InMemoryTraceStore(max_items=2)
    assert store.save(trace) is True
    data = store.latest(1)[0]
    assert data["selected_pipeline"] == "normal_chat"
    assert data["total_latency_ms"] is not None


def test_job_queue_state_transition():
    q = JobQueue(history_limit=3)
    q.create("j1", prompt="x")
    q.transition("j1", "running")
    q.update_progress("j1", stage="render", pct=30)
    q.transition("j1", "completed", final_image_path="/tmp/a.png")
    rec = q.get("j1")
    assert rec is not None
    assert rec.state == "completed"
    assert rec.progress_stage == "render"
