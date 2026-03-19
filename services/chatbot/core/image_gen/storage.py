"""
ImageStorage â€” save, retrieve, and manage generated images.
Supports local filesystem + optional cloud upload (ImgBB, S3, etc.)
"""

from __future__ import annotations

import os
import io
import time
import base64
import uuid
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class ImageStorage:
    """
    Persistent image storage with metadata.
    
    Directory structure:
        Storage/Image_Gen/
            2026/
                03/
                    04/
                        {uuid}.png
                        {uuid}.meta.json
    """

    def __init__(
        self,
        base_dir: str | Path = "",
        imgbb_key: str = "",
        max_local_gb: float = 10.0,
    ):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent.parent / "Storage" / "Image_Gen"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.imgbb_key = imgbb_key or os.getenv("IMGBB_API_KEY", "")
        self.max_local_bytes = int(max_local_gb * 1024 * 1024 * 1024)

    def save(
        self,
        image_b64: Optional[str] = None,
        image_url: Optional[str] = None,
        prompt: str = "",
        provider: str = "",
        model: str = "",
        conversation_id: str = "",
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Save an image (from base64 or URL) to local storage.
        Returns: {"local_path": str, "url": str, "image_id": str}
        """
        image_id = str(uuid.uuid4())[:12]
        now = datetime.now()
        
        # Create date-based directory
        day_dir = self.base_dir / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        day_dir.mkdir(parents=True, exist_ok=True)

        img_path = day_dir / f"{image_id}.png"
        meta_path = day_dir / f"{image_id}.meta.json"

        try:
            # Get image bytes
            if image_b64:
                img_bytes = base64.b64decode(image_b64)
            elif image_url:
                img_bytes = self._download(image_url)
                if not image_b64:
                    image_b64 = base64.b64encode(img_bytes).decode()
            else:
                return {"error": "No image data provided"}

            # Save locally
            img_path.write_bytes(img_bytes)

            # Save metadata
            meta = {
                "image_id": image_id,
                "created_at": now.isoformat(),
                "prompt": prompt,
                "provider": provider,
                "model": model,
                "conversation_id": conversation_id,
                "file_size": len(img_bytes),
                "local_path": str(img_path),
                **(metadata or {}),
            }
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

            # Upload to cloud if configured
            cloud_url = ""
            if self.imgbb_key and image_b64:
                cloud_url = self._upload_imgbb(image_b64, image_id)

            result = {
                "image_id": image_id,
                "local_path": str(img_path),
                "url": cloud_url or f"/api/image-gen/images/{image_id}",
                "file_size": len(img_bytes),
            }

            logger.info(f"[ImageStorage] Saved {image_id} ({len(img_bytes)} bytes) â†’ {img_path.name}")
            return result

        except Exception as e:
            logger.error(f"[ImageStorage] Save failed: {e}", exc_info=True)
            return {"error": str(e)}

    def get(self, image_id: str) -> Optional[bytes]:
        """Get image bytes by ID (search in date directories)."""
        for path in self.base_dir.rglob(f"{image_id}.png"):
            return path.read_bytes()
        return None

    def get_metadata(self, image_id: str) -> Optional[dict]:
        """Get image metadata by ID."""
        for path in self.base_dir.rglob(f"{image_id}.meta.json"):
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def list_recent(self, limit: int = 20, conversation_id: str = "") -> list[dict]:
        """List recent images with metadata."""
        all_meta = []
        for meta_path in self.base_dir.rglob("*.meta.json"):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if conversation_id and meta.get("conversation_id") != conversation_id:
                    continue
                all_meta.append(meta)
            except Exception:
                continue

        # Sort by created_at descending
        all_meta.sort(key=lambda m: m.get("created_at", ""), reverse=True)
        return all_meta[:limit]

    def delete(self, image_id: str) -> bool:
        """Delete an image and its metadata."""
        deleted = False
        for path in self.base_dir.rglob(f"{image_id}.*"):
            path.unlink(missing_ok=True)
            deleted = True
        return deleted

    def get_disk_usage(self) -> dict:
        """Get storage statistics."""
        total_bytes = 0
        total_files = 0
        for path in self.base_dir.rglob("*.png"):
            total_bytes += path.stat().st_size
            total_files += 1
        return {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "limit_gb": round(self.max_local_bytes / (1024 * 1024 * 1024), 1),
            "usage_pct": round(total_bytes / self.max_local_bytes * 100, 1) if self.max_local_bytes else 0,
        }

    def _download(self, url: str) -> bytes:
        """Download image from URL."""
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content

    def _upload_imgbb(self, image_b64: str, name: str = "") -> str:
        """Upload to ImgBB and return URL."""
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.imgbb.com/1/upload",
                    data={
                        "key": self.imgbb_key,
                        "image": image_b64,
                        "name": name,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    return data["data"]["url"]
        except Exception as e:
            logger.warning(f"[ImageStorage] ImgBB upload failed: {e}")
        return ""
