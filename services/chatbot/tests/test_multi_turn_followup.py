"""
Multi-turn image follow-up tests
=================================
Validates the complete edit follow-up pipeline:

  1. ScenePlanner correctly classifies edit messages
  2. merge_scene_delta() preserves base scene while applying only the delta
  3. Session memory tracks edit_lineage_count
  4. Orchestrator wires everything together for multi-turn chains

Six Vietnamese follow-up cases:
    "làm nền tối hơn"                       — modify lighting/atmosphere darker
    "đổi tóc thành trắng"                   — change hair to white
    "thêm kính"                             — add glasses
    "giữ nhân vật cũ nhưng đổi bg cyberpunk"— keep+change background
    "thêm chữ summer sale"                  — add_text overlay
    "bỏ cái nón"                            — remove hat

Run:
    cd services/chatbot
    python -m pytest tests/test_multi_turn_followup.py -v -s --tb=short
"""
from __future__ import annotations

import os
import sys
import logging
import unittest
from dataclasses import replace as dc_replace

# ── Ensure project root on sys.path ──────────────────────────────────
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
)
from app.services.image_orchestrator.scene_planner import (
    ScenePlanner,
    merge_scene_delta,
)
from app.services.image_orchestrator.session_memory import (
    ImageSessionMemory,
    SessionMemoryStore,
)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _base_scene() -> SceneSpec:
    """A realistic base scene that a first-turn generation would produce."""
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
    """Minimal stand-in for core.image_gen.providers.base.ImageResult."""
    def __init__(self, url: str = "https://example.com/img.png", provider: str = "fal"):
        self.success    = True
        self.images_url = [url]
        self.images_b64 = []
        self.provider   = provider
        self.model      = "test-model"
        self.cost_usd   = 0.01
        self.prompt_used = "test prompt"
        self.metadata   = {"seed": 42}
        self.error      = ""


# ─────────────────────────────────────────────────────────────────────
# Test: merge_scene_delta — 6 Vietnamese follow-up cases
# ─────────────────────────────────────────────────────────────────────

class TestMergeSceneDelta(unittest.TestCase):
    """Each test starts from _base_scene() and applies one edit."""

    def setUp(self):
        self.planner = ScenePlanner()
        self.base    = _base_scene()

    # Helper: classify + merge in one step
    def _plan_edit(self, message: str) -> SceneSpec:
        result = self.planner.classify_and_plan(
            message=message,
            language="vi",
            has_previous_image=True,
            previous_scene=self.base,
        )
        self.assertEqual(result.classification, PlanClassification.EDIT_FOLLOWUP,
                         f"Expected EDIT_FOLLOWUP for: {message!r}")
        return result.scene

    # ── 1. "làm nền tối hơn" ─────────────────────────────────────────

    def test_01_darken_background(self):
        scene = self._plan_edit("làm nền tối hơn")

        # Subject preserved from base
        self.assertIn("pink hair", scene.subject.lower())
        # Lighting or mood should reflect darker
        combined = f"{scene.lighting} {scene.mood} {' '.join(scene.extra_tags)}".lower()
        self.assertTrue(
            any(w in combined for w in ("dark", "tối", "dim", "shadow", "moody")),
            f"Expected darker hint, got lighting={scene.lighting!r}, mood={scene.mood!r}",
        )
        # Style preserved
        self.assertEqual(scene.style, "anime")

    # ── 2. "đổi tóc thành trắng" ─────────────────────────────────────

    def test_02_change_hair_to_white(self):
        scene = self._plan_edit("đổi tóc thành trắng")

        # Subject should mention white hair now
        all_text = f"{scene.subject} {' '.join(scene.subject_attributes)}".lower()
        self.assertIn("white", all_text,
                       f"Expected 'white' in subject/attributes: {all_text}")
        # Background preserved
        self.assertIn("cherry", scene.background.lower())
        # Edit strength applied
        self.assertAlmostEqual(scene.strength, 0.65, places=2)

    # ── 3. "thêm kính" ───────────────────────────────────────────────

    def test_03_add_glasses(self):
        scene = self._plan_edit("thêm kính")

        all_attrs = " ".join(scene.subject_attributes).lower()
        all_text  = f"{scene.subject} {all_attrs}".lower()
        self.assertTrue(
            "glasses" in all_text or "kính" in all_text,
            f"Expected glasses in scene: subject={scene.subject!r}, attrs={scene.subject_attributes}",
        )
        # Original attributes preserved
        self.assertTrue(
            any("blue eyes" in a.lower() for a in scene.subject_attributes),
            "Original 'blue eyes' attribute should be preserved",
        )

    # ── 4. "giữ nhân vật cũ nhưng đổi background cyberpunk" ──────────

    def test_04_keep_character_change_bg(self):
        scene = self._plan_edit("giữ nhân vật cũ nhưng đổi background cyberpunk")

        # Subject preserved (may be Vietnamese or English from base)
        # The key is the base scene's attributes survive
        self.assertTrue(
            any("pink" in a.lower() for a in scene.subject_attributes),
            f"Pink hair attribute should persist: {scene.subject_attributes}",
        )

        # Background changed to cyberpunk
        self.assertIn("cyberpunk", scene.background.lower())

        # wants_consistency flag from "giữ" keyword
        self.assertTrue(scene.wants_consistency_with_previous)

    # ── 5. "thêm chữ summer sale" ────────────────────────────────────

    def test_05_add_text_overlay(self):
        scene = self._plan_edit("thêm chữ summer sale")

        # Should have text-in-image flag and the text content
        all_text = f"{scene.subject} {' '.join(scene.extra_tags)} {' '.join(scene.subject_attributes)}".lower()
        self.assertTrue(
            scene.wants_text_in_image or "summer sale" in all_text,
            f"Expected text overlay marker; wants_text={scene.wants_text_in_image}, combined={all_text}",
        )

    # ── 6. "bỏ cái nón" ──────────────────────────────────────────────

    def test_06_remove_hat(self):
        # Add a hat to the base scene first
        self.base = dc_replace(
            self.base,
            subject_attributes=list(self.base.subject_attributes) + ["wearing a hat"],
        )

        scene = self._plan_edit("bỏ cái nón")

        # Hat should be removed or in negative hints
        attrs_text = " ".join(scene.subject_attributes).lower()
        neg_text   = " ".join(scene.negative_hints).lower()
        self.assertTrue(
            "hat" not in attrs_text or "hat" in neg_text or "nón" in neg_text,
            f"Hat should be removed; attrs={scene.subject_attributes}, neg={scene.negative_hints}",
        )
        # Other attributes preserved
        self.assertTrue(
            any("blue eyes" in a.lower() for a in scene.subject_attributes),
            "Original 'blue eyes' should survive",
        )


# ─────────────────────────────────────────────────────────────────────
# Test: merge_scene_delta standalone function
# ─────────────────────────────────────────────────────────────────────

class TestMergeSceneDeltaFunction(unittest.TestCase):
    """Test the standalone merge_scene_delta() directly."""

    def test_standalone_merge_preserves_base(self):
        """merge_scene_delta should not mutate the base scene."""
        base = _base_scene()
        original_bg = base.background

        ops = [EditOperation(operation="change", target="background", new_value="cyberpunk city")]
        merged = merge_scene_delta(base, "đổi background cyberpunk city", ops)

        # Base unchanged
        self.assertEqual(base.background, original_bg)
        # Merged has new background
        self.assertIn("cyberpunk", merged.background.lower())

    def test_standalone_merge_applies_edit_ops(self):
        """Edit operations should be reflected in the merged scene."""
        base = _base_scene()
        ops  = [EditOperation(operation="add", target="glasses")]
        merged = merge_scene_delta(base, "thêm kính", ops)

        all_text = f"{merged.subject} {' '.join(merged.subject_attributes)}".lower()
        self.assertTrue(
            "glasses" in all_text or "kính" in all_text,
            f"Glasses not found: {all_text}",
        )

    def test_standalone_merge_strength(self):
        """Merged scene should have default edit strength."""
        base   = _base_scene()
        merged = merge_scene_delta(base, "tối hơn", [])
        self.assertAlmostEqual(merged.strength, 0.65, places=2)


# ─────────────────────────────────────────────────────────────────────
# Test: Session memory lineage tracking
# ─────────────────────────────────────────────────────────────────────

class TestSessionMemoryLineage(unittest.TestCase):
    """edit_lineage_count increments on edits, resets on fresh generation."""

    def setUp(self):
        self.store = SessionMemoryStore(max_sessions=16)

    def test_lineage_increments_on_edit(self):
        fake = _FakeImageResult()
        self.store.update("s1", "prompt1", _base_scene(), fake, is_edit=False)

        mem = self.store.get("s1")
        self.assertEqual(mem.edit_lineage_count, 0)

        # Simulate 3 sequential edits
        for i in range(1, 4):
            self.store.update("s1", f"edit-{i}", _base_scene(), fake, is_edit=True)
            mem = self.store.get("s1")
            self.assertEqual(mem.edit_lineage_count, i)

    def test_lineage_resets_on_fresh_generate(self):
        fake = _FakeImageResult()

        # Build up lineage
        self.store.update("s2", "gen", _base_scene(), fake, is_edit=False)
        self.store.update("s2", "edit1", _base_scene(), fake, is_edit=True)
        self.store.update("s2", "edit2", _base_scene(), fake, is_edit=True)
        mem = self.store.get("s2")
        self.assertEqual(mem.edit_lineage_count, 2)

        # Fresh generation resets
        self.store.update("s2", "new image", _base_scene(), fake, is_edit=False)
        mem = self.store.get("s2")
        self.assertEqual(mem.edit_lineage_count, 0)

    def test_lineage_default_zero(self):
        mem = self.store.get_or_create("new-session")
        self.assertEqual(mem.edit_lineage_count, 0)


# ─────────────────────────────────────────────────────────────────────
# Test: Multi-turn chain (generate → edit → edit → ...)
# ─────────────────────────────────────────────────────────────────────

class TestMultiTurnChain(unittest.TestCase):
    """
    Simulate a realistic conversation:
        Turn 1: "vẽ cô gái anime tóc hồng dưới ánh trăng" → GENERATE
        Turn 2: "đổi tóc thành trắng"                      → EDIT (lineage=1)
        Turn 3: "thêm kính"                                 → EDIT (lineage=2)
        Turn 4: "giữ nhân vật cũ nhưng đổi background cyberpunk" → EDIT (lineage=3)

    After each turn we verify session state is consistent.
    """

    def setUp(self):
        self.planner = ScenePlanner()
        self.store   = SessionMemoryStore(max_sessions=16)
        self.fake    = _FakeImageResult()
        self.sid     = "multi-turn-test"

    def _do_turn(self, message: str, intent: ImageIntent) -> SceneSpec:
        """Simulate one turn of the pipeline (planner → memory update)."""
        mem = self.store.get_or_create(self.sid)
        is_edit = intent in (ImageIntent.EDIT, ImageIntent.FOLLOWUP_EDIT)

        result = self.planner.classify_and_plan(
            message=message,
            language="vi",
            has_previous_image=mem.has_previous_image,
            previous_scene=mem.last_scene_spec,
        )
        scene = result.scene

        self.store.update(
            self.sid, message, scene, self.fake, is_edit=is_edit,
        )
        return scene

    def test_full_chain(self):
        # Turn 1: initial generation (subject may be in Vietnamese)
        scene1 = self._do_turn(
            "vẽ cô gái anime tóc hồng dưới ánh trăng", ImageIntent.GENERATE,
        )
        mem = self.store.get(self.sid)
        self.assertEqual(mem.edit_lineage_count, 0)
        # "tóc hồng" is Vietnamese for pink hair
        all1 = f"{scene1.subject} {' '.join(scene1.subject_attributes)}".lower()
        self.assertTrue(
            "pink" in all1 or "hồng" in all1,
            f"Expected pink/hồng in scene: {all1}",
        )
        self.assertTrue(mem.has_previous_scene)

        # Turn 2: change hair → white
        scene2 = self._do_turn("đổi tóc thành trắng", ImageIntent.FOLLOWUP_EDIT)
        mem = self.store.get(self.sid)
        self.assertEqual(mem.edit_lineage_count, 1)
        all2 = f"{scene2.subject} {' '.join(scene2.subject_attributes)}".lower()
        self.assertIn("white", all2, f"Hair should be white: {all2}")

        # Turn 3: add glasses (cumulative)
        scene3 = self._do_turn("thêm kính", ImageIntent.FOLLOWUP_EDIT)
        mem = self.store.get(self.sid)
        self.assertEqual(mem.edit_lineage_count, 2)
        all3 = f"{scene3.subject} {' '.join(scene3.subject_attributes)}".lower()
        self.assertTrue(
            "glasses" in all3 or "kính" in all3,
            f"Glasses should be present: {all3}",
        )

        # Turn 4: keep character, change background
        scene4 = self._do_turn(
            "giữ nhân vật cũ nhưng đổi background cyberpunk",
            ImageIntent.FOLLOWUP_EDIT,
        )
        mem = self.store.get(self.sid)
        self.assertEqual(mem.edit_lineage_count, 3)
        self.assertIn("cyberpunk", scene4.background.lower())
        self.assertTrue(scene4.wants_consistency_with_previous)

    def test_context_never_lost(self):
        """Session memory always preserves the latest scene and image ref."""
        self._do_turn("vẽ cô gái anime tóc hồng", ImageIntent.GENERATE)
        self._do_turn("đổi tóc thành trắng", ImageIntent.FOLLOWUP_EDIT)
        self._do_turn("thêm kính", ImageIntent.FOLLOWUP_EDIT)

        mem = self.store.get(self.sid)

        # Previous image reference always set (from _FakeImageResult)
        self.assertTrue(mem.has_previous_image)
        # Scene never None after any turn
        self.assertIsNotNone(mem.last_scene_spec)
        # Provider recorded
        self.assertEqual(mem.last_provider, "fal")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    unittest.main(verbosity=2)
