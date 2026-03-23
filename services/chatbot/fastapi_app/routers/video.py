"""
Video generation router — /api/video/*
Uses OpenAI Sora 2 via the Videos API (openai>=2.29.0).
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from fastapi_app.models import VideoGenerateRequest, VideoStatusResponse
from core.extensions import logger

router = APIRouter()


@router.post("/generate", response_model=VideoStatusResponse)
async def generate_video(body: VideoGenerateRequest):
    """
    Submit a video generation job (returns immediately, job runs async on OpenAI).

    - **prompt**: Text description of the video
    - **size**: 720x1280 | 1280x720 | 1024x1792 | 1792x1024
    - **seconds**: 4, 8, or 12
    - **model**: sora-2 or sora-2-pro
    """
    try:
        from src.video_generation import generate_video as _gen

        result = _gen(
            prompt=body.prompt,
            size=body.size.value,
            seconds=body.seconds.value,
            model=body.model.value,
        )
        return VideoStatusResponse(**result)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.error(f"[Video] Generation error: {e}")
        raise HTTPException(500, str(e))


@router.post("/generate-sync", response_model=VideoStatusResponse)
async def generate_video_sync(body: VideoGenerateRequest):
    """
    Generate a video and wait for completion (blocks until done).
    Can take several minutes depending on duration.
    """
    try:
        from src.video_generation import generate_video_sync as _gen_sync

        result = _gen_sync(
            prompt=body.prompt,
            size=body.size.value,
            seconds=body.seconds.value,
            model=body.model.value,
        )
        return VideoStatusResponse(**result)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.error(f"[Video] Sync generation error: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/{video_id}", response_model=VideoStatusResponse)
async def video_status(video_id: str):
    """
    Poll the OpenAI API for current status of a video job.
    Updates local metadata cache.
    """
    try:
        from src.video_generation import poll_video

        job = poll_video(video_id)
        return VideoStatusResponse(**job)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.error(f"[Video] Status poll error: {e}")
        raise HTTPException(500, str(e))


@router.get("/download/{video_id}")
async def download_video(video_id: str):
    """Download the generated video file (mp4)."""
    from src.video_generation import VIDEO_STORAGE_DIR, download_video as _dl

    local_path = VIDEO_STORAGE_DIR / f"{video_id}.mp4"
    if not local_path.exists():
        try:
            local_path = _dl(video_id)
        except RuntimeError as e:
            raise HTTPException(503, str(e))
        except Exception as e:
            logger.error(f"[Video] Download error: {e}")
            raise HTTPException(500, str(e))

    return FileResponse(
        str(local_path),
        media_type="video/mp4",
        filename=f"{video_id}.mp4",
    )


@router.get("/list")
async def list_videos(limit: int = 20):
    """List recent video generation jobs from local metadata."""
    from src.video_generation import list_jobs

    return {"videos": list_jobs(limit=min(limit, 100))}
