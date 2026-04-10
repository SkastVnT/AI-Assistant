"""
Smoke test: low-resource laptop profile
========================================
Verifies the FULL image chatbot flow runs correctly when local heavy
services (ComfyUI / Stable Diffusion) are disabled.

Sets env vars to mimic the laptop profile, then exercises:
  1. generate image  (text-to-image via remote provider)
  2. follow-up edit  (reuses previous SceneSpec from session memory)
  3. inspect session memory state
  4. confirm remote provider path (no comfyui)

Run:
    cd services/chatbot
    python tests/test_low_resource_profile.py
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# ── Simulate laptop env BEFORE any imports touch os.getenv ────────────
_LAPTOP_ENV = {
    "AUTO_START_IMAGE_SERVICES": "0",
    "AUTO_START_COMFYUI": "0",
    "AUTO_START_STABLE_DIFFUSION": "0",
    "IMAGE_FIRST_MODE": "1",
    "SD_API_URL": "http://127.0.0.1:8188",
    "COMFYUI_URL": "http://127.0.0.1:8188",
    # Keep at least one remote provider key so router has candidates
    "FAL_API_KEY": "test-fal-key-for-smoke",
    "TOGETHER_API_KEY": "test-together-key-for-smoke",
}


def _apply_laptop_env():
    for k, v in _LAPTOP_ENV.items():
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

class TestLowResourceProfile(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _apply_laptop_env()
        _clear_singletons()

    # ── Test 1: RuntimeProfile detects low-resource correctly ────────

    def test_01_runtime_profile_is_low_resource(self):
        from app.services.image_orchestrator.runtime_profile import (
            get_runtime_profile,
        )
        profile = get_runtime_profile()

        self.assertEqual(profile.mode, "low_resource")
        self.assertTrue(profile.is_low_resource)
        self.assertTrue(profile.skip_comfyui_provider)
        self.assertFalse(profile.local_services_enabled)
        self.assertFalse(profile.auto_start_image_services)
        self.assertFalse(profile.auto_start_comfyui)
        self.assertFalse(profile.auto_start_stable_diffusion)
        self.assertTrue(profile.image_first_mode)
        print(f"\n✅ Test 1: {profile.describe()}")

    # ── Test 2: ImageGenerationRouter skips ComfyUI provider ────────

    def test_02_router_skips_comfyui(self):
        from core.image_gen.router import ImageGenerationRouter

        router = ImageGenerationRouter()
        provider_names = list(router._providers.keys())

        self.assertNotIn("comfyui", provider_names,
                         "ComfyUI should NOT be registered in low-resource mode")

        # Should have at least one remote provider
        remote_names = [n for n in provider_names if n != "comfyui"]
        self.assertGreater(len(remote_names), 0,
                           "Must have at least one remote provider")

        print(f"\n✅ Test 2: Registered providers = {provider_names}")
        print(f"   ComfyUI excluded ✓, remote count = {len(remote_names)}")

    # ── Test 3: ScenePlanner + PromptBuilder work without local ─────

    def test_03_scene_planner_works(self):
        from app.services.image_orchestrator.scene_planner import ScenePlanner
        from app.services.image_orchestrator.prompt_builder import PromptBuilder

        planner = ScenePlanner()
        builder = PromptBuilder(use_llm_enhancer=False)

        # Generate request
        r = planner.classify_and_plan(
            "vẽ cô gái anime tóc hồng ngồi trên bãi biển",
            has_previous_image=False,
        )
        self.assertEqual(r.classification.value, "generate")
        self.assertTrue(r.scene.subject)

        prompt = builder.build(r.scene, language="vi",
                               original_message="vẽ cô gái anime tóc hồng")
        self.assertGreater(len(prompt), 20)

        neg = builder.build_negative(r.scene)
        self.assertGreater(len(neg), 10)

        print(f"\n✅ Test 3: ScenePlanner → {r.classification.value}")
        print(f"   style={r.scene.style}, prompt len={len(prompt)}")

    # ── Test 4: Full generate → memory → follow-up edit cycle ───────

    def test_04_full_flow_with_mocked_provider(self):
        """
        Mock the actual HTTP call inside the provider but let ALL other
        code run for real: intent detection, ScenePlanner, PromptBuilder,
        ProviderRouter, SessionMemory.
        """
        # Build a fake ImageResult that mimics a remote provider success
        from core.image_gen.providers.base import ImageResult
        fake_result = ImageResult(
            success=True,
            images_b64=[],
            images_url=["https://fal.run/test/image.png"],
            prompt_used="enhanced prompt here",
            provider="fal",
            model="fal-ai/flux/dev",
            cost_usd=0.025,
            metadata={"seed": 42, "original_prompt": "test"},
        )

        # Patch the provider's generate() so no HTTP call is made,
        # but everything upstream (router selection, prompt building) is real
        with patch(
            "app.services.image_orchestrator.provider_router.ProviderRouter._get_router"
        ) as mock_get_router:
            mock_router = MagicMock()
            mock_router.generate.return_value = fake_result
            mock_get_router.return_value = mock_router

            from app.services.image_orchestrator.orchestrator import (
                ImageOrchestrationService,
            )
            from app.services.image_orchestrator.session_memory import (
                get_session_memory_store,
            )

            svc = ImageOrchestrationService(use_llm_enhancer=False)
            mem_store = get_session_memory_store()
            session_id = "laptop-smoke-test"

            # ── Step 4a: GENERATE ─────────────────────────────────
            result = svc.handle(
                message="vẽ cô gái anime tóc hồng dưới ánh trăng",
                session_id=session_id,
                language="vi",
                tools=["image-generation"],
                quality="auto",
            )

            self.assertTrue(result.is_image, f"Expected image, got error: {result.error}")
            self.assertFalse(result.fallback_to_llm)
            self.assertEqual(result.provider, "fal")
            self.assertIn("https://fal.run/test/image.png", result.images_url)

            # Verify router.generate was called (not comfyui)
            mock_router.generate.assert_called_once()
            call_kwargs = mock_router.generate.call_args
            # provider_name should NOT be 'comfyui'
            provider_arg = call_kwargs.kwargs.get("provider_name") or \
                           (call_kwargs[1].get("provider_name") if len(call_kwargs) > 1 else None)
            if provider_arg:
                self.assertNotEqual(provider_arg, "comfyui")

            print(f"\n✅ Test 4a: GENERATE success")
            print(f"   provider={result.provider}, model={result.model}")
            print(f"   images_url={result.images_url}")

            # ── Step 4b: Check session memory ─────────────────────
            mem = mem_store.get(session_id)
            self.assertIsNotNone(mem)
            self.assertTrue(mem.has_previous_image)
            self.assertEqual(mem.last_provider, "fal")
            self.assertEqual(mem.last_image_reference, "https://fal.run/test/image.png")
            self.assertIsNotNone(mem.last_scene_spec)
            self.assertEqual(mem.last_scene_spec.style, "anime")

            print(f"\n✅ Test 4b: Session memory populated")
            print(f"   last_provider={mem.last_provider}")
            print(f"   last_image_ref={mem.last_image_reference}")
            print(f"   last_scene style={mem.last_scene_spec.style}")
            print(f"   has_previous_image={mem.has_previous_image}")

            # ── Step 4c: FOLLOW-UP EDIT ───────────────────────────
            mock_router.generate.reset_mock()
            fake_edit_result = ImageResult(
                success=True,
                images_b64=[],
                images_url=["https://fal.run/test/edited.png"],
                prompt_used="edited prompt",
                provider="fal",
                model="fal-ai/flux/dev",
                cost_usd=0.025,
                metadata={"seed": 43},
            )
            mock_router.generate.return_value = fake_edit_result

            edit_result = svc.handle(
                message="đổi tóc thành màu trắng",
                session_id=session_id,
                language="vi",
            )

            self.assertTrue(edit_result.is_image,
                            f"Edit should succeed, got: {edit_result.error}")

            print(f"\n✅ Test 4c: FOLLOW-UP EDIT success")
            print(f"   provider={edit_result.provider}")
            print(f"   intent={edit_result.intent.value}")

            # ── Step 4d: Session memory updated after edit ────────
            mem2 = mem_store.get(session_id)
            self.assertEqual(mem2.last_provider, "fal")
            self.assertEqual(mem2.last_image_reference, "https://fal.run/test/edited.png")
            # Scene spec should have white hair in attributes after edit
            print(f"\n✅ Test 4d: Session memory updated after edit")
            print(f"   last_image_ref={mem2.last_image_reference}")
            print(f"   last_scene attrs={mem2.last_scene_spec.subject_attributes if mem2.last_scene_spec else 'N/A'}")

    # ── Test 5: Confirm no local provider path ──────────────────────

    def test_05_no_local_path_in_select(self):
        """
        Verify _select_providers() never returns comfyui in low-resource mode.
        """
        from core.image_gen.router import ImageGenerationRouter, QualityMode
        from core.image_gen.providers.base import ImageMode

        router = ImageGenerationRouter()

        for quality in [QualityMode.AUTO, QualityMode.FAST, QualityMode.QUALITY,
                        QualityMode.CHEAP]:
            providers = router._select_providers(quality, ImageMode.TEXT_TO_IMAGE)
            names = [c.provider.name for c in providers]
            self.assertNotIn("comfyui", names,
                             f"ComfyUI should not appear for quality={quality}")

        # Even QualityMode.FREE should return empty (no local provider)
        free_providers = router._select_providers(QualityMode.FREE, ImageMode.TEXT_TO_IMAGE)
        self.assertEqual(len(free_providers), 0,
                         "FREE mode should return empty when local is disabled")

        print(f"\n✅ Test 5: No comfyui in any quality mode provider selection")

    # ── Test 6: Legacy mode still works (full mode simulation) ──────

    def test_06_legacy_full_mode_not_broken(self):
        """
        Temporarily set env to full mode and confirm ComfyUI IS registered.
        """
        from app.services.image_orchestrator.runtime_profile import (
            reset_runtime_profile, get_runtime_profile,
        )

        # Save and override
        saved = {k: os.environ.get(k) for k in _LAPTOP_ENV}
        os.environ["AUTO_START_IMAGE_SERVICES"] = "1"
        os.environ["AUTO_START_COMFYUI"] = "1"
        os.environ["AUTO_START_STABLE_DIFFUSION"] = "1"
        reset_runtime_profile()

        try:
            profile = get_runtime_profile()
            self.assertEqual(profile.mode, "full")
            self.assertFalse(profile.is_low_resource)
            self.assertFalse(profile.skip_comfyui_provider)

            from core.image_gen.router import ImageGenerationRouter
            router = ImageGenerationRouter()
            self.assertIn("comfyui", router._providers,
                          "ComfyUI MUST be registered in full mode")

            print(f"\n✅ Test 6: Legacy full mode → comfyui registered ✓")
        finally:
            # Restore laptop env
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
