"""Tests for image_pipeline.reasoning.capability_router."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

from image_pipeline.reasoning.capability_router import (
    CapabilityRequest,
    RequestKind,
    classify,
)


class TestSimpleClassification:
    def test_empty_text_no_image_is_text_to_image(self):
        d = classify(CapabilityRequest(text=""))
        assert d.kind is RequestKind.TEXT_TO_IMAGE

    def test_simple_text_to_image(self):
        d = classify(CapabilityRequest(text="a photo of a red apple on a wooden table"))
        assert d.kind is RequestKind.TEXT_TO_IMAGE
        assert "base" in d.required_stages

    def test_one_image_is_edit(self):
        d = classify(CapabilityRequest(text="make the sky bluer", attached_images=1))
        assert d.kind is RequestKind.IMAGE_EDIT
        assert d.confidence >= 0.7

    def test_one_image_no_keyword_still_edit(self):
        d = classify(CapabilityRequest(text="this picture", attached_images=1))
        assert d.kind is RequestKind.IMAGE_EDIT

    def test_two_images_is_compose(self):
        d = classify(CapabilityRequest(text="merge these", attached_images=2))
        assert d.kind is RequestKind.MULTI_IMAGE_COMPOSE

    def test_compose_keyword_with_one_image(self):
        d = classify(
            CapabilityRequest(
                text="use these references as a moodboard",
                attached_images=1,
            )
        )
        assert d.kind is RequestKind.MULTI_IMAGE_COMPOSE


class TestRefine:
    def test_followup_with_refine_keyword(self):
        d = classify(
            CapabilityRequest(
                text="now make it brighter",
                attached_images=0,
                is_followup=True,
            )
        )
        assert d.kind is RequestKind.ITERATIVE_REFINE

    def test_followup_without_keyword_falls_through(self):
        d = classify(
            CapabilityRequest(
                text="a cat sitting on a chair",
                attached_images=0,
                is_followup=True,
            )
        )
        # No refine keyword, no edit keyword, no image → text_to_image.
        assert d.kind is RequestKind.TEXT_TO_IMAGE

    def test_followup_with_prior_image_and_edit_keyword(self):
        d = classify(
            CapabilityRequest(
                text="remove the watermark",
                attached_images=0,
                is_followup=True,
                prior_image_ref="img_abc",
            )
        )
        assert d.kind is RequestKind.IMAGE_EDIT


class TestComicSequence:
    def test_panel_count_phrase(self):
        d = classify(CapabilityRequest(text="4 panel comic of Alice in her bedroom"))
        assert d.kind is RequestKind.COMIC_SEQUENCE
        assert d.panel_count_hint == 4

    def test_storyboard_keyword(self):
        d = classify(CapabilityRequest(text="storyboard for a chase scene"))
        assert d.kind is RequestKind.COMIC_SEQUENCE

    def test_panel_labels(self):
        d = classify(
            CapabilityRequest(text="panel 1 she enters. panel 2 she sits. panel 3 she sleeps.")
        )
        assert d.kind is RequestKind.COMIC_SEQUENCE
        assert d.panel_count_hint == 3

    def test_ten_panel_comic(self):
        d = classify(CapabilityRequest(text="please make a 10-panel comic about a ninja cat"))
        assert d.kind is RequestKind.COMIC_SEQUENCE
        assert d.panel_count_hint == 10

    def test_single_panel_word_does_not_trigger(self):
        d = classify(CapabilityRequest(text="1 panel scene of a cat"))
        # 1 panel is below the >=2 threshold → not a sequence by count alone.
        assert d.kind is RequestKind.TEXT_TO_IMAGE


class TestOverride:
    def test_explicit_kind_wins(self):
        d = classify(
            CapabilityRequest(
                text="merge these references",
                attached_images=2,
                explicit_kind=RequestKind.TEXT_TO_IMAGE,
            )
        )
        assert d.kind is RequestKind.TEXT_TO_IMAGE
        assert d.confidence == 1.0


class TestDecisionShape:
    def test_decision_to_dict_round_trip(self):
        d = classify(CapabilityRequest(text="a 4 panel comic"))
        out = d.to_dict()
        assert out["kind"] == "comic_sequence"
        assert isinstance(out["reasons"], list)
        assert isinstance(out["required_stages"], list)
