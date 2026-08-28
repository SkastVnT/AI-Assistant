"""
Batch-upload all gallery images to Google Drive.

For each *.meta.json in Storage/Image_Gen:
  - Finds the paired PNG (meta_path.parent / image_id.png)
  - Skips if drive_url already set
  - Uploads to Drive, updates meta.json + upserts MongoDB doc

Run: python services/chatbot/scripts/backfill_drive_upload.py
"""

import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

CHATBOT = Path(__file__).resolve().parents[1]
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

# ── MongoDB ───────────────────────────────────────────────────────────────────
from pymongo import MongoClient

X509_URI  = os.getenv("MONGODB_X509_URI", "").strip()
X509_CERT = os.getenv("MONGODB_X509_CERT_PATH", "").strip()
TLS_INVALID = os.getenv("MONGODB_TLS_ALLOW_INVALID_CERTIFICATES", "false").lower() == "true"
DB_NAME = os.getenv("MONGODB_DB_NAME", "ai_assistant_v2")

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
if svc._service is None:
    print("ERROR: Google Drive not initialized")
    sys.exit(1)

folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
svc._folder_id = folder_id
print(f"Drive OK (mode={svc._auth_mode}) — folder={folder_id}\n")

# ── scan ──────────────────────────────────────────────────────────────────────
storage_root = CHATBOT / "Storage" / "Image_Gen"
meta_files = sorted(storage_root.rglob("*.meta.json"))
print(f"Found {len(meta_files)} meta.json files on disk\n")

ok = skip_done = skip_no_png = fail = 0

for meta_path in meta_files:
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        continue

    image_id = meta.get("image_id", meta_path.stem.replace(".meta", ""))
    filename  = f"{image_id}.png"

    # Skip if already uploaded
    if meta.get("drive_url"):
        skip_done += 1
        continue

    # Find PNG next to meta.json (ignore stale local_path in meta)
    png_path = meta_path.parent / filename
    if not png_path.exists():
        print(f"  SKIP (no png)  {filename}")
        skip_no_png += 1
        continue

    img_b64 = base64.b64encode(png_path.read_bytes()).decode()
    res = svc.upload_image(img_b64, filename=filename)

    if not res["success"]:
        print(f"  FAIL  {filename}  — {res.get('error','?')[:100]}")
        fail += 1
        time.sleep(0.5)
        continue

    drive_url    = res["web_view_link"]
    drive_file_id = res["file_id"]
    print(f"  OK  {filename}  -> {drive_file_id}")

    # Update meta.json
    meta["drive_url"]     = drive_url
    meta["drive_file_id"] = drive_file_id
    meta["share_url"]     = drive_url
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # Upsert MongoDB doc
    prompt = meta.get("prompt") or meta.get("original_prompt") or ""
    doc = {
        "image_id":       image_id,
        "filename":       filename,
        "prompt":         prompt,
        "provider":       meta.get("provider", ""),
        "model":          meta.get("model", ""),
        "conversation_id": meta.get("conversation_id", ""),
        "local_path":     str(png_path),
        "url":            meta.get("url") or f"/api/image-gen/images/{image_id}",
        "cloud_url":      meta.get("cloud_url") or meta.get("url") or "",
        "drive_url":      drive_url,
        "drive_file_id":  drive_file_id,
        "share_url":      drive_url,
        "file_size":      meta.get("file_size", 0),
        "created_at":     meta.get("created_at", datetime.utcnow().isoformat()),
    }
    col.update_one({"image_id": image_id}, {"$set": doc}, upsert=True)

    ok += 1
    time.sleep(0.2)  # gentle rate-limit

# ── summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Done — uploaded={ok}  already_done={skip_done}  no_png={skip_no_png}  failed={fail}")
mongo.close()
