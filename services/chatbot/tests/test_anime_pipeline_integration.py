"""
Tests for the anime pipeline service layer and Flask routes.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass, field


# ════════════════════════════════════════════════════════════════════════
# Service-layer tests
# ════════════════════════════════════════════════════════════════════════


class TestPipelineEnabled:
    def test_enabled_true(self):
        with patch.dict("os.environ", {"IMAGE_PIPELINE_V2": "true"}):
            from core.anime_pipeline_service import pipeline_enabled
            assert pipeline_enabled() is True

    def test_enabled_false(self):
        with patch.dict("os.environ", {"IMAGE_PIPELINE_V2": ""}, clear=False):
            from core.anime_pipeline_service import pipeline_enabled
            assert pipeline_enabled() is False

    def test_enabled_1(self):
        with patch.dict("os.environ", {"IMAGE_PIPELINE_V2": "1"}):
            from core.anime_pipeline_service import pipeline_enabled
            assert pipeline_enabled() is True


class TestComfyuiUrl:
    def test_default(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("COMFYUI_URL", None)
            from core.anime_pipeline_service import comfyui_url
            assert comfyui_url() == "http://127.0.0.1:8188"

    def test_custom(self):
        with patch.dict("os.environ", {"COMFYUI_URL": "http://gpu:8188"}):
            from core.anime_pipeline_service import comfyui_url
            assert comfyui_url() == "http://gpu:8188"


class TestCheckAvailability:
    def test_all_ok(self):
        from core.anime_pipeline_service import check_availability
        with patch("core.anime_pipeline_service.pipeline_enabled", return_value=True), \
             patch("core.anime_pipeline_service.comfyui_reachable", return_value=True):
            result = check_availability()
            assert result.available is True
            assert result.errors == []

    def test_flag_off(self):
        from core.anime_pipeline_service import check_availability
        with patch("core.anime_pipeline_service.pipeline_enabled", return_value=False), \
             patch("core.anime_pipeline_service.comfyui_reachable", return_value=True):
            result = check_availability()
            assert result.available is False
            assert any("disabled" in e.lower() for e in result.errors)

    def test_comfyui_down(self):
        from core.anime_pipeline_service import check_availability
        with patch("core.anime_pipeline_service.pipeline_enabled", return_value=True), \
             patch("core.anime_pipeline_service.comfyui_reachable", return_value=False):
            result = check_availability()
            assert result.available is False
            assert any("comfyui" in e.lower() for e in result.errors)

    def test_both_bad(self):
        from core.anime_pipeline_service import check_availability
        with patch("core.anime_pipeline_service.pipeline_enabled", return_value=False), \
             patch("core.anime_pipeline_service.comfyui_reachable", return_value=False):
            result = check_availability()
            assert result.available is False
            assert len(result.errors) == 2

    def test_to_dict(self):
        from core.anime_pipeline_service import AvailabilityResult
        r = AvailabilityResult(available=True, feature_flag=True, comfyui_reachable=True)
        d = r.to_dict()
        assert d["available"] is True
        assert d["errors"] == []


class TestValidateRequest:
    def test_missing_prompt(self):
        from core.anime_pipeline_service import validate_request
        req, err = validate_request({})
        assert req is None
        assert "required" in err.lower()

    def test_prompt_too_long(self):
        from core.anime_pipeline_service import validate_request
        req, err = validate_request({"prompt": "x" * 2001})
        assert req is None
        assert "too long" in err.lower()

    def test_too_many_refs(self):
        from core.anime_pipeline_service import validate_request
        req, err = validate_request({"prompt": "test", "reference_images": ["a"] * 5})
        assert req is None
        assert "too many" in err.lower()

    def test_valid_minimal(self):
        from core.anime_pipeline_service import validate_request
        req, err = validate_request({"prompt": "a cute cat"})
        assert err is None
        assert req.prompt == "a cute cat"
        assert req.preset == "anime_quality"
        assert req.quality_mode == "quality"

    def test_valid_full(self):
        from core.anime_pipeline_service import validate_request
        req, err = validate_request({
            "prompt": "test",
            "reference_images": ["img1", "img2"],
            "preset": "anime_speed",
            "quality_mode": "fast",
            "model_base": "base.safetensors",
            "debug": True,
            "width": 1024,
            "height": 1024,
        })
        assert err is None
        assert req.preset == "anime_speed"
        assert req.quality_mode == "fast"
        assert req.debug is True
        assert len(req.reference_images_b64) == 2

    def test_invalid_preset_falls_back(self):
        from core.anime_pipeline_service import validate_request
        req, err = validate_request({"prompt": "test", "preset": "invalid"})
        assert err is None
        assert req.preset == "anime_quality"

    def test_invalid_quality_falls_back(self):
        from core.anime_pipeline_service import validate_request
        req, err = validate_request({"prompt": "test", "quality_mode": "ultra"})
        assert err is None
        assert req.quality_mode == "quality"


class TestSSELine:
    def test_format(self):
        from core.anime_pipeline_service import _sse_line
        line = _sse_line("ap_status", {"msg": "ok"})
        assert line.startswith("event: ap_status\n")
        assert '"msg": "ok"' in line
        assert line.endswith("\n\n")


class TestBuildJob:
    def test_creates_job(self):
        from core.anime_pipeline_service import PipelineRequest, build_job

        # Mock the import
        mock_job = MagicMock()
        mock_job.job_id = "test-123"
        mock_cls = MagicMock(return_value=mock_job)

        with patch.dict("sys.modules", {
            "image_pipeline": MagicMock(),
            "image_pipeline.anime_pipeline": MagicMock(AnimePipelineJob=mock_cls),
        }):
            req = PipelineRequest(prompt="test", preset="anime_speed", quality_mode="fast")
            job = build_job(req)
            assert job == mock_job
            mock_cls.assert_called_once()


class TestStreamPipeline:
    def test_emits_events(self):
        from core.anime_pipeline_service import PipelineRequest, stream_pipeline

        mock_job = MagicMock()
        mock_job.job_id = "j1"
        mock_job.status.value = "completed"
        mock_job.final_image_b64 = "AAAA"
        mock_job.to_dict.return_value = {"job_id": "j1"}
        mock_job.total_latency_ms = 1234.5
        mock_job.stages_executed = ["vision_analysis"]
        mock_job.refine_rounds = 1
        mock_job.models_used = ["model.safetensors"]
        mock_job.intermediates = []

        mock_orch = MagicMock()
        mock_orch.run_stream.return_value = iter([
            {"event": "anime_pipeline_pipeline_start", "data": {"stages": ["vision_analysis"]}},
            {"event": "anime_pipeline_stage_start", "data": {"stage": "vision_analysis", "stage_num": 1, "total_stages": 7}},
            {"event": "anime_pipeline_stage_complete", "data": {"stage": "vision_analysis", "stage_num": 1, "latency_ms": 500}},
            {"event": "anime_pipeline_pipeline_complete", "data": {}},
        ])
        mock_orch_cls = MagicMock(return_value=mock_orch)

        with patch.dict("sys.modules", {
            "image_pipeline": MagicMock(),
            "image_pipeline.anime_pipeline": MagicMock(
                AnimePipelineOrchestrator=mock_orch_cls,
                AnimePipelineJob=MagicMock(return_value=mock_job),
            ),
        }):
            req = PipelineRequest(prompt="test")
            frames = list(stream_pipeline(req))
            events = [f.split("\n")[0] for f in frames if f.startswith("event:")]
            assert "event: ap_status" in events
            assert "event: ap_stage_start" in events
            assert "event: ap_stage_done" in events
            assert "event: ap_result" in events
            assert "event: ap_done" in events

    def test_error_handling(self):
        from core.anime_pipeline_service import PipelineRequest, stream_pipeline

        mock_job = MagicMock()
        mock_job.job_id = "j2"
        mock_job.status.value = "failed"
        mock_job.final_image_b64 = None
        mock_job.to_dict.return_value = {"job_id": "j2"}
        mock_job.total_latency_ms = 0
        mock_job.stages_executed = []
        mock_job.refine_rounds = 0
        mock_job.models_used = []
        mock_job.intermediates = []

        mock_orch = MagicMock()
        mock_orch.run_stream.side_effect = RuntimeError("GPU OOM")
        mock_orch_cls = MagicMock(return_value=mock_orch)

        with patch.dict("sys.modules", {
            "image_pipeline": MagicMock(),
            "image_pipeline.anime_pipeline": MagicMock(
                AnimePipelineOrchestrator=mock_orch_cls,
                AnimePipelineJob=MagicMock(return_value=mock_job),
            ),
        }):
            req = PipelineRequest(prompt="test")
            frames = list(stream_pipeline(req))
            error_frames = [f for f in frames if "ap_error" in f]
            assert len(error_frames) >= 1
            assert "GPU OOM" in error_frames[0]


# ════════════════════════════════════════════════════════════════════════
# Flask route tests
# ════════════════════════════════════════════════════════════════════════

@pytest.fixture
def flask_app():
    """Minimal Flask app with the anime_pipeline blueprint."""
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"

    from routes.anime_pipeline import anime_pipeline_bp
    app.register_blueprint(anime_pipeline_bp)
    return app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


class TestHealthEndpoint:
    def test_available(self, client):
        with patch("core.anime_pipeline_service.pipeline_enabled", return_value=True), \
             patch("core.anime_pipeline_service.comfyui_reachable", return_value=True):
            resp = client.get("/api/anime-pipeline/health")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["available"] is True

    def test_unavailable(self, client):
        with patch("core.anime_pipeline_service.pipeline_enabled", return_value=False), \
             patch("core.anime_pipeline_service.comfyui_reachable", return_value=False):
            resp = client.get("/api/anime-pipeline/health")
            assert resp.status_code == 503
            data = resp.get_json()
            assert data["available"] is False


class TestStreamEndpoint:
    def test_unavailable_returns_sse_error(self, client):
        with patch("core.anime_pipeline_service.check_availability") as mock_avail:
            from core.anime_pipeline_service import AvailabilityResult
            mock_avail.return_value = AvailabilityResult(
                available=False, errors=["ComfyUI is not reachable"]
            )
            resp = client.post(
                "/api/anime-pipeline/stream",
                data=json.dumps({"prompt": "test"}),
                content_type="application/json",
            )
            assert resp.status_code == 503
            body = resp.get_data(as_text=True)
            assert "ap_error" in body

    def test_validation_error_returns_sse(self, client):
        with patch("core.anime_pipeline_service.check_availability") as mock_avail:
            from core.anime_pipeline_service import AvailabilityResult
            mock_avail.return_value = AvailabilityResult(
                available=True, feature_flag=True, comfyui_reachable=True
            )
            resp = client.post(
                "/api/anime-pipeline/stream",
                data=json.dumps({}),  # no prompt
                content_type="application/json",
            )
            assert resp.status_code == 400
            body = resp.get_data(as_text=True)
            assert "ap_error" in body

    def test_successful_stream(self, client):
        with patch("core.anime_pipeline_service.check_availability") as mock_avail, \
             patch("core.anime_pipeline_service.stream_pipeline") as mock_stream:
            from core.anime_pipeline_service import AvailabilityResult
            mock_avail.return_value = AvailabilityResult(
                available=True, feature_flag=True, comfyui_reachable=True
            )
            mock_stream.return_value = iter([
                'event: ap_status\ndata: {"job_id": "j1"}\n\n',
                'event: ap_done\ndata: {"job_id": "j1"}\n\n',
            ])
            resp = client.post(
                "/api/anime-pipeline/stream",
                data=json.dumps({"prompt": "cute anime cat"}),
                content_type="application/json",
            )
            assert resp.status_code == 200
            assert resp.mimetype == "text/event-stream"
            body = resp.get_data(as_text=True)
            assert "ap_status" in body
            assert "ap_done" in body


class TestGenerateEndpoint:
    def test_unavailable(self, client):
        with patch("core.anime_pipeline_service.check_availability") as mock_avail:
            from core.anime_pipeline_service import AvailabilityResult
            mock_avail.return_value = AvailabilityResult(
                available=False, errors=["disabled"]
            )
            resp = client.post(
                "/api/anime-pipeline/generate",
                data=json.dumps({"prompt": "test"}),
                content_type="application/json",
            )
            assert resp.status_code == 503

    def test_validation_error(self, client):
        with patch("core.anime_pipeline_service.check_availability") as mock_avail:
            from core.anime_pipeline_service import AvailabilityResult
            mock_avail.return_value = AvailabilityResult(
                available=True, feature_flag=True, comfyui_reachable=True
            )
            resp = client.post(
                "/api/anime-pipeline/generate",
                data=json.dumps({}),
                content_type="application/json",
            )
            assert resp.status_code == 400
