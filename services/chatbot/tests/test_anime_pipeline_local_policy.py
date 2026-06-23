# """Focused tests for the standalone LOCAL anime pipeline contract."""

# from __future__ import annotations

# import asyncio
# import hashlib
# import json
# import os
# import sys
# from pathlib import Path
# from types import SimpleNamespace
# from unittest.mock import patch

# import pytest
# import yaml

# ROOT = Path(__file__).resolve().parents[3]
# APP_ROOT = ROOT / "app"
# for path in (ROOT, APP_ROOT, ROOT / "services" / "chatbot"):
#     if str(path) not in sys.path:
#         sys.path.insert(0, str(path))


# def test_pc_policy_blocks_external_urls_and_allows_loopback():
#     from image_pipeline.anime_pipeline.runtime_policy import (
#         PolicyViolation,
#         RuntimePolicy,
#     )

#     policy = RuntimePolicy.from_profile("pc_12gb")
#     policy.assert_url("http://127.0.0.1:8188/system_stats", purpose="comfyui")
#     with pytest.raises(PolicyViolation):
#         policy.assert_url("https://api.openai.com/v1/chat/completions", purpose="cloud")


# def test_laptop_external_validator_requires_sfw_opt_in():
#     from image_pipeline.anime_pipeline.runtime_policy import (
#         PolicyViolation,
#         RuntimePolicy,
#     )

#     policy = RuntimePolicy.from_profile("laptop_6gb")
#     policy.assert_url(
#         "https://api.openai.com/v1/chat/completions",
#         purpose="external_validation",
#         content_mode="sfw",
#         validator_mode="external_sfw_opt_in",
#     )
#     with pytest.raises(PolicyViolation):
#         policy.assert_url(
#             "https://api.openai.com/v1/chat/completions",
#             purpose="external_validation",
#             content_mode="adult_only",
#             validator_mode="external_sfw_opt_in",
#         )


# def test_adult_only_laptop_is_disabled_even_with_request_attestation():
#     from image_pipeline.anime_pipeline.runtime_policy import (
#         PolicyViolation,
#         RuntimePolicy,
#     )

#     with pytest.raises(PolicyViolation):
#         RuntimePolicy.from_profile("laptop_6gb").validate_request(
#             content_mode="adult_only", adult_verified=False
#         )
#     with pytest.raises(PolicyViolation, match="disabled on laptop_6gb"):
#         RuntimePolicy.from_profile("laptop_6gb").validate_request(
#             content_mode="adult_only", adult_verified=True
#         )


# def test_pc_worker_default_requires_operator_assertion(monkeypatch):
#     from image_pipeline.anime_pipeline.runtime_policy import (
#         PolicyViolation,
#         RuntimePolicy,
#     )

#     monkeypatch.delenv("ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER", raising=False)
#     with pytest.raises(PolicyViolation):
#         RuntimePolicy.from_profile("pc_12gb").validate_request(content_mode="sfw")

#     monkeypatch.setenv("ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER", "1")
#     policy = RuntimePolicy.from_profile("pc_12gb")
#     assert policy.default_content_mode.value == "adult_only"
#     policy.validate_request(content_mode="adult_only", adult_verified=False)


# def test_rtx5070_uses_pc_worker_default_policy(monkeypatch):
#     from image_pipeline.anime_pipeline.runtime_policy import (
#         PolicyViolation,
#         RuntimePolicy,
#     )

#     monkeypatch.delenv("ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER", raising=False)
#     with pytest.raises(PolicyViolation):
#         RuntimePolicy.from_profile("rtx5070").validate_request(content_mode="sfw")

#     monkeypatch.setenv("ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER", "1")
#     policy = RuntimePolicy.from_profile("rtx5070")
#     assert policy.default_content_mode.value == "adult_only"
#     policy.validate_request(content_mode="adult_only")


# def test_adult_subject_guard_rejects_age_ambiguous_context():
#     from image_pipeline.anime_pipeline.adult_subject_guard import (
#         assert_adult_subject_allowed,
#         assert_sfw_prompt_allowed,
#     )
#     from image_pipeline.anime_pipeline.runtime_policy import PolicyViolation

#     with pytest.raises(PolicyViolation, match="age-ambiguous"):
#         assert_adult_subject_allowed(
#             "age-ambiguous subject portrait",
#             adult_verified=True,
#             attestation_source="request",
#         )
#     with pytest.raises(PolicyViolation, match="age-ambiguous"):
#         assert_adult_subject_allowed(
#             "adult scene with loli character",
#             adult_verified=True,
#             attestation_source="request",
#         )
#     with pytest.raises(PolicyViolation, match="sfw request rejected"):
#         assert_sfw_prompt_allowed("anime portrait, nude, ahegao")


# def test_service_rejects_explicit_prompt_in_sfw_mode(monkeypatch):
#     from core.anime_pipeline_service import validate_request

#     monkeypatch.setenv("ANIME_PIPELINE_PROFILE", "laptop_6gb")
#     req, error = validate_request(
#         {"prompt": "anime portrait, explicit nude", "content_mode": "sfw"}
#     )
#     assert req is None
#     assert error is not None
#     assert "sfw request rejected" in error


# def test_service_auto_promotes_explicit_adult_prompt_on_pc(monkeypatch):
#     from core.anime_pipeline_service import validate_request

#     monkeypatch.delenv("ANIME_PIPELINE_PROFILE", raising=False)
#     monkeypatch.delenv("ANIME_PIPELINE_CONFIG", raising=False)
#     monkeypatch.delenv("ANIME_PIPELINE_ADULT_CONTENT_POLICY", raising=False)
#     request, error = validate_request({"prompt": "adult woman nude portrait"})
#     assert error is None
#     assert request is not None
#     assert request.deployment_profile == "rtx5070"
#     assert request.content_mode == "adult_only"
#     assert request.adult_verified is True
#     assert request.adult_attestation_source == "request"


# def test_service_auto_promoted_adult_prompt_still_blocks_age_ambiguous(monkeypatch):
#     from core.anime_pipeline_service import validate_request

#     monkeypatch.delenv("ANIME_PIPELINE_PROFILE", raising=False)
#     monkeypatch.delenv("ANIME_PIPELINE_CONFIG", raising=False)
#     monkeypatch.delenv("ANIME_PIPELINE_ADULT_CONTENT_POLICY", raising=False)
#     request, error = validate_request({"prompt": "adult loli nude portrait"})
#     assert request is None
#     assert "adult_only rejected" in str(error)


# def test_character_pack_registry_tracks_adult_verification(tmp_path):
#     from image_pipeline.anime_pipeline.character_pack import (
#         character_is_adult_verified,
#         get_character_pack,
#     )

#     registry = tmp_path / "packs.yaml"
#     registry.write_text(
#         "packs:\n"
#         "  - key: original_adult\n"
#         "    display_name: Original Adult\n"
#         "    aliases: [adult_alias]\n"
#         "    adult_verified: true\n",
#         encoding="utf-8",
#     )
#     assert get_character_pack("adult alias", registry) is not None
#     assert character_is_adult_verified("original_adult", registry)
#     assert not character_is_adult_verified("unknown", registry)


# def test_profile_loader_uses_default_wai_v160_checkpoint():
#     from image_pipeline.anime_pipeline.config import load_config

#     with patch.dict("os.environ", {"ANIME_PIPELINE_PROFILE": "pc_12gb"}):
#         config = load_config()
#     assert config.deployment_profile == "pc_12gb"
#     assert config.composition_model.checkpoint == "waiIllustriousSDXL_v160.safetensors"
#     assert config.capabilities["controlnet"] is True
#     assert config.capabilities["ipadapter"] is True
#     assert config.capabilities["flux2_klein"] is False
#     assert config.capabilities["qwen_image_edit"] is False
#     assert config.native_providers == {}
#     assert config.ipadapter.enabled is True
#     assert config.default_loras == [
#         {
#             "name": "Anime_artistic_2.safetensors",
#             "strength": 0.65,
#             "enabled": True,
#         },
#         {
#             "name": "HueSpark1llust.safetensors",
#             "strength": 0.35,
#             "enabled": True,
#         },
#     ]
#     assert any(
#         layer.enabled and layer.union_control_type
#         for layer in config.structure_layers
#     )


# def test_vps_profile_enables_bounded_tier1_detection_only():
#     from image_pipeline.anime_pipeline.config import load_config

#     with patch.dict("os.environ", {"ANIME_PIPELINE_PROFILE": "vps_96gb"}):
#         config = load_config()
#     assert config.detection_inpaint_enabled is True
#     assert config.capabilities["flux2_klein"] is True
#     assert config.capabilities["qwen_image_edit"] is True
#     assert config.capabilities["pre_upscale_v2"] is True
#     assert config.detection_inpaint_max_passes == 5
#     assert config.detection_inpaint_max_regions_per_pass == 4
#     assert {
#         layer["region_type"] for layer in config.detection_inpaint_layers
#     } == {"face", "full_eyes", "eyes", "mouth", "hand"}


# def test_preflight_blocks_missing_required_checkpoint(tmp_path):
#     from image_pipeline.anime_pipeline.config import AnimePipelineConfig, ModelConfig
#     from image_pipeline.anime_pipeline.preflight import run_preflight

#     config = AnimePipelineConfig(
#         composition_model=ModelConfig(checkpoint="missing.safetensors"),
#         beauty_model=ModelConfig(checkpoint="missing.safetensors"),
#         final_model=ModelConfig(checkpoint="missing.safetensors"),
#     )
#     report = run_preflight(config, comfyui_dir=tmp_path)
#     assert report.readiness == "blocked"
#     assert any(path.endswith("missing.safetensors") for path in report.missing_assets)


# def test_preflight_blocks_missing_active_default_lora(tmp_path):
#     from image_pipeline.anime_pipeline.config import AnimePipelineConfig, ModelConfig
#     from image_pipeline.anime_pipeline.preflight import run_preflight

#     checkpoint_dir = tmp_path / "models" / "checkpoints"
#     checkpoint_dir.mkdir(parents=True)
#     (checkpoint_dir / "waiIllustriousSDXL_v160.safetensors").write_bytes(b"ckpt")

#     config = AnimePipelineConfig(
#         composition_model=ModelConfig(checkpoint="waiIllustriousSDXL_v160.safetensors"),
#         beauty_model=ModelConfig(checkpoint="waiIllustriousSDXL_v160.safetensors"),
#         final_model=ModelConfig(checkpoint="waiIllustriousSDXL_v160.safetensors"),
#         default_loras=[
#             {"name": "Anime_artistic_2.safetensors", "enabled": True},
#             {"name": "disabled.safetensors", "enabled": False},
#         ],
#     )

#     report = run_preflight(config, comfyui_dir=tmp_path)
#     assert report.readiness == "blocked"
#     assert any(
#         path.endswith("Anime_artistic_2.safetensors")
#         for path in report.missing_assets
#     )
#     assert not any(path.endswith("disabled.safetensors") for path in report.missing_assets)


# def test_comfy_upload_failure_is_fail_fast():
#     from image_pipeline.anime_pipeline.comfy_client import ComfyClient

#     client = ComfyClient(base_url="http://test:8188")
#     workflow = {
#         "1": {
#             "class_type": "LoadImageFromBase64",
#             "inputs": {"base64_image": "abc"},
#         }
#     }
#     with patch.object(client, "upload_image_b64", side_effect=RuntimeError("upload failed")), pytest.raises(RuntimeError):
#             client._preprocess_workflow(workflow)


# def test_native_workflow_provider_replaces_typed_tokens(tmp_path):
#     from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

#     template = tmp_path / "native.json"
#     template.write_text(
#         json.dumps(
#             {
#                 "1": {
#                     "class_type": "EmptyFlux2LatentImage",
#                     "inputs": {"width": "{{width}}", "label": "seed={{seed}}"},
#                 }
#             }
#         ),
#         encoding="utf-8",
#     )
#     workflow = WorkflowBuilder().build_native(
#         "flux2_klein",
#         {"workflow_template": str(template)},
#         {"width": 768, "seed": 42},
#     )
#     assert workflow["1"]["inputs"]["width"] == 768
#     assert workflow["1"]["inputs"]["label"] == "seed=42"


# def test_policy_router_uses_local_table_without_api_quality_override():
#     from image_pipeline.anime_pipeline.runtime_policy import RuntimePolicy
#     from image_pipeline.workflow.capability_router import CapabilityRouter

#     router = CapabilityRouter(runtime_policy=RuntimePolicy.from_profile("pc_12gb"))
#     assert router.route("t2i", quality="cheap").model == "comfyui-wai-v160"
#     assert router.route("inpaint").model == "comfyui-wai-v160"
#     assert router.route("preview").model == "comfyui-wai-v160"
#     decision = router.route("semantic_edit")
#     assert decision.model == "comfyui-qwen-image-edit-2511"
#     assert decision.location == "local"
#     assert decision.fallbacks == []
#     with pytest.raises(ValueError):
#         router.route("semantic_edit", unavailable={"local"})


# def test_native_qwen_editor_submits_comfy_workflow(tmp_path):
#     from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult
#     from image_pipeline.anime_pipeline.config import AnimePipelineConfig
#     from image_pipeline.semantic_editor.native_comfy_editor import (
#         NativeComfySemanticEditor,
#     )

#     template = tmp_path / "qwen_native.json"
#     template.write_text(
#         json.dumps(
#             {
#                 "1": {
#                     "class_type": "LoadImageFromBase64",
#                     "inputs": {"base64_image": "{{source_image_b64}}"},
#                 },
#                 "2": {
#                     "class_type": "TextEncodeQwenImageEdit",
#                     "inputs": {"prompt": "{{instruction}}"},
#                 },
#             }
#         ),
#         encoding="utf-8",
#     )

#     class FakeClient:
#         base_url = "http://127.0.0.1:8188"

#         def submit_workflow(self, workflow, job_id="", pass_name=""):
#             assert workflow["1"]["inputs"]["base64_image"] == "source-b64"
#             assert workflow["2"]["inputs"]["prompt"] == "add glasses"
#             assert pass_name == "semantic_edit"
#             return ComfyJobResult(success=True, images_b64=["edited-b64"])

#     config = AnimePipelineConfig(
#         deployment_profile="vps_96gb",
#         native_providers={
#             "qwen_image_edit": {
#                 "workflow_template": str(template),
#                 "model": "Qwen-Image-Edit-2511",
#             }
#         },
#     )
#     response = NativeComfySemanticEditor(config, client=FakeClient()).edit(
#         instruction="add glasses",
#         source_image_b64="source-b64",
#     )
#     assert response.success is True
#     assert response.image_b64 == "edited-b64"
#     assert response.provider == "comfyui-native"


# def test_local_dispatcher_runs_qwen_multi_turn_sequentially():
#     from image_pipeline.anime_pipeline.config import AnimePipelineConfig
#     from image_pipeline.anime_pipeline.local_dispatcher import LocalAnimeTaskDispatcher
#     from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
#     from image_pipeline.semantic_editor.qwen_client import EditResponse

#     class FakeEditor:
#         def __init__(self):
#             self.sources = []

#         def edit(self, *, source_image_b64, **kwargs):
#             self.sources.append(source_image_b64)
#             return EditResponse(
#                 success=True,
#                 image_b64=f"turn-{len(self.sources)}",
#                 provider="comfyui-native",
#                 model="qwen-test",
#             )

#     editor = FakeEditor()
#     job = AnimePipelineJob(
#         user_prompt="apply edits",
#         task_type="multi_turn_edit",
#         source_image_b64="source",
#         edit_turns=["add glasses", "change scarf"],
#     )
#     LocalAnimeTaskDispatcher(
#         AnimePipelineConfig(capabilities={"qwen_image_edit": True}),
#         editor=editor,
#     ).run(job)

#     assert editor.sources == ["source", "turn-1"]
#     assert job.final_image_b64 == "turn-2"
#     assert [item.stage for item in job.intermediates] == [
#         "semantic_edit_turn_1",
#         "semantic_edit_turn_2",
#         "multi_turn_edit",
#     ]
#     assert (
#         job.metadata["route_provenance"]["executor"]
#         == "native_qwen_image_edit_sequential"
#     )


# def test_native_flux_composer_submits_local_workflow(tmp_path):
#     from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult
#     from image_pipeline.anime_pipeline.config import AnimePipelineConfig
#     from image_pipeline.multi_reference.native_comfy_composer import (
#         NativeComfyMultiRefComposer,
#     )

#     template = tmp_path / "flux_native.json"
#     template.write_text(
#         json.dumps(
#             {
#                 "1": {
#                     "class_type": "LoadImageFromBase64",
#                     "inputs": {"base64_image": "{{reference_0_b64}}"},
#                 },
#                 "2": {
#                     "class_type": "CLIPTextEncode",
#                     "inputs": {"text": "{{prompt}}"},
#                 },
#             }
#         ),
#         encoding="utf-8",
#     )

#     class FakeClient:
#         base_url = "http://127.0.0.1:8188"

#         def submit_workflow(self, workflow, job_id="", pass_name=""):
#             assert workflow["1"]["inputs"]["base64_image"] == "face-b64"
#             assert workflow["2"]["inputs"]["text"] == "combine references"
#             assert pass_name == "multi_ref"
#             return ComfyJobResult(success=True, images_b64=["combined-b64"])

#     config = AnimePipelineConfig(
#         native_providers={
#             "flux2_klein": {
#                 "workflow_template": str(template),
#                 "model": "flux-test",
#             }
#         }
#     )
#     response = NativeComfyMultiRefComposer(config, client=FakeClient()).compose(
#         prompt="combine references",
#         reference_images_b64=["face-b64"],
#     )
#     assert response.success is True
#     assert response.image_b64 == "combined-b64"
#     assert response.model == "flux-test"


# def test_legacy_semantic_editor_has_no_cloud_fallback_by_default():
#     from image_pipeline.semantic_editor.editor import SemanticEditor

#     editor = SemanticEditor(prefer_vps=False)
#     assert editor._fallback is None
#     assert editor._allow_cloud_fallbacks is False


# def test_unscored_critique_never_passes():
#     from image_pipeline.anime_pipeline.schemas import CritiqueReport

#     report = CritiqueReport(
#         anatomy_score=10,
#         face_score=10,
#         unscored=True,
#         scoring_error="worker unavailable",
#     )
#     assert report.passed is False
#     assert report.to_dict()["unscored"] is True


# def test_live_benchmark_requires_real_pipeline_and_scorer(tmp_path):
#     from image_pipeline.evaluator.benchmark_runner import BenchmarkRunner

#     suite = tmp_path / "suite.yaml"
#     suite.write_text(
#         "test_cases:\n"
#         "  - id: T-001\n"
#         "    category: smoke\n"
#         "    instruction: test\n",
#         encoding="utf-8",
#     )
#     runner = BenchmarkRunner(benchmark_path=suite)
#     with pytest.raises(RuntimeError, match="requires both"):
#         asyncio.run(runner.run_suite())


# def test_benchmark_scores_with_source_references_and_case_dimensions(tmp_path, monkeypatch):
#     from image_pipeline.evaluator import experiment_log
#     from image_pipeline.evaluator.benchmark_runner import (
#         BenchmarkExecution,
#         BenchmarkRunner,
#     )
#     from image_pipeline.job_schema import EvalResult

#     suite = tmp_path / "suite.yaml"
#     suite.write_text(
#         "test_cases:\n"
#         "  - id: EDIT-001\n"
#         "    category: semantic_edit\n"
#         "    instruction: add glasses\n"
#         "    dimensions: [semantic_edit]\n"
#         "    setup:\n"
#         "      mode: semantic_edit\n",
#         encoding="utf-8",
#     )
#     output = tmp_path / "output.png"
#     source = tmp_path / "source.png"
#     reference = tmp_path / "reference.png"
#     for path in (output, source, reference):
#         path.write_bytes(b"png")

#     class FakePipeline:
#         def __init__(self):
#             self.prepare_calls = 0

#         def prepare_suite(self, cases, *, parity=False, run_id=""):
#             self.prepare_calls += 1

#         async def __call__(self, job):
#             return BenchmarkExecution(
#                 output_path=output,
#                 source_image_path=source,
#                 reference_paths=[reference],
#             )

#     class FakeScorer:
#         def __init__(self):
#             self.kwargs = {}

#         async def score(self, job, output_path, **kwargs):
#             self.kwargs = kwargs
#             result = EvalResult(scores={"semantic_edit": 1.0}, evaluated=["semantic_edit"])
#             result.evaluate()
#             return result

#     monkeypatch.setattr(experiment_log, "_BENCHMARK_DIR", tmp_path / "records")
#     pipeline = FakePipeline()
#     scorer = FakeScorer()
#     asyncio.run(
#         BenchmarkRunner(suite, scorer=scorer, pipeline_fn=pipeline).run_suite()
#     )

#     assert pipeline.prepare_calls == 1
#     assert scorer.kwargs["source_image_path"] == source
#     assert scorer.kwargs["reference_paths"] == [reference]
#     assert scorer.kwargs["force_dimensions"] == ["semantic_edit"]


# def test_benchmark_case_conversion_preserves_multi_turn_sequence():
#     from image_pipeline.evaluator.benchmark_runner import BenchmarkRunner

#     job = BenchmarkRunner._case_to_job(
#         {
#             "instruction": "apply edits",
#             "setup": {"mode": "multi_turn_edit"},
#             "turns": [
#                 {"instruction": "add glasses"},
#                 {"instruction": "change scarf"},
#             ],
#         }
#     )
#     assert job.user_instruction == "apply edits"
#     assert job.edit_turns == ["add glasses", "change scarf"]


# def test_benchmark_dry_run_records_stub_without_execution_error(tmp_path):
#     from image_pipeline.evaluator import experiment_log
#     from image_pipeline.evaluator.benchmark_runner import BenchmarkRunner

#     suite = tmp_path / "suite.yaml"
#     suite.write_text(
#         "test_cases:\n"
#         "  - id: T-001\n"
#         "    category: smoke\n"
#         "    difficulty: easy\n"
#         "    instruction: test\n"
#         "    dimensions: [instruction_adherence]\n",
#         encoding="utf-8",
#     )

#     with patch.object(experiment_log, "_BENCHMARK_DIR", tmp_path / "records"):
#         summary = asyncio.run(BenchmarkRunner(suite).run_suite(dry_run=True))

#     assert summary.total_cases == 1
#     assert summary.execution_errors == []


# def test_benchmark_adapter_lists_all_missing_fixtures(tmp_path, monkeypatch):
#     from image_pipeline.evaluator import anime_benchmark_adapter
#     from image_pipeline.evaluator.anime_benchmark_adapter import AnimeBenchmarkAdapter

#     monkeypatch.setattr(
#         anime_benchmark_adapter,
#         "run_preflight",
#         lambda *args, **kwargs: SimpleNamespace(
#             readiness="ready",
#             endpoint_health={"comfyui": True},
#         ),
#     )
#     adapter = AnimeBenchmarkAdapter(artifact_root=tmp_path)
#     with pytest.raises(RuntimeError) as exc_info:
#         adapter.prepare_suite(
#             [
#                 {
#                     "setup": {
#                         "source_image": "fixtures/missing-source.png",
#                         "references": [{"image": "fixtures/missing-ref.png"}],
#                     }
#                 }
#             ]
#         )
#     message = str(exc_info.value)
#     assert "missing-source.png" in message
#     assert "missing-ref.png" in message


# def test_experiment_log_execution_error_fails_quality_gate(tmp_path):
#     from image_pipeline.evaluator.experiment_log import ExperimentLog
#     from image_pipeline.job_schema import EvalResult, ImageJob

#     result = EvalResult(scores={"instruction_adherence": 1.0}, evaluated=["instruction_adherence"])
#     result.evaluate()
#     log = ExperimentLog(output_dir=tmp_path)
#     log.record_case("T-001", ImageJob(user_instruction="test"), result)
#     log.record_execution_error("T-002", "executor failed")
#     summary = log.summarize()
#     assert summary.execution_errors == ["T-002:executor failed"]
#     assert summary.local_quality_gate_passed is False


# def test_benchmark_auto_suite_resolves_to_sfw_for_quality_profiles():
#     from image_pipeline.evaluator.benchmark_config import resolve_suite_path

#     assert resolve_suite_path("auto", "pc_12gb").name == "anime_benchmark_suite.yaml"
#     assert resolve_suite_path("auto", "rtx5070").name == "anime_benchmark_suite.yaml"
#     assert resolve_suite_path("auto", "vps_96gb").name == "anime_benchmark_suite.yaml"


# def test_run_benchmark_env_selects_profile_and_forces_sfw_policy(monkeypatch):
#     from scripts import run_anime_benchmark

#     monkeypatch.setenv("ANIME_PIPELINE_CONFIG", "app/configs_vps/custom.yaml")
#     monkeypatch.setenv("ANIME_PIPELINE_ADULT_CONTENT_POLICY", "worker_default")

#     selected_suite = run_anime_benchmark._configure_benchmark_env("pc_12gb", "auto")

#     assert selected_suite == "sfw"
#     assert "ANIME_PIPELINE_CONFIG" not in os.environ
#     assert os.environ["ANIME_PIPELINE_PROFILE"] == "pc_12gb"
#     assert os.environ["ANIME_PIPELINE_ADULT_CONTENT_POLICY"] == "sfw_only"


# def test_evidence_summary_strips_private_prompts_paths_and_reasoning(tmp_path):
#     from scripts import anime_benchmark_evidence

#     artifact_root = tmp_path / "private"
#     run_dir = artifact_root / "run-001"
#     report_root = tmp_path / "public"
#     run_dir.mkdir(parents=True)
#     (run_dir / "summary.json").write_text(
#         json.dumps(
#             {
#                 "run_id": "run-001",
#                 "stack_version": "abc123",
#                 "execution_errors": ["private/path/error"],
#             }
#         ),
#         encoding="utf-8",
#     )
#     (run_dir / "CASE-001.json").write_text(
#         json.dumps(
#             {
#                 "case_id": "CASE-001",
#                 "category": "identity",
#                 "instruction": "private prompt",
#                 "scores": {"identity_consistency": 0.9},
#                 "thresholds": {"identity_consistency": 0.7},
#                 "overall_score": 0.9,
#                 "case_passed": True,
#                 "judge_model": "local-vlm",
#                 "judge_reasoning": {"identity_consistency": "private reasoning"},
#                 "output_image_path": "private/output.png",
#             }
#         ),
#         encoding="utf-8",
#     )

#     anime_benchmark_evidence.summarize(
#         SimpleNamespace(
#             artifact_root=str(artifact_root),
#             run_id="run-001",
#             report_root=str(report_root),
#         )
#     )

#     public_summary = json.loads(
#         (report_root / "run-001" / "summary.json").read_text(encoding="utf-8")
#     )
#     public_cases = json.loads(
#         (report_root / "run-001" / "case_scores.json").read_text(encoding="utf-8")
#     )
#     assert public_summary["execution_error_count"] == 1
#     assert "execution_errors" not in public_summary
#     assert public_summary["comparator_review_complete"] is False
#     assert public_summary["parity_evidence_complete"] is False
#     assert "instruction" not in public_cases[0]
#     assert "judge_reasoning" not in public_cases[0]
#     assert "output_image_path" not in public_cases[0]


# def test_evidence_alias_import_and_summary_reports_review_coverage(tmp_path):
#     from scripts import anime_benchmark_evidence

#     artifact_root = tmp_path / "private"
#     run_dir = artifact_root / "run-001"
#     report_root = tmp_path / "public"
#     capture_dirs = {
#         "chatgpt_pro": tmp_path / "chatgpt",
#         "gemini_nano_banana": tmp_path / "nano_banana_2",
#         "nano_banana_pro": tmp_path / "nano_banana_pro",
#     }
#     run_dir.mkdir(parents=True)
#     for capture_dir in capture_dirs.values():
#         capture_dir.mkdir()
#         (capture_dir / "CASE-001.png").write_bytes(b"comparator")
#     output = run_dir / "CASE-001.local.png"
#     output.write_bytes(b"local")
#     (run_dir / "summary.json").write_text(
#         json.dumps(
#             {
#                 "run_id": "run-001",
#                 "stack_version": "abc123",
#                 "local_quality_gate_passed": True,
#                 "nano_banana_qualified": True,
#                 "execution_errors": [],
#             }
#         ),
#         encoding="utf-8",
#     )
#     (run_dir / "CASE-001.json").write_text(
#         json.dumps(
#             {
#                 "case_id": "CASE-001",
#                 "category": "identity",
#                 "difficulty": "medium",
#                 "scores": {"identity_consistency": 0.9},
#                 "thresholds": {"identity_consistency": 0.7},
#                 "overall_score": 0.9,
#                 "case_passed": True,
#                 "judge_model": "local-vlm",
#                 "output_image_path": str(output),
#             }
#         ),
#         encoding="utf-8",
#     )

#     for provider, capture_dir in capture_dirs.items():
#         anime_benchmark_evidence.import_comparator(
#             SimpleNamespace(
#                 artifact_root=str(artifact_root),
#                 run_id="run-001",
#                 provider=provider,
#                 capture_dir=str(capture_dir),
#             )
#         )
#     assert (run_dir / "comparators" / "chatgpt_images" / "CASE-001.png").is_file()
#     assert (run_dir / "comparators" / "nano_banana_2" / "CASE-001.png").is_file()
#     assert (run_dir / "comparators" / "nano_banana_pro" / "CASE-001.png").is_file()

#     anime_benchmark_evidence.build_review(
#         SimpleNamespace(artifact_root=str(artifact_root), run_id="run-001", seed=7)
#     )
#     (run_dir / "comparator_verdicts.json").write_text(
#         json.dumps(
#             [
#                 {
#                     "case_id": "CASE-001",
#                     "provider": "chatgpt_pro",
#                     "verdict": "local_preferred",
#                 }
#             ]
#         ),
#         encoding="utf-8",
#     )
#     anime_benchmark_evidence.summarize(
#         SimpleNamespace(
#             artifact_root=str(artifact_root),
#             run_id="run-001",
#             report_root=str(report_root),
#         )
#     )

#     public_summary = json.loads(
#         (report_root / "run-001" / "summary.json").read_text(encoding="utf-8")
#     )
#     comparator = json.loads(
#         (report_root / "run-001" / "comparator_verdict.json").read_text(
#             encoding="utf-8"
#         )
#     )
#     coverage = json.loads(
#         (report_root / "run-001" / "comparator_coverage.json").read_text(
#             encoding="utf-8"
#         )
#     )
#     assert "nano_banana_qualified" not in public_summary
#     assert public_summary["comparator_review_complete"] is True
#     assert public_summary["parity_evidence_complete"] is True
#     assert comparator == {"chatgpt_images": {"local_preferred": 1}}
#     assert coverage["review_packet_complete"] is True
#     assert coverage["comparator_captures_complete"] is True
#     assert coverage["verdict_complete"] is True


# def test_anime_benchmark_suite_contains_48_sfw_cases():
#     suite_path = APP_ROOT / "configs_vps" / "anime_benchmark_suite.yaml"
#     suite = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
#     assert suite["content_mode"] == "sfw"
#     assert len(suite["test_cases"]) == 48


# def test_service_request_contract_disables_laptop_adult_content():
#     from core.anime_pipeline_service import validate_request

#     with patch.dict("os.environ", {"ANIME_PIPELINE_PROFILE": "laptop_6gb"}):
#         request, error = validate_request(
#             {"prompt": "original adult character portrait", "content_mode": "adult_only"}
#         )
#         assert request is None
#         assert "disabled on laptop_6gb" in str(error)

#         request, error = validate_request(
#             {
#                 "prompt": "original adult character portrait",
#                 "content_mode": "adult_only",
#                 "adult_verified": True,
#                 "deployment_profile": "laptop_6gb",
#             }
#         )
#         assert request is None
#         assert "disabled on laptop_6gb" in str(error)


# def test_service_request_contract_pc_profile_uses_request_opt_in():
#     from core.anime_pipeline_service import validate_request

#     with patch.dict(
#         "os.environ",
#         {
#             "ANIME_PIPELINE_PROFILE": "pc_12gb",
#         },
#     ):
#         request, error = validate_request({"prompt": "verified adult portrait"})
#     assert error is None
#     assert request is not None
#     assert request.content_mode == "sfw"
#     assert request.adult_verified is False

#     with patch.dict("os.environ", {"ANIME_PIPELINE_PROFILE": "pc_12gb"}):
#         request, error = validate_request(
#             {
#                 "prompt": "verified adult nude portrait",
#                 "content_mode": "adult_only",
#                 "adult_verified": True,
#             }
#         )
#     assert error is None
#     assert request is not None
#     assert request.content_mode == "adult_only"
#     assert request.adult_verified is True
#     assert request.adult_attestation_source == "request"


# def test_service_request_contract_allows_laptop_sfw_validator_opt_in():
#     from core.anime_pipeline_service import validate_request

#     with patch.dict("os.environ", {"ANIME_PIPELINE_PROFILE": "laptop_6gb"}):
#         request, error = validate_request(
#             {
#                 "prompt": "anime landscape",
#                 "validator_mode": "external_sfw_opt_in",
#             }
#         )
#     assert error is None
#     assert request is not None
#     assert request.validator_mode == "external_sfw_opt_in"


# def test_service_request_contract_accepts_typed_references_and_turns():
#     from core.anime_pipeline_service import build_job, validate_request

#     with patch.dict("os.environ", {"ANIME_PIPELINE_PROFILE": "laptop_6gb"}):
#         request, error = validate_request(
#             {
#                 "prompt": "add glasses, then change the scarf",
#                 "task_type": "multi_turn_edit",
#                 "source_image": "source-b64",
#                 "references": [{"role": "face", "image_b64": "face-b64"}],
#                 "turns": ["add glasses", {"instruction": "change the scarf"}],
#             }
#         )
#     assert error is None
#     assert request is not None
#     job = build_job(request)
#     assert job.task_type == "multi_turn_edit"
#     assert job.source_image_b64 == "source-b64"
#     assert job.references[0].role == "face"
#     assert job.edit_turns == ["add glasses", "change the scarf"]


# def test_identity_plan_enables_ipadapter_only_for_identity_task():
#     from image_pipeline.anime_pipeline.agents.layer_planner import LayerPlannerAgent
#     from image_pipeline.anime_pipeline.config import (
#         AnimePipelineConfig,
#         IPAdapterConfig,
#     )
#     from image_pipeline.anime_pipeline.schemas import (
#         AnimePipelineJob,
#         PipelineReference,
#     )

#     config = AnimePipelineConfig(ipadapter=IPAdapterConfig(enabled=True))
#     identity_job = AnimePipelineJob(
#         user_prompt="portrait",
#         task_type="identity",
#         references=[PipelineReference(role="face", image_b64="face-b64")],
#     )
#     t2i_job = AnimePipelineJob(
#         user_prompt="portrait",
#         task_type="t2i",
#         references=[PipelineReference(role="face", image_b64="face-b64")],
#     )

#     identity_plan = LayerPlannerAgent(config).build_plan(identity_job)
#     t2i_plan = LayerPlannerAgent(config).build_plan(t2i_job)

#     assert identity_plan.composition_pass.ipadapter_image_b64 == "face-b64"
#     assert t2i_plan.composition_pass.ipadapter_image_b64 == ""


# def test_service_build_job_applies_local_character_pack():
#     from image_pipeline.anime_pipeline.character_pack import CharacterPack

#     from core.anime_pipeline_service import PipelineRequest, build_job

#     pack = CharacterPack(
#         key="original_adult",
#         prompt_alias="blue_hair_adult",
#         trigger_words=("silver_eyes",),
#         loras=({"name": "identity.safetensors", "enabled": True},),
#         checksums={"identity.safetensors": "abc123"},
#         adult_verified=True,
#     )
#     with patch(
#         "image_pipeline.anime_pipeline.character_pack.get_character_pack",
#         return_value=pack,
#     ):
#         job = build_job(
#             PipelineRequest(prompt="portrait", character_key="original_adult")
#         )
#     assert job.user_prompt == "portrait, blue_hair_adult, silver_eyes"
#     assert job.user_loras[0]["name"] == "identity.safetensors"
#     assert job.metadata["character_pack"]["key"] == "original_adult"
#     assert job.metadata["model_checksums"]["identity.safetensors"] == "abc123"


# def test_detection_inpaint_blocks_sensitive_regions_for_sfw():
#     from image_pipeline.anime_pipeline.agents.detection_inpaint import (
#         _region_allowed_for_job,
#     )
#     from image_pipeline.anime_pipeline.schemas import AnimePipelineJob

#     sfw_job = AnimePipelineJob(user_prompt="portrait", content_mode="sfw")
#     assert _region_allowed_for_job("face", sfw_job)
#     assert not _region_allowed_for_job("breasts", sfw_job)
#     assert not _region_allowed_for_job("underwear", sfw_job)
#     assert not _region_allowed_for_job("torso", sfw_job)

#     adult_job = AnimePipelineJob(
#         user_prompt="portrait",
#         content_mode="adult_only",
#         adult_verified=True,
#     )
#     assert _region_allowed_for_job("breasts", adult_job)


# def test_local_only_scorer_has_no_cloud_fallback():
#     from image_pipeline.anime_pipeline.runtime_policy import RuntimePolicy
#     from image_pipeline.evaluator.scorer import Scorer

#     scorer = Scorer(
#         local_only=True,
#         local_vlm_url="http://127.0.0.1:8080/v1",
#         local_vlm_model="local-test-vlm",
#         runtime_policy=RuntimePolicy.from_profile("pc_12gb"),
#     )
#     assert len(scorer._judge_chain) == 1
#     assert scorer._judge_chain[0].provider == "local"


# def test_result_store_writes_job_local_and_canonical_manifests(tmp_path):
#     from image_pipeline.anime_pipeline.result_store import ResultStore
#     from image_pipeline.anime_pipeline.schemas import AnimePipelineJob

#     intermediate = tmp_path / "intermediate"
#     metadata = tmp_path / "metadata"
#     job = AnimePipelineJob(user_prompt="portrait")
#     local_path = Path(
#         ResultStore(base_dir=intermediate, metadata_dir=metadata).save_manifest(job)
#     )
#     canonical_path = metadata / f"{job.job_id}.json"

#     assert local_path == intermediate / job.job_id / "output_manifest.json"
#     assert local_path.is_file()
#     assert canonical_path.is_file()
#     assert job.manifest_path == str(canonical_path)
#     assert json.loads(canonical_path.read_text(encoding="utf-8"))["manifest_path"] == str(
#         canonical_path
#     )


# def test_native_workflow_provider_rejects_operator_stub(tmp_path):
#     from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

#     template = tmp_path / "stub.json"
#     template.write_text(
#         json.dumps({"1": {"class_type": "STUB_OPERATOR_MUST_EXPORT", "inputs": {}}}),
#         encoding="utf-8",
#     )
#     with pytest.raises(ValueError, match="still a stub"):
#         WorkflowBuilder().build_native("flux2_klein", {"workflow_template": str(template)}, {})


# def test_preflight_blocks_required_native_workflow_stub(tmp_path, monkeypatch):
#     from image_pipeline.anime_pipeline import preflight
#     from image_pipeline.anime_pipeline.config import AnimePipelineConfig

#     stub = tmp_path / "stub.json"
#     stub.write_text(
#         json.dumps({"1": {"class_type": "STUB_OPERATOR_MUST_EXPORT", "inputs": {}}}),
#         encoding="utf-8",
#     )
#     manifest = tmp_path / "assets.yaml"
#     manifest.write_text(
#         "assets:\n"
#         "  - id: flux2_klein_workflow\n"
#         "    profiles: [rtx5070]\n"
#         f"    destination: {stub.as_posix()}\n"
#         "    sha256: placeholder\n"
#         "    required_for_capability: flux2_klein\n",
#         encoding="utf-8",
#     )
#     monkeypatch.setattr(preflight, "_PROVISIONING_MANIFEST", manifest)
#     report = preflight.run_preflight(
#         AnimePipelineConfig(capabilities={"flux2_klein": True}),
#         comfyui_dir=tmp_path / "ComfyUI",
#     )
#     assert report.readiness == "blocked"
#     assert report.capabilities["flux2_klein"] == "blocked"
#     assert any(check.detail == "Replace operator-export workflow stub" for check in report.checks)


# def test_preflight_blocks_pc_worker_without_operator_assertion(monkeypatch):
#     from image_pipeline.anime_pipeline.config import load_config
#     from image_pipeline.anime_pipeline.preflight import run_preflight

#     monkeypatch.setenv("ANIME_PIPELINE_PROFILE", "pc_12gb")
#     monkeypatch.setenv("ANIME_PIPELINE_ADULT_CONTENT_POLICY", "worker_default")
#     monkeypatch.delenv("ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER", raising=False)
#     report = run_preflight(load_config())
#     assert report.readiness == "blocked"
#     assert report.capabilities["flux2_klein"] == "disabled"
#     assert any("ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER=1" in error for error in report.errors)


# def test_parity_preflight_checks_comfyui_node_contract(tmp_path, monkeypatch):
#     from image_pipeline.anime_pipeline import preflight
#     from image_pipeline.anime_pipeline.config import AnimePipelineConfig, ModelConfig

#     checkpoint = tmp_path / "ComfyUI" / "models" / "checkpoints" / "test.safetensors"
#     checkpoint.parent.mkdir(parents=True)
#     checkpoint.write_bytes(b"x")
#     digest = hashlib.sha256(b"x").hexdigest()
#     manifest = tmp_path / "assets.yaml"
#     manifest.write_text(
#         "assets:\n"
#         "  - id: checkpoint\n"
#         "    profiles: [rtx5070]\n"
#         "    destination: ComfyUI/models/checkpoints/test.safetensors\n"
#         "    source_url: https://example.invalid/test\n"
#         "    license: operator-verified\n"
#         f"    sha256: {digest}\n",
#         encoding="utf-8",
#     )
#     monkeypatch.setattr(preflight, "_PROVISIONING_MANIFEST", manifest)
#     monkeypatch.setattr(preflight, "_probe", lambda *args, **kwargs: True)
#     monkeypatch.setattr(
#         preflight,
#         "_probe_json",
#         lambda *args, **kwargs: {"SetUnionControlNetType": {}},
#     )
#     model = ModelConfig(checkpoint="test.safetensors")
#     config = AnimePipelineConfig(
#         capabilities={"controlnet": True, "ipadapter": True},
#         composition_model=model,
#         beauty_model=model,
#         final_model=model,
#     )

#     report = preflight.run_preflight(
#         config,
#         comfyui_dir=tmp_path / "ComfyUI",
#         probe_remote=True,
#         parity=True,
#     )

#     assert report.readiness == "blocked"
#     assert report.node_contract["SetUnionControlNetType"] is True
#     assert report.node_contract["IPAdapter"] is False
#     assert any("missing required node classes" in error for error in report.errors)


# def test_adult_benchmark_suite_contains_56_local_fixture_cases():
#     suite_path = APP_ROOT / "configs_vps" / "anime_benchmark_suite_adult_only.yaml"
#     suite = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
#     assert suite["content_mode"] == "adult_only"
#     assert suite["requires_adult_verified"] is True
#     assert len(suite["test_cases"]) == 56


# def test_adult_benchmark_requires_explicit_verification():
#     from image_pipeline.evaluator.benchmark_runner import BenchmarkRunner

#     suite_path = APP_ROOT / "configs_vps" / "anime_benchmark_suite_adult_only.yaml"
#     runner = BenchmarkRunner(benchmark_path=suite_path)
#     with pytest.raises(RuntimeError, match="adult_only benchmark requires"):
#         asyncio.run(runner.run_suite(dry_run=True))
