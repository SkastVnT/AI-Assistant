"""Tests for the chat <-> local-image-pipeline glue.

Scope (verbatim from task):
  * a chat turn launches an image job and records job metadata
  * a follow-up turn sees the latest image asset context
  * missing manifest degrades gracefully
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

_CHATBOT_DIR = Path(__file__).resolve().parents[1]
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


# ---------------------------------------------------------------------------
# Fake JobQueue: stand-in for core.job_queue.get_queue() in tests so we
# never touch the real singleton (which carries process-wide state).
# ---------------------------------------------------------------------------


class _FakeJob(SimpleNamespace):
    def to_dict(self):
        return dict(self.__dict__)


class _FakeQueue:
    def __init__(self, jobs=None):
        self._jobs = dict(jobs or {})

    def get(self, job_id):
        return self._jobs.get(job_id)


def _install_fake_queue(monkeypatch, jobs):
    """Wire a fake queue into core.image_pipeline_link's lazy import."""
    fake_queue = _FakeQueue(jobs)
    fake_module = SimpleNamespace(get_queue=lambda: fake_queue)
    monkeypatch.setitem(sys.modules, "core.job_queue", fake_module)
    return fake_queue


def _job(**fields):
    base = dict(
        job_id="job_abc123",
        state="completed",
        prompt="Raiden Shogun in Genshin Impact, lightning",
        character_key="raiden_shogun_genshin_impact",
        character_display="Raiden Shogun",
        series_key="genshin_impact",
        preset="anime_quality",
        progress_stage="composition_pass",
        progress_pct=100.0,
        manifest_path="storage/metadata/job_abc123.json",
        final_image_path="storage/output/job_abc123.png",
        error=None,
    )
    base.update(fields)
    return _FakeJob(**base)


# ---------------------------------------------------------------------------
# image_pipeline_link.summarize_job
# ---------------------------------------------------------------------------


def test_summarize_known_job(monkeypatch):
    _install_fake_queue(monkeypatch, {"job_abc123": _job()})
    from core.image_pipeline_link import summarize_job

    out = summarize_job("job_abc123")
    assert out is not None
    assert out["job_id"] == "job_abc123"
    assert out["state"] == "completed"
    assert out["character_key"] == "raiden_shogun_genshin_impact"
    assert out["preset"] == "anime_quality"
    assert out["manifest_path"].endswith("job_abc123.json")
    assert out["final_image_path"].endswith("job_abc123.png")


def test_summarize_unknown_job(monkeypatch):
    _install_fake_queue(monkeypatch, {})
    from core.image_pipeline_link import summarize_job

    assert summarize_job("missing_job") is None
    assert summarize_job("") is None
    assert summarize_job(None) is None  # type: ignore[arg-type]


def test_summarize_when_queue_unavailable(monkeypatch):
    """Importing core.job_queue raises -> summarize_job degrades to None."""
    monkeypatch.delitem(sys.modules, "core.job_queue", raising=False)

    real_import = (
        __builtins__["__import__"]
        if isinstance(__builtins__, dict)
        else __builtins__.__import__
    )

    def _broken_import(name, *a, **kw):
        if name == "core.job_queue":
            raise ImportError("queue subsystem missing")
        return real_import(name, *a, **kw)

    monkeypatch.setattr("builtins.__import__", _broken_import)
    # Force re-import of image_pipeline_link's lazy lookup path.
    sys.modules.pop("core.image_pipeline_link", None)
    from core.image_pipeline_link import summarize_job

    assert summarize_job("anything") is None


# ---------------------------------------------------------------------------
# enrich_records_with_live_state
# ---------------------------------------------------------------------------


def test_enrich_fills_missing_fields_only(monkeypatch):
    _install_fake_queue(monkeypatch, {"job_abc123": _job()})
    from core.image_pipeline_link import enrich_records_with_live_state

    record = {"job_id": "job_abc123", "url": "/static/x.png", "prompt": "user prompt"}
    out = enrich_records_with_live_state([record])

    assert len(out) == 1
    enriched = out[0]
    # Frontend-supplied fields untouched
    assert enriched["url"] == "/static/x.png"
    assert enriched["prompt"] == "user prompt"
    # Server-side fields back-filled from JobQueue
    assert enriched["character_key"] == "raiden_shogun_genshin_impact"
    assert enriched["preset"] == "anime_quality"
    assert enriched["manifest_path"].endswith("job_abc123.json")
    # Live-state block added
    assert enriched["pipeline"]["state"] == "completed"
    # Original input not mutated
    assert "pipeline" not in record
    assert "character_key" not in record


def test_enrich_does_not_overwrite_explicit_fields(monkeypatch):
    _install_fake_queue(monkeypatch, {"job_abc123": _job(preset="anime_quality")})
    from core.image_pipeline_link import enrich_records_with_live_state

    record = {"job_id": "job_abc123", "preset": "user_picked_preset"}
    enriched = enrich_records_with_live_state([record])[0]
    assert enriched["preset"] == "user_picked_preset"


def test_enrich_skips_records_without_job_id(monkeypatch):
    _install_fake_queue(monkeypatch, {"job_abc123": _job()})
    from core.image_pipeline_link import enrich_records_with_live_state

    records = [
        {"url": "/static/x.png", "prompt": "no job id here"},
        "not a dict",
        None,
    ]
    out = enrich_records_with_live_state(records)
    assert out == records


def test_enrich_caps_lookup_count(monkeypatch):
    """Reject DOS via huge generated_images arrays."""
    jobs = {f"job_{i}": _job(job_id=f"job_{i}") for i in range(20)}
    _install_fake_queue(monkeypatch, jobs)
    from core.image_pipeline_link import MAX_LOOKUPS, enrich_records_with_live_state

    records = [{"job_id": f"job_{i}"} for i in range(20)]
    out = enrich_records_with_live_state(records)
    enriched_count = sum(1 for r in out if isinstance(r, dict) and "pipeline" in r)
    assert enriched_count == MAX_LOOKUPS


# ---------------------------------------------------------------------------
# Follow-up turn: the LLM context block sees the live state
# ---------------------------------------------------------------------------


def test_followup_turn_sees_image_context(monkeypatch):
    """Simulate the path: chat turn launches a job (record stored with only
    job_id), next chat turn calls the request normalizer, which must enrich
    the record and put a useful context block in front of the LLM.
    """
    _install_fake_queue(monkeypatch, {"job_abc123": _job(state="completed")})
    # Force re-import so request_normalizer picks up our fake queue.
    sys.modules.pop("core.image_pipeline_link", None)
    sys.modules.pop("core.request_normalizer", None)
    from core.request_normalizer import apply_image_context

    user_message = "What color is her dress?"
    records = [{"job_id": "job_abc123"}]
    msg_out, injected = apply_image_context(user_message, records)

    assert injected == 1
    # Original user text preserved
    assert msg_out.startswith(user_message)
    # Context block carries the back-filled identity + live state
    assert "raiden_shogun_genshin_impact" in msg_out
    assert "anime_quality" in msg_out
    assert "completed" in msg_out  # pipeline-state hint


def test_followup_turn_with_running_job_shows_progress(monkeypatch):
    _install_fake_queue(
        monkeypatch,
        {
            "job_abc123": _job(
                state="running",
                progress_pct=42.0,
                progress_stage="critique",
                manifest_path=None,
                final_image_path=None,
            )
        },
    )
    sys.modules.pop("core.image_pipeline_link", None)
    sys.modules.pop("core.request_normalizer", None)
    from core.request_normalizer import apply_image_context

    msg_out, injected = apply_image_context("status?", [{"job_id": "job_abc123"}])
    assert injected == 1
    assert "running" in msg_out
    assert "stage=critique" in msg_out


# ---------------------------------------------------------------------------
# Missing manifest degrades gracefully
# ---------------------------------------------------------------------------


def test_missing_manifest_degrades_gracefully(monkeypatch, tmp_path):
    """A job whose manifest_path points at a non-existent file must still
    produce a usable context block -- no exception, just no manifest line.
    """
    bogus_path = str(tmp_path / "does_not_exist.json")
    _install_fake_queue(
        monkeypatch,
        {"job_abc123": _job(manifest_path=bogus_path, state="completed")},
    )
    sys.modules.pop("core.image_pipeline_link", None)
    sys.modules.pop("core.request_normalizer", None)
    from core.request_normalizer import apply_image_context

    msg_out, injected = apply_image_context(
        "describe the image", [{"job_id": "job_abc123"}]
    )
    assert injected == 1
    assert "raiden_shogun_genshin_impact" in msg_out
    assert "manifest:" not in msg_out  # no manifest line because file missing
    assert "completed" in msg_out  # but pipeline-state hint still appears


def test_unknown_job_record_passes_through(monkeypatch):
    """Frontend may have a stale job_id (eg. the queue was restarted).
    The record must still appear in context using whatever fields it has."""
    _install_fake_queue(monkeypatch, {})
    sys.modules.pop("core.image_pipeline_link", None)
    sys.modules.pop("core.request_normalizer", None)
    from core.request_normalizer import apply_image_context

    msg_out, injected = apply_image_context(
        "explain",
        [
            {
                "job_id": "ghost_job",
                "prompt": "the prompt user typed",
                "url": "/static/img.png",
            }
        ],
    )
    assert injected == 1
    assert "ghost_job" in msg_out
    assert "the prompt user typed" in msg_out
    assert "/static/img.png" in msg_out


# ---------------------------------------------------------------------------
# format_pipeline_hint formatting
# ---------------------------------------------------------------------------


def test_format_pipeline_hint_completed():
    from core.image_pipeline_link import format_pipeline_hint

    rec = {
        "job_id": "x",
        "pipeline": {
            "state": "completed",
            "progress_pct": 100,
            "progress_stage": "done",
            "error": None,
        },
    }
    assert format_pipeline_hint(rec) == "pipeline: completed"


def test_format_pipeline_hint_running_with_stage():
    from core.image_pipeline_link import format_pipeline_hint

    rec = {
        "pipeline": {
            "state": "running",
            "progress_pct": 33.3,
            "progress_stage": "composition_pass",
            "error": None,
        }
    }
    out = format_pipeline_hint(rec)
    assert out is not None
    assert "running" in out
    assert "stage=composition_pass" in out
    assert "33%" in out


def test_format_pipeline_hint_failed_carries_error():
    from core.image_pipeline_link import format_pipeline_hint

    rec = {
        "pipeline": {
            "state": "failed",
            "progress_pct": 0,
            "progress_stage": None,
            "error": "OOM in upscaler",
        }
    }
    out = format_pipeline_hint(rec)
    assert out is not None
    assert "failed" in out
    assert "OOM in upscaler" in out


def test_format_pipeline_hint_no_pipeline_block():
    from core.image_pipeline_link import format_pipeline_hint

    assert format_pipeline_hint({"job_id": "x"}) is None
    assert format_pipeline_hint({}) is None
    assert format_pipeline_hint(None) is None  # type: ignore[arg-type]
    assert format_pipeline_hint("not a dict") is None  # type: ignore[arg-type]
