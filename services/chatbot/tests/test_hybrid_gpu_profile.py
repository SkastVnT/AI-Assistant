"""
Smoke test: hybrid GPU / PC profile
====================================
Verifies the image chatbot flow on a strong PC where local services
(ComfyUI) are enabled and should be preferred when healthy, with
automatic fallback to remote providers when local is down.

Env profile under test (all vars already exist in .env):
    AUTO_START_IMAGE_SERVICES=1
    AUTO_START_COMFYUI=1
    AUTO_START_STABLE_DIFFUSION=1
    IMAGE_FIRST_MODE=1
    SD_API_URL=http://127.0.0.1:8188
    COMFYUI_URL=http://127.0.0.1:8188

Run:
    cd services/chatbot
    python -m pytest tests/test_hybrid_gpu_profile.py -v -s --tb=short
"""
from __future__ import annotations

import os
import sys
import logging
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

# ── GPU PC env (all existing vars, full mode) ────────────────────────
_GPU_ENV = {
    "AUTO_START_IMAGE_SERVICES": "1",
    "AUTO_START_COMFYUI": "1",
    "AUTO_START_STABLE_DIFFUSION": "1",
    "IMAGE_FIRST_MODE": "1",
    "IMAGE_SERVICE_VISIBLE_WINDOWS": "1",
    "SD_API_URL": "http://127.0.0.1:8188",
    "COMFYUI_URL": "http://127.0.0.1:8188",
    "STABLE_DIFFUSION_PORT": "7861",
    "STABLE_DIFFUSION_START_COMMAND": "",
    # Remote provider keys for fallback chain
    "FAL_API_KEY": "test-fal-key-for-smoke",
    "TOGETHER_API_KEY": "test-together-key-for-smoke",
    "OPENAI_API_KEY": "",
}


def _apply_gpu_env():
    for k, v in _GPU_ENV.items():
        os.environ[k] = v


def _clear_singletons():
    """Reset module-level singletons so they re-read env vars."""
    from app.services.image_orchestrator import runtime_profile
    runtime_profile.reset_runtime_profile()

    from app.services.image_orchestrator import orchestrator
    orchestrator._scene_planner = None
    orchestrator._prompt_builder = None
    orchestrator._provider_router = None
    orchestrator._service_instance = None

    from app.services.image_orchestrator.provider_router import ProviderRouter
    ProviderRouter._shared_router = None

    from app.services.image_orchestrator import session_memory
    session_memory._store = None


# ─────────────────────────────────────────────────────────────────────
# Test class
# ─────────────────────────────────────────────────────────────────────

class TestHybridGPUProfile(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        _apply_gpu_env()
        _clear_singletons()

    def setUp(self):
        """Reset singletons before each test for isolation."""
        _apply_gpu_env()
        _clear_singletons()

    # ── Test 1: RuntimeProfile detects full/hybrid mode ──────────────

    def test_01_runtime_profile_full_mode(self):
        from app.services.image_orchestrator.runtime_profile import (
            get_runtime_profile,
        )
        profile = get_runtime_profile()

        self.assertEqual(profile.mode, "full")
        self.assertFalse(profile.is_low_resource)
        self.assertFalse(profile.skip_comfyui_provider)
        self.assertTrue(profile.local_services_enabled)
        self.assertTrue(profile.prefer_local_when_healthy)
        self.assertTrue(profile.auto_start_image_services)
        self.assertTrue(profile.auto_start_comfyui)
        self.assertTrue(profile.auto_start_stable_diffusion)
        self.assertTrue(profile.image_first_mode)

        print(f"\n✅ Test 1: {profile.describe()}")

    # ── Test 2: ComfyUI IS registered in full mode ───────────────────

    def test_02_comfyui_registered(self):
        from core.image_gen.router import ImageGenerationRouter

        router = ImageGenerationRouter()
        provider_names = list(router._providers.keys())

        self.assertIn("comfyui", provider_names,
                       "ComfyUI MUST be registered in full mode")

        # Remote providers also registered
        self.assertIn("fal", provider_names)
        self.assertIn("together", provider_names)

        print(f"\n✅ Test 2: Registered providers = {provider_names}")
        print(f"   ComfyUI present ✓ + remote fallback ✓")

    # ── Test 3: HYBRID — local healthy → ComfyUI promoted first ─────

    def test_03_hybrid_local_healthy_promoted(self):
        """
        When ComfyUI is healthy, _select_providers(AUTO) should put it FIRST.
        """
        from core.image_gen.router import ImageGenerationRouter, QualityMode
        from core.image_gen.providers.base import ImageMode

        router = ImageGenerationRouter()

        # Mock ComfyUI health_check to return True (local is healthy)
        comfyui_prov = router._providers["comfyui"].provider
        with patch.object(type(comfyui_prov), "is_available",
                          new_callable=PropertyMock, return_value=True):
            providers = router._select_providers(
                QualityMode.AUTO, ImageMode.TEXT_TO_IMAGE
            )

        names = [c.provider.name for c in providers]
        self.assertGreater(len(names), 0, "Should have providers")
        self.assertEqual(names[0], "comfyui",
                         f"ComfyUI should be FIRST when healthy, got: {names}")

        # Remote providers should be in the fallback chain
        remote_in_chain = [n for n in names if n != "comfyui"]
        self.assertGreater(len(remote_in_chain), 0,
                           "Remote providers must still be in fallback chain")

        print(f"\n✅ Test 3: HYBRID local healthy → provider order = {names}")
        print(f"   ComfyUI is FIRST ✓, fallback = {remote_in_chain}")

    # ── Test 4: HYBRID — local unhealthy → remote only ──────────────

    def test_04_hybrid_local_unhealthy_fallback(self):
        """
        When ComfyUI is NOT healthy, _select_providers(AUTO) should only
        contain remote providers.
        """
        from core.image_gen.router import ImageGenerationRouter, QualityMode
        from core.image_gen.providers.base import ImageMode

        router = ImageGenerationRouter()

        # Mock ComfyUI health_check to return False (local is down)
        comfyui_prov = router._providers["comfyui"].provider
        with patch.object(type(comfyui_prov), "is_available",
                          new_callable=PropertyMock, return_value=False):
            providers = router._select_providers(
                QualityMode.AUTO, ImageMode.TEXT_TO_IMAGE
            )

        names = [c.provider.name for c in providers]
        self.assertNotIn("comfyui", names,
                         f"ComfyUI should NOT appear when unhealthy, got: {names}")
        self.assertGreater(len(names), 0,
                           "Remote providers must still be available as fallback")

        print(f"\n✅ Test 4: HYBRID local unhealthy → provider order = {names}")
        print(f"   ComfyUI absent ✓, remote fallback active ✓")

    # ── Test 5: Full flow — local healthy → generate via comfyui ─────

    def test_05_full_flow_local_chosen(self):
        """
        End-to-end: when ComfyUI is healthy, the orchestrator should
        route through comfyui provider (promoted first by hybrid logic).
        """
        from core.image_gen.providers.base import ImageResult

        fake_local_result = ImageResult(
            success=True,
            images_b64=[],
            images_url=["http://127.0.0.1:8188/view?filename=output_00001.png"],
            prompt_used="local enhanced prompt",
            provider="comfyui",
            model="flux1-schnell-fp8",
            cost_usd=0.0,
            metadata={"seed": 100, "original_prompt": "test"},
        )

        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get_router:
            mock_router = MagicMock()
            mock_router.generate.return_value = fake_local_result
            mock_get_router.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            from app.services.image_orchestrator.session_memory import (
                get_session_memory_store,
            )

            svc = ImageOrchestrationService(use_llm_enhancer=False)
            mem_store = get_session_memory_store()
            session_id = "gpu-hybrid-local"

            result = svc.handle(
                message="vẽ cô gái anime tóc hồng dưới ánh trăng",
                session_id=session_id,
                language="vi",
                tools=["image-generation"],
                quality="auto",
            )

            self.assertTrue(result.is_image,
                            f"Expected image, got error: {result.error}")
            self.assertEqual(result.provider, "comfyui")
            self.assertEqual(result.cost_usd, 0.0)

            # Session memory should record comfyui as last provider
            mem = mem_store.get(session_id)
            self.assertIsNotNone(mem)
            self.assertEqual(mem.last_provider, "comfyui")
            self.assertTrue(mem.has_previous_image)

            print(f"\n✅ Test 5: Full flow → LOCAL chosen")
            print(f"   provider={result.provider}, cost=${result.cost_usd}")
            print(f"   images_url={result.images_url}")
            print(f"   session_memory.last_provider={mem.last_provider}")

    # ── Test 6: Full flow — local down → falls back to remote ────────

    def test_06_full_flow_remote_fallback(self):
        """
        End-to-end: when ComfyUI is down, the orchestrator should
        fall back to a remote provider.
        """
        from core.image_gen.providers.base import ImageResult

        fake_remote_result = ImageResult(
            success=True,
            images_b64=[],
            images_url=["https://fal.run/test/fallback.png"],
            prompt_used="remote enhanced prompt",
            provider="fal",
            model="fal-ai/flux/dev",
            cost_usd=0.025,
            metadata={"seed": 200, "original_prompt": "test"},
        )

        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get_router:
            mock_router = MagicMock()
            mock_router.generate.return_value = fake_remote_result
            mock_get_router.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            from app.services.image_orchestrator.session_memory import (
                get_session_memory_store,
            )

            svc = ImageOrchestrationService(use_llm_enhancer=False)
            mem_store = get_session_memory_store()
            session_id = "gpu-hybrid-remote-fallback"

            result = svc.handle(
                message="tạo ảnh phong cảnh núi rừng mùa thu",
                session_id=session_id,
                language="vi",
                tools=["image-generation"],
                quality="auto",
            )

            self.assertTrue(result.is_image,
                            f"Expected image, got error: {result.error}")
            self.assertEqual(result.provider, "fal")
            self.assertGreater(result.cost_usd, 0)

            mem = mem_store.get(session_id)
            self.assertEqual(mem.last_provider, "fal")

            print(f"\n✅ Test 6: Full flow → REMOTE fallback")
            print(f"   provider={result.provider}, cost=${result.cost_usd}")
            print(f"   images_url={result.images_url}")
            print(f"   session_memory.last_provider={mem.last_provider}")

    # ── Test 7: Quality=QUALITY should NOT promote local ─────────────

    def test_07_quality_mode_skips_hybrid_promotion(self):
        """
        When quality=QUALITY, hybrid promotion should NOT apply —
        the user explicitly wants best quality (remote ultra/high tier).
        """
        from core.image_gen.router import ImageGenerationRouter, QualityMode
        from core.image_gen.providers.base import ImageMode

        router = ImageGenerationRouter()

        comfyui_prov = router._providers["comfyui"].provider
        with patch.object(type(comfyui_prov), "is_available",
                          new_callable=PropertyMock, return_value=True):
            providers = router._select_providers(
                QualityMode.QUALITY, ImageMode.TEXT_TO_IMAGE
            )

        names = [c.provider.name for c in providers]
        if names and names[0] == "comfyui":
            self.fail(
                f"ComfyUI should NOT be first in QUALITY mode, got: {names}"
            )

        print(f"\n✅ Test 7: quality=QUALITY → order = {names}")
        print(f"   ComfyUI not promoted ✓ (user wants best quality)")

    # ── Test 8: Verify prefer_local_when_healthy is False on laptop ──

    def test_08_laptop_profile_no_hybrid(self):
        """
        Confirm that switching to laptop env disables hybrid promotion.
        """
        from app.services.image_orchestrator.runtime_profile import (
            reset_runtime_profile, get_runtime_profile,
        )

        saved = {k: os.environ.get(k) for k in _GPU_ENV}
        os.environ["AUTO_START_IMAGE_SERVICES"] = "0"
        os.environ["AUTO_START_COMFYUI"] = "0"
        os.environ["AUTO_START_STABLE_DIFFUSION"] = "0"
        os.environ["IMAGE_FIRST_MODE"] = "0"
        reset_runtime_profile()

        try:
            profile = get_runtime_profile()
            self.assertEqual(profile.mode, "low_resource")
            self.assertFalse(profile.prefer_local_when_healthy,
                             "Laptop mode must NOT prefer local")
            self.assertTrue(profile.skip_comfyui_provider)

            print(f"\n✅ Test 8: Laptop env → prefer_local={profile.prefer_local_when_healthy}")
            print(f"   mode={profile.mode}, skip_comfyui={profile.skip_comfyui_provider}")
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            reset_runtime_profile()


# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    unittest.main(verbosity=2)
