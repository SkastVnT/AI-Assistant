"""
Memory CRUD router — /api/memory/*
"""
import json
import shutil
import uuid
import base64
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException

from fastapi_app.models import SaveMemoryRequest, UpdateMemoryRequest
from core.config import MEMORY_DIR, IMAGE_STORAGE_DIR
from core.extensions import logger

router = APIRouter()


@router.post("/save")
async def save_memory(body: SaveMemoryRequest):
    try:
        memory_id = str(uuid.uuid4())
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = body.title[:30].replace("/", "-").replace("\\", "-")
        folder = MEMORY_DIR / f"{safe_title}_{ts}"
        folder.mkdir(parents=True, exist_ok=True)
        img_folder = folder / "image_gen"
        img_folder.mkdir(exist_ok=True)

        saved_images: list[str] = []
        for idx, img in enumerate(body.images):
            url = img.get("url", "")
            b64 = img.get("base64", "")
            if url and url.startswith("/storage/images/"):
                src = IMAGE_STORAGE_DIR / url.split("/")[-1]
                if src.exists():
                    dest_name = f"image_{idx+1}_{src.name}"
                    shutil.copy2(src, img_folder / dest_name)
                    saved_images.append(dest_name)
            elif b64:
                if "," in b64:
                    b64 = b64.split(",")[1]
                dest_name = f"image_{idx+1}.png"
                (img_folder / dest_name).write_bytes(base64.b64decode(b64))
                saved_images.append(dest_name)

        memory = {
            "id": memory_id,
            "folder_name": folder.name,
            "title": body.title,
            "content": body.content,
            "tags": body.tags,
            "images": saved_images,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        (folder / "memory.json").write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "memory": memory, "message": f"Saved with {len(saved_images)} images"}
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        raise HTTPException(500, str(e))


@router.get("/list")
async def list_memories():
    try:
        memories: list[dict] = []
        for p in MEMORY_DIR.glob("*.json"):
            try:
                memories.append(json.loads(p.read_text("utf-8")))
            except Exception:
                pass
        for d in MEMORY_DIR.iterdir():
            if d.is_dir():
                mf = d / "memory.json"
                if mf.exists():
                    try:
                        memories.append(json.loads(mf.read_text("utf-8")))
                    except Exception:
                        pass
        memories.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"memories": memories}
    except Exception as e:
        logger.error(f"[Memory List] Error: {e}")
        raise HTTPException(500, str(e))


@router.get("/get/{memory_id}")
async def get_memory(memory_id: str):
    try:
        f = MEMORY_DIR / f"{memory_id}.json"
        if f.exists():
            return {"memory": json.loads(f.read_text("utf-8"))}
        for d in MEMORY_DIR.iterdir():
            if d.is_dir():
                mf = d / "memory.json"
                if mf.exists():
                    m = json.loads(mf.read_text("utf-8"))
                    if m.get("id") == memory_id:
                        return {"memory": m}
        raise HTTPException(404, "Memory not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/delete/{memory_id}")
async def delete_memory(memory_id: str):
    try:
        f = MEMORY_DIR / f"{memory_id}.json"
        if f.exists():
            f.unlink()
            return {"success": True, "message": "Memory deleted"}
        for d in MEMORY_DIR.iterdir():
            if d.is_dir():
                mf = d / "memory.json"
                if mf.exists():
                    m = json.loads(mf.read_text("utf-8"))
                    if m.get("id") == memory_id:
                        shutil.rmtree(d)
                        return {"success": True, "message": "Memory deleted"}
        raise HTTPException(404, "Memory not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/update/{memory_id}")
async def update_memory(memory_id: str, body: UpdateMemoryRequest):
    try:
        target: Path | None = None
        f = MEMORY_DIR / f"{memory_id}.json"
        if f.exists():
            target = f
        else:
            for d in MEMORY_DIR.iterdir():
                if d.is_dir():
                    mf = d / "memory.json"
                    if mf.exists():
                        m = json.loads(mf.read_text("utf-8"))
                        if m.get("id") == memory_id:
                            target = mf
                            break
        if not target:
            raise HTTPException(404, "Memory not found")

        memory = json.loads(target.read_text("utf-8"))
        if body.title is not None:
            memory["title"] = body.title
        if body.content is not None:
            memory["content"] = body.content
        if body.tags is not None:
            memory["tags"] = body.tags
        memory["updated_at"] = datetime.now().isoformat()
        target.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "memory": memory}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/search")
async def search_memories(q: str = ""):
    if not q:
        return {"memories": []}
    try:
        query = q.lower()
        memories: list[dict] = []

        def _matches(m: dict) -> bool:
            title = m.get("title", "").lower()
            content = m.get("content", "").lower()
            tags = [t.lower() for t in m.get("tags", [])]
            return query in title or query in content or any(query in t for t in tags)

        for d in MEMORY_DIR.iterdir():
            if d.is_dir():
                mf = d / "memory.json"
                if mf.exists():
                    try:
                        m = json.loads(mf.read_text("utf-8"))
                        if _matches(m):
                            memories.append(m)
                    except Exception:
                        pass
        for p in MEMORY_DIR.glob("*.json"):
            try:
                m = json.loads(p.read_text("utf-8"))
                if _matches(m):
                    memories.append(m)
            except Exception:
                pass

        memories.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"memories": memories, "count": len(memories)}
    except Exception as e:
        raise HTTPException(500, str(e))
