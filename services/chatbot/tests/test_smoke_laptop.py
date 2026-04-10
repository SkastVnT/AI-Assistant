"""
Smoke tests: LAPTOP mode end-to-end
====================================
Validates the complete image orchestration pipeline on a laptop where
local GPU services (ComfyUI, Stable Diffusion) are disabled.

What is tested:
    1. Local services disabled — ProviderRouter never touches ComfyUI
    2. Remote provider selected — fal/together as first candidates
    3. Multi-turn follow-up still works — generate → edit → edit chain
       with provider mocked at the HTTP boundary only

Run:
    cd services/chatbot
    python -m pytest tests/test_smoke_laptop.py -v -s --tb=short
"""
from __future__ import annotations

import os
import sys
import unittest
from dataclasses import replace as dc_replace
from unittest.mock import patch, MagicMock

# ── Project path ──────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Simulate laptop env BEFORE any module reads os.getenv ─────────────
_LAPTOP_ENV = {
    "AUTO_START_IMAGE_SERVICES": "0",
    "AUTO_START_COMFYUI": "0",
    "AUTO_START_STABLE_DIFFUSION": "0",
    "IMAGE_FIRST_MODE": "1",
    "SD_API_URL": "http://127.0.0.1:8188",
    "COMFYUI_URL": "http://127.0.0.1:8188",
    "FAL_API_KEY": "test-fal-key-for-smoke",
    "TOGETHER_API_KEY": "test-together-key-for-smoke",
}


def _apply_laptop_env():
    for k, v in _LAPTOP_ENV.items():
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


def _fake_image_result(*, url="https://fal.run/test/img.png",
                       provider="fal", model="fal-ai/flux/dev",
                       cost=0.025, seed=42):
    from core.image_gen.providers.base import ImageResult
    return ImageResult(
        success=True,
        images_b64=[],
        images_url=[url],
        prompt_used="enhanced prompt",
        provider=provider,
        model=model,
        cost_usd=cost,
        metadata={"seed": seed, "original_prompt": "test"},
    )


# =====================================================================
# Test class
# =====================================================================

class TestSmokeLaptop(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _apply_laptop_env()
        _clear_singletons()

    def setUp(self):
        _apply_laptop_env()
        _clear_singletons()

    # ── 1. Local services disabled ────────────────────────────────────

    def test_01_profile_is_low_resource(self):
        """RuntimeProfile should detect low_resource mode."""
        from app.services.image_orchestrator.runtime_profile import (
            get_runtime_profile,
        )
        profile = get_runtime_profile()
        self.assertEqual(profile.mode, "low_resource")
        self.assertTrue(profile.is_low_resource)
        self.assertTrue(profile.skip_comfyui_provider)
        self.assertFalse(profile.prefer_local_when_healthy)
        print(f"\n✅ 1: Profile = {profile.mode}")

    def test_02_comfyui_not_in_router(self):
        """ImageGenerationRouter should NOT register ComfyUI."""
        from core.image_gen.router import ImageGenerationRouter
        router = ImageGenerationRouter()
        self.assertNotIn("comfyui", router._providers,
                         "ComfyUI must be excluded in laptop mode")
        print(f"\n✅ 2: Providers = {list(router._providers.keys())}")

    def test_03_no_comfyui_in_selection(self):
        """_select_providers() must never return ComfyUI."""
        from core.image_gen.router import ImageGenerationRouter, QualityMode
        from core.image_gen.providers.base import ImageMode

        router = ImageGenerationRouter()
        for q in (QualityMode.AUTO, QualityMode.FAST, QualityMode.QUALITY):
            provs = router._select_providers(q, ImageMode.TEXT_TO_IMAGE)
            names = [c.provider.name for c in provs]
            self.assertNotIn("comfyui", names,
                             f"ComfyUI leaked into selection for {q}")
        print("\n✅ 3: ComfyUI absent from all quality modes")

    # ── 2. Remote provider selected ───────────────────────────────────

    def test_04_remote_provider_selected(self):
        """Full pipeline should select a remote provider, never comfyui."""
        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get:
            fake = _fake_image_result()
            mock_router = MagicMock()
            mock_router.generate.return_value = fake
            mock_get.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            svc = ImageOrchestrationService(use_llm_enhancer=False)
            result = svc.handle(
                message="vẽ con mèo tam thể ngồi cạnh cửa sổ mưa buồn",
                session_id="laptop-remote-test",
                language="vi",
                tools=["image-generation"],
            )

        self.assertTrue(result.is_image, f"Expected image: {result.error}")
        self.assertEqual(result.provider, "fal")
        self.assertFalse(result.fallback_to_llm)
        print(f"\n✅ 4: Remote provider = {result.provider}")

    def test_05_cost_is_nonzero(self):
        """Remote providers have cost > 0."""
        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get:
            fake = _fake_image_result(cost=0.03)
            mock_router = MagicMock()
            mock_router.generate.return_value = fake
            mock_get.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            svc = ImageOrchestrationService(use_llm_enhancer=False)
            result = svc.handle(
                message="tạo ảnh phong cảnh núi rừng mùa thu",
                session_id="cost-check",
                language="vi",
                tools=["image-generation"],
            )

        self.assertGreater(result.cost_usd, 0)
        print(f"\n✅ 5: cost_usd = ${result.cost_usd}")

    # ── 3. Multi-turn follow-up still works ───────────────────────────

    def test_06_multi_turn_generate_then_edit(self):
        """
        Full 3-turn chain on laptop:
          Turn 1: generate anime girl
          Turn 2: change hair to white  (edit, lineage=1)
          Turn 3: add glasses           (edit, lineage=2)
        """
        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get:
            gen_result = _fake_image_result(
                url="https://fal.run/test/gen.png", seed=100,
            )
            edit1_result = _fake_image_result(
                url="https://fal.run/test/edit1.png", seed=101,
            )
            edit2_result = _fake_image_result(
                url="https://fal.run/test/edit2.png", seed=102,
            )

            mock_router = MagicMock()
            mock_router.generate.side_effect = [gen_result, edit1_result, edit2_result]
            mock_get.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            from app.services.image_orchestrator.session_memory import (
                get_session_memory_store,
            )

            svc = ImageOrchestrationService(use_llm_enhancer=False)
            store = get_session_memory_store()
            sid = "laptop-multi-turn"

            # Turn 1: GENERATE
            r1 = svc.handle(
                message="vẽ cô gái anime tóc hồng dưới ánh trăng",
                session_id=sid, language="vi",
                tools=["image-generation"],
            )
            self.assertTrue(r1.is_image)
            mem1 = store.get(sid)
            self.assertEqual(mem1.edit_lineage_count, 0)
            self.assertTrue(mem1.has_previous_image)
            print(f"\n✅ 6a: Turn 1 GENERATE → {r1.provider}")

            # Turn 2: EDIT — change hair
            r2 = svc.handle(
                message="đổi tóc thành trắng",
                session_id=sid, language="vi",
            )
            self.assertTrue(r2.is_image)
            mem2 = store.get(sid)
            self.assertEqual(mem2.edit_lineage_count, 1)
            print(f"✅ 6b: Turn 2 EDIT → lineage={mem2.edit_lineage_count}")

            # Turn 3: EDIT — add glasses
            r3 = svc.handle(
                message="thêm kính",
                session_id=sid, language="vi",
            )
            self.assertTrue(r3.is_image)
            mem3 = store.get(sid)
            self.assertEqual(mem3.edit_lineage_count, 2)
            print(f"✅ 6c: Turn 3 EDIT → lineage={mem3.edit_lineage_count}")

            # Verify scene accumulated edits
            scene = mem3.last_scene_spec
            self.assertIsNotNone(scene)
            combined = f"{scene.subject} {' '.join(scene.subject_attributes)}".lower()
            self.assertTrue(
                "white" in combined or "trắng" in combined,
                f"White hair not found after edit chain: {combined}",
            )

    def test_07_edit_without_previous_falls_back_to_generate(self):
        """An edit message with no prior session should still produce output."""
        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get:
            fake = _fake_image_result()
            mock_router = MagicMock()
            mock_router.generate.return_value = fake
            mock_get.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            svc = ImageOrchestrationService(use_llm_enhancer=False)
            result = svc.handle(
                message="thêm kính cho nhân vật",
                session_id="fresh-no-prior",
                language="vi",
                tools=["image-generation"],
            )

        # Should either produce an image or fall back to LLM — never crash
        self.assertTrue(result.is_image or result.fallback_to_llm)
        print(f"\n✅ 7: Edit w/o prior → is_image={result.is_image}, "
              f"fallback={result.fallback_to_llm}")

    def test_08_streaming_events_on_laptop(self):
        """handle_stream() should yield SSE events on laptop mode."""
        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get:
            fake = _fake_image_result()
            mock_router = MagicMock()
            mock_router.generate.return_value = fake
            mock_get.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            svc = ImageOrchestrationService(use_llm_enhancer=False)
            events = list(svc.handle_stream(
                message="vẽ con mèo dễ thương",
                session_id="laptop-stream",
                language="vi",
                tools=["image-generation"],
            ))

        self.assertGreater(len(events), 0, "Should yield at least one SSE event")
        event_types = [e["event"] for e in events]
        self.assertIn("image_gen_result", event_types)
        print(f"\n✅ 8: Streaming events = {event_types}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
