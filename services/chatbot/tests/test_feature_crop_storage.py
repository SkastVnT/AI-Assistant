"""Tests for image_pipeline.anime_pipeline.feature_crop_storage.

Covers the spec (2026-04-23):
  "cat ra thanh cac tam nho coi no lam mot layer va luu no tai nhu la
   <ten session chat><dac trung><nhan vat><game/?><ts(HH/DD/MM/YYYY)>
   .<file_extension>"
"""
from __future__ import annotations

import base64
import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from image_pipeline.anime_pipeline.feature_crop_storage import (  # noqa: E402
    _slug,
    persist_feature_crops,
)


# ── helpers ─────────────────────────────────────────────────────────

def _png_b64(w: int = 256, h: int = 256, color=(180, 90, 40)) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _region(rtype: str, x1=10, y1=10, x2=80, y2=80, conf=0.91):
    return SimpleNamespace(
        region_type=rtype, x1=x1, y1=y1, x2=x2, y2=y2,
        confidence=conf, label=rtype,
    )


def _job(session="chat-abc", char="Klee", series="Genshin Impact",
         img_b64: str | None = None):
    return SimpleNamespace(
        job_id="job-001",
        session_id=session,
        character_name=char,
        series_name=series,
        final_image_b64=img_b64 if img_b64 is not None else _png_b64(),
        metadata={},
    )


def _detection(regions: dict[str, list]):
    return SimpleNamespace(
        regions=regions,
        total_regions=sum(len(v) for v in regions.values()),
    )


# ── slug ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("Genshin Impact", "Genshin_Impact"),
    ("Re:Zero / kara Hajimeru", "Re_Zero_kara_Hajimeru"),
    ("../../etc/passwd", "etc_passwd"),
    ("", "fallback"),
    ("   ", "fallback"),
])
def test_slug_filesystem_safe(raw, expected):
    assert _slug(raw, fallback="fallback") == expected


def test_slug_truncates():
    assert len(_slug("a" * 200, max_len=32)) == 32


# ── persist_feature_crops ───────────────────────────────────────────

def test_persist_no_detection_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_LAYER_DIR", str(tmp_path))
    assert persist_feature_crops(_job(), None) == []
    assert persist_feature_crops(_job(), _detection({})) == []


def test_persist_no_image_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_LAYER_DIR", str(tmp_path))
    job = _job(img_b64="")
    det = _detection({"face": [_region("face")]})
    assert persist_feature_crops(job, det) == []


def test_persist_creates_files_per_region(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_LAYER_DIR", str(tmp_path))
    det = _detection({
        "face": [_region("face", 10, 10, 90, 90)],
        "lips": [_region("lips", 30, 50, 70, 70)],
        "iris": [_region("iris", 35, 35, 50, 50),
                 _region("iris", 55, 35, 70, 50)],
    })
    out = persist_feature_crops(_job(), det)

    assert len(out) == 4
    feats = {e["feature"] for e in out}
    assert feats == {"face", "lips", "iris"}

    for entry in out:
        p = Path(entry["path"])
        assert p.exists() and p.stat().st_size > 0
        # filename template: <char>__<series>__<feature>__<ts>__<idx>.png
        parts = p.stem.split("__")
        assert len(parts) == 5
        assert parts[0] == "Klee"
        assert parts[1] == "Genshin_Impact"
        assert parts[2] == entry["feature"]
        assert parts[4] == f"{entry['index']:02d}"
        # session subdir
        assert p.parent.name == "chat-abc"


def test_persist_color_stats_present(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_LAYER_DIR", str(tmp_path))
    job = _job(img_b64=_png_b64(color=(200, 50, 25)))
    det = _detection({"face": [_region("face", 0, 0, 100, 100)]})
    out = persist_feature_crops(job, det)
    assert len(out) == 1
    e = out[0]
    assert "mean_rgb" in e and len(e["mean_rgb"]) == 3
    assert e["hex"].startswith("#") and len(e["hex"]) == 7
    # Crop is uniform color, mean must match the source colour exactly.
    assert e["mean_rgb"] == [200, 50, 25]


def test_persist_clamps_bbox_within_image(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_LAYER_DIR", str(tmp_path))
    job = _job(img_b64=_png_b64(64, 64))
    # bbox extends past image; padding pushes it further out
    det = _detection({"hand": [_region("hand", -20, -20, 200, 200)]})
    out = persist_feature_crops(job, det, padding_px=16)
    assert len(out) == 1
    bbox = out[0]["bbox"]
    assert bbox[0] >= 0 and bbox[1] >= 0
    assert bbox[2] <= 64 and bbox[3] <= 64


def test_persist_skips_invalid_bbox(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_LAYER_DIR", str(tmp_path))
    det = _detection({"face": [_region("face", 50, 50, 50, 50)]})  # zero area
    assert persist_feature_crops(_job(), det, padding_px=0) == []


def test_persist_falls_back_to_job_id_when_no_session(tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_LAYER_DIR", str(tmp_path))
    job = _job(session="")
    det = _detection({"face": [_region("face")]})
    out = persist_feature_crops(job, det)
    assert len(out) == 1
    # session_id was empty → falls back to job_id ("job-001")
    assert out[0]["session_id"] == "job-001"
    assert Path(out[0]["path"]).parent.name == "job-001"
