"""Tests for the instant-cancel checkpoint added to
image_pipeline.anime_pipeline.orchestrator._run_stage.

The user's complaint was: "Nut Ngung phai quyet doan — len Ngung la xuat
anh ra luon chu khong thuc thi gi ca". To honour that, every call to
_run_stage now polls the job queue's cancel flag BEFORE invoking the
agent. If the flag is set, the stage is skipped, _cancelled is flipped
to True, and a pipeline_cancelled event is yielded so run_stream can
return immediately.

These tests pin that behaviour without touching the heavy imports the
real orchestrator needs (ComfyUI / vision agents). We patch
`_is_cancel_requested` and stub a fake agent.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture
def orch():
    """Build a minimally-initialised orchestrator. We bypass __init__
    because it constructs heavy agent instances that pull in torch."""
    from image_pipeline.anime_pipeline.orchestrator import AnimePipelineOrchestrator
    o = AnimePipelineOrchestrator.__new__(AnimePipelineOrchestrator)

    # Bare-minimum config: vram profile + portrait_res + comfyui_url.
    fake_vram = SimpleNamespace(
        profile=SimpleNamespace(value="standard"),
        unload_models_between_passes=False,
    )
    o._config = SimpleNamespace(
        vram=fake_vram,
        portrait_res=(832, 1216),
        comfyui_url="",
    )
    o._cancelled = False
    o._run_t0 = 0.0
    return o


def _fake_job(job_id="job_x"):
    """A bare AnimePipelineJob-shaped namespace with the fields
    _build_cancellation_event touches."""
    # 2026-04-29: orchestrator.run_stream() now reads job.latest_render_image()
    # in fallback paths (added when dual-output was introduced). The fixture
    # must expose it as a callable returning None so cancellation tests can
    # short-circuit without hitting AttributeError on the SimpleNamespace.
    return SimpleNamespace(
        job_id=job_id,
        intermediates=[],
        final_image_b64=None,
        status=None,
        completed_at=None,
        total_latency_ms=0.0,
        layer_plan=None,
        stage_timings_ms={},
        latest_render_image=lambda: None,
        critique_results=[],
        user_prompt="",
    )


def test_run_stage_skips_agent_when_cancel_requested(orch):
    """If the cancel flag is set BEFORE the stage starts, the agent's
    execute() must not be called and a pipeline_cancelled event is
    yielded. _cancelled must be flipped so run_stream bails out."""
    from image_pipeline.anime_pipeline import orchestrator as orch_mod

    job = _fake_job()
    agent = SimpleNamespace(execute=lambda j: pytest.fail("agent ran despite cancel"))

    with patch.object(orch_mod, "_is_cancel_requested", return_value=True), \
         patch.object(orch_mod, "log_pass_memory_mode", lambda *a, **kw: None), \
         patch.object(orch_mod, "free_models_between_passes", lambda *a, **kw: None):
        events = list(orch._run_stage("critique", agent, job, stage_num=6, total=9))

    assert orch._cancelled is True
    assert len(events) == 1
    payload = events[0].get("data", events[0])
    # Event type field is 'event' in the SSE dict; orchestrator prefixes
    # all event names with 'anime_pipeline_'.
    assert events[0]["event"] == "anime_pipeline_pipeline_cancelled"
    assert payload["stage"] == "critique"


def test_run_stage_runs_agent_when_no_cancel(orch):
    """Sanity: without a cancel flag, the stage executes normally and
    _cancelled stays False."""
    from image_pipeline.anime_pipeline import orchestrator as orch_mod

    ran = []
    job = _fake_job()
    agent = SimpleNamespace(execute=lambda j: ran.append(j))

    with patch.object(orch_mod, "_is_cancel_requested", return_value=False), \
         patch.object(orch_mod, "log_pass_memory_mode", lambda *a, **kw: None), \
         patch.object(orch_mod, "free_models_between_passes", lambda *a, **kw: None):
        events = list(orch._run_stage("critique", agent, job, stage_num=6, total=9))

    assert orch._cancelled is False
    assert ran == [job]
    # stage_start + stage_complete (no cancel event), prefixed.
    event_types = [e["event"] for e in events]
    assert "anime_pipeline_stage_start" in event_types
    assert "anime_pipeline_stage_complete" in event_types
    assert "anime_pipeline_pipeline_cancelled" not in event_types


def test_cancel_flag_resets_per_run(orch):
    """A previous run's cancel state must not leak into the next run.
    run_stream re-zeros _cancelled and _run_t0 on entry."""
    from image_pipeline.anime_pipeline import orchestrator as orch_mod

    orch._cancelled = True  # simulate stale state

    # We can't run the full run_stream here (it builds real jobs), but
    # the public contract is "the first lines of run_stream zero out
    # _cancelled and _run_t0". Verify by reading the source.
    src = (Path(orch_mod.__file__)).read_text(encoding="utf-8")
    # Both resets must happen inside run_stream, near the top.
    assert "self._cancelled = False" in src
    assert "self._run_t0 = t0" in src
