"""Unit tests for ``services/chatbot/core/job_queue``."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

_CHATBOT_DIR = Path(__file__).resolve().parents[1]
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


@pytest.fixture(autouse=True)
def _fresh_queue():
    from core import job_queue as jq

    jq.JobQueue._instance = None
    yield
    jq.JobQueue._instance = None


def test_create_and_get():
    from core.job_queue import get_queue

    q = get_queue()
    rec = q.create(
        "j1",
        prompt="hello",
        preset="anime_quality",
        character_key="raiden_shogun_genshin_impact",
    )
    assert rec.state == "queued"
    assert rec.prompt == "hello"
    got = q.get("j1")
    assert got is rec


def test_lifecycle_transitions():
    from core.job_queue import get_queue

    q = get_queue()
    q.create("j2", prompt="x")
    q.transition("j2", "running")
    assert q.get("j2").state == "running"
    assert q.get("j2").started_at is not None
    q.transition("j2", "completed", progress_pct=100.0)
    rec = q.get("j2")
    assert rec.state == "completed"
    assert rec.progress_pct == 100.0
    assert rec.completed_at is not None


def test_invalid_state_rejected():
    from core.job_queue import get_queue

    q = get_queue()
    q.create("j3", prompt="x")
    with pytest.raises(ValueError):
        q.transition("j3", "bogus")


def test_progress_clamped():
    from core.job_queue import get_queue

    q = get_queue()
    q.create("j4", prompt="x")
    q.update_progress("j4", stage="composition", pct=150.0)
    assert q.get("j4").progress_pct == 100.0
    q.update_progress("j4", pct=-10.0)
    assert q.get("j4").progress_pct == 0.0


def test_cancel_request():
    from core.job_queue import get_queue

    q = get_queue()
    q.create("j5", prompt="x")
    assert q.request_cancel("j5") is True
    assert q.is_cancel_requested("j5") is True
    # Cannot cancel terminal
    q.transition("j5", "completed")
    assert q.request_cancel("j5") is False


def test_cancel_unknown_returns_false():
    from core.job_queue import get_queue

    q = get_queue()
    assert q.request_cancel("nope") is False


def test_list_filter_and_order():
    from core.job_queue import get_queue

    q = get_queue()
    for i in range(3):
        q.create(f"k{i}", prompt=f"p{i}")
    q.transition("k1", "running")
    q.transition("k2", "completed")
    items = q.list()
    # newest first
    assert items[0].job_id == "k2"
    running = q.list(state="running")
    assert {r.job_id for r in running} == {"k1"}


def test_history_eviction():
    from core.job_queue import JobQueue

    q = JobQueue(history_limit=3)
    for i in range(5):
        q.create(f"e{i}", prompt="p")
    items = q.list(limit=10)
    job_ids = [r.job_id for r in items]
    assert "e0" not in job_ids
    assert "e1" not in job_ids
    assert "e4" in job_ids
    assert q.stats()["total"] == 3


def test_thread_safety_smoke():
    from core.job_queue import get_queue

    q = get_queue()
    errors = []

    def worker(idx):
        try:
            q.create(f"t{idx}", prompt="x")
            q.transition(f"t{idx}", "running")
            q.transition(f"t{idx}", "completed", progress_pct=100.0)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    completed = q.list(state="completed", limit=50)
    assert len(completed) == 20


def test_stats_contract():
    from core.job_queue import get_queue

    q = get_queue()
    q.create("s1", prompt="x")
    q.create("s2", prompt="x")
    q.transition("s2", "running")
    q.create("s3", prompt="x")
    q.transition("s3", "failed", error="boom")
    s = q.stats()
    assert s["total"] == 3
    assert s["by_state"]["queued"] == 1
    assert s["by_state"]["running"] == 1
    assert s["by_state"]["failed"] == 1
    assert "history_limit" in s
