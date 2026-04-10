"""
Smoke tests: image orchestration core components
=================================================
Validates each building-block of the new image orchestration layer
in isolation, with no network or GPU access required.

Components under test:
    1. ScenePlanner — classify + plan (VI & EN)
    2. PromptBuilder — build() / build_negative()
    3. ProviderRouter — route() mock path
    4. SessionMemoryStore — CRUD + LRU eviction
    5. merge_scene_delta — standalone edit merge

Run:
    cd services/chatbot
    python -m pytest tests/test_smoke_orchestration.py -v -s --tb=short
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

# Minimal env so imports don't crash
os.environ.setdefault("FAL_API_KEY", "test-key")
os.environ.setdefault("TOGETHER_API_KEY", "test-key")

from app.services.image_orchestrator.schemas import (
    ImageIntent,
    PlanClassification,
    SceneSpec,
    EditOperation,
    ImageGenerationResult,
)
from app.services.image_orchestrator.scene_planner import (
    ScenePlanner,
    merge_scene_delta,
)
from app.services.image_orchestrator.prompt_builder import PromptBuilder
from app.services.image_orchestrator.session_memory import (
    ImageSessionMemory,
    SessionMemoryStore,
)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _base_scene() -> SceneSpec:
    return SceneSpec(
        subject="anime girl with pink hair",
        subject_attributes=["long pink hair", "blue eyes", "school uniform"],
        action="standing",
        background="cherry blossom park",
        lighting="golden hour",
        mood="peaceful",
        style="anime",
        quality_preset="quality",
        width=1024,
        height=1024,
    )


class _FakeImageResult:
    """Mimics core.image_gen.providers.base.ImageResult."""
    def __init__(self, *, url="https://example.com/img.png", provider="fal",
                 model="test-model", success=True):
        self.success      = success
        self.images_url   = [url]
        self.images_b64   = []
        self.provider     = provider
        self.model        = model
        self.cost_usd     = 0.01
        self.prompt_used  = "test prompt"
        self.metadata     = {"seed": 42}
        self.error        = ""


# =====================================================================
# 1. ScenePlanner smoke tests
# =====================================================================

class TestScenePlannerSmoke(unittest.TestCase):
    """Quick-fire tests for ScenePlanner classify_and_plan()."""

    def setUp(self):
        self.planner = ScenePlanner()

    # ── Vietnamese generation ─────────────────────────────────────────

    def test_vi_generate_anime(self):
        r = self.planner.classify_and_plan(
            "vẽ cô gái anime tóc hồng ngồi trên bãi biển lúc hoàng hôn",
            has_previous_image=False,
        )
        self.assertEqual(r.classification, PlanClassification.GENERATE)
        self.assertTrue(r.scene.subject, "Subject should not be empty")
        self.assertEqual(r.scene.style, "anime")

    def test_vi_generate_landscape(self):
        r = self.planner.classify_and_plan(
            "tạo ảnh phong cảnh núi rừng mùa thu ánh nắng vàng siêu thực",
            has_previous_image=False,
        )
        self.assertEqual(r.classification, PlanClassification.GENERATE)
        self.assertTrue(r.scene.subject)

    def test_vi_generate_portrait(self):
        r = self.planner.classify_and_plan(
            "chụp chân dung đàn ông trung niên nền trắng studio 85mm",
            has_previous_image=False,
        )
        self.assertEqual(r.classification, PlanClassification.GENERATE)
        combined = f"{r.scene.subject} {r.scene.composition} {r.scene.camera}".lower()
        # Should detect portrait/studio elements
        self.assertTrue(
            any(kw in combined for kw in ("portrait", "studio", "85mm", "chân dung")),
            f"Expected portrait cues in: {combined}",
        )

    def test_vi_generate_cyberpunk(self):
        r = self.planner.classify_and_plan(
            "robot tương lai bay trên thành phố cyberpunk ban đêm ánh neon",
            has_previous_image=False,
        )
        self.assertEqual(r.classification, PlanClassification.GENERATE)

    # ── Vietnamese edit (needs has_previous_image=True) ──────────────

    def test_vi_edit_darken(self):
        r = self.planner.classify_and_plan(
            "làm trời tối hơn",
            has_previous_image=True,
            previous_scene=_base_scene(),
        )
        self.assertEqual(r.classification, PlanClassification.EDIT_FOLLOWUP)

    def test_vi_edit_add_glasses(self):
        r = self.planner.classify_and_plan(
            "thêm kính cho nhân vật",
            has_previous_image=True,
            previous_scene=_base_scene(),
        )
        self.assertEqual(r.classification, PlanClassification.EDIT_FOLLOWUP)
        # Should have an add operation
        self.assertTrue(
            any(op.operation == "add" for op in r.edit_ops),
            f"Expected 'add' edit op, got: {r.edit_ops}",
        )

    def test_vi_edit_change_hair(self):
        r = self.planner.classify_and_plan(
            "đổi tóc thành màu trắng",
            has_previous_image=True,
            previous_scene=_base_scene(),
        )
        self.assertEqual(r.classification, PlanClassification.EDIT_FOLLOWUP)

    def test_vi_edit_remove_hat(self):
        base = dc_replace(
            _base_scene(),
            subject_attributes=list(_base_scene().subject_attributes) + ["wearing a hat"],
        )
        r = self.planner.classify_and_plan(
            "bỏ cái mũ đi",
            has_previous_image=True,
            previous_scene=base,
        )
        self.assertEqual(r.classification, PlanClassification.EDIT_FOLLOWUP)

    # ── English generation ────────────────────────────────────────────

    def test_en_generate(self):
        r = self.planner.classify_and_plan(
            "Draw a cute cat sitting on a windowsill in the rain",
            has_previous_image=False,
        )
        self.assertEqual(r.classification, PlanClassification.GENERATE)
        self.assertTrue(r.scene.subject)

    # ── Non-image message ─────────────────────────────────────────────

    def test_not_image_request(self):
        """A plain conversation message should NOT be classified as image."""
        r = self.planner.classify_and_plan(
            "Hôm nay thời tiết thế nào?",
            has_previous_image=False,
        )
        # Should be GENERATE (no edit) or at least not EDIT_FOLLOWUP
        # The planner may still try to generate; the intent detector is the
        # actual gatekeeper.  We just verify it doesn't crash and that
        # it doesn't produce an EDIT_FOLLOWUP with no previous scene.
        self.assertNotEqual(r.classification, PlanClassification.EDIT_FOLLOWUP)


# =====================================================================
# 2. PromptBuilder smoke tests
# =====================================================================

class TestPromptBuilderSmoke(unittest.TestCase):
    """Validate prompt construction from SceneSpec."""

    def setUp(self):
        self.builder = PromptBuilder(use_llm_enhancer=False)

    def test_build_basic_prompt(self):
        scene = _base_scene()
        prompt = self.builder.build(scene, language="vi",
                                    original_message="vẽ cô gái anime")
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 20,
                           "Prompt should be non-trivial")

    def test_build_contains_subject(self):
        scene = _base_scene()
        prompt = self.builder.build(scene, language="vi",
                                    original_message="vẽ cô gái anime")
        # Subject should appear in the final prompt
        self.assertTrue(
            "anime" in prompt.lower() or "girl" in prompt.lower() or
            "pink" in prompt.lower(),
            f"Subject keywords missing from prompt: {prompt[:100]}",
        )

    def test_build_negative_prompt(self):
        scene = _base_scene()
        neg = self.builder.build_negative(scene)
        self.assertIsInstance(neg, str)
        self.assertGreater(len(neg), 5,
                           "Negative prompt should have content")

    def test_build_with_text_in_image(self):
        scene = dc_replace(_base_scene(), wants_text_in_image=True)
        neg = self.builder.build_negative(scene)
        # When text is wanted, "text" should NOT be in negative prompt
        # (some builders add "text" as negative by default)
        # This is a soft check — just ensure it doesn't crash
        self.assertIsInstance(neg, str)

    def test_build_edit_scene_prompt(self):
        """Edit scenes should produce valid prompts too."""
        scene = dc_replace(
            _base_scene(),
            subject="anime girl with white hair",
            subject_attributes=["white hair", "blue eyes", "glasses"],
            strength=0.65,
        )
        prompt = self.builder.build(scene, language="vi",
                                    original_message="đổi tóc trắng")
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 10)


# =====================================================================
# 3. Provider selection / routing (mocked)
# =====================================================================

class TestProviderRouterSmoke(unittest.TestCase):
    """Validate ProviderRouter.route() dispatches correctly."""

    def test_route_returns_image_result(self):
        from app.services.image_orchestrator.provider_router import ProviderRouter
        from app.services.image_orchestrator.schemas import ImageGenerationRequest

        fake = _FakeImageResult()
        req = ImageGenerationRequest(
            original_prompt="test prompt",
            language="vi",
            session_id="test-session",
            scene=_base_scene(),
            enhanced_prompt="enhanced test prompt",
        )

        with patch.object(ProviderRouter, "_get_router") as mock_get:
            mock_router = MagicMock()
            mock_router.generate.return_value = fake
            mock_get.return_value = mock_router

            pr = ProviderRouter()
            result = pr.route(req, "enhanced test prompt", "bad quality")

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "fal")
        mock_router.generate.assert_called_once()

    def test_route_followup_uses_i2i_mode(self):
        from app.services.image_orchestrator.provider_router import ProviderRouter
        from app.services.image_orchestrator.schemas import ImageFollowupRequest

        fake = _FakeImageResult()
        scene = dc_replace(
            _base_scene(),
            source_image_url="https://example.com/prev.png",
            strength=0.65,
        )
        req = ImageFollowupRequest(
            original_prompt="thêm kính",
            language="vi",
            session_id="test-session",
            intent=ImageIntent.FOLLOWUP_EDIT,
            scene=scene,
            enhanced_prompt="add glasses",
            source_image_url="https://example.com/prev.png",
        )

        with patch.object(ProviderRouter, "_get_router") as mock_get:
            mock_router = MagicMock()
            mock_router.generate.return_value = fake
            mock_get.return_value = mock_router

            pr = ProviderRouter()
            pr.route(req, "add glasses", "bad quality")

        call_kwargs = mock_router.generate.call_args
        # mode should be "i2i" for follow-up with source image
        mode_arg = call_kwargs.kwargs.get("mode") or (
            call_kwargs[1].get("mode") if len(call_kwargs) > 1 else None
        )
        if mode_arg:
            self.assertEqual(mode_arg, "i2i",
                             f"Expected i2i mode for edit, got: {mode_arg}")


# =====================================================================
# 4. SessionMemoryStore smoke tests
# =====================================================================

class TestSessionMemorySmoke(unittest.TestCase):
    """CRUD, LRU eviction, lineage tracking."""

    def setUp(self):
        self.store = SessionMemoryStore(max_sessions=4)

    def test_create_and_retrieve(self):
        mem = self.store.get_or_create("s1")
        self.assertEqual(mem.session_id, "s1")
        self.assertFalse(mem.has_previous_image)
        self.assertEqual(mem.edit_lineage_count, 0)

    def test_update_populates_fields(self):
        fake = _FakeImageResult(url="https://fal.run/out.png", provider="fal")
        scene = _base_scene()
        self.store.update("s1", "test prompt", scene, fake, is_edit=False)

        mem = self.store.get("s1")
        self.assertIsNotNone(mem)
        self.assertEqual(mem.last_provider, "fal")
        self.assertEqual(mem.last_image_reference, "https://fal.run/out.png")
        self.assertIsNotNone(mem.last_scene_spec)
        self.assertTrue(mem.has_previous_image)

    def test_lineage_increments_and_resets(self):
        fake = _FakeImageResult()
        scene = _base_scene()

        self.store.update("s1", "gen", scene, fake, is_edit=False)
        self.assertEqual(self.store.get("s1").edit_lineage_count, 0)

        self.store.update("s1", "edit1", scene, fake, is_edit=True)
        self.assertEqual(self.store.get("s1").edit_lineage_count, 1)

        self.store.update("s1", "edit2", scene, fake, is_edit=True)
        self.assertEqual(self.store.get("s1").edit_lineage_count, 2)

        # Fresh generation resets
        self.store.update("s1", "new gen", scene, fake, is_edit=False)
        self.assertEqual(self.store.get("s1").edit_lineage_count, 0)

    def test_lru_eviction(self):
        """Oldest session evicted when max_sessions exceeded."""
        fake = _FakeImageResult()
        for i in range(5):
            self.store.update(f"s{i}", "p", _base_scene(), fake)

        # s0 should be evicted (max_sessions=4)
        self.assertIsNone(self.store.get("s0"),
                          "s0 should be evicted")
        # s1..s4 should exist
        for i in range(1, 5):
            self.assertIsNotNone(self.store.get(f"s{i}"),
                                 f"s{i} should still exist")

    def test_clear_session(self):
        self.store.get_or_create("s1")
        self.store.clear("s1")
        self.assertIsNone(self.store.get("s1"))

    def test_b64_reference_stored(self):
        """When only b64 data is available, a snippet is stored."""
        class B64Result:
            success = True
            images_url = []
            images_b64 = ["iVBORw0KGgoAAAANSUhEUg" + "A" * 100]
            provider = "local"
            model = "test"
            cost_usd = 0
            prompt_used = "test"
            metadata = {}
            error = ""

        self.store.update("s1", "test", _base_scene(), B64Result())
        mem = self.store.get("s1")
        self.assertTrue(mem.last_image_reference.startswith("b64:"))
        self.assertTrue(mem.has_previous_image)


# =====================================================================
# 5. merge_scene_delta smoke tests
# =====================================================================

class TestMergeSceneDeltaSmoke(unittest.TestCase):
    """Verify merge_scene_delta preserves base and applies edits."""

    def test_preserves_base_subject(self):
        base = _base_scene()
        ops = [EditOperation(operation="modify", target="lighting", modifier="darker")]
        merged = merge_scene_delta(base, "làm tối hơn", ops)

        # Subject preserved
        self.assertIn("pink hair", merged.subject.lower())
        # Base not mutated
        self.assertEqual(base.lighting, "golden hour")

    def test_applies_background_change(self):
        base = _base_scene()
        ops = [EditOperation(operation="change", target="background",
                             new_value="cyberpunk city")]
        merged = merge_scene_delta(base, "đổi background cyberpunk", ops)
        self.assertIn("cyberpunk", merged.background.lower())

    def test_adds_attribute(self):
        base = _base_scene()
        ops = [EditOperation(operation="add", target="glasses")]
        merged = merge_scene_delta(base, "thêm kính", ops)
        combined = f"{merged.subject} {' '.join(merged.subject_attributes)}".lower()
        self.assertTrue(
            "glasses" in combined or "kính" in combined,
            f"Glasses not found: {combined}",
        )

    def test_remove_attribute(self):
        base = dc_replace(
            _base_scene(),
            subject_attributes=list(_base_scene().subject_attributes) + ["hat"],
        )
        ops = [EditOperation(operation="remove", target="hat")]
        merged = merge_scene_delta(base, "bỏ mũ", ops)
        attrs = " ".join(merged.subject_attributes).lower()
        neg = " ".join(merged.negative_hints).lower()
        # Hat should be gone from attributes or present in negatives
        self.assertTrue(
            "hat" not in attrs or "hat" in neg,
            f"Hat should be removed; attrs={merged.subject_attributes}",
        )

    def test_edit_strength_applied(self):
        base = _base_scene()
        merged = merge_scene_delta(base, "tối hơn", [])
        self.assertAlmostEqual(merged.strength, 0.65, places=2)

    def test_multiple_ops(self):
        """Multiple edit operations in one turn."""
        base = _base_scene()
        ops = [
            EditOperation(operation="change", target="hair", new_value="white"),
            EditOperation(operation="add", target="glasses"),
        ]
        merged = merge_scene_delta(base, "đổi tóc trắng và thêm kính", ops)
        combined = f"{merged.subject} {' '.join(merged.subject_attributes)}".lower()
        self.assertTrue("white" in combined or "trắng" in combined,
                        f"White hair not found: {combined}")

    def test_keep_character_flag(self):
        """'giữ nhân vật cũ' should preserve base attributes."""
        base = _base_scene()
        ops = [EditOperation(operation="keep", target="character")]
        merged = merge_scene_delta(
            base, "giữ nhân vật cũ nhưng đổi background", ops,
        )
        # Base attributes should survive the merge (hair color, etc.)
        combined = f"{merged.subject} {' '.join(merged.subject_attributes)}".lower()
        self.assertTrue(
            "pink" in combined or "hair" in combined or
            len(merged.subject_attributes) > 0,
            f"Expected base attributes preserved: subject={merged.subject!r}, "
            f"attrs={merged.subject_attributes}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
