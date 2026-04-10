"""
Smoke tests: PC/GPU mode end-to-end
====================================
Validates the complete image orchestration pipeline on a PC with
a GPU where local services (ComfyUI) are enabled.

What is tested:
    1. Local health check succeeds — ComfyUI registered and healthy
    2. Local provider selected when healthy — hybrid promotion puts ComfyUI first
    3. Remote fallback when local fails — ComfyUI down → fal/together
    4. Multi-turn chain preserves local-first behavior
    5. Cost tracking — local is free ($0), remote has cost

Run:
    cd services/chatbot
    python -m pytest tests/test_smoke_gpu.py -v -s --tb=short
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

# ── Project path ──────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Simulate GPU PC env ───────────────────────────────────────────────
_GPU_ENV = {
    "AUTO_START_IMAGE_SERVICES": "1",
    "AUTO_START_COMFYUI": "1",
    "AUTO_START_STABLE_DIFFUSION": "1",
    "IMAGE_FIRST_MODE": "1",
    "IMAGE_SERVICE_VISIBLE_WINDOWS": "1",
    "SD_API_URL": "http://127.0.0.1:8188",
    "COMFYUI_URL": "http://127.0.0.1:8188",
    "STABLE_DIFFUSION_PORT": "7861",
    "FAL_API_KEY": "test-fal-key-for-smoke",
    "TOGETHER_API_KEY": "test-together-key-for-smoke",
}


def _apply_gpu_env():
    for k, v in _GPU_ENV.items():
        os.environ[k] = v


def _clear_singletons():
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


def _fake_local_result(*, url="http://127.0.0.1:8188/view?filename=out.png",
                       seed=100):
    from core.image_gen.providers.base import ImageResult
    return ImageResult(
        success=True,
        images_b64=[],
        images_url=[url],
        prompt_used="local enhanced prompt",
        provider="comfyui",
        model="flux1-schnell-fp8",
        cost_usd=0.0,
        metadata={"seed": seed, "original_prompt": "test"},
    )


def _fake_remote_result(*, url="https://fal.run/test/fallback.png",
                        provider="fal", seed=200):
    from core.image_gen.providers.base import ImageResult
    return ImageResult(
        success=True,
        images_b64=[],
        images_url=[url],
        prompt_used="remote enhanced prompt",
        provider=provider,
        model="fal-ai/flux/dev",
        cost_usd=0.025,
        metadata={"seed": seed, "original_prompt": "test"},
    )


# =====================================================================
# Test class
# =====================================================================

class TestSmokeGPU(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _apply_gpu_env()
        _clear_singletons()

    def setUp(self):
        _apply_gpu_env()
        _clear_singletons()

    # ── 1. Local health check succeeds ────────────────────────────────

    def test_01_profile_is_full(self):
        from app.services.image_orchestrator.runtime_profile import (
            get_runtime_profile,
        )
        profile = get_runtime_profile()
        self.assertEqual(profile.mode, "full")
        self.assertFalse(profile.is_low_resource)
        self.assertFalse(profile.skip_comfyui_provider)
        self.assertTrue(profile.prefer_local_when_healthy)
        print(f"\n✅ 1: Profile = {profile.mode}")

    def test_02_comfyui_registered(self):
        from core.image_gen.router import ImageGenerationRouter
        router = ImageGenerationRouter()
        self.assertIn("comfyui", router._providers)
        print(f"\n✅ 2: Providers = {list(router._providers.keys())}")

    def test_03_comfyui_promoted_when_healthy(self):
        """When healthy, ComfyUI should be FIRST in AUTO mode."""
        from core.image_gen.router import ImageGenerationRouter, QualityMode
        from core.image_gen.providers.base import ImageMode

        router = ImageGenerationRouter()
        comfyui_prov = router._providers["comfyui"].provider

        with patch.object(type(comfyui_prov), "is_available",
                          new_callable=PropertyMock, return_value=True):
            provs = router._select_providers(
                QualityMode.AUTO, ImageMode.TEXT_TO_IMAGE,
            )
        names = [c.provider.name for c in provs]
        self.assertEqual(names[0], "comfyui",
                         f"ComfyUI should be first: {names}")
        print(f"\n✅ 3: Provider order = {names}")

    # ── 2. Local provider selected when healthy ───────────────────────

    def test_04_generate_uses_local(self):
        """Full pipeline → ComfyUI when mocked provider returns local result."""
        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get:
            mock_router = MagicMock()
            mock_router.generate.return_value = _fake_local_result()
            mock_get.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            from app.services.image_orchestrator.session_memory import (
                get_session_memory_store,
            )

            svc = ImageOrchestrationService(use_llm_enhancer=False)
            store = get_session_memory_store()
            result = svc.handle(
                message="vẽ cô gái anime tóc hồng dưới ánh trăng",
                session_id="gpu-local", language="vi",
                tools=["image-generation"],
            )

        self.assertTrue(result.is_image)
        self.assertEqual(result.provider, "comfyui")
        self.assertEqual(result.cost_usd, 0.0)

        mem = store.get("gpu-local")
        self.assertEqual(mem.last_provider, "comfyui")
        print(f"\n✅ 4: Local provider used = {result.provider}, "
              f"cost=${result.cost_usd}")

    def test_05_local_images_are_localhost_urls(self):
        """Local provider returns localhost URLs."""
        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get:
            mock_router = MagicMock()
            mock_router.generate.return_value = _fake_local_result()
            mock_get.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            svc = ImageOrchestrationService(use_llm_enhancer=False)
            result = svc.handle(
                message="tạo ảnh robot",
                session_id="gpu-urls", language="vi",
                tools=["image-generation"],
            )

        self.assertTrue(any("127.0.0.1" in u for u in result.images_url),
                        f"Expected localhost URL: {result.images_url}")
        print(f"\n✅ 5: Image URLs = {result.images_url}")

    # ── 3. Remote fallback when local fails ───────────────────────────

    def test_06_remote_fallback_when_local_down(self):
        """When ComfyUI health is False, selection skips it."""
        from core.image_gen.router import ImageGenerationRouter, QualityMode
        from core.image_gen.providers.base import ImageMode

        router = ImageGenerationRouter()
        comfyui_prov = router._providers["comfyui"].provider

        with patch.object(type(comfyui_prov), "is_available",
                          new_callable=PropertyMock, return_value=False):
            provs = router._select_providers(
                QualityMode.AUTO, ImageMode.TEXT_TO_IMAGE,
            )
        names = [c.provider.name for c in provs]
        self.assertNotIn("comfyui", names)
        self.assertGreater(len(names), 0,
                           "Remote providers should be available as fallback")
        print(f"\n✅ 6: Fallback providers = {names}")

    def test_07_generate_remote_when_local_down(self):
        """Full pipeline falls back to remote when local provider fails."""
        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get:
            mock_router = MagicMock()
            mock_router.generate.return_value = _fake_remote_result()
            mock_get.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            from app.services.image_orchestrator.session_memory import (
                get_session_memory_store,
            )

            svc = ImageOrchestrationService(use_llm_enhancer=False)
            store = get_session_memory_store()
            result = svc.handle(
                message="tạo ảnh phong cảnh núi rừng",
                session_id="gpu-fallback", language="vi",
                tools=["image-generation"],
            )

        self.assertTrue(result.is_image)
        self.assertEqual(result.provider, "fal")
        self.assertGreater(result.cost_usd, 0)

        mem = store.get("gpu-fallback")
        self.assertEqual(mem.last_provider, "fal")
        print(f"\n✅ 7: Remote fallback → {result.provider}, "
              f"cost=${result.cost_usd}")

    # ── 4. Multi-turn on GPU mode ─────────────────────────────────────

    def test_08_multi_turn_local_stays_local(self):
        """Multi-turn editing chain should continue using local provider."""
        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get:
            gen = _fake_local_result(url="http://127.0.0.1:8188/view?f=gen.png", seed=10)
            ed1 = _fake_local_result(url="http://127.0.0.1:8188/view?f=ed1.png", seed=11)
            ed2 = _fake_local_result(url="http://127.0.0.1:8188/view?f=ed2.png", seed=12)

            mock_router = MagicMock()
            mock_router.generate.side_effect = [gen, ed1, ed2]
            mock_get.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            from app.services.image_orchestrator.session_memory import (
                get_session_memory_store,
            )

            svc = ImageOrchestrationService(use_llm_enhancer=False)
            store = get_session_memory_store()
            sid = "gpu-multi-turn"

            # Turn 1: Generate
            r1 = svc.handle(
                message="vẽ cô gái anime tóc hồng dưới ánh trăng",
                session_id=sid, language="vi",
                tools=["image-generation"],
            )
            self.assertTrue(r1.is_image)
            self.assertEqual(r1.provider, "comfyui")

            # Turn 2: Edit
            r2 = svc.handle(
                message="đổi tóc thành trắng",
                session_id=sid, language="vi",
            )
            self.assertTrue(r2.is_image)
            mem2 = store.get(sid)
            self.assertEqual(mem2.edit_lineage_count, 1)

            # Turn 3: Another edit
            r3 = svc.handle(
                message="thêm kính",
                session_id=sid, language="vi",
            )
            self.assertTrue(r3.is_image)
            mem3 = store.get(sid)
            self.assertEqual(mem3.edit_lineage_count, 2)

        # All 3 turns should have used comfyui
        self.assertEqual(r1.provider, "comfyui")
        self.assertEqual(r2.provider, "comfyui")
        self.assertEqual(r3.provider, "comfyui")
        print(f"\n✅ 8: 3-turn chain all via comfyui, lineage={mem3.edit_lineage_count}")

    # ── 5. Quality mode skips hybrid ──────────────────────────────────

    def test_09_quality_mode_prefers_remote(self):
        """quality=QUALITY should not promote ComfyUI first."""
        from core.image_gen.router import ImageGenerationRouter, QualityMode
        from core.image_gen.providers.base import ImageMode

        router = ImageGenerationRouter()
        comfyui_prov = router._providers["comfyui"].provider

        with patch.object(type(comfyui_prov), "is_available",
                          new_callable=PropertyMock, return_value=True):
            provs = router._select_providers(
                QualityMode.QUALITY, ImageMode.TEXT_TO_IMAGE,
            )
        names = [c.provider.name for c in provs]
        if names:
            self.assertNotEqual(names[0], "comfyui",
                                f"ComfyUI should not be first in QUALITY: {names}")
        print(f"\n✅ 9: QUALITY mode order = {names}")

    # ── 6. Streaming events on GPU ────────────────────────────────────

    def test_10_streaming_events_on_gpu(self):
        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get:
            mock_router = MagicMock()
            mock_router.generate.return_value = _fake_local_result()
            mock_get.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            svc = ImageOrchestrationService(use_llm_enhancer=False)
            events = list(svc.handle_stream(
                message="vẽ con mèo dễ thương",
                session_id="gpu-stream", language="vi",
                tools=["image-generation"],
            ))

        self.assertGreater(len(events), 0)
        event_types = [e["event"] for e in events]
        self.assertIn("image_gen_result", event_types)

        # Should contain comfyui as provider in the result event
        result_event = [e for e in events if e["event"] == "image_gen_result"][0]
        self.assertEqual(result_event["data"]["provider"], "comfyui")
        print(f"\n✅ 10: Stream events = {event_types}, "
              f"provider = {result_event['data']['provider']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
