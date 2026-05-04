"""Tests for image_pipeline.reasoning.prompt_revision."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

from image_pipeline.reasoning.prompt_revision import revise
from image_pipeline.reasoning.schemas import OverlayKind


class TestNormalization:
    def test_filler_stripped(self):
        r = revise("Please could you make me a red apple on a wooden table, thank you")
        normalized = r.normalized_prompt.lower()
        for filler in ("please", "could you", "thank you", "make me"):
            assert filler not in normalized
        assert "red apple" in normalized
        assert "wooden table" in normalized

    def test_source_text_preserved(self):
        text = "I would like a cute cat"
        r = revise(text)
        assert r.source_text == text
        # No invented content.
        assert "dog" not in r.normalized_prompt.lower()

    def test_midjourney_style_commas(self):
        r = revise("a tall warrior with a red sword and golden armor")
        # "and"/"with" collapsed to commas.
        assert ", " in r.normalized_prompt
        # Tokens are individually preserved.
        for token in ("tall warrior", "red sword", "golden armor"):
            assert token in r.normalized_prompt.lower()


class TestMustKeepForbidden:
    def test_must_keep_extracted(self):
        r = revise("change the dress, keep the red hair")
        assert any("red hair" in m for m in r.must_keep)

    def test_forbidden_drift_extracted(self):
        r = revise("a portrait, no glasses, without the hat")
        joined = " ".join(r.forbidden_drift)
        assert "glasses" in joined
        assert "hat" in joined

    def test_may_change_extracted(self):
        r = revise("same character but change the outfit to a red dress")
        assert any("outfit" in m for m in r.may_change)

    def test_prior_must_keep_carried(self):
        r = revise("now in the kitchen", prior_must_keep=("red hair", "blue eyes"))
        assert "red hair" in r.must_keep
        assert "blue eyes" in r.must_keep

    def test_prior_forbidden_carried_and_deduped(self):
        r = revise("no glasses", prior_forbidden_drift=("glasses", "hat"))
        # "glasses" appears in both prior and current, must dedupe.
        assert r.forbidden_drift.count("glasses") == 1
        assert "hat" in r.forbidden_drift


class TestOverlay:
    def test_quoted_text_implies_caption(self):
        r = revise('a phone screen showing "Hello world"')
        assert r.requires_overlay is True
        assert "Hello world" in r.extracted_quoted_text
        # phone_ui keyword present → that overlay kind detected.
        assert OverlayKind.PHONE_UI in r.detected_overlay_kinds

    def test_speech_bubble(self):
        r = revise('a comic with a speech bubble saying "boom"')
        assert OverlayKind.SPEECH_BUBBLE in r.detected_overlay_kinds
        assert "boom" in r.extracted_quoted_text

    def test_no_overlay_when_none_mentioned(self):
        r = revise("a quiet forest at dawn")
        assert r.requires_overlay is False
        assert r.extracted_quoted_text == ()

    def test_id_card_overlay(self):
        r = revise('an ID card lying on the desk with the name "Alice"')
        assert OverlayKind.ID_CARD in r.detected_overlay_kinds


class TestRegions:
    def test_face_region(self):
        r = revise("fix the face, eyes look weird")
        assert r.requires_regional_patch is True
        assert "face" in r.detected_regions
        assert "eyes" in r.detected_regions

    def test_background_region(self):
        r = revise("change the background to a beach")
        assert r.requires_regional_patch is True
        assert "background" in r.detected_regions

    def test_no_region_when_none(self):
        r = revise("a quiet forest scene")
        assert r.requires_regional_patch is False


class TestRobustness:
    def test_empty_string(self):
        r = revise("")
        assert r.normalized_prompt == ""
        assert r.must_keep == ()

    def test_to_dict_round_trip(self):
        r = revise('a "hello" caption')
        d = r.to_dict()
        assert d["source_text"] == 'a "hello" caption'
        assert d["requires_overlay"] is True
        assert isinstance(d["detected_overlay_kinds"], list)
