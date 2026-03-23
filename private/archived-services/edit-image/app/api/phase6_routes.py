"""
Phase 6 API Routes
==================

API endpoints for v0.4.0 features:
- PuLID (identity-preserving generation)
- EcomID (e-commerce identity)
- Batch Processing
- Multi-GPU management
- Model Offloading
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# =============================================================================
# Request/Response Models
# =============================================================================

# PuLID
class PuLIDGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Generation prompt")
    face_image: str = Field(..., description="Base64 encoded face image")
    negative_prompt: str = Field("", description="Negative prompt")
    id_strength: float = Field(0.8, ge=0.0, le=1.0, description="Identity strength")
    num_steps: int = Field(30, ge=1, le=100)
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0)
    seed: int = Field(-1, description="Random seed (-1 for random)")
    mode: str = Field("standard", description="Mode: standard, lightning, fidelity")

class PuLIDEditRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded image to edit")
    face_image: str = Field(..., description="Base64 encoded reference face")
    prompt: str = Field("", description="Edit prompt")
    id_strength: float = Field(0.8, ge=0.0, le=1.0)
    edit_strength: float = Field(0.5, ge=0.0, le=1.0)

class PuLIDSwapRequest(BaseModel):
    source_image: str = Field(..., description="Source image")
    target_face: str = Field(..., description="Target face to swap in")
    swap_strength: float = Field(0.9, ge=0.0, le=1.0)
    preserve_expression: bool = Field(True)


# EcomID
class EcomIDGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Generation prompt")
    face_image: str = Field(..., description="Base64 face image")
    negative_prompt: str = Field("")
    identity_strength: float = Field(0.8, ge=0.0, le=1.0)
    pose_strength: float = Field(0.5, ge=0.0, le=1.0)
    num_steps: int = Field(30)
    guidance_scale: float = Field(7.5)
    mode: str = Field("standard", description="Mode: standard, ecommerce, portrait, multi_pose")

class EcomIDMultiPoseRequest(BaseModel):
    prompt: str
    face_image: str
    pose_angles: List[str] = Field(default=["front", "left", "right"], description="Pose angles")
    grid_layout: bool = Field(True)


# Batch Processing
class BatchJobRequest(BaseModel):
    task_type: str = Field(..., description="Task type: generate, edit, upscale, face_swap")
    params: Dict[str, Any] = Field(..., description="Task parameters")
    priority: int = Field(1, ge=0, le=10, description="Job priority (higher = more urgent)")
    callback_url: Optional[str] = Field(None, description="Callback URL for completion")

class BatchSubmitRequest(BaseModel):
    jobs: List[BatchJobRequest]


# GPU Management
class GPUConfigRequest(BaseModel):
    strategy: str = Field("least_loaded", description="Load balancing strategy")
    device_ids: Optional[List[int]] = None
    enable_auto_balance: bool = Field(True)


# Memory/Offload
class OffloadConfigRequest(BaseModel):
    strategy: str = Field("attention", description="Offload strategy")
    target_vram_gb: float = Field(6.0)
    enable_xformers: bool = Field(True)
    quantization: str = Field("fp16")


# Responses
class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class BatchStatusResponse(BaseModel):
    total_jobs: int
    completed: int
    failed: int
    pending: int
    in_progress: int
    jobs: List[Dict[str, Any]]


class GPUStatusResponse(BaseModel):
    gpus: List[Dict[str, Any]]
    strategy: str
    recommendations: List[str]


class MemoryStatusResponse(BaseModel):
    memory: Dict[str, float]
    current_strategy: str
    recommendations: List[str]


# =============================================================================
# Routers
# =============================================================================

pulid_router = APIRouter(prefix="/pulid", tags=["PuLID"])
ecomid_router = APIRouter(prefix="/ecomid", tags=["EcomID"])
batch_router = APIRouter(prefix="/batch", tags=["Batch Processing"])
gpu_router = APIRouter(prefix="/gpu", tags=["GPU Management"])
memory_router = APIRouter(prefix="/memory", tags=["Memory Management"])


# =============================================================================
# PuLID Endpoints
# =============================================================================

@pulid_router.post("/generate", response_model=TaskResponse)
async def pulid_generate(request: PuLIDGenerateRequest, background_tasks: BackgroundTasks):
    """Generate image with identity preservation using PuLID"""
    try:
        from app.core.pulid import get_pulid_pipeline, PuLIDConfig, PuLIDMode
        
        pipeline = get_pulid_pipeline()
        
        # Decode images
        from app.utils.image import decode_base64_image
        face_image = decode_base64_image(request.face_image)
        
        mode = PuLIDMode(request.mode.upper())
        config = PuLIDConfig(
            id_strength=request.id_strength,
            num_inference_steps=request.num_steps,
            guidance_scale=request.guidance_scale,
            mode=mode,
        )
        
        # Generate
        result = await asyncio.to_thread(
            pipeline.generate,
            prompt=request.prompt,
            face_image=face_image,
            negative_prompt=request.negative_prompt,
            config=config,
            seed=request.seed if request.seed >= 0 else None,
        )
        
        # Encode result
        from app.utils.image import encode_image_base64
        result_b64 = encode_image_base64(result.image)
        
        return TaskResponse(
            task_id=f"pulid_{hash(result_b64) % 10000:04d}",
            status="completed",
            message=result_b64,
        )
    except Exception as e:
        logger.error(f"PuLID generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@pulid_router.post("/edit", response_model=TaskResponse)
async def pulid_edit(request: PuLIDEditRequest):
    """Edit image while preserving identity"""
    try:
        from app.core.pulid import get_pulid_pipeline
        from app.utils.image import decode_base64_image, encode_image_base64
        
        pipeline = get_pulid_pipeline()
        
        image = decode_base64_image(request.image)
        face_image = decode_base64_image(request.face_image)
        
        result = await asyncio.to_thread(
            pipeline.edit_with_id,
            image=image,
            face_reference=face_image,
            prompt=request.prompt,
            id_strength=request.id_strength,
            edit_strength=request.edit_strength,
        )
        
        result_b64 = encode_image_base64(result.image)
        
        return TaskResponse(
            task_id=f"pulid_edit_{hash(result_b64) % 10000:04d}",
            status="completed",
            message=result_b64,
        )
    except Exception as e:
        logger.error(f"PuLID edit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@pulid_router.post("/swap", response_model=TaskResponse)
async def pulid_swap(request: PuLIDSwapRequest):
    """Swap face in image"""
    try:
        from app.core.pulid import get_pulid_pipeline
        from app.utils.image import decode_base64_image, encode_image_base64
        
        pipeline = get_pulid_pipeline()
        
        source = decode_base64_image(request.source_image)
        target_face = decode_base64_image(request.target_face)
        
        result = await asyncio.to_thread(
            pipeline.swap_face,
            source_image=source,
            target_face=target_face,
            swap_strength=request.swap_strength,
            preserve_expression=request.preserve_expression,
        )
        
        result_b64 = encode_image_base64(result.image)
        
        return TaskResponse(
            task_id=f"pulid_swap_{hash(result_b64) % 10000:04d}",
            status="completed",
            message=result_b64,
        )
    except Exception as e:
        logger.error(f"PuLID swap error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# EcomID Endpoints
# =============================================================================

@ecomid_router.post("/generate", response_model=TaskResponse)
async def ecomid_generate(request: EcomIDGenerateRequest):
    """Generate image with EcomID identity"""
    try:
        from app.core.ecomid import get_ecomid_pipeline, EcomIDConfig, EcomIDMode
        from app.utils.image import decode_base64_image, encode_image_base64
        
        pipeline = get_ecomid_pipeline()
        
        face_image = decode_base64_image(request.face_image)
        mode = EcomIDMode(request.mode.upper())
        
        config = EcomIDConfig(
            identity_strength=request.identity_strength,
            pose_strength=request.pose_strength,
            num_inference_steps=request.num_steps,
            guidance_scale=request.guidance_scale,
            mode=mode,
        )
        
        result = await asyncio.to_thread(
            pipeline.generate,
            prompt=request.prompt,
            face_image=face_image,
            negative_prompt=request.negative_prompt,
            config=config,
        )
        
        result_b64 = encode_image_base64(result.image)
        
        return TaskResponse(
            task_id=f"ecomid_{hash(result_b64) % 10000:04d}",
            status="completed",
            message=result_b64,
        )
    except Exception as e:
        logger.error(f"EcomID generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ecomid_router.post("/multi-pose", response_model=TaskResponse)
async def ecomid_multi_pose(request: EcomIDMultiPoseRequest):
    """Generate multi-pose images"""
    try:
        from app.core.ecomid import get_ecomid_pipeline
        from app.utils.image import decode_base64_image, encode_image_base64
        
        pipeline = get_ecomid_pipeline()
        
        face_image = decode_base64_image(request.face_image)
        
        result = await asyncio.to_thread(
            pipeline.generate_multi_pose,
            prompt=request.prompt,
            face_image=face_image,
            pose_angles=request.pose_angles,
            grid_layout=request.grid_layout,
        )
        
        result_b64 = encode_image_base64(result.image)
        
        return TaskResponse(
            task_id=f"ecomid_multipose_{hash(result_b64) % 10000:04d}",
            status="completed",
            message=result_b64,
        )
    except Exception as e:
        logger.error(f"EcomID multi-pose error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ecomid_router.post("/ecommerce", response_model=TaskResponse)
async def ecomid_ecommerce(
    prompt: str = Form(...),
    face_image: UploadFile = File(...),
    identity_strength: float = Form(0.8),
):
    """Generate e-commerce product images with identity"""
    try:
        from app.core.ecomid import get_ecomid_pipeline, EcomIDConfig, EcomIDMode
        from PIL import Image
        import io
        
        pipeline = get_ecomid_pipeline()
        
        # Read uploaded file
        contents = await face_image.read()
        face = Image.open(io.BytesIO(contents)).convert("RGB")
        
        config = EcomIDConfig(
            identity_strength=identity_strength,
            mode=EcomIDMode.ECOMMERCE,
        )
        
        result = await asyncio.to_thread(
            pipeline.generate_ecommerce,
            prompt=prompt,
            face_image=face,
            config=config,
        )
        
        from app.utils.image import encode_image_base64
        result_b64 = encode_image_base64(result.image)
        
        return TaskResponse(
            task_id=f"ecomid_ecom_{hash(result_b64) % 10000:04d}",
            status="completed",
            message=result_b64,
        )
    except Exception as e:
        logger.error(f"EcomID ecommerce error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Batch Processing Endpoints
# =============================================================================

@batch_router.post("/submit", response_model=TaskResponse)
async def batch_submit(request: BatchJobRequest, background_tasks: BackgroundTasks):
    """Submit a single batch job"""
    try:
        from app.core.batch_processing import get_batch_processor
        
        processor = get_batch_processor()
        
        job_id = await processor.submit(
            task_type=request.task_type,
            params=request.params,
            priority=request.priority,
            callback_url=request.callback_url,
        )
        
        return TaskResponse(
            task_id=job_id,
            status="queued",
            message=f"Job {job_id} submitted successfully",
        )
    except Exception as e:
        logger.error(f"Batch submit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@batch_router.post("/submit-batch", response_model=BatchStatusResponse)
async def batch_submit_multiple(request: BatchSubmitRequest):
    """Submit multiple jobs at once"""
    try:
        from app.core.batch_processing import get_batch_processor
        
        processor = get_batch_processor()
        
        job_ids = await processor.submit_batch([
            {
                "task_type": job.task_type,
                "params": job.params,
                "priority": job.priority,
                "callback_url": job.callback_url,
            }
            for job in request.jobs
        ])
        
        return BatchStatusResponse(
            total_jobs=len(job_ids),
            completed=0,
            failed=0,
            pending=len(job_ids),
            in_progress=0,
            jobs=[{"id": jid, "status": "queued"} for jid in job_ids],
        )
    except Exception as e:
        logger.error(f"Batch submit multiple error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@batch_router.get("/status/{job_id}", response_model=TaskResponse)
async def batch_job_status(job_id: str):
    """Get status of a batch job"""
    try:
        from app.core.batch_processing import get_batch_processor
        
        processor = get_batch_processor()
        status = await processor.get_job_status(job_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return TaskResponse(
            task_id=job_id,
            status=status["status"],
            message=status.get("result", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@batch_router.delete("/cancel/{job_id}")
async def batch_cancel(job_id: str):
    """Cancel a batch job"""
    try:
        from app.core.batch_processing import get_batch_processor
        
        processor = get_batch_processor()
        success = await processor.cancel_job(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or already completed")
        
        return {"status": "cancelled", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch cancel error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@batch_router.get("/queue")
async def batch_queue_status():
    """Get batch queue status"""
    try:
        from app.core.batch_processing import get_batch_processor
        
        processor = get_batch_processor()
        stats = await processor.get_queue_stats()
        
        return stats
    except Exception as e:
        logger.error(f"Batch queue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GPU Management Endpoints
# =============================================================================

@gpu_router.get("/status", response_model=GPUStatusResponse)
async def gpu_status():
    """Get GPU status and statistics"""
    try:
        from app.core.multi_gpu import get_gpu_manager
        
        manager = get_gpu_manager()
        report = manager.get_gpu_report()
        
        return GPUStatusResponse(
            gpus=report["gpus"],
            strategy=report["current_strategy"],
            recommendations=report.get("recommendations", []),
        )
    except Exception as e:
        logger.error(f"GPU status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@gpu_router.post("/configure")
async def gpu_configure(request: GPUConfigRequest):
    """Configure GPU management"""
    try:
        from app.core.multi_gpu import get_gpu_manager, LoadBalanceStrategy
        
        manager = get_gpu_manager()
        
        # Update strategy
        strategy = LoadBalanceStrategy(request.strategy)
        manager.strategy = strategy
        
        if request.device_ids:
            manager.available_gpus = [
                gpu for gpu in manager.available_gpus
                if gpu.device_id in request.device_ids
            ]
        
        return {
            "status": "configured",
            "strategy": strategy.value,
            "active_gpus": [gpu.device_id for gpu in manager.available_gpus],
        }
    except Exception as e:
        logger.error(f"GPU configure error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@gpu_router.get("/best")
async def gpu_get_best(model_vram_gb: float = 6.0):
    """Get best GPU for a model"""
    try:
        from app.core.multi_gpu import get_gpu_manager
        
        manager = get_gpu_manager()
        gpu = manager.get_best_gpu(model_vram_gb)
        
        if not gpu:
            raise HTTPException(status_code=404, detail="No suitable GPU found")
        
        return {
            "device_id": gpu.device_id,
            "name": gpu.name,
            "vram_total": gpu.vram_total,
            "vram_free": gpu.vram_free,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GPU get best error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@gpu_router.post("/clear-cache")
async def gpu_clear_cache(device_id: Optional[int] = None):
    """Clear GPU cache"""
    try:
        import torch
        
        if device_id is not None:
            with torch.cuda.device(device_id):
                torch.cuda.empty_cache()
        else:
            torch.cuda.empty_cache()
        
        return {"status": "cache_cleared"}
    except Exception as e:
        logger.error(f"GPU clear cache error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Memory Management Endpoints
# =============================================================================

@memory_router.get("/status", response_model=MemoryStatusResponse)
async def memory_status():
    """Get memory status"""
    try:
        from app.core.model_offload import get_memory_optimizer
        
        optimizer = get_memory_optimizer()
        report = optimizer.get_optimization_report()
        
        return MemoryStatusResponse(
            memory=report["memory"],
            current_strategy=report["recommended_strategy"],
            recommendations=report["recommendations"],
        )
    except Exception as e:
        logger.error(f"Memory status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@memory_router.post("/configure")
async def memory_configure(request: OffloadConfigRequest):
    """Configure memory/offload settings"""
    try:
        from app.core.model_offload import (
            get_memory_optimizer,
            OffloadStrategy,
            QuantizationType,
        )
        
        optimizer = get_memory_optimizer()
        
        optimizer.config.strategy = OffloadStrategy(request.strategy)
        optimizer.config.target_vram_usage_gb = request.target_vram_gb
        optimizer.config.enable_xformers = request.enable_xformers
        optimizer.config.quantization = QuantizationType(request.quantization)
        
        return {
            "status": "configured",
            "strategy": optimizer.config.strategy.value,
            "target_vram_gb": optimizer.config.target_vram_usage_gb,
        }
    except Exception as e:
        logger.error(f"Memory configure error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@memory_router.post("/cleanup")
async def memory_cleanup(aggressive: bool = False):
    """Trigger memory cleanup"""
    try:
        from app.core.model_offload import get_memory_optimizer
        
        optimizer = get_memory_optimizer()
        optimizer.cleanup(aggressive=aggressive)
        
        # Get updated stats
        stats = optimizer.get_memory_stats()
        
        return {
            "status": "cleanup_complete",
            "aggressive": aggressive,
            "memory": stats.to_dict(),
        }
    except Exception as e:
        logger.error(f"Memory cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Router Registration
# =============================================================================

def register_phase6_routes(app):
    """Register all Phase 6 routes"""
    app.include_router(pulid_router, prefix="/api/v1")
    app.include_router(ecomid_router, prefix="/api/v1")
    app.include_router(batch_router, prefix="/api/v1")
    app.include_router(gpu_router, prefix="/api/v1")
    app.include_router(memory_router, prefix="/api/v1")
    
    logger.info("Phase 6 routes registered")
