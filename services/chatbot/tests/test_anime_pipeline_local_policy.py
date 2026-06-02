"""Focused tests for the standalone LOCAL anime pipeline contract."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = ROOT / "app"
for path in (ROOT, APP_ROOT, ROOT / "services" / "chatbot"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def test_pc_policy_blocks_external_urls_and_allows_loopback():
    from image_pipeline.anime_pipeline.runtime_policy import (
        PolicyViolation,
        RuntimePolicy,
    )

    policy = RuntimePolicy.from_profile("pc_12gb")
    policy.assert_url("http://127.0.0.1:8188/system_stats", purpose="comfyui")
    with pytest.raises(PolicyViolation):
        policy.assert_url("https://api.openai.com/v1/chat/completions", purpose="cloud")


def test_laptop_external_validator_requires_sfw_opt_in():
    from image_pipeline.anime_pipeline.runtime_policy import (
        PolicyViolation,
        RuntimePolicy,
    )

    policy = RuntimePolicy.from_profile("laptop_6gb")
    policy.assert_url(
        "https://api.openai.com/v1/chat/completions",
        purpose="external_validation",
        content_mode="sfw",
        validator_mode="external_sfw_opt_in",
    )
    with pytest.raises(PolicyViolation):
        policy.assert_url(
            "https://api.openai.com/v1/chat/completions",
            purpose="external_validation",
            content_mode="adult_only",
            validator_mode="external_sfw_opt_in",
        )


def test_adult_only_laptop_requires_explicit_verified_adult_opt_in():
    from image_pipeline.anime_pipeline.runtime_policy import (
        PolicyViolation,
        RuntimePolicy,
    )

    with pytest.raises(PolicyViolation):
        RuntimePolicy.from_profile("laptop_6gb").validate_request(
            content_mode="adult_only", adult_verified=False
        )
    RuntimePolicy.from_profile("laptop_6gb").validate_request(
        content_mode="adult_only", adult_verified=True
    )


def test_pc_worker_default_requires_operator_assertion(monkeypatch):
    from image_pipeline.anime_pipeline.runtime_policy import (
        PolicyViolation,
        RuntimePolicy,
    )

    monkeypatch.delenv("ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER", raising=False)
    with pytest.raises(PolicyViolation):
        RuntimePolicy.from_profile("pc_12gb").validate_request(content_mode="sfw")

    monkeypatch.setenv("ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER", "1")
    policy = RuntimePolicy.from_profile("pc_12gb")
    assert policy.default_content_mode.value == "adult_only"
    policy.validate_request(content_mode="adult_only", adult_verified=False)


def test_adult_subject_guard_rejects_age_ambiguous_context():
    from image_pipeline.anime_pipeline.adult_subject_guard import (
        assert_adult_subject_allowed,
    )
    from image_pipeline.anime_pipeline.runtime_policy import PolicyViolation

    with pytest.raises(PolicyViolation, match="age-ambiguous"):
        assert_adult_subject_allowed(
            "age-ambiguous subject portrait",
            adult_verified=True,
            attestation_source="request",
        )


def test_character_pack_registry_tracks_adult_verification(tmp_path):
    from image_pipeline.anime_pipeline.character_pack import (
        character_is_adult_verified,
        get_character_pack,
    )

    registry = tmp_path / "packs.yaml"
    registry.write_text(
        "packs:\n"
        "  - key: original_adult\n"
        "    display_name: Original Adult\n"
        "    aliases: [adult_alias]\n"
        "    adult_verified: true\n",
        encoding="utf-8",
    )
    assert get_character_pack("adult alias", registry) is not None
    assert character_is_adult_verified("original_adult", registry)
    assert not character_is_adult_verified("unknown", registry)


def test_profile_loader_uses_real_wai_v170_checkpoint():
    from image_pipeline.anime_pipeline.config import load_config

    with patch.dict("os.environ", {"ANIME_PIPELINE_PROFILE": "pc_12gb"}):
        config = load_config()
    assert config.deployment_profile == "pc_12gb"
    assert config.composition_model.checkpoint == "waiIllustriousSDXL_v170.safetensors"
    assert not any(layer.enabled for layer in config.structure_layers)


def test_preflight_blocks_missing_required_checkpoint(tmp_path):
    from image_pipeline.anime_pipeline.config import AnimePipelineConfig, ModelConfig
    from image_pipeline.anime_pipeline.preflight import run_preflight

    config = AnimePipelineConfig(
        composition_model=ModelConfig(checkpoint="missing.safetensors"),
        beauty_model=ModelConfig(checkpoint="missing.safetensors"),
        final_model=ModelConfig(checkpoint="missing.safetensors"),
    )
    report = run_preflight(config, comfyui_dir=tmp_path)
    assert report.readiness == "blocked"
    assert any(path.endswith("missing.safetensors") for path in report.missing_assets)


def test_comfy_upload_failure_is_fail_fast():
    from image_pipeline.anime_pipeline.comfy_client import ComfyClient

    client = ComfyClient(base_url="http://test:8188")
    workflow = {
        "1": {
            "class_type": "LoadImageFromBase64",
            "inputs": {"base64_image": "abc"},
        }
    }
    with patch.object(client, "upload_image_b64", side_effect=RuntimeError("upload failed")), pytest.raises(RuntimeError):
            client._preprocess_workflow(workflow)


def test_native_workflow_provider_replaces_typed_tokens(tmp_path):
    from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

    template = tmp_path / "native.json"
    template.write_text(
        json.dumps(
            {
                "1": {
                    "class_type": "EmptyFlux2LatentImage",
                    "inputs": {"width": "{{width}}", "label": "seed={{seed}}"},
                }
            }
        ),
        encoding="utf-8",
    )
    workflow = WorkflowBuilder().build_native(
        "flux2_klein",
        {"workflow_template": str(template)},
        {"width": 768, "seed": 42},
    )
    assert workflow["1"]["inputs"]["width"] == 768
    assert workflow["1"]["inputs"]["label"] == "seed=42"


def test_policy_router_uses_local_table_without_api_quality_override():
    from image_pipeline.anime_pipeline.runtime_policy import RuntimePolicy
    from image_pipeline.workflow.capability_router import CapabilityRouter

    router = CapabilityRouter(runtime_policy=RuntimePolicy.from_profile("pc_12gb"))
    assert router.route("t2i", quality="cheap").model == "comfyui-wai-v170"
    decision = router.route("semantic_edit")
    assert decision.model == "comfyui-qwen-image-edit-2511"
    assert decision.location == "local"
    assert decision.fallbacks == []
    with pytest.raises(ValueError):
        router.route("semantic_edit", unavailable={"local"})


def test_native_qwen_editor_submits_comfy_workflow(tmp_path):
    from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult
    from image_pipeline.anime_pipeline.config import AnimePipelineConfig
    from image_pipeline.semantic_editor.native_comfy_editor import (
        NativeComfySemanticEditor,
    )

    template = tmp_path / "qwen_native.json"
    template.write_text(
        json.dumps(
            {
                "1": {
                    "class_type": "LoadImageFromBase64",
                    "inputs": {"base64_image": "{{source_image_b64}}"},
                },
                "2": {
                    "class_type": "TextEncodeQwenImageEdit",
                    "inputs": {"prompt": "{{instruction}}"},
                },
            }
        ),
        encoding="utf-8",
    )

    class FakeClient:
        base_url = "http://127.0.0.1:8188"

        def submit_workflow(self, workflow, job_id="", pass_name=""):
            assert workflow["1"]["inputs"]["base64_image"] == "source-b64"
            assert workflow["2"]["inputs"]["prompt"] == "add glasses"
            assert pass_name == "semantic_edit"
            return ComfyJobResult(success=True, images_b64=["edited-b64"])

    config = AnimePipelineConfig(
        deployment_profile="vps_96gb",
        native_providers={
            "qwen_image_edit": {
                "workflow_template": str(template),
                "model": "Qwen-Image-Edit-2511",
            }
        },
    )
    response = NativeComfySemanticEditor(config, client=FakeClient()).edit(
        instruction="add glasses",
        source_image_b64="source-b64",
    )
    assert response.success is True
    assert response.image_b64 == "edited-b64"
    assert response.provider == "comfyui-native"


def test_legacy_semantic_editor_has_no_cloud_fallback_by_default():
    from image_pipeline.semantic_editor.editor import SemanticEditor

    editor = SemanticEditor(prefer_vps=False)
    assert editor._fallback is None
    assert editor._allow_cloud_fallbacks is False


def test_unscored_critique_never_passes():
    from image_pipeline.anime_pipeline.schemas import CritiqueReport

    report = CritiqueReport(
        anatomy_score=10,
        face_score=10,
        unscored=True,
        scoring_error="worker unavailable",
    )
    assert report.passed is False
    assert report.to_dict()["unscored"] is True


def test_live_benchmark_requires_real_pipeline_and_scorer(tmp_path):
    from image_pipeline.evaluator.benchmark_runner import BenchmarkRunner

    suite = tmp_path / "suite.yaml"
    suite.write_text(
        "test_cases:\n"
        "  - id: T-001\n"
        "    category: smoke\n"
        "    instruction: test\n",
        encoding="utf-8",
    )
    runner = BenchmarkRunner(benchmark_path=suite)
    with pytest.raises(RuntimeError, match="requires both"):
        asyncio.run(runner.run_suite())


def test_anime_benchmark_suite_contains_48_sfw_cases():
    suite_path = APP_ROOT / "configs_vps" / "anime_benchmark_suite.yaml"
    suite = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
    assert suite["content_mode"] == "sfw"
    assert len(suite["test_cases"]) == 48


def test_service_request_contract_enforces_laptop_adult_verification():
    from core.anime_pipeline_service import validate_request

    with patch.dict("os.environ", {"ANIME_PIPELINE_PROFILE": "laptop_6gb"}):
        request, error = validate_request(
            {"prompt": "original adult character portrait", "content_mode": "adult_only"}
        )
        assert request is None
        assert "requires explicit verification" in str(error)

        request, error = validate_request(
            {
                "prompt": "original adult character portrait",
                "content_mode": "adult_only",
                "adult_verified": True,
                "deployment_profile": "laptop_6gb",
            }
        )
        assert error is None
        assert request is not None
        assert request.content_mode == "adult_only"
        assert request.adult_attestation_source == "request"


def test_service_request_contract_defaults_asserted_pc_worker_to_adult_only():
    from core.anime_pipeline_service import validate_request

    with patch.dict(
        "os.environ",
        {
            "ANIME_PIPELINE_PROFILE": "pc_12gb",
            "ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER": "1",
        },
    ):
        request, error = validate_request({"prompt": "verified adult portrait"})
    assert error is None
    assert request is not None
    assert request.content_mode == "adult_only"
    assert request.adult_verified is True
    assert request.adult_attestation_source == "worker"


def test_service_request_contract_allows_laptop_sfw_validator_opt_in():
    from core.anime_pipeline_service import validate_request

    with patch.dict("os.environ", {"ANIME_PIPELINE_PROFILE": "laptop_6gb"}):
        request, error = validate_request(
            {
                "prompt": "anime landscape",
                "validator_mode": "external_sfw_opt_in",
            }
        )
    assert error is None
    assert request is not None
    assert request.validator_mode == "external_sfw_opt_in"


def test_service_build_job_applies_local_character_pack():
    from image_pipeline.anime_pipeline.character_pack import CharacterPack

    from core.anime_pipeline_service import PipelineRequest, build_job

    pack = CharacterPack(
        key="original_adult",
        prompt_alias="blue_hair_adult",
        trigger_words=("silver_eyes",),
        loras=({"name": "identity.safetensors", "enabled": True},),
        checksums={"identity.safetensors": "abc123"},
        adult_verified=True,
    )
    with patch(
        "image_pipeline.anime_pipeline.character_pack.get_character_pack",
        return_value=pack,
    ):
        job = build_job(
            PipelineRequest(prompt="portrait", character_key="original_adult")
        )
    assert job.user_prompt == "portrait, blue_hair_adult, silver_eyes"
    assert job.user_loras[0]["name"] == "identity.safetensors"
    assert job.metadata["character_pack"]["key"] == "original_adult"
    assert job.metadata["model_checksums"]["identity.safetensors"] == "abc123"


def test_local_only_scorer_has_no_cloud_fallback():
    from image_pipeline.anime_pipeline.runtime_policy import RuntimePolicy
    from image_pipeline.evaluator.scorer import Scorer

    scorer = Scorer(
        local_only=True,
        local_vlm_url="http://127.0.0.1:8080/v1",
        local_vlm_model="local-test-vlm",
        runtime_policy=RuntimePolicy.from_profile("pc_12gb"),
    )
    assert len(scorer._judge_chain) == 1
    assert scorer._judge_chain[0].provider == "local"


def test_result_store_writes_job_local_and_canonical_manifests(tmp_path):
    from image_pipeline.anime_pipeline.result_store import ResultStore
    from image_pipeline.anime_pipeline.schemas import AnimePipelineJob

    intermediate = tmp_path / "intermediate"
    metadata = tmp_path / "metadata"
    job = AnimePipelineJob(user_prompt="portrait")
    local_path = Path(
        ResultStore(base_dir=intermediate, metadata_dir=metadata).save_manifest(job)
    )
    canonical_path = metadata / f"{job.job_id}.json"

    assert local_path == intermediate / job.job_id / "output_manifest.json"
    assert local_path.is_file()
    assert canonical_path.is_file()
    assert job.manifest_path == str(canonical_path)
    assert json.loads(canonical_path.read_text(encoding="utf-8"))["manifest_path"] == str(
        canonical_path
    )


def test_native_workflow_provider_rejects_operator_stub(tmp_path):
    from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

    template = tmp_path / "stub.json"
    template.write_text(
        json.dumps({"1": {"class_type": "STUB_OPERATOR_MUST_EXPORT", "inputs": {}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="still a stub"):
        WorkflowBuilder().build_native("flux2_klein", {"workflow_template": str(template)}, {})


def test_preflight_blocks_required_native_workflow_stub(tmp_path, monkeypatch):
    from image_pipeline.anime_pipeline import preflight
    from image_pipeline.anime_pipeline.config import AnimePipelineConfig

    stub = tmp_path / "stub.json"
    stub.write_text(
        json.dumps({"1": {"class_type": "STUB_OPERATOR_MUST_EXPORT", "inputs": {}}}),
        encoding="utf-8",
    )
    manifest = tmp_path / "assets.yaml"
    manifest.write_text(
        "assets:\n"
        "  - id: flux2_klein_workflow\n"
        "    profiles: [laptop_6gb]\n"
        f"    destination: {stub.as_posix()}\n"
        "    sha256: placeholder\n"
        "    required_for_capability: flux2_klein\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(preflight, "_PROVISIONING_MANIFEST", manifest)
    report = preflight.run_preflight(
        AnimePipelineConfig(capabilities={"flux2_klein": True}),
        comfyui_dir=tmp_path / "ComfyUI",
    )
    assert report.readiness == "blocked"
    assert report.capabilities["flux2_klein"] == "blocked"
    assert any(check.detail == "Replace operator-export workflow stub" for check in report.checks)


def test_preflight_blocks_pc_worker_without_operator_assertion(monkeypatch):
    from image_pipeline.anime_pipeline.config import load_config
    from image_pipeline.anime_pipeline.preflight import run_preflight

    monkeypatch.setenv("ANIME_PIPELINE_PROFILE", "pc_12gb")
    monkeypatch.delenv("ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER", raising=False)
    report = run_preflight(load_config())
    assert report.readiness == "blocked"
    assert any("ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER=1" in error for error in report.errors)


def test_adult_benchmark_suite_contains_48_local_fixture_cases():
    suite_path = APP_ROOT / "configs_vps" / "anime_benchmark_suite_adult_only.yaml"
    suite = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
    assert suite["content_mode"] == "adult_only"
    assert suite["requires_adult_verified"] is True
    assert len(suite["test_cases"]) == 48


def test_adult_benchmark_requires_explicit_verification():
    from image_pipeline.evaluator.benchmark_runner import BenchmarkRunner

    suite_path = APP_ROOT / "configs_vps" / "anime_benchmark_suite_adult_only.yaml"
    runner = BenchmarkRunner(benchmark_path=suite_path)
    with pytest.raises(RuntimeError, match="adult_only benchmark requires"):
        asyncio.run(runner.run_suite(dry_run=True))
