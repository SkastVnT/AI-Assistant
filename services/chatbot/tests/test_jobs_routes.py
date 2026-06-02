"""Focused tests for local image-job manifest resolution."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHATBOT_ROOT = ROOT / "services" / "chatbot"
if str(CHATBOT_ROOT) not in sys.path:
    sys.path.insert(0, str(CHATBOT_ROOT))


def test_manifest_resolution_prefers_recorded_safe_path(tmp_path, monkeypatch):
    from routes import jobs

    monkeypatch.setattr(jobs, "_REPO_ROOT", tmp_path)
    recorded = tmp_path / "app" / "storage" / "intermediate" / "j1" / "custom.json"
    recorded.parent.mkdir(parents=True)
    recorded.write_text(json.dumps({"job_id": "j1"}), encoding="utf-8")

    assert jobs._find_manifest_file("j1", str(recorded)) == recorded.resolve()


def test_manifest_resolution_rejects_recorded_traversal_and_uses_canonical(
    tmp_path, monkeypatch
):
    from routes import jobs

    monkeypatch.setattr(jobs, "_REPO_ROOT", tmp_path)
    canonical = tmp_path / "app" / "storage" / "metadata" / "j2.json"
    canonical.parent.mkdir(parents=True)
    canonical.write_text(json.dumps({"job_id": "j2"}), encoding="utf-8")
    unsafe = tmp_path / "private" / "j2.json"
    unsafe.parent.mkdir(parents=True)
    unsafe.write_text("{}", encoding="utf-8")

    assert jobs._find_manifest_file("j2", str(unsafe)) == canonical.resolve()


def test_manifest_resolution_falls_back_to_legacy_intermediate(tmp_path, monkeypatch):
    from routes import jobs

    monkeypatch.setattr(jobs, "_REPO_ROOT", tmp_path)
    legacy = (
        tmp_path
        / "app"
        / "storage"
        / "intermediate"
        / "j3"
        / "output_manifest.json"
    )
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"job_id": "j3"}), encoding="utf-8")

    assert jobs._find_manifest_file("j3") == legacy.resolve()
