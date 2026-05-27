"""
Tests for the character parser and identity-aware overrides in the anime
pipeline orchestrator.

Covers:
  * exact preposition parsing (from / of / in / trong / của)
  * alias normalization (HSR, ZZZ, GI, HI3)
  * ambiguous / homonym detection
  * single-character solo-intent enforcement
  * collision-block emission and orchestrator injection

Run:
    cd services/chatbot && pytest tests/test_character_parser.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Ensure project root is importable ────────────────────────────────
_root = Path(__file__).resolve().parents[3]  # AI-Assistant/
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "services" / "chatbot"))

from image_pipeline.anime_pipeline.character_parser import (  # noqa: E402
    ParsedIdentity,
    parse_character_identity,
)
from image_pipeline.anime_pipeline.character_research import (  # noqa: E402
    detect_character,
)
from image_pipeline.anime_pipeline.schemas import (  # noqa: E402
    AnimePipelineJob,
    VisionAnalysis,
)

# ═══════════════════════════════════════════════════════════════════════
# 1. Exact preposition parsing
# ═══════════════════════════════════════════════════════════════════════


class TestExplicitPrepositionPatterns:
    """The four spec patterns must parse to explicit_pattern."""

    def test_english_from(self):
        r = parse_character_identity("Kafka from Honkai Star Rail")
        assert r.resolved
        assert r.character_tag == "kafka_(honkai:_star_rail)"
        assert r.series_tag == "honkai:_star_rail"
        assert r.character_name == "Kafka"
        assert r.series_name == "Honkai: Star Rail"
        assert r.alias_source == "explicit_pattern"

    def test_english_of(self):
        r = parse_character_identity("Rem of Re:Zero")
        assert r.resolved
        assert r.character_tag == "rem_(re:zero)"
        assert r.series_tag == "re:zero"
        assert r.alias_source == "explicit_pattern"

    def test_english_in(self):
        r = parse_character_identity("Nahida in Genshin Impact")
        assert r.resolved
        assert r.character_tag == "nahida_(genshin_impact)"
        assert r.series_tag == "genshin_impact"
        assert r.alias_source == "explicit_pattern"

    def test_vietnamese_trong(self):
        r = parse_character_identity("Raiden Shogun trong Genshin Impact")
        assert r.resolved
        assert r.character_tag == "raiden_shogun"
        assert r.series_tag == "genshin_impact"
        assert r.character_name == "Raiden Shogun"
        assert r.alias_source == "explicit_pattern"

    def test_vietnamese_cua(self):
        r = parse_character_identity("Hu Tao của Genshin")
        assert r.resolved
        assert r.character_tag == "hu_tao_(genshin_impact)"
        assert r.series_tag == "genshin_impact"
        assert r.alias_source == "explicit_pattern"


# ═══════════════════════════════════════════════════════════════════════
# 2. Alias normalization (HSR, ZZZ, GI, HI3)
# ═══════════════════════════════════════════════════════════════════════


class TestSeriesAliases:
    def test_hsr_alias(self):
        r = parse_character_identity("Kafka HSR")
        assert r.resolved
        assert r.series_tag == "honkai:_star_rail"

    def test_zzz_alias(self):
        r = parse_character_identity("Ellen Joe ZZZ")
        assert r.resolved
        assert r.series_tag == "zenless_zone_zero"

    def test_gi_alias(self):
        r = parse_character_identity("Hu Tao GI")
        assert r.resolved
        assert r.series_tag == "genshin_impact"

    def test_hi3_alias_no_character(self):
        # No character matched — resolved should stay False but parse
        # should still succeed without error.
        r = parse_character_identity("HI3 artwork")
        assert isinstance(r, ParsedIdentity)
        assert not r.resolved


# ═══════════════════════════════════════════════════════════════════════
# 3. Ambiguous / homonym disambiguation
# ═══════════════════════════════════════════════════════════════════════


class TestHomonymDisambiguation:
    def test_unqualified_name_no_series(self):
        """Bare "Kafka" resolves deterministically but should carry
        off-domain collision blocks (Franz Kafka, photographs)."""
        r = parse_character_identity("draw Kafka")
        assert r.resolved
        assert r.character_tag == "kafka_(honkai:_star_rail)"
        assert r.alias_source == "alias_only"
        # Off-domain homonym suppressors present
        joined = ", ".join(b.lower() for b in r.collision_blocks)
        assert "franz kafka" in joined

    def test_series_hint_wins_over_alias_order(self):
        """When both a character and a series hint appear, series hint
        must pick the matching character."""
        r = parse_character_identity("Seele from Honkai Star Rail standing alone")
        assert r.resolved
        assert r.series_tag == "honkai:_star_rail"
        # Solo enforcement triggered by "alone"
        assert r.solo_intent is True

    def test_word_boundary_prevents_partial_match(self):
        """The alias ``ram`` must not match inside ``framework``."""
        r = parse_character_identity("build a framework diagram")
        assert not r.resolved

    def test_multiple_characters_flag_homonym_collision(self):
        """When the prompt names two different characters without a
        series hint, the parser resolves deterministically but flags
        ``homonym_collision`` for downstream auditing."""
        # "Rem" and "Emilia" are both Re:Zero; to get a true collision
        # we use characters from different series with no hint: "Kafka"
        # (HSR) + "Rin" (Fate) — both are aliases.
        r = parse_character_identity("Kafka and Rin")
        assert r.resolved
        # Multiple distinct candidates → homonym_collision flagged
        assert r.homonym_collision is True
        # Collision blocks must include the losing character's name
        losers = [c[2] for c in r.candidates if c[0] != r.character_tag]
        assert losers, "expected at least one losing candidate"
        joined = ", ".join(b.lower() for b in r.collision_blocks)
        assert any(n.lower() in joined for n in losers)


# ═══════════════════════════════════════════════════════════════════════
# 4. Solo-intent enforcement
# ═══════════════════════════════════════════════════════════════════════


class TestSoloIntent:
    def test_solo_keyword(self):
        r = parse_character_identity("Hu Tao solo")
        assert r.solo_intent is True

    def test_1girl_keyword(self):
        r = parse_character_identity("Firefly HSR 1girl")
        assert r.solo_intent is True

    def test_vietnamese_solo(self):
        r = parse_character_identity("một cô gái Nahida Genshin")
        assert r.solo_intent is True

    def test_plural_disables_solo(self):
        r = parse_character_identity("Hu Tao and Nahida 2girls")
        assert r.solo_intent is False

    def test_solo_emits_multi_subject_negatives(self):
        r = parse_character_identity("Kafka HSR solo")
        assert r.solo_intent is True
        joined = ", ".join(b.lower() for b in r.collision_blocks)
        assert "2girls" in joined
        assert "multiple girls" in joined
        assert "crowd" in joined

    def test_solo_without_character(self):
        """Solo keyword with no known character still flags intent and
        still produces multi-subject collision negatives so downstream
        negatives can suppress crowds."""
        r = parse_character_identity("a single anime girl solo")
        assert r.solo_intent is True
        assert not r.resolved
        assert r.collision_blocks  # multi-subject negatives still present


# ═══════════════════════════════════════════════════════════════════════
# 5. Collision-block content
# ═══════════════════════════════════════════════════════════════════════


class TestCollisionBlocks:
    def test_kafka_off_domain_suppressors(self):
        r = parse_character_identity("Kafka HSR")
        joined = ", ".join(b.lower() for b in r.collision_blocks)
        assert "franz kafka" in joined

    def test_no_character_no_off_domain_blocks(self):
        """Empty prompt → empty everything."""
        r = parse_character_identity("")
        assert not r.resolved
        assert r.collision_blocks == []
        assert r.solo_intent is False

    def test_collision_blocks_deduplicate(self):
        """Repeated collision triggers must not duplicate entries."""
        r = parse_character_identity("Kafka HSR solo Kafka")
        lowered = [b.lower() for b in r.collision_blocks]
        assert len(lowered) == len(set(lowered))


# ═══════════════════════════════════════════════════════════════════════
# 6. Backward-compat: detect_character still works
# ═══════════════════════════════════════════════════════════════════════


class TestDetectCharacterBackwardCompat:
    def test_detect_character_returns_tuple(self):
        result = detect_character("Raiden Shogun trong Genshin Impact")
        assert result is not None
        tag, series_tag, name, series_name = result
        assert tag == "raiden_shogun"
        assert series_tag == "genshin_impact"

    def test_detect_character_none_on_no_match(self):
        assert detect_character("just a landscape") is None


# ═══════════════════════════════════════════════════════════════════════
# 7. Orchestrator identity-override helper
# ═══════════════════════════════════════════════════════════════════════


class TestIdentityOverrideInjection:
    """Verify the orchestrator's ``_apply_identity_overrides`` hook wires
    solo_intent and collision_blocks into vision_analysis.
    """

    def _make_orchestrator(self):
        # Import lazily — orchestrator requires optional deps at import
        # time, so we guard the import.
        from image_pipeline.anime_pipeline.orchestrator import (
            AnimePipelineOrchestrator,
        )

        return AnimePipelineOrchestrator()

    def test_solo_injects_solo_tag(self):
        orch = self._make_orchestrator()
        job = AnimePipelineJob(user_prompt="Hu Tao solo")
        job.solo_intent = True
        job.vision_analysis = VisionAnalysis(anime_tags=["hu_tao", "dress"])
        orch._apply_identity_overrides(job)
        assert job.vision_analysis.anime_tags[0] == "solo"

    def test_collision_blocks_merge_into_negatives(self):
        orch = self._make_orchestrator()
        job = AnimePipelineJob(user_prompt="Kafka HSR solo")
        job.solo_intent = True
        job.collision_blocks = ["2girls", "franz kafka", "crowd"]
        job.vision_analysis = VisionAnalysis(suggested_negative="lowres, blurry")
        orch._apply_identity_overrides(job)
        neg = job.vision_analysis.suggested_negative.lower()
        assert "2girls" in neg
        assert "franz kafka" in neg
        assert "crowd" in neg
        assert "lowres" in neg  # pre-existing negative preserved

    def test_idempotent(self):
        orch = self._make_orchestrator()
        job = AnimePipelineJob(user_prompt="Kafka HSR solo")
        job.solo_intent = True
        job.collision_blocks = ["2girls", "crowd"]
        job.vision_analysis = VisionAnalysis(suggested_negative="")
        orch._apply_identity_overrides(job)
        neg_once = job.vision_analysis.suggested_negative
        orch._apply_identity_overrides(job)
        neg_twice = job.vision_analysis.suggested_negative
        assert neg_once == neg_twice

    def test_no_vision_analysis_is_noop(self):
        orch = self._make_orchestrator()
        job = AnimePipelineJob(user_prompt="Kafka HSR solo")
        job.solo_intent = True
        job.collision_blocks = ["2girls"]
        job.vision_analysis = None
        # Must not raise.
        orch._apply_identity_overrides(job)


# ═══════════════════════════════════════════════════════════════════════
# 8. AnimePipelineJob new fields
# ═══════════════════════════════════════════════════════════════════════


class TestJobIdentityFields:
    def test_default_identity_fields_empty(self):
        job = AnimePipelineJob()
        assert job.character_name == ""
        assert job.series_name == ""
        assert job.character_tag == ""
        assert job.series_tag == ""
        assert job.alias_source == ""
        assert job.solo_intent is False
        assert job.collision_blocks == []

    def test_identity_fields_in_to_dict(self):
        job = AnimePipelineJob(user_prompt="Kafka HSR")
        job.character_name = "Kafka"
        job.series_name = "Honkai: Star Rail"
        job.character_tag = "kafka_(honkai:_star_rail)"
        job.series_tag = "honkai:_star_rail"
        job.alias_source = "series_hint"
        job.solo_intent = True
        job.collision_blocks = ["franz kafka"]
        d = job.to_dict()
        assert d["character_name"] == "Kafka"
        assert d["series_tag"] == "honkai:_star_rail"
        assert d["alias_source"] == "series_hint"
        assert d["solo_intent"] is True
        assert d["collision_blocks"] == ["franz kafka"]
