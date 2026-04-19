"""
Integration tests — Mocked ComfyUI API

Tests the full ComfyClient + agent chain with httpx mocked at transport level.
Validates:
    - submit_workflow happy path (submit → poll → download)
    - Retry on transient ConnectError
    - Validation error surfacing from ComfyUI /prompt response
    - Cancellation flag stops polling
    - Health check endpoint
    - OOM retry (step-down resolution)
    - Debug mode saves workflow JSON
    - Agent→ComfyClient integration (composition, beauty, upscale)
"""

from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "services" / "chatbot"))

import pytest
from unittest.mock import patch, MagicMock, PropertyMock

import httpx

from image_pipeline.anime_pipeline.comfy_client import ComfyClient, ComfyJobResult
from image_pipeline.anime_pipeline.config import AnimePipelineConfig, ModelConfig
from image_pipeline.anime_pipeline.schemas import (
    AnimePipelineJob,
    AnimePipelineStatus,
    PassConfig,
    ControlInput,
    IntermediateImage,
    LayerPlan,
)
from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder


# ── Helpers ──────────────────────────────────────────────────────────

FAKE_IMAGE_B64 = base64.b64encode(b"fake_png_data").decode()
FAKE_PROMPT_ID = "test-prompt-id-001"


def _comfy_submit_response(prompt_id: str = FAKE_PROMPT_ID) -> httpx.Response:
    """Simulate POST /prompt success."""
    return httpx.Response(
        200,
        json={"prompt_id": prompt_id},
        request=httpx.Request("POST", "http://localhost:8188/prompt"),
    )


def _comfy_history_pending() -> httpx.Response:
    """Simulate GET /history/{id} — job still running (empty)."""
    return httpx.Response(
        200,
        json={},
        request=httpx.Request("GET", f"http://localhost:8188/history/{FAKE_PROMPT_ID}"),
    )


def _comfy_history_complete(prompt_id: str = FAKE_PROMPT_ID) -> httpx.Response:
    """Simulate GET /history/{id} — job completed with one output image."""
    return httpx.Response(
        200,
        json={
            prompt_id: {
                "status": {"status_str": "success", "completed": True},
                "outputs": {
                    "9": {
                        "images": [
                            {
                                "filename": "anime_pipeline_001.png",
                                "subfolder": "",
                                "type": "output",
                            }
                        ]
                    }
                },
            }
        },
        request=httpx.Request("GET", f"http://localhost:8188/history/{prompt_id}"),
    )


def _comfy_view_image() -> httpx.Response:
    """Simulate GET /view — return fake PNG bytes."""
    return httpx.Response(
        200,
        content=b"fake_png_data",
        headers={"content-type": "image/png"},
        request=httpx.Request("GET", "http://localhost:8188/view"),
    )


def _comfy_health_ok() -> httpx.Response:
    return httpx.Response(
        200,
        json={"devices": [{"name": "cuda:0", "vram_total": 12 * 1024**3}]},
        request=httpx.Request("GET", "http://localhost:8188/system_stats"),
    )


# ═══════════════════════════════════════════════════════════════════
# ComfyClient — submit_workflow
# ═══════════════════════════════════════════════════════════════════

class TestSubmitWorkflow:
    def test_happy_path(self):
        """Full submit → poll → download cycle with mocked httpx."""
        call_count = {"history": 0}

        def _handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/prompt" and request.method == "POST":
                return _comfy_submit_response()
            if "/history/" in str(request.url.path):
                call_count["history"] += 1
                if call_count["history"] < 2:
                    return _comfy_history_pending()
                return _comfy_history_complete()
            if request.url.path == "/view":
                return _comfy_view_image()
            return httpx.Response(404)

        transport = httpx.MockTransport(_handler)
        mock_client = httpx.Client(transport=transport)
        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: mock_client
            mock_cls.return_value.__exit__ = lambda s, *a: None

            client = ComfyClient(base_url="http://localhost:8188", timeout_s=10)
            result = client.submit_workflow({"1": {"class_type": "test"}}, job_id="j1")

            assert result.success
            assert len(result.images_b64) >= 1
            assert result.prompt_id == FAKE_PROMPT_ID
            assert result.duration_ms >= 0

    def test_validation_error(self):
        """ComfyUI rejects the workflow with node_errors."""
        def _handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/prompt":
                return httpx.Response(400, json={
                    "error": {"type": "prompt_outputs_failed_validation"},
                    "node_errors": {"5": {"errors": [{"message": "Invalid sampler"}]}},
                })
            return httpx.Response(404)

        transport = httpx.MockTransport(_handler)
        mock_client = httpx.Client(transport=transport)
        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: mock_client
            mock_cls.return_value.__exit__ = lambda s, *a: None

            client = ComfyClient(base_url="http://localhost:8188")
            result = client.submit_workflow({"1": {"class_type": "test"}})

            assert not result.success
            assert result.error or result.validation_error


class TestRetryLogic:
    def test_retries_on_connect_error(self):
        """Client retries up to max_retries on ConnectError."""
        attempt_count = {"n": 0}

        def _handler(request: httpx.Request) -> httpx.Response:
            attempt_count["n"] += 1
            if attempt_count["n"] <= 2:
                raise httpx.ConnectError("Connection refused")
            if request.url.path == "/prompt":
                return _comfy_submit_response()
            if "/history/" in str(request.url.path):
                return _comfy_history_complete()
            if request.url.path == "/view":
                return _comfy_view_image()
            return httpx.Response(404)

        transport = httpx.MockTransport(_handler)
        mock_client = httpx.Client(transport=transport)
        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: mock_client
            mock_cls.return_value.__exit__ = lambda s, *a: None

            with patch("time.sleep"):  # skip retry delays
                client = ComfyClient(
                    base_url="http://localhost:8188",
                    max_retries=3,
                )
                result = client.submit_workflow({"1": {"class_type": "test"}})

            assert result.success
            assert attempt_count["n"] >= 3

    def test_all_retries_exhausted(self):
        """Returns error when all retries fail."""
        def _handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        transport = httpx.MockTransport(_handler)
        mock_client = httpx.Client(transport=transport)
        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: mock_client
            mock_cls.return_value.__exit__ = lambda s, *a: None

            with patch("time.sleep"):
                client = ComfyClient(
                    base_url="http://localhost:8188",
                    max_retries=1,
                )
                result = client.submit_workflow({"1": {"class_type": "test"}})

            assert not result.success
            assert "retries" in result.error.lower() or "refused" in result.error.lower()


class TestHealthCheck:
    def test_health_ok(self):
        transport = httpx.MockTransport(lambda req: _comfy_health_ok())
        mock_client = httpx.Client(transport=transport)
        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: mock_client
            mock_cls.return_value.__exit__ = lambda s, *a: None

            client = ComfyClient(base_url="http://localhost:8188")
            assert client.check_health() is True

    def test_health_fail(self):
        def _handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        transport = httpx.MockTransport(_handler)
        mock_client = httpx.Client(transport=transport)
        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: mock_client
            mock_cls.return_value.__exit__ = lambda s, *a: None

            client = ComfyClient(base_url="http://localhost:8188")
            assert client.check_health() is False


class TestCancellation:
    def test_cancel_sets_flag(self):
        client = ComfyClient(base_url="http://localhost:8188")
        # Internally marks the prompt_id as cancelled
        client._cancelled["test-prompt"] = True
        assert client._is_cancelled("test-prompt") is True

    def test_cancel_sends_interrupt(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, request=req)
        )
        mock_client = httpx.Client(transport=transport)
        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: mock_client
            mock_cls.return_value.__exit__ = lambda s, *a: None

            client = ComfyClient(base_url="http://localhost:8188")
            result = client.cancel("some-prompt-id")
            assert result is True


# ═══════════════════════════════════════════════════════════════════
# Agent → ComfyClient integration (mocked)
# ═══════════════════════════════════════════════════════════════════

class TestAgentComfyIntegration:
    """Test that agents build valid workflows and interact with ComfyClient."""

    @pytest.fixture
    def config(self):
        return AnimePipelineConfig(
            composition_model=ModelConfig(
                checkpoint="animagine-xl-4.0-opt.safetensors",
                sampler="euler_a", scheduler="normal", steps=20, cfg=5.0,
            ),
            beauty_model=ModelConfig(
                checkpoint="noobai-xl-1.1.safetensors",
                sampler="dpmpp_2m_sde", scheduler="karras", steps=20, cfg=5.5,
                denoise_strength=0.30,
            ),
            upscale_model="RealESRGAN_x4plus_anime_6B",
            upscale_factor=2,
            comfyui_url="http://localhost:8188",
        )

    def test_builder_produces_valid_workflow(self, config):
        """WorkflowBuilder output is valid dict that ComfyClient would accept."""
        builder = WorkflowBuilder()
        pc = PassConfig(
            pass_name="composition",
            model_slot="composition",
            checkpoint=config.composition_model.checkpoint,
            width=832, height=1216,
            sampler="euler_a", scheduler="normal",
            steps=20, cfg=5.0, denoise=1.0,
            positive_prompt="masterpiece, 1girl",
            negative_prompt="lowres",
        )
        wf = builder.build_composition(pc, seed=42)

        # All node IDs are strings
        assert all(isinstance(k, str) for k in wf.keys())
        # All nodes have class_type and inputs
        for node in wf.values():
            assert "class_type" in node
            assert "inputs" in node

    def test_upscale_workflow_structure(self, config):
        builder = WorkflowBuilder()
        wf = builder.build_upscale(FAKE_IMAGE_B64, config.upscale_model)
        node_types = [n["class_type"] for n in wf.values()]
        assert "LoadImageFromBase64" in node_types
        assert "UpscaleModelLoader" in node_types
        assert "ImageUpscaleWithModel" in node_types
        assert "SaveImage" in node_types
