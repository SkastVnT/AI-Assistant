"""Unit tests for ``services/chatbot/core/character_registry``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure services/chatbot is on sys.path
_CHATBOT_DIR = Path(__file__).resolve().parents[1]
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


@pytest.fixture(autouse=True)
def _fresh_registry(monkeypatch, tmp_path):
    """Force a fresh registry instance per test, pointed at a temp DB."""
    from core import character_registry as cr

    db_dir = tmp_path / "character_db"
    db_dir.mkdir()
    chars_file = db_dir / "characters.json"
    aliases_file = db_dir / "series_aliases.json"

    chars_file.write_text(
        json.dumps(
            {
                "raiden_shogun_genshin_impact": {
                    "key": "raiden_shogun_genshin_impact",
                    "display_name": "Raiden Shogun",
                    "series": "Genshin Impact",
                    "series_key": "genshin_impact",
                    "character_tag": "raiden_shogun",
                    "series_tag": "genshin_impact",
                    "aliases": ["Ei", "Baal"],
                    "thumbnail": None,
                },
                "rem_re_zero": {
                    "key": "rem_re_zero",
                    "display_name": "Rem",
                    "series": "Re:Zero",
                    "series_key": "re_zero",
                    "character_tag": "rem_(re:zero)",
                    "series_tag": "re:zero",
                    "aliases": [],
                },
                "rem_pokemon": {
                    "key": "rem_pokemon",
                    "display_name": "Rem",
                    "series": "Pokemon",
                    "series_key": "pokemon",
                    "character_tag": "rem_(pokemon)",
                    "series_tag": "pokemon",
                    "aliases": [],
                },
            }
        ),
        encoding="utf-8",
    )
    aliases_file.write_text(
        json.dumps(
            {
                "GI": "genshin_impact",
                "Genshin": "genshin_impact",
                "HSR": "honkai_star_rail",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(cr, "_CHARACTERS_FILE", chars_file)
    monkeypatch.setattr(cr, "_SERIES_ALIASES_FILE", aliases_file)
    cr.CharacterRegistry._instance = None
    yield
    cr.CharacterRegistry._instance = None


def test_load_and_count():
    from core.character_registry import get_registry

    reg = get_registry()
    assert len(reg.list_all()) == 3


def test_get_by_key():
    from core.character_registry import get_registry

    reg = get_registry()
    rec = reg.get("raiden_shogun_genshin_impact")
    assert rec is not None
    assert rec.display_name == "Raiden Shogun"
    assert rec.series_key == "genshin_impact"


def test_find_by_query():
    from core.character_registry import get_registry

    reg = get_registry()
    res = reg.find(query="raiden")
    assert len(res) == 1
    assert res[0].key == "raiden_shogun_genshin_impact"


def test_find_by_alias_in_query():
    from core.character_registry import get_registry

    reg = get_registry()
    res = reg.find(query="ei")
    keys = {r.key for r in res}
    assert "raiden_shogun_genshin_impact" in keys


def test_series_filter_with_alias():
    from core.character_registry import get_registry

    reg = get_registry()
    res = reg.find(series_filter="GI")
    assert len(res) == 1
    assert res[0].series_key == "genshin_impact"


def test_series_filter_with_canonical():
    from core.character_registry import get_registry

    reg = get_registry()
    res = reg.find(series_filter="re_zero")
    assert len(res) == 1
    assert res[0].key == "rem_re_zero"


def test_normalize_series():
    from core.character_registry import get_registry

    reg = get_registry()
    assert reg.normalize_series("HSR") == "honkai_star_rail"
    assert reg.normalize_series("hsr") == "honkai_star_rail"
    assert (
        reg.normalize_series("Genshin Impact") is None
    )  # not in alias map (only "GI"/"Genshin")
    assert (
        reg.normalize_series("genshin_impact") == "genshin_impact"
    )  # canonical fallback
    assert reg.normalize_series("nonsense") is None


def test_resolve_query_exact_name():
    from core.character_registry import get_registry

    reg = get_registry()
    rec = reg.resolve_query("Raiden Shogun")
    assert rec is not None
    assert rec.key == "raiden_shogun_genshin_impact"


def test_resolve_query_alias():
    from core.character_registry import get_registry

    reg = get_registry()
    rec = reg.resolve_query("Ei")
    assert rec is not None
    assert rec.key == "raiden_shogun_genshin_impact"


def test_resolve_query_partial():
    from core.character_registry import get_registry

    reg = get_registry()
    rec = reg.resolve_query("shogun")
    assert rec is not None


def test_collision_detection():
    from core.character_registry import get_registry

    reg = get_registry()
    collisions = reg.detect_collisions("Rem")
    keys = {c.key for c in collisions}
    assert keys == {"rem_re_zero", "rem_pokemon"}


def test_list_series():
    from core.character_registry import get_registry

    reg = get_registry()
    series = reg.list_series()
    keys = {s["key"] for s in series}
    assert keys == {"genshin_impact", "re_zero", "pokemon"}
