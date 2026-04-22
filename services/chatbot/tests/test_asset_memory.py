"""Focused tests for core.asset_memory.

Covers exactly the four contracts called out in the upgrade brief:
  1. migration from the old generatedImages[] frontend shape
  2. bounded storage / record count
  3. manifest-aware context formatting
  4. safe missing-field handling

Pure stdlib + pytest. No Flask app needed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.asset_memory import (
    MAX_RECORDS_IN_CONTEXT,
    build_asset_context_block,
    format_asset_context_lines,
    normalize_asset_record,
)


# ── 1. Migration from the legacy frontend shape ──────────────────────────────
def test_normalize_legacy_record_shape():
    legacy = {
        "url": "https://cdn/x.png",
        "prompt": "anime girl, blue hair",
        "provider": "fal",
        "model": "flux-dev",
        "timestamp": 1_700_000_000_000,
    }
    rec = normalize_asset_record(legacy)
    assert rec is not None
    assert rec["url"] == "https://cdn/x.png"
    assert rec["prompt"] == "anime girl, blue hair"
    assert rec["provider"] == "fal"
    assert rec["model"] == "flux-dev"
    assert rec["timestamp"] == 1_700_000_000_000
    # New fields default to None — old sessions don't break.
    for new_field in ("job_id", "character_key", "series_key", "preset", "manifest_path", "seed"):
        assert rec[new_field] is None


def test_normalize_new_record_shape_keeps_all_fields():
    raw = {
        "job_id": "job_abc",
        "conversation_id": "chat_42",
        "url": "/static/out.png",
        "prompt": "p",
        "provider": "local",
        "model": "anime_xl",
        "character_key": "miku",
        "series_key": "vocaloid",
        "preset": "anime_quality",
        "manifest_path": "/tmp/manifest.json",
        "seed": 12345,
    }
    rec = normalize_asset_record(raw)
    assert rec is not None
    assert rec["job_id"] == "job_abc"
    assert rec["character_key"] == "miku"
    assert rec["preset"] == "anime_quality"
    assert rec["seed"] == 12345


def test_normalize_aliases_and_default_conversation_id():
    raw = {"image_url": "https://cdn/y.png", "prompt": "p"}
    rec = normalize_asset_record(raw, default_conversation_id="chat_99")
    assert rec is not None
    assert rec["url"] == "https://cdn/y.png"
    assert rec["conversation_id"] == "chat_99"


# ── 2. Bounded storage / record count in the formatted context ───────────────
def test_formatter_caps_record_count():
    records = [{"url": f"https://x/{i}.png", "prompt": f"p{i}"} for i in range(20)]
    lines = format_asset_context_lines(records)
    assert len(lines) == MAX_RECORDS_IN_CONTEXT == 5


def test_formatter_explicit_max_zero_returns_empty():
    records = [{"url": "https://x/0.png", "prompt": "p"}]
    assert format_asset_context_lines(records, max_records=0) == []


def test_normalize_drops_base64_url():
    rec = normalize_asset_record({"url": "data:image/png;base64,AAA", "prompt": "p"})
    # url stripped but prompt keeps it salvageable
    assert rec is not None
    assert rec["url"] is None
    assert rec["prompt"] == "p"


def test_normalize_clips_oversized_prompt():
    huge = "x" * 10_000
    rec = normalize_asset_record({"url": "https://x/a.png", "prompt": huge})
    assert rec is not None
    assert len(rec["prompt"]) <= 240


# ── 3. Manifest-aware formatting ─────────────────────────────────────────────
def test_manifest_enrichment_populates_summary(tmp_path: Path):
    manifest = {
        "job_id": "j1",
        "preset": "anime_quality",
        "character_key": "rem",
        "seed": 7,
        "models_used": ["sdxl_anime", "esrgan"],
        "refine_rounds": 2,
    }
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(manifest), encoding="utf-8")
    record = {
        "url": "https://cdn/z.png",
        "prompt": "girl",
        "manifest_path": str(mp),
    }
    block = build_asset_context_block([record])
    assert "manifest:" in block
    assert "preset=anime_quality" in block
    assert "character_key=rem" in block
    assert "seed=7" in block
    assert "models=[sdxl_anime,esrgan]" in block
    assert "refine_rounds=2" in block


def test_manifest_path_traversal_rejected(tmp_path: Path):
    record = {
        "url": "https://cdn/z.png",
        "prompt": "p",
        "manifest_path": "../../etc/passwd",
    }
    block = build_asset_context_block([record])
    # Manifest enrichment silently skipped, but base record still shows.
    assert "manifest:" not in block
    assert "url: https://cdn/z.png" in block


def test_manifest_missing_file_silently_skipped():
    record = {
        "url": "https://cdn/z.png",
        "prompt": "p",
        "manifest_path": "/definitely/not/a/real/path/manifest.json",
    }
    block = build_asset_context_block([record])
    assert "manifest:" not in block
    assert "https://cdn/z.png" in block


def test_manifest_oversized_rejected(tmp_path: Path, monkeypatch):
    # Force the size cap low so we don't have to actually write 256 KiB.
    monkeypatch.setattr("core.asset_memory.MAX_MANIFEST_BYTES", 10)
    mp = tmp_path / "big.json"
    mp.write_text(json.dumps({"preset": "anime_quality", "extra": "padding" * 100}), encoding="utf-8")
    record = {"prompt": "p", "manifest_path": str(mp)}
    block = build_asset_context_block([record])
    assert "manifest:" not in block


def test_manifest_malformed_json_swallowed(tmp_path: Path):
    mp = tmp_path / "bad.json"
    mp.write_text("{not valid json", encoding="utf-8")
    record = {"prompt": "p", "manifest_path": str(mp)}
    block = build_asset_context_block([record])
    assert "manifest:" not in block
    assert "prompt: p" in block


# ── 4. Safe missing-field / malformed-input handling ─────────────────────────
@pytest.mark.parametrize("bad", [None, "", 0, [], {}, {"foo": "bar"}, {"url": ""}, {"prompt": ""}])
def test_normalize_returns_none_for_unsalvageable_input(bad):
    # Non-dict OR empty dict OR dict with no usable fields all → None.
    assert normalize_asset_record(bad) is None


def test_formatter_skips_non_dict_entries():
    records = [None, "string", 42, {"url": "https://x/a.png", "prompt": "ok"}, {"prompt": ""}]
    lines = format_asset_context_lines(records)
    assert len(lines) == 1
    assert "https://x/a.png" in lines[0]


def test_block_empty_when_no_records():
    assert build_asset_context_block([]) == ""
    assert build_asset_context_block([{"foo": "bar"}]) == ""


def test_seed_zero_is_preserved_but_invalid_is_dropped():
    # Seed 0 is a legitimate value, must survive normalization.
    rec = normalize_asset_record({"prompt": "p", "seed": 0})
    assert rec is not None
    assert rec["seed"] == 0
    rec2 = normalize_asset_record({"prompt": "p", "seed": "not-an-int"})
    assert rec2 is not None
    assert rec2["seed"] is None


def test_format_handles_record_with_only_prompt():
    block = build_asset_context_block([{"prompt": "girl with cat"}])
    assert "girl with cat" in block
    # No url/job — head fallback to "image"
    assert "- image" in block or "prompt: girl with cat" in block
