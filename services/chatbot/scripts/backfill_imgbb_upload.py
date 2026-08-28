"""
Batch-upload all gallery images to ImgBB + Google Drive.

Scans two directories:
  - Storage/Image_Gen  (chatbot outputs — paired *.meta.json)
  - ComfyUI/final      (anime pipeline outputs — no meta.json, create on the fly)

Skips 0-byte files and images already uploaded (cloud_url set).
Updates meta.json + upserts MongoDB for every image processed.

Run: python services/chatbot/scripts/backfill_imgbb_upload.py
"""

import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

CHATBOT = Path(__file__).resolve().parents[1]
REPO    = CHATBOT.parents[1]
sys.path.insert(0, str(CHATBOT))

# ── env ───────────────────────────────────────────────────────────────────────
def load_env(p: Path):
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

load_env(CHATBOT / ".env")
os.environ["GOOGLE_DRIVE_ENABLED"] = "true"

IMGBB_KEY = os.getenv("IMGBB_API_KEY", "").strip()
if not IMGBB_KEY:
    print("ERROR: IMGBB_API_KEY not set in .env")
    sys.exit(1)

# ── MongoDB ───────────────────────────────────────────────────────────────────
from pymongo import MongoClient

X509_URI    = os.getenv("MONGODB_X509_URI", "").strip()
X509_CERT   = os.getenv("MONGODB_X509_CERT_PATH", "").strip()
TLS_INVALID = os.getenv("MONGODB_TLS_ALLOW_INVALID_CERTIFICATES", "false").lower() == "true"
DB_NAME     = os.getenv("MONGODB_DB_NAME", "ai_assistant_v2")

kw = {"serverSelectionTimeoutMS": 8000, "tls": True, "tlsAllowInvalidCertificates": TLS_INVALID}
if X509_CERT and Path(X509_CERT).exists():
    kw["tlsCertificateKeyFile"] = X509_CERT
    kw["authMechanism"] = "MONGODB-X509"
    kw["authSource"] = "$external"

mongo = MongoClient(X509_URI, **kw)
mongo.admin.command("ping")
col = mongo[DB_NAME]["generated_images"]
print(f"MongoDB OK — {DB_NAME}.generated_images")

# ── Drive ─────────────────────────────────────────────────────────────────────
from core.google_drive_service import GoogleDriveService

svc = GoogleDriveService()
drive_ok = svc._service is not None
svc._folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
print(f"Drive OK (mode={svc._auth_mode})" if drive_ok else "Drive: not initialized, skipping")

# ── helpers ───────────────────────────────────────────────────────────────────
def upload_imgbb(img_b64: str, name: str = "") -> str:
    try:
        r = httpx.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_KEY, "image": img_b64, "name": name},
            timeout=40.0,
        )
        r.raise_for_status()
        d = r.json()
        if d.get("success"):
            return d["data"]["url"]
        print(f"    ImgBB error: {d}")
    except Exception as e:
        print(f"    ImgBB error: {e}")
    return ""


def upload_drive(img_b64: str, filename: str) -> tuple[str, str]:
    """Returns (web_view_link, file_id) or ('', '')."""
    if not drive_ok:
        return "", ""
    res = svc.upload_image(img_b64, filename=filename)
    if res["success"]:
        return res["web_view_link"], res["file_id"]
    return "", ""


def process(png_path: Path, meta_path: Path | None):
    """Upload one PNG to ImgBB + Drive, update meta.json + MongoDB."""
    filename = png_path.name
    image_id = png_path.stem  # e.g. "5496ee2c-05a" or "anime_pipeline_20260525_..."

    # Load or build meta
    if meta_path and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {
            "image_id":    image_id,
            "filename":    filename,
            "local_path":  str(png_path),
            "created_at":  datetime.utcfromtimestamp(png_path.stat().st_mtime).isoformat(),
            "provider":    "anime_pipeline" if "anime_pipeline" in filename else "unknown",
            "prompt":      "",
        }
        if meta_path:
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    already_imgbb = bool(meta.get("cloud_url"))
    already_drive = bool(meta.get("drive_url"))

    if already_imgbb and already_drive:
        return "skip"

    img_b64 = base64.b64encode(png_path.read_bytes()).decode()

    changed = False

    # ImgBB
    if not already_imgbb:
        cloud_url = upload_imgbb(img_b64, name=image_id)
        if cloud_url:
            meta["cloud_url"] = cloud_url
            meta["url"]       = cloud_url
            changed = True
            print(f"  ImgBB OK  {filename}")
        else:
            print(f"  ImgBB FAIL  {filename}")
            return "fail_imgbb"

    # Drive
    if not already_drive:
        drive_url, drive_file_id = upload_drive(img_b64, filename)
        if drive_url:
            meta["drive_url"]     = drive_url
            meta["drive_file_id"] = drive_file_id
            meta["share_url"]     = drive_url
            changed = True
            print(f"  Drive OK  {filename}")
        # Drive failures are non-fatal — continue

    if changed:
        if not meta_path:
            meta_path = png_path.with_suffix(".meta.json")
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # Upsert MongoDB
    doc = {
        "image_id":        image_id,
        "filename":        filename,
        "prompt":          meta.get("prompt") or meta.get("original_prompt") or "",
        "provider":        meta.get("provider", ""),
        "model":           meta.get("model", ""),
        "conversation_id": meta.get("conversation_id", ""),
        "local_path":      str(png_path),
        "url":             meta.get("cloud_url") or meta.get("url") or f"/api/image-gen/images/{image_id}",
        "cloud_url":       meta.get("cloud_url", ""),
        "drive_url":       meta.get("drive_url", ""),
        "drive_file_id":   meta.get("drive_file_id", ""),
        "share_url":       meta.get("drive_url") or meta.get("cloud_url") or "",
        "file_size":       meta.get("file_size") or png_path.stat().st_size,
        "created_at":      meta.get("created_at", datetime.utcnow().isoformat()),
    }
    col.update_one({"image_id": image_id}, {"$set": doc}, upsert=True)
    return "ok"


# ── collect all images ────────────────────────────────────────────────────────
SCAN_DIRS = [
    CHATBOT / "Storage" / "Image_Gen",
    REPO / "ComfyUI" / "final",
]

jobs: list[tuple[Path, Path | None]] = []  # (png_path, meta_path | None)

for scan_dir in SCAN_DIRS:
    if not scan_dir.exists():
        print(f"Skip (not found): {scan_dir}")
        continue
    for png in sorted(scan_dir.rglob("*.png")):
        if png.stat().st_size == 0:
            continue  # skip empty files
        meta_candidate = png.with_suffix("").with_suffix(".meta.json")
        # Storage/Image_Gen uses {stem}.meta.json; ComfyUI/final has none
        meta_path = meta_candidate if meta_candidate.exists() else None
        jobs.append((png, meta_path))

print(f"\nTotal images to process: {len(jobs)}\n")

# ── run ───────────────────────────────────────────────────────────────────────
ok = skipped = fail = 0

for png_path, meta_path in jobs:
    result = process(png_path, meta_path)
    if result == "ok":
        ok += 1
    elif result == "skip":
        skipped += 1
    else:
        fail += 1
    time.sleep(0.4)

print(f"\n{'='*60}")
print(f"Done — uploaded={ok}  already_done={skipped}  failed={fail}")
mongo.close()
