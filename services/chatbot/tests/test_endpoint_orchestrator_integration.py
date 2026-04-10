"""
Integration test: new orchestrator wiring in FastAPI chat endpoint
==================================================================
Verifies that the feature flag USE_NEW_IMAGE_ORCHESTRATOR correctly
routes image requests through the new pipeline, and that the response
shape includes the extra metadata fields without breaking the existing
ChatResponse contract.

These tests mock out the heavy FastAPI import chain (pgvector, RAG, etc.)
and test the helpers and dispatch logic directly.

Run:
    cd services/chatbot
    python -m pytest tests/test_endpoint_orchestrator_integration.py -v -s --tb=short
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass, field
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Minimal env
os.environ.setdefault("FAL_API_KEY", "test")
os.environ.setdefault("TOGETHER_API_KEY", "test")


# ── Helpers ────────────────────────────────────────────────────────────

@dataclass
class _FakeNewResult:
    """Mimics app.services.image_orchestrator.schemas.ImageGenerationResult."""
    is_image:        bool = True
    fallback_to_llm: bool = False
    intent:          MagicMock = field(default_factory=lambda: MagicMock(value="generate"))
    images_b64:      list = field(default_factory=list)
    images_url:      list = field(default_factory=lambda: ["https://example.com/img.png"])
    enhanced_prompt: str = "enhanced prompt"
    original_prompt: str = "user prompt"
    provider:        str = "fal"
    model:           str = "flux-dev"
    cost_usd:        float = 0.003
    latency_ms:      float = 2100.0
    seed:            Optional[int] = 42
    response_text:   str = "## 🎨 Image Generated!"
    error:           str = ""
    scene:           Optional[MagicMock] = None


@dataclass
class _FakeLegacyResult:
    """Mimics core.image_gen.orchestrator.OrchestratorResult."""
    is_image:        bool = True
    fallback_to_llm: bool = False
    intent:          MagicMock = field(default_factory=lambda: MagicMock(value="generate"))
    images_b64:      list = field(default_factory=list)
    images_url:      list = field(default_factory=lambda: ["https://example.com/legacy.png"])
    enhanced_prompt: str = "legacy enhanced prompt"
    original_prompt: str = "user prompt"
    provider:        str = "together"
    model:           str = "flux-schnell"
    cost_usd:        float = 0.001
    latency_ms:      float = 3000.0
    response_text:   str = "## 🎨 Image Generated (legacy)!"
    error:           str = ""


# ── Patch the heavy import chain so fastapi_app can be imported ────────

def _install_stubs():
    """Install lightweight stubs for modules that require heavy deps."""
    stubs = {}
    # pgvector
    pgvec_mod = MagicMock()
    stubs["pgvector"] = pgvec_mod
    stubs["pgvector.sqlalchemy"] = pgvec_mod

    # Stub out rag modules
    for mod in [
        "src.rag.db", "src.rag.db.base", "src.rag.db.models",
        "src.rag.service", "src.rag.service.ingest_service",
        "src.rag.service.orchestrator",
    ]:
        stubs.setdefault(mod, MagicMock())

    # Patch before any fastapi_app import
    for k, v in stubs.items():
        sys.modules.setdefault(k, v)


_install_stubs()


# ── Tests ──────────────────────────────────────────────────────────────

class TestFeatureFlag(unittest.TestCase):
    """Test the USE_NEW_IMAGE_ORCHESTRATOR flag."""

    def test_flag_off_by_default(self):
        from fastapi_app.dependencies import use_new_image_orchestrator
        with patch.dict(os.environ, {"USE_NEW_IMAGE_ORCHESTRATOR": ""}):
            self.assertFalse(use_new_image_orchestrator())

    def test_flag_on(self):
        from fastapi_app.dependencies import use_new_image_orchestrator
        for val in ("1", "true", "yes", "on", "True", "ON"):
            with patch.dict(os.environ, {"USE_NEW_IMAGE_ORCHESTRATOR": val}):
                self.assertTrue(use_new_image_orchestrator(), f"Failed for {val!r}")

    def test_flag_off_explicit(self):
        from fastapi_app.dependencies import use_new_image_orchestrator
        for val in ("0", "false", "no", "off", ""):
            with patch.dict(os.environ, {"USE_NEW_IMAGE_ORCHESTRATOR": val}):
                self.assertFalse(use_new_image_orchestrator(), f"Failed for {val!r}")


class TestImageResultMetadata(unittest.TestCase):
    """Test the _image_result_metadata helper directly."""

    def test_new_pipeline_metadata_fields(self):
        from fastapi_app.routers.chat import _image_result_metadata

        result = _FakeNewResult()
        result.scene = MagicMock()
        result.scene.subject = "anime girl"
        result.scene.style = "anime"
        result.scene.background = "park"
        result.scene.lighting = "golden hour"
        result.scene.mood = "peaceful"
        result.scene.strength = 0.65

        meta = _image_result_metadata(result, pipeline="new", session_id="test-s1")

        # Existing fields preserved
        self.assertEqual(meta["intent"], "generate")
        self.assertEqual(meta["provider"], "fal")
        self.assertEqual(meta["model"], "flux-dev")
        self.assertEqual(meta["images_url"], ["https://example.com/img.png"])
        self.assertAlmostEqual(meta["cost_usd"], 0.003)
        self.assertAlmostEqual(meta["latency_ms"], 2100.0)

        # New metadata fields
        self.assertEqual(meta["request_kind"], "generate")
        self.assertEqual(meta["provider_selected"], "fal")
        self.assertFalse(meta["used_local_backend"])
        self.assertTrue(meta["used_remote_backend"])
        self.assertEqual(meta["pipeline"], "new")
        self.assertFalse(meta["used_previous_image_context"])

        # Scene summary
        self.assertIsNotNone(meta["scene_spec_summary"])
        self.assertEqual(meta["scene_spec_summary"]["subject"], "anime girl")
        self.assertEqual(meta["scene_spec_summary"]["style"], "anime")

    def test_legacy_pipeline_metadata(self):
        from fastapi_app.routers.chat import _image_result_metadata

        result = _FakeLegacyResult()
        meta = _image_result_metadata(result, pipeline="legacy", session_id="test-s2")

        self.assertEqual(meta["provider"], "together")
        self.assertEqual(meta["pipeline"], "legacy")
        self.assertIsNone(meta["scene_spec_summary"])
        self.assertFalse(meta["used_local_backend"])
        self.assertTrue(meta["used_remote_backend"])

    def test_local_backend_detection(self):
        from fastapi_app.routers.chat import _image_result_metadata

        result = _FakeNewResult(provider="comfyui")
        meta = _image_result_metadata(result, pipeline="new")

        self.assertTrue(meta["used_local_backend"])
        self.assertFalse(meta["used_remote_backend"])

    def test_edit_intent_flags(self):
        from fastapi_app.routers.chat import _image_result_metadata

        result = _FakeNewResult()
        result.intent = MagicMock(value="followup_edit")
        meta = _image_result_metadata(result, pipeline="new")

        self.assertEqual(meta["request_kind"], "followup_edit")
        self.assertTrue(meta["used_previous_image_context"])


class TestTryImageOrchestration(unittest.TestCase):
    """Test the _try_image_orchestration dispatcher function."""

    def _make_mock_request(self):
        request = MagicMock()
        request.session = {"session_id": "test-session-123"}
        return request

    @patch("fastapi_app.routers.chat.use_new_image_orchestrator", return_value=True)
    @patch("fastapi_app.routers.chat.get_new_orchestration_service")
    @patch("fastapi_app.routers.chat.get_session_id", return_value="test-session-123")
    def test_new_pipeline_returns_response(self, mock_sid, mock_new_svc, mock_flag):
        from fastapi_app.routers.chat import _try_image_orchestration

        fake_result = _FakeNewResult()
        svc = MagicMock()
        svc.handle.return_value = fake_result
        mock_new_svc.return_value = svc

        resp = _try_image_orchestration(
            request=self._make_mock_request(),
            original_message="vẽ con mèo",
            language="vi",
            tools=["image-generation"],
            image_quality="auto",
            model="grok",
            context="casual",
            deep_thinking=False,
        )

        self.assertIsNotNone(resp)
        self.assertEqual(resp.model, "grok")
        self.assertIn("provider", resp.image_result)
        self.assertEqual(resp.image_result["pipeline"], "new")

    @patch("fastapi_app.routers.chat.use_new_image_orchestrator", return_value=True)
    @patch("fastapi_app.routers.chat.get_new_orchestration_service")
    @patch("fastapi_app.routers.chat.get_session_id", return_value="test-session-123")
    def test_new_pipeline_fallback_returns_none(self, mock_sid, mock_new_svc, mock_flag):
        from fastapi_app.routers.chat import _try_image_orchestration

        fake_result = _FakeNewResult(is_image=False, fallback_to_llm=True)
        svc = MagicMock()
        svc.handle.return_value = fake_result
        mock_new_svc.return_value = svc

        resp = _try_image_orchestration(
            request=self._make_mock_request(),
            original_message="hello how are you",
            language="vi",
            tools=[],
            image_quality="auto",
            model="grok",
            context="casual",
            deep_thinking=False,
        )

        self.assertIsNone(resp)

    @patch("fastapi_app.routers.chat.use_new_image_orchestrator", return_value=False)
    @patch("fastapi_app.routers.chat.get_image_orchestrator_for_session")
    def test_legacy_pipeline_when_flag_off(self, mock_legacy, mock_flag):
        from fastapi_app.routers.chat import _try_image_orchestration

        fake_result = _FakeLegacyResult()
        legacy_orch = MagicMock()
        legacy_orch.handle.return_value = fake_result
        mock_legacy.return_value = legacy_orch

        resp = _try_image_orchestration(
            request=self._make_mock_request(),
            original_message="vẽ con mèo",
            language="vi",
            tools=["image-generation"],
            image_quality="auto",
            model="grok",
            context="casual",
            deep_thinking=False,
        )

        self.assertIsNotNone(resp)
        self.assertEqual(resp.image_result["pipeline"], "legacy")
        self.assertEqual(resp.image_result["provider"], "together")

    @patch("fastapi_app.routers.chat.use_new_image_orchestrator", return_value=False)
    @patch("fastapi_app.routers.chat.get_image_orchestrator_for_session", return_value=None)
    def test_no_orchestrator_available(self, mock_legacy, mock_flag):
        from fastapi_app.routers.chat import _try_image_orchestration

        resp = _try_image_orchestration(
            request=self._make_mock_request(),
            original_message="vẽ con mèo",
            language="vi",
            tools=["image-generation"],
            image_quality="auto",
            model="grok",
            context="casual",
            deep_thinking=False,
        )

        self.assertIsNone(resp)


class TestResponseShapeBackwardCompat(unittest.TestCase):
    """Ensure the response shape matches what the frontend expects."""

    def test_existing_fields_always_present(self):
        from fastapi_app.routers.chat import _image_result_metadata

        result = _FakeNewResult()
        meta = _image_result_metadata(result, pipeline="new")

        required_keys = {
            "intent", "provider", "model", "images_url", "images_b64",
            "enhanced_prompt", "cost_usd", "latency_ms",
        }
        for key in required_keys:
            self.assertIn(key, meta, f"Missing required field: {key}")

    def test_new_fields_are_additive(self):
        from fastapi_app.routers.chat import _image_result_metadata

        result = _FakeNewResult()
        meta = _image_result_metadata(result, pipeline="new")

        new_keys = {
            "request_kind", "provider_selected", "used_local_backend",
            "used_remote_backend", "scene_spec_summary",
            "used_previous_image_context", "pipeline", "edit_lineage",
        }
        for key in new_keys:
            self.assertIn(key, meta, f"Missing new metadata field: {key}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
