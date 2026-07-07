"""
Upload local FINAL images to ImgBB and register them in MongoDB so they show
in the gallery as cloud images. ImgBB-only (no Drive).

Why this exists (vs backfill_imgbb_upload.py):
  * Uploads ONLY finals — skips pipeline intermediates (preview/structure/
    composition/detection/mask/lineart/detail/critique/upscaled).
  * STRIPS embedded PNG metadata via a PIL re-encode before upload. ComfyUI
    bakes the workflow/prompt into tEXt chunks; imgbb's content filter rejects
    some of those with HTTP 400 code 103 ("You have been forbidden…"). Re-
    encoding drops the chunks (pixels unchanged) so every valid image uploads.
  * Skips anything already cloud-backed (meta.json cloud_url OR a Mongo doc
    with a cloud URL) — safe to re-run; it resumes where it left off.

Scope dirs: services/chatbot/Storage/Image_Gen  +  ComfyUI/final
Env:  IMGBB_API_KEY, MONGODB_* (read from services/chatbot/.env)
Args: LIMIT=<n> env → only process first n names (0/unset = all).

Run:  python services/chatbot/scripts/upload_finals_imgbb.py
"""
import base64
import io
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from PIL import Image

CHATBOT = Path(__file__).resolve().parents[1]
REPO = CHATBOT.parents[1]
sys.path.insert(0, str(CHATBOT))


def load_env(p: Path):
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


load_env(CHATBOT / ".env")

IMGBB_KEY = os.getenv("IMGBB_API_KEY", "").strip()
if not IMGBB_KEY:
    print("ERROR: IMGBB_API_KEY not set", flush=True)
    sys.exit(1)

LIMIT = int(os.getenv("LIMIT", "0"))

from core.image_storage import images_collection, _try_connect_mongodb  # noqa: E402

if images_collection is None:
    _try_connect_mongodb()
    from core.image_storage import images_collection  # noqa: E402,F811
if images_collection is None:
    print("ERROR: MongoDB not connected", flush=True)
    sys.exit(1)

IG = CHATBOT / "Storage" / "Image_Gen"
FINAL_DIR = REPO / "ComfyUI" / "final"
STAGE = ("preview", "structure", "composition", "detection", "lineart",
         "depth", "mask", "detail_", "critique", "upscaled", "_grid",
         "candidate", "_seg", "openpose", "canny")


def is_stage(name: str) -> bool:
    low = name.lower()
    return any(k in low for k in STAGE)


def meta_for(png: Path):
    for cand in (png.with_suffix(".meta.json"),
                 png.with_suffix("").with_suffix(".meta.json"),
                 png.with_suffix(".json")):
        if cand.exists():
            return cand
    return None


def clean_image_b64(path: Path) -> str:
    """Re-encode via PIL to strip embedded metadata (imgbb code-103 trigger).
    Lossless PNG preserves pixels; JPEG q92 fallback only if PNG > 20 MB."""
    im = Image.open(path)
    im = im.convert("RGB") if im.mode not in ("RGB", "RGBA") else im
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    data = buf.getvalue()
    if len(data) > 20_000_000:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="JPEG", quality=92)
        data = buf.getvalue()
    return base64.b64encode(data).decode()


def upload_imgbb(img_b64: str, name: str) -> str:
    for attempt in (1, 2, 3):
        try:
            r = httpx.post(
                "https://api.imgbb.com/1/upload",
                data={"key": IMGBB_KEY, "image": img_b64, "name": name},
                timeout=60.0,
            )
            if r.status_code == 429 or r.status_code >= 500:
                wait = 5 * attempt
                print(f"    {r.status_code} transient, wait {wait}s", flush=True)
                time.sleep(wait)
                continue
            if r.status_code == 400:
                print(f"    ImgBB 400: {r.text[:160]}", flush=True)
                return ""
            r.raise_for_status()
            d = r.json()
            if d.get("success"):
                return d["data"]["url"]
            print(f"    ImgBB error body: {str(d)[:200]}", flush=True)
            return ""
        except Exception as e:
            print(f"    ImgBB attempt {attempt} error: {e}", flush=True)
            time.sleep(2 * attempt)
    return ""


# ── collect finals (dedup by filename) ──────────────────────────────────────
finals: dict[str, Path] = {}
for d in (IG, FINAL_DIR):
    if not d.exists():
        print(f"[skip missing] {d}", flush=True)
        continue
    for p in sorted(d.rglob("*.png")):
        try:
            if p.stat().st_size == 0:
                continue
        except OSError:
            continue
        if is_stage(p.name):
            continue
        finals.setdefault(p.name, p)

names = sorted(finals)
if LIMIT:
    names = names[:LIMIT]
print(f"Finals to consider: {len(names)}  (LIMIT={LIMIT or 'all'})", flush=True)

# ── already-cloud identifiers from Mongo ────────────────────────────────────
cloud_names, cloud_ids = set(), set()
cloud_q = {"$or": [{f: {"$exists": True, "$nin": [None, ""]}}
                   for f in ("cloud_url", "url", "drive_url")]}
for doc in images_collection.find(cloud_q, {"filename": 1, "image_id": 1}):
    if doc.get("filename"):
        cloud_names.add(doc["filename"])
    if doc.get("image_id"):
        cloud_ids.add(doc["image_id"])
print(f"Already-cloud in Mongo: {len(cloud_names)} filenames", flush=True)

# ── process ─────────────────────────────────────────────────────────────────
ok = skip = fail = 0
t0 = time.time()
for i, name in enumerate(names, 1):
    png = finals[name]
    image_id = png.stem
    mp = meta_for(png)
    meta = {}
    if mp:
        try:
            meta = json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    if meta.get("cloud_url") or name in cloud_names or image_id in cloud_ids:
        skip += 1
        continue

    try:
        b64 = clean_image_b64(png)
    except Exception as e:
        print(f"[{i}/{len(names)}] ENCODE FAIL {name}: {e}", flush=True)
        fail += 1
        continue

    url = upload_imgbb(b64, image_id)
    if not url:
        print(f"[{i}/{len(names)}] IMGBB FAIL {name}", flush=True)
        fail += 1
        continue

    created = meta.get("created_at") or datetime.utcfromtimestamp(
        png.stat().st_mtime).isoformat()

    meta.update({
        "image_id": image_id, "filename": name,
        "cloud_url": url, "url": url,
        "local_path": f"/storage/images/{name}",
        "created_at": created,
        "provider": meta.get("provider")
        or ("anime_pipeline" if "anime_pipeline" in name else "local"),
    })
    try:
        (mp or png.with_suffix(".meta.json")).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"    meta write warn {name}: {e}", flush=True)

    doc = {
        "image_id": image_id, "filename": name,
        "prompt": meta.get("prompt") or meta.get("original_prompt") or "",
        "provider": meta.get("provider", ""), "model": meta.get("model", ""),
        "local_path": f"/storage/images/{name}",
        "url": url, "cloud_url": url, "share_url": url,
        "file_size": png.stat().st_size, "created_at": created,
        "backfill_imgbb": True,
    }
    try:
        images_collection.update_one({"image_id": image_id}, {"$set": doc}, upsert=True)
    except Exception as e:
        print(f"    mongo upsert warn {name}: {e}", flush=True)

    ok += 1
    if ok % 25 == 0 or i == len(names):
        rate = ok / max(1e-9, (time.time() - t0))
        print(f"[{i}/{len(names)}] ok={ok} skip={skip} fail={fail}  ({rate:.1f}/s)", flush=True)
    time.sleep(0.4)

print(f"\n{'='*56}\nDONE finals — uploaded={ok} skipped={skip} failed={fail}  in {time.time()-t0:.0f}s", flush=True)
