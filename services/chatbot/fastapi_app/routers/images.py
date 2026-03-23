"""
Image storage router — save / serve / list / delete generated images
"""
import base64
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse

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
