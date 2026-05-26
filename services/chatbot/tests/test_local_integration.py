"""
Tests for local integration of character references, LoRA routing,
detection stage availability, and inpaint hooks in the anime pipeline.

Covers:
  * ``lora_file_exists`` helper
  * ``_inject_character_lora`` skip-on-missing guard
  * ``_inject_user_loras`` filters missing files and records them on job.metadata
  * ``_filter_existing_loras`` helper drops missing region LoRAs
  * ``get_character_ref_set`` loads from local cache dir
  * ``_augment_references_from_cache`` injects refs + eye_detail only when empty
  * ``DetectionInpaintAgent.is_available`` returns False when YOLO missing and
    ``execute`` is a no-op in that case
  * Parser-only identity fall-through in ``_run_lora_stage`` (no web research)

Run:
    cd services/chatbot && pytest tests/test_local_integration.py -v
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path
from unittest.mock import MagicMock

# ── Make imports work ────────────────────────────────────────────────
_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "services" / "chatbot"))

from image_pipeline.anime_pipeline import (
    character_references,  # noqa: E402
    lora_manager,  # noqa: E402
)
from image_pipeline.anime_pipeline.agents.detection_inpaint import (  # noqa: E402
    DetectionInpaintAgent,
)
from image_pipeline.anime_pipeline.character_references import (  # noqa: E402
    get_character_ref_set,
)
from image_pipeline.anime_pipeline.lora_manager import (  # noqa: E402
    LoRAVerificationResult,
    lora_file_exists,
)
from image_pipeline.anime_pipeline.schemas import (  # noqa: E402
    AnimePipelineJob,
    LayerPlan,
    PassConfig,
)

# ════════════════════════════════════════════════════════════════════
# lora_file_exists
# ════════════════════════════════════════════════════════════════════


def test_lora_file_exists_returns_false_for_empty():
    assert lora_file_exists("") is False
    assert lora_file_exists(None) is False  # type: ignore[arg-type]


def test_lora_file_exists_returns_false_for_nonexistent():
    assert lora_file_exists("definitely_not_a_real_lora_xyz123.safetensors") is False


def test_lora_file_exists_detects_file(tmp_path, monkeypatch):
    fake_loras_root = tmp_path / "ComfyUI" / "models" / "loras"
    fake_loras_root.mkdir(parents=True)
    fake = fake_loras_root / "fake.safetensors"
    fake.write_bytes(b"placeholder")

    monkeypatch.setattr(lora_manager, "_COMFYUI_LORA_ROOT", fake_loras_root)

    assert lora_file_exists("fake.safetensors") is True
    assert lora_file_exists("missing.safetensors") is False
    # Forward-slash subdir path works too
    sub = fake_loras_root / "characters" / "foo"
    sub.mkdir(parents=True)
    (sub / "nested.safetensors").write_bytes(b"x")
    assert lora_file_exists("characters/foo/nested.safetensors") is True


# ════════════════════════════════════════════════════════════════════
# Character references — local cache
# ════════════════════════════════════════════════════════════════════


def _make_png_bytes() -> bytes:
    # 1x1 transparent PNG
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgAAIAAAUAAeImBZsAAAAASUVORK5CYII="
    )


def test_get_character_ref_set_empty_for_unknown_tag(tmp_path, monkeypatch):
    monkeypatch.setattr(character_references, "_CACHE_DIR", tmp_path / "refs")

    ref = get_character_ref_set("unknown_character_xyz")
    assert ref.character_tag == "unknown_character_xyz"
    assert ref.images_b64 == []
    assert ref.loaded_from_cache is False


def test_get_character_ref_set_loads_known_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(character_references, "_CACHE_DIR", tmp_path / "refs")

    ref = get_character_ref_set("tokisaki_kurumi")
    # Known character — identity metadata populated even without image files
    assert ref.series_tag == "date_a_live"
    assert ref.eye_detail != {}
    assert ref.eye_detail.get("type") == "heterochromia"
    # No cached images yet
    assert ref.images_b64 == []


def test_get_character_ref_set_loads_cached_images(tmp_path, monkeypatch):
    cache_root = tmp_path / "refs"
    monkeypatch.setattr(character_references, "_CACHE_DIR", cache_root)

    char_dir = cache_root / "tokisaki_kurumi"
    char_dir.mkdir(parents=True)
    (char_dir / "ref1.png").write_bytes(_make_png_bytes())
    (char_dir / "ref2.png").write_bytes(_make_png_bytes())

    ref = get_character_ref_set("tokisaki_kurumi")
    assert ref.loaded_from_cache is True
    assert len(ref.images_b64) == 2
    assert ref.eye_detail.get("type") == "heterochromia"


# ════════════════════════════════════════════════════════════════════
# Orchestrator helpers — inject & augment
# ════════════════════════════════════════════════════════════════════


def _make_orchestrator_stub():
    """Import and instantiate the orchestrator with minimal mocking so we
    can exercise the helper methods without wiring the whole pipeline."""
    from image_pipeline.anime_pipeline import orchestrator as orch_mod

    inst = orch_mod.AnimePipelineOrchestrator.__new__(
        orch_mod.AnimePipelineOrchestrator
    )
    inst._verified_lora = None
    inst._research = None
    inst._detected_character = None
    return inst, orch_mod


def _make_job_with_plan(user_loras=None):
    plan = LayerPlan(
        passes=[
            PassConfig(
                pass_name="composition",
                model_slot="composition",
                checkpoint="x.safetensors",
                width=832,
                height=1216,
                sampler="euler",
                scheduler="normal",
                steps=30,
                cfg=7.0,
                denoise=1.0,
                seed=42,
                positive_prompt="p",
                negative_prompt="n",
            ),
            PassConfig(
                pass_name="beauty",
                model_slot="final",
                checkpoint="x.safetensors",
                width=832,
                height=1216,
                sampler="euler",
                scheduler="normal",
                steps=30,
                cfg=7.0,
                denoise=1.0,
                seed=43,
                positive_prompt="p",
                negative_prompt="n",
            ),
        ]
    )
    job = AnimePipelineJob(
        user_prompt="Kurumi from Date A Live",
        user_loras=list(user_loras or []),
    )
    job.layer_plan = plan
    return job


def test_inject_character_lora_skipped_when_file_missing(monkeypatch):
    inst, orch_mod = _make_orchestrator_stub()
    monkeypatch.setattr(orch_mod, "lora_file_exists", lambda name: False)
    inst._verified_lora = LoRAVerificationResult(
        accepted=True,
        vision_score=8.0,
        test_image_b64=None,
        lora_filename="characters/kurumi/kurumi.safetensors",
        lora_path=None,
        trigger_words=["kurumi"],
    )
    job = _make_job_with_plan()

    inst._inject_character_lora(job)

    # Plan must NOT contain the missing LoRA
    for pc in job.layer_plan.passes:
        names = [l.get("name") for l in (pc.lora_models or [])]
        assert "characters/kurumi/kurumi.safetensors" not in names
    # Metadata records the miss, verified slot cleared
    assert (
        job.metadata.get("character_lora_missing")
        == "characters/kurumi/kurumi.safetensors"
    )
    assert inst._verified_lora is None


def test_inject_character_lora_injects_when_file_present(monkeypatch):
    inst, orch_mod = _make_orchestrator_stub()
    monkeypatch.setattr(orch_mod, "lora_file_exists", lambda name: True)
    inst._verified_lora = LoRAVerificationResult(
        accepted=True,
        vision_score=8.0,
        test_image_b64=None,
        lora_filename="characters/kurumi/kurumi.safetensors",
        lora_path=None,
        trigger_words=["kurumi"],
    )
    job = _make_job_with_plan()

    inst._inject_character_lora(job)

    for pc in job.layer_plan.passes:
        names = [l.get("name") for l in (pc.lora_models or [])]
        assert names[0] == "characters/kurumi/kurumi.safetensors"
    assert job.metadata.get("character_lora_triggers") == ["kurumi"]


def test_inject_user_loras_filters_missing_files(monkeypatch):
    inst, orch_mod = _make_orchestrator_stub()
    monkeypatch.setattr(
        orch_mod,
        "lora_file_exists",
        lambda name: name == "real.safetensors",
    )
    job = _make_job_with_plan(
        user_loras=[
            {"name": "real.safetensors", "strength_model": 0.8, "strength_clip": 0.7},
            {"name": "ghost.safetensors", "strength_model": 0.8, "strength_clip": 0.7},
        ]
    )

    inst._inject_user_loras(job)

    # job.user_loras narrows to only the real one
    assert [l["name"] for l in job.user_loras] == ["real.safetensors"]
    assert job.metadata.get("user_loras_missing") == ["ghost.safetensors"]
    # The real one is injected
    for pc in job.layer_plan.passes:
        names = [l.get("name") for l in (pc.lora_models or [])]
        assert "real.safetensors" in names
        assert "ghost.safetensors" not in names


def test_inject_user_loras_all_missing_is_graceful(monkeypatch):
    inst, orch_mod = _make_orchestrator_stub()
    monkeypatch.setattr(orch_mod, "lora_file_exists", lambda name: False)
    job = _make_job_with_plan(
        user_loras=[
            {"name": "a.safetensors", "strength_model": 0.8, "strength_clip": 0.7},
            {"name": "b.safetensors", "strength_model": 0.8, "strength_clip": 0.7},
        ]
    )

    inst._inject_user_loras(job)

    assert sorted(job.metadata.get("user_loras_missing", [])) == [
        "a.safetensors",
        "b.safetensors",
    ]
    # No pass gets injected with anything
    for pc in job.layer_plan.passes:
        names = [l.get("name") for l in (pc.lora_models or [])]
        assert "a.safetensors" not in names
        assert "b.safetensors" not in names


def test_augment_references_from_cache_injects_refs_and_eye_detail(
    tmp_path, monkeypatch
):
    inst, _orch_mod = _make_orchestrator_stub()
    monkeypatch.setattr(character_references, "_CACHE_DIR", tmp_path / "refs")

    char_dir = tmp_path / "refs" / "tokisaki_kurumi"
    char_dir.mkdir(parents=True)
    (char_dir / "ref1.png").write_bytes(_make_png_bytes())

    job = AnimePipelineJob(user_prompt="Kurumi", reference_images_b64=[])
    inst._augment_references_from_cache(job, "tokisaki_kurumi")

    assert len(job.reference_images_b64) == 1
    assert job.metadata.get("character_eye_detail", {}).get("type") == "heterochromia"
    assert job.metadata.get("character_series_tag") == "date_a_live"


def test_augment_references_does_not_override_existing(tmp_path, monkeypatch):
    inst, _orch_mod = _make_orchestrator_stub()
    monkeypatch.setattr(character_references, "_CACHE_DIR", tmp_path / "refs")

    char_dir = tmp_path / "refs" / "tokisaki_kurumi"
    char_dir.mkdir(parents=True)
    (char_dir / "ref1.png").write_bytes(_make_png_bytes())

    existing = "data:image/png;base64,AAAA"
    job = AnimePipelineJob(user_prompt="Kurumi", reference_images_b64=[existing])
    inst._augment_references_from_cache(job, "tokisaki_kurumi")

    # Existing references are preserved; cache is NOT injected
    assert job.reference_images_b64 == [existing]
    # eye_detail metadata is still attached (it's the main value-add)
    assert job.metadata.get("character_eye_detail", {}).get("type") == "heterochromia"


# ════════════════════════════════════════════════════════════════════
# Detection inpaint — graceful skip + region LoRA filter
# ════════════════════════════════════════════════════════════════════


def test_filter_existing_loras_drops_missing(monkeypatch):
    monkeypatch.setattr(
        lora_manager,
        "_COMFYUI_LORA_ROOT",
        Path("/___definitely_not_a_real_dir___"),
    )
    loras = [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.5,
            "strength_clip": 0.4,
        },
        {
            "name": "totally_missing.safetensors",
            "strength_model": 0.5,
            "strength_clip": 0.4,
        },
    ]
    kept = DetectionInpaintAgent._filter_existing_loras(loras, region_type="face")
    assert kept == []  # both missing in the stub root


def test_filter_existing_loras_keeps_present(tmp_path, monkeypatch):
    fake_root = tmp_path / "loras"
    fake_root.mkdir()
    (fake_root / "Anime_artistic_2.safetensors").write_bytes(b"x")
    monkeypatch.setattr(lora_manager, "_COMFYUI_LORA_ROOT", fake_root)

    loras = [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.5,
            "strength_clip": 0.4,
        },
        {"name": "not_there.safetensors", "strength_model": 0.5, "strength_clip": 0.4},
    ]
    kept = DetectionInpaintAgent._filter_existing_loras(loras, region_type="face")
    assert len(kept) == 1
    assert kept[0]["name"] == "Anime_artistic_2.safetensors"


def test_detection_inpaint_skips_when_unavailable():
    """When the detector reports unavailable, execute() must be a no-op and
    must not mutate the job's final_image_b64 or intermediates."""
    agent = DetectionInpaintAgent.__new__(DetectionInpaintAgent)
    agent._detector = MagicMock()
    agent._detector.available.return_value = False
    agent._enabled = True

    job = AnimePipelineJob(user_prompt="x")
    job.final_image_b64 = "original_b64"

    # Should not raise, should not mutate
    agent.execute(job)
    assert job.final_image_b64 == "original_b64"
    assert job.intermediates == []
    assert "detection_inpaint" not in job.stages_executed


def test_detection_inpaint_is_available_false_when_disabled():
    agent = DetectionInpaintAgent.__new__(DetectionInpaintAgent)
    agent._detector = MagicMock()
    agent._detector.available.return_value = True
    agent._enabled = False
    assert agent.is_available() is False


def test_detection_inpaint_is_available_false_when_no_detector():
    agent = DetectionInpaintAgent.__new__(DetectionInpaintAgent)
    agent._detector = MagicMock()
    agent._detector.available.return_value = False
    agent._enabled = True
    assert agent.is_available() is False


# ════════════════════════════════════════════════════════════════════
# Parser-only LoRA fall-through
# ════════════════════════════════════════════════════════════════════


def test_run_lora_stage_falls_through_to_parser_identity(monkeypatch):
    """When character research fails but the parser resolved an identity,
    the LoRA stage must still attempt CivitAI search using parser fields."""
    from image_pipeline.anime_pipeline import orchestrator as orch_mod

    inst = orch_mod.AnimePipelineOrchestrator.__new__(
        orch_mod.AnimePipelineOrchestrator
    )
    inst._verified_lora = None
    inst._research = None  # research did not produce a result
    inst._detected_character = None

    # Minimal config stub
    inst._config = MagicMock()
    inst._config.vram.profile.value = "medium"
    inst._config.comfyui_url = ""
    inst._config.composition_model.checkpoint = "test.safetensors"

    # Capture what find_and_verify_character_lora is called with
    call_args = {}

    def _fake_find(**kwargs):
        call_args.update(kwargs)
        return LoRAVerificationResult(
            accepted=False,
            vision_score=0.0,
            test_image_b64=None,
            lora_filename="",
            lora_path=None,
            rejection_reason="stub",
        )

    monkeypatch.setattr(orch_mod, "find_and_verify_character_lora", _fake_find)

    job = AnimePipelineJob(
        user_prompt="Kafka from Honkai Star Rail",
    )
    job.character_name = "Kafka"
    job.series_name = "Honkai: Star Rail"
    job.character_tag = "kafka_(honkai_star_rail)"
    job.series_tag = "honkai:_star_rail"

    events = list(inst._run_lora_stage(job))

    # The search WAS attempted
    assert call_args.get("danbooru_tag") == "kafka_(honkai_star_rail)"
    assert "honkai" in call_args.get("series_name", "").lower()
    # lora_search stage should have run (not skipped)
    stage_complete_events = [
        e
        for e in events
        if e.get("data", {}).get("stage") == "lora_search"
        and "skipped" not in e.get("data", {})
    ]
    assert len(stage_complete_events) >= 1


def test_run_lora_stage_skips_when_no_identity_at_all(monkeypatch):
    """With no research and no parser tag, skip cleanly."""
    from image_pipeline.anime_pipeline import orchestrator as orch_mod

    inst = orch_mod.AnimePipelineOrchestrator.__new__(
        orch_mod.AnimePipelineOrchestrator
    )
    inst._verified_lora = None
    inst._research = None
    inst._detected_character = None
    inst._config = MagicMock()
    inst._config.vram.profile.value = "medium"

    job = AnimePipelineJob(user_prompt="a generic anime girl")
    # no character_tag, no series_tag

    events = list(inst._run_lora_stage(job))

    # Must emit stage_complete with skipped=True and reason
    completes = [
        e
        for e in events
        if e.get("data", {}).get("stage") == "lora_search"
        and e.get("data", {}).get("skipped") is True
    ]
    assert len(completes) == 1
    assert completes[0]["data"].get("reason") == "no_character_detected"
