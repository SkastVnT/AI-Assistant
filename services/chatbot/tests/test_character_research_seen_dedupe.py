"""Unit tests for the seen-URL / byte-hash dedupe logic in
character_research.

User contract (2026-04-23): reference image search MUST always return
fresh images. URLs we've downloaded before AND files whose bytes we've
seen before must both be rejected by the downloader, and the cached-set
short-circuit in research_character must NOT skip a fresh search.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from unittest import mock

import pytest

# Module under test
from image_pipeline.anime_pipeline import character_research as cr


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def tmp_storage(tmp_path, monkeypatch):
    """Redirect _REF_DIR / _RESEARCH_DIR into a temp dir."""
    storage = tmp_path / "storage"
    ref_dir = storage / "character_refs"
    research_dir = storage / "character_research"
    ref_dir.mkdir(parents=True)
    research_dir.mkdir(parents=True)
    monkeypatch.setattr(cr, "_REF_DIR", ref_dir)
    monkeypatch.setattr(cr, "_RESEARCH_DIR", research_dir)
    # Disable opt-in to old behaviour
    monkeypatch.delenv("CHAR_RESEARCH_REUSE_REFS", raising=False)
    return storage


def _png_bytes(seed: int = 0) -> bytes:
    """Return a deterministic blob big enough to pass the 5KB filter."""
    head = b"\x89PNG\r\n\x1a\n"
    body = bytes((seed + i) & 0xFF for i in range(8000))
    return head + body


# ── Registry ─────────────────────────────────────────────────────────


def test_seen_registry_roundtrip(tmp_storage):
    tag = "tag_x"
    cr._save_seen_registry(tag, {
        "url_hashes": {"abc123de": "web_abc123de.png"},
        "byte_hashes": {"f" * 64: "web_abc123de.png"},
    })
    reg = cr._load_seen_registry(tag)
    assert reg["url_hashes"]["abc123de"] == "web_abc123de.png"
    assert reg["byte_hashes"]["f" * 64] == "web_abc123de.png"


def test_seen_registry_backfills_existing_files(tmp_storage):
    tag = "back_fill"
    ref_dir = tmp_storage / "character_refs" / tag
    ref_dir.mkdir(parents=True)
    data = _png_bytes(1)
    fname = "web_deadbeef.png"
    (ref_dir / fname).write_bytes(data)

    reg = cr._load_seen_registry(tag)

    assert "deadbeef" in reg["url_hashes"]
    assert reg["url_hashes"]["deadbeef"] == fname
    assert hashlib.sha256(data).hexdigest() in reg["byte_hashes"]


def test_url_hash_stable():
    a = cr._url_hash("https://example.com/cat.png")
    b = cr._url_hash("https://example.com/cat.png")
    c = cr._url_hash("https://example.com/dog.png")
    assert a == b
    assert a != c
    assert len(a) == 8


def test_is_url_seen():
    reg = {"url_hashes": {cr._url_hash("https://x/y.png"): "y.png"},
           "byte_hashes": {}}
    assert cr._is_url_seen("https://x/y.png", reg) is True
    assert cr._is_url_seen("https://x/z.png", reg) is False


# ── Downloader ───────────────────────────────────────────────────────


def test_downloader_skips_seen_url(tmp_storage):
    tag = "skip_url"
    url = "https://cdn.example/x.png"
    # Pre-populate registry with this URL
    cr._save_seen_registry(tag, {
        "url_hashes": {cr._url_hash(url): "web_old.png"},
        "byte_hashes": {},
    })
    image_results = [{"url": url, "width": 1024, "height": 1024}]

    with mock.patch("httpx.get") as mock_get:
        out = cr._download_reference_images(image_results, tag, max_images=5)

    # Network must not be called for a seen URL
    mock_get.assert_not_called()
    assert out == []


def test_downloader_rejects_byte_duplicate(tmp_storage):
    tag = "byte_dup"
    body = _png_bytes(7)
    bh = hashlib.sha256(body).hexdigest()
    cr._save_seen_registry(tag, {
        "url_hashes": {},
        "byte_hashes": {bh: "web_existing.png"},
    })

    fake_resp = mock.Mock()
    fake_resp.status_code = 200
    fake_resp.headers = {"content-type": "image/png"}
    fake_resp.content = body

    with mock.patch("httpx.get", return_value=fake_resp):
        out = cr._download_reference_images(
            [{"url": "https://new.example/x.png",
              "width": 1024, "height": 1024}],
            tag, max_images=5,
        )

    # File must NOT be re-saved despite a fresh URL
    assert out == []
    saved = list((tmp_storage / "character_refs" / tag).glob("*.png"))
    # Only no new file beyond what was pre-existing (none were written)
    assert all(p.name != f"web_{cr._url_hash('https://new.example/x.png')}.png"
               for p in saved)
    # Registry now records the URL→existing-file mapping
    reg = cr._load_seen_registry(tag)
    assert cr._url_hash("https://new.example/x.png") in reg["url_hashes"]


def test_downloader_persists_fresh_download(tmp_storage):
    tag = "fresh_save"
    body = _png_bytes(11)

    fake_resp = mock.Mock()
    fake_resp.status_code = 200
    fake_resp.headers = {"content-type": "image/png"}
    fake_resp.content = body

    with mock.patch("httpx.get", return_value=fake_resp):
        out = cr._download_reference_images(
            [{"url": "https://fresh.example/a.png",
              "width": 1024, "height": 1024}],
            tag, max_images=5,
        )

    assert len(out) == 1
    # Decoded base64 must match the bytes we returned
    assert base64.b64decode(out[0]) == body
    # File saved under the deterministic name
    fname = f"web_{cr._url_hash('https://fresh.example/a.png')}.png"
    assert (tmp_storage / "character_refs" / tag / fname).read_bytes() == body
    # Registry persisted
    reg = cr._load_seen_registry(tag)
    assert cr._url_hash("https://fresh.example/a.png") in reg["url_hashes"]
    assert hashlib.sha256(body).hexdigest() in reg["byte_hashes"]


def test_downloader_falls_back_to_cached_when_no_fresh(tmp_storage):
    tag = "fallback_only"
    ref_dir = tmp_storage / "character_refs" / tag
    ref_dir.mkdir(parents=True)
    body = _png_bytes(99)
    (ref_dir / "web_cafebabe.png").write_bytes(body)

    # Pass an empty image_results list — fresh fetch yields nothing
    out = cr._download_reference_images([], tag, max_images=5)

    assert len(out) == 1
    assert base64.b64decode(out[0]) == body


def test_reuse_env_flag_uses_cached_first(tmp_storage, monkeypatch):
    tag = "opt_in_reuse"
    ref_dir = tmp_storage / "character_refs" / tag
    ref_dir.mkdir(parents=True)
    body = _png_bytes(42)
    (ref_dir / "web_baadf00d.png").write_bytes(body)

    monkeypatch.setenv("CHAR_RESEARCH_REUSE_REFS", "1")

    # Even with fresh image_results, opt-in should return cached
    with mock.patch("httpx.get") as mock_get:
        out = cr._download_reference_images(
            [{"url": "https://new.example/x.png",
              "width": 1024, "height": 1024}],
            tag, max_images=5,
        )

    mock_get.assert_not_called()
    assert len(out) == 1
    assert base64.b64decode(out[0]) == body
