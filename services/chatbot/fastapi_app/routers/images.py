"""
Image storage router — save / serve / list / delete generated images
"""
import base64
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from fastapi_app.dependencies import get_gallery_session_id
from fastapi_app.models import SaveImageRequest
from core.config import IMAGE_STORAGE_DIR
from core.extensions import logger

router = APIRouter()


@router.post("/api/save-image")
async def save_image(body: SaveImageRequest, request: Request):
    try:
        session_id = get_gallery_session_id(request)
        image_b64 = body.image
        if "base64," in image_b64:
            image_b64 = image_b64.split("base64,")[1]

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_{ts}.png"
        filepath = IMAGE_STORAGE_DIR / filename
        filepath.write_bytes(base64.b64decode(image_b64))

        metadata = {**body.metadata, "session_id": session_id}

        cloud_url = None
        try:
            from core.image_storage import store_generated_image
            res = store_generated_image(
                image_base64=image_b64,
                prompt=metadata.get("prompt", ""),
                negative_prompt=metadata.get("negative_prompt", ""),
                metadata=metadata,
            )
            if res.get("success"):
                cloud_url = res.get("imgbb_url")
        except Exception as e:
            logger.warning(f"[SaveImage] Cloud upload failed: {e}")

        return {
            "success": True,
            "filename": filename,
            "url": f"/storage/images/{filename}",
            "cloud_url": cloud_url,
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        raise HTTPException(500, str(e))


@router.get("/storage/images/{filename}")
async def serve_image(filename: str):
    path = IMAGE_STORAGE_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Image not found")
    # Ensure the resolved path is under IMAGE_STORAGE_DIR to prevent path traversal
    if not path.resolve().is_relative_to(IMAGE_STORAGE_DIR.resolve()):
        raise HTTPException(403, "Access denied")
    return FileResponse(path)


@router.get("/api/images")
async def list_images(request: Request):
    try:
        session_id = get_gallery_session_id(request)
        images = []
        for f in sorted(IMAGE_STORAGE_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True):
            meta_path = f.with_suffix(".json")
            meta = {}
            if meta_path.exists():
                import json
                try:
                    meta = json.loads(meta_path.read_text("utf-8"))
                except Exception:
                    pass
            # Only return images from this session (privacy)
            if meta.get("session_id") and meta["session_id"] != session_id:
                continue
            images.append({
                "filename": f.name,
                "url": f"/storage/images/{f.name}",
                "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "metadata": meta,
            })
        return {"images": images, "count": len(images)}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/api/images/{filename}")
async def delete_image(filename: str):
    path = IMAGE_STORAGE_DIR / filename
    if not path.resolve().is_relative_to(IMAGE_STORAGE_DIR.resolve()):
        raise HTTPException(403, "Access denied")
    if not path.exists():
        raise HTTPException(404, "Image not found")
    path.unlink()
    meta = path.with_suffix(".json")
    if meta.exists():
        meta.unlink()
    return {"success": True, "message": "Image deleted"}


# ---------------------------------------------------------------------------
# Gallery endpoints
# ---------------------------------------------------------------------------

_URL_PAT = re.compile(
    r'https?://\S+\.(?:png|jpg|jpeg|gif|webp)(?:\?\S*)?',
    re.IGNORECASE,
)


@router.get("/api/gallery")
@router.get("/api/gallery/images")
async def get_gallery(request: Request, page: int = 1, per_page: int = 50, all: str = "false"):
    """Get image gallery — MongoDB first, local disk fallback, then message scan."""
    try:
        show_all = all.lower() == "true"
        current_session_id = get_gallery_session_id(request)
        images: list[dict] = []
        source = "local"

        # ── MongoDB: generated_images collection ──
        try:
            from core.image_storage import images_collection
            if images_collection is not None:
                query: dict = {} if show_all else {"$or": [
                    {"session_id": current_session_id},
                    {"session_id": {"$exists": False}},
                    {"session_id": ""},
                ]}
                cursor = images_collection.find(query).sort("created_at", -1).limit(per_page * page)
                for doc in cursor:
                    created = doc.get("created_at", "")
                    if hasattr(created, "isoformat"):
                        created = created.isoformat()
                    cloud_url = doc.get("cloud_url") or doc.get("url")
                    drive_url = doc.get("drive_url")
                    local_path = doc.get("local_path", "")
                    display_url = cloud_url if cloud_url else local_path
                    images.append({
                        "id": str(doc.get("_id", "")),
                        "filename": doc.get("filename", ""),
                        "url": display_url,
                        "path": display_url,
                        "cloud_url": cloud_url,
                        "drive_url": drive_url,
                        "share_url": drive_url or cloud_url or local_path,
                        "local_path": local_path,
                        "created_at": created,
                        "created": created,
                        "prompt": doc.get("prompt", "No prompt"),
                        "creator": doc.get("creator") or doc.get("session_id") or "unknown",
                        "db_status": {"mongodb": True, "firebase": bool(doc.get("firebase_id"))},
                        "metadata": {
                            "prompt": doc.get("prompt", ""),
                            "negative_prompt": doc.get("negative_prompt", ""),
                            "model": doc.get("model", ""),
                            "sampler": doc.get("sampler", ""),
                            "steps": doc.get("steps", ""),
                            "cfg_scale": doc.get("cfg_scale", ""),
                            "width": doc.get("width", ""),
                            "height": doc.get("height", ""),
                            "seed": doc.get("seed", ""),
                            "vae": doc.get("vae", ""),
                            "lora_models": doc.get("lora_models", ""),
                            "cloud_url": cloud_url,
                            "drive_url": drive_url,
                            "filename": doc.get("filename", ""),
                        },
                    })
                if images:
                    source = "mongodb"
                    logger.info(f"[Gallery] Loaded {len(images)} images from MongoDB")
        except Exception as mongo_err:
            logger.warning(f"[Gallery] MongoDB fetch failed, falling back to local: {mongo_err}")

        # ── Local disk fallback ──
        if not images:
            for img_file in IMAGE_STORAGE_DIR.rglob("*.png"):
                meta_path = img_file.with_suffix(".meta.json") if not img_file.with_suffix(".json").exists() else img_file.with_suffix(".json")
                metadata: dict = {}
                if meta_path.exists():
                    try:
                        metadata = json.loads(meta_path.read_text("utf-8"))
                    except Exception:
                        pass
                image_session_id = metadata.get("session_id")
                if not show_all and image_session_id and image_session_id != current_session_id:
                    continue
                image_id = metadata.get("image_id", "")
                serve_url = f"/api/image-gen/images/{image_id}" if image_id else f"/storage/images/{img_file.name}"
                images.append({
                    "filename": img_file.name,
                    "url": serve_url,
                    "path": serve_url,
                    "cloud_url": metadata.get("cloud_url"),
                    "drive_url": metadata.get("drive_url"),
                    "share_url": metadata.get("drive_url") or metadata.get("cloud_url") or serve_url,
                    "local_path": serve_url,
                    "created_at": metadata.get("created_at", ""),
                    "created": metadata.get("created_at", ""),
                    "prompt": metadata.get("prompt", "No prompt"),
                    "creator": metadata.get("creator") or metadata.get("session_id") or "local-session",
                    "db_status": metadata.get("db_status", {"mongodb": False, "firebase": False}),
                    "metadata": metadata.get("metadata", metadata),
                })
            images.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            source = "local"

        # ── Scan assistant messages for image URLs ──
        try:
            from config.mongodb_config import get_db as _get_mongo_db
            _db = _get_mongo_db()
            if _db is not None:
                existing_urls = {img.get("cloud_url") or img.get("url") or img.get("path") for img in images}
                msg_query: dict = {"role": "assistant", "content": {"$regex": r"https?://", "$options": "i"}}
                for msg in _db.messages.find(msg_query).sort("created_at", -1).limit(500):
                    content = msg.get("content", "")
                    for url in _URL_PAT.findall(content):
                        if url in existing_urls:
                            continue
                        if any(skip in url for skip in ("/favicon", "/icon", "/logo", "/avatar")):
                            continue
                        existing_urls.add(url)
                        created = msg.get("created_at", "")
                        if hasattr(created, "isoformat"):
                            created = created.isoformat()
                        images.append({
                            "filename": url.split("/")[-1].split("?")[0],
                            "url": url,
                            "path": url,
                            "cloud_url": url,
                            "drive_url": None,
                            "share_url": url,
                            "local_path": "",
                            "created_at": created,
                            "created": created,
                            "prompt": (content[:80] + "...") if len(content) > 80 else content,
                            "creator": "assistant",
                            "db_status": {"mongodb": True, "firebase": False},
                            "metadata": {"source": "message"},
                        })
        except Exception as msg_err:
            logger.debug(f"[Gallery] Message scan skipped: {msg_err}")

        images.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        total = len(images)
        start = (page - 1) * per_page
        paginated = images[start: start + per_page]

        return {
            "success": True,
            "images": paginated,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page else 1,
            "session_id": current_session_id,
            "showing_all": show_all,
            "source": source,
        }
    except Exception as e:
        logger.error(f"[Gallery] Error: {e}")
        raise HTTPException(500, "Failed to get gallery")


@router.get("/api/gallery/image-info")
async def get_image_info(filename: str = ""):
    """Get metadata for a specific gallery image."""
    if not filename or not re.match(r"^[a-zA-Z0-9_\-\.]+$", filename):
        raise HTTPException(400, "Invalid filename")
    meta_path = IMAGE_STORAGE_DIR / (filename.rsplit(".", 1)[0] + ".json")
    alt_meta_path = IMAGE_STORAGE_DIR / (filename + ".meta.json")
    metadata: dict = {}
    for p in (meta_path, alt_meta_path):
        if p.exists():
            try:
                metadata = json.loads(p.read_text("utf-8"))
                break
            except Exception:
                pass
    return {"success": True, "filename": filename, "metadata": metadata}


@router.delete("/api/gallery/delete/{filename}")
@router.delete("/api/delete-image/{filename}")
@router.post("/api/delete-image/{filename}")
async def delete_gallery_image(filename: str):
    """Delete a gallery image and its metadata."""
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", filename):
        raise HTTPException(400, "Invalid filename")
    path = IMAGE_STORAGE_DIR / filename
    if not path.resolve().is_relative_to(IMAGE_STORAGE_DIR.resolve()):
        raise HTTPException(403, "Access denied")
    if path.exists():
        path.unlink()
    for ext in (".json", ".meta.json"):
        mp = path.with_suffix(ext) if ext == ".json" else IMAGE_STORAGE_DIR / (filename + ".meta.json")
        if mp.exists():
            mp.unlink()
    return {"success": True, "message": "Image deleted"}


# ---------------------------------------------------------------------------
# Gallery upload to DB / cloud
# ---------------------------------------------------------------------------

class GalleryUploadBody(BaseModel):
    filename: str


@router.post("/api/gallery/upload-db")
async def upload_image_to_db(body: GalleryUploadBody, request: Request):
    """Upload a locally stored image + metadata to MongoDB/Firebase/ImgBB."""
    import json as _json
    import re as _re

    filename = body.filename.strip()
    if not filename or not _re.match(r"^[a-zA-Z0-9_\-\.]+$", filename):
        raise HTTPException(400, "Invalid filename")

    filepath = IMAGE_STORAGE_DIR / filename
    if not filepath.exists() or not filepath.resolve().is_relative_to(IMAGE_STORAGE_DIR.resolve()):
        raise HTTPException(404, "Image not found locally")

    raw_bytes = filepath.read_bytes()
    image_b64 = base64.b64encode(raw_bytes).decode()

    meta_path = filepath.with_suffix(".json")
    local_payload: dict = {}
    if meta_path.exists():
        try:
            local_payload = _json.loads(meta_path.read_text("utf-8"))
        except Exception:
            pass

    session_id = get_gallery_session_id(request)
    metadata = local_payload.get("metadata", local_payload if isinstance(local_payload, dict) else {})
    metadata["filename"] = filename
    metadata.setdefault("session_id", session_id)

    try:
        from core.image_storage import store_generated_image
        result = store_generated_image(
            image_base64=image_b64,
            prompt=metadata.get("prompt", ""),
            negative_prompt=metadata.get("negative_prompt", ""),
            metadata=metadata,
            raw_legacy_payload=local_payload if isinstance(local_payload, dict) else {},
        )
    except Exception as e:
        logger.error(f"[UploadDB] store_generated_image error: {e}")
        raise HTTPException(500, "Failed to upload to database")

    db_status = {
        "mongodb": bool(result.get("saved_to_mongodb")),
        "firebase": bool(result.get("saved_to_firebase")),
    }

    merged = {
        **(local_payload if isinstance(local_payload, dict) else {}),
        "filename": filename,
        "created_at": local_payload.get("created_at", datetime.now().isoformat()),
        "cloud_url": result.get("imgbb_url") or local_payload.get("cloud_url"),
        "drive_url": result.get("drive_url") or local_payload.get("drive_url"),
        "drive_file_id": result.get("drive_file_id") or local_payload.get("drive_file_id"),
        "db_status": db_status,
        "metadata": metadata,
    }
    try:
        meta_path.write_text(_json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    return {
        "success": True,
        "filename": filename,
        "imageURL": result.get("drive_url") or result.get("imgbb_url") or f"/storage/images/{filename}",
        "cloud_url": result.get("imgbb_url"),
        "drive_url": result.get("drive_url"),
        "db_status": db_status,
        "storage_result": result,
    }


# ---------------------------------------------------------------------------
# Upload to ImgBB
# ---------------------------------------------------------------------------

class ImgBBUploadBody(BaseModel):
    image: str  # base64-encoded image data
    name: str | None = None


@router.post("/api/upload-imgbb")
async def upload_to_imgbb(body: ImgBBUploadBody):
    """Upload a base64 image to ImgBB and return the URL."""
    if not body.image:
        raise HTTPException(400, "No image data provided")
    try:
        from core.image_storage import upload_to_imgbb as _imgbb_upload
        url = _imgbb_upload(body.image, body.name)
        if url:
            return {"success": True, "url": url}
        return JSONResponse(status_code=500, content={"success": False, "error": "Upload failed"})
    except Exception as e:
        logger.error(f"[UploadImgBB] Error: {e}")
        raise HTTPException(500, "Failed to upload image")
