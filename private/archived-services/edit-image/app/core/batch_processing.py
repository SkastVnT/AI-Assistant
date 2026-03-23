"""
Batch Processing Module
=======================

Process multiple images in parallel with queue management.
Features:
- Async queue processing
- Priority scheduling
- Progress tracking
- Resource management
"""

import logging
import asyncio
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading
import queue as sync_queue

import torch
from PIL import Image

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Batch job status"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(int, Enum):
    """Job priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class BatchJob:
    """Single batch job"""
    id: str
    job_type: str  # "generate", "edit", "upscale", etc.
    params: Dict[str, Any]
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: float = 0.0
    
    # Input/Output
    input_images: List[str] = field(default_factory=list)
    output_images: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "priority": self.priority.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "error": self.error,
            "input_count": len(self.input_images),
            "output_count": len(self.output_images),
        }


@dataclass
class BatchConfig:
    """Batch processing configuration"""
    # Queue settings
    max_queue_size: int = 100
    max_concurrent_jobs: int = 2
    
    # Timeout settings
    job_timeout: int = 600  # 10 minutes
    queue_timeout: int = 3600  # 1 hour
    
    # Output settings
    output_dir: str = "./outputs/batch"
    save_intermediate: bool = False
    
    # Resource management
    auto_cleanup: bool = True
    cleanup_after_hours: int = 24
    max_memory_percent: float = 0.9


class PriorityQueue:
    """Thread-safe priority queue for batch jobs"""
    
    def __init__(self, maxsize: int = 100):
        self._queue = sync_queue.PriorityQueue(maxsize=maxsize)
        self._counter = 0
        self._lock = threading.Lock()
    
    def put(self, job: BatchJob, block: bool = True, timeout: Optional[float] = None):
        """Add job to queue with priority"""
        with self._lock:
            # Higher priority = lower number (processed first)
            # Counter ensures FIFO within same priority
            priority_key = (-job.priority.value, self._counter)
            self._counter += 1
        
        self._queue.put((priority_key, job), block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> BatchJob:
        """Get highest priority job"""
        _, job = self._queue.get(block=block, timeout=timeout)
        return job
    
    def empty(self) -> bool:
        return self._queue.empty()
    
    def qsize(self) -> int:
        return self._queue.qsize()


class BatchProcessor:
    """
    Batch image processing with queue management
    
    Features:
    - Async job processing
    - Priority queue
    - Progress tracking
    - Resource management
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.config = BatchConfig()
        self.queue = PriorityQueue(maxsize=self.config.max_queue_size)
        self.jobs: Dict[str, BatchJob] = {}
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_jobs)
        
        # Processing handlers
        self.handlers: Dict[str, Callable] = {}
        
        # State
        self._running = False
        self._worker_task = None
        self._lock = threading.Lock()
        
        self._initialized = True
        logger.info("BatchProcessor initialized")
    
    def register_handler(self, job_type: str, handler: Callable):
        """Register a handler for a job type"""
        self.handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type}")
    
    def create_job(
        self,
        job_type: str,
        params: Dict[str, Any],
        input_images: Optional[List[str]] = None,
        priority: JobPriority = JobPriority.NORMAL,
    ) -> BatchJob:
        """Create a new batch job"""
        job_id = str(uuid.uuid4())[:8]
        
        job = BatchJob(
            id=job_id,
            job_type=job_type,
            params=params,
            priority=priority,
            input_images=input_images or [],
        )
        
        with self._lock:
            self.jobs[job_id] = job
        
        return job
    
    def submit(self, job: BatchJob) -> str:
        """Submit job to queue"""
        if job.job_type not in self.handlers:
            raise ValueError(f"No handler registered for job type: {job.job_type}")
        
        job.status = JobStatus.QUEUED
        self.queue.put(job)
        
        logger.info(f"Job {job.id} submitted to queue (priority: {job.priority.name})")
        
        # Auto-start worker if not running
        if not self._running:
            self.start()
        
        return job.id
    
    def submit_batch(
        self,
        job_type: str,
        images: List[Union[str, Image.Image]],
        params: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
    ) -> List[str]:
        """Submit multiple images as batch jobs"""
        job_ids = []
        
        for i, img in enumerate(images):
            # Save image if PIL
            if isinstance(img, Image.Image):
                output_dir = Path(self.config.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                img_path = output_dir / f"input_{uuid.uuid4()[:8]}.png"
                img.save(img_path)
                img_path_str = str(img_path)
            else:
                img_path_str = img
            
            job = self.create_job(
                job_type=job_type,
                params=params.copy(),
                input_images=[img_path_str],
                priority=priority,
            )
            
            self.submit(job)
            job_ids.append(job.id)
        
        logger.info(f"Submitted batch of {len(job_ids)} jobs")
        return job_ids
    
    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get job by ID"""
        return self.jobs.get(job_id)
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        job = self.get_job(job_id)
        return job.to_dict() if job else None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        job = self.get_job(job_id)
        if job and job.status in [JobStatus.PENDING, JobStatus.QUEUED]:
            job.status = JobStatus.CANCELLED
            logger.info(f"Job {job_id} cancelled")
            return True
        return False
    
    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List jobs with optional status filter"""
        jobs = list(self.jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # Sort by created_at descending
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        return [j.to_dict() for j in jobs[:limit]]
    
    def start(self):
        """Start background worker"""
        if self._running:
            return
        
        self._running = True
        self._worker_task = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_task.start()
        
        logger.info("Batch processor started")
    
    def stop(self):
        """Stop background worker"""
        self._running = False
        if self._worker_task:
            self._worker_task.join(timeout=5)
        
        logger.info("Batch processor stopped")
    
    def _worker_loop(self):
        """Main worker loop"""
        while self._running:
            try:
                # Get job from queue with timeout
                try:
                    job = self.queue.get(timeout=1.0)
                except sync_queue.Empty:
                    continue
                
                # Skip cancelled jobs
                if job.status == JobStatus.CANCELLED:
                    continue
                
                # Process job
                self._process_job(job)
                
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    def _process_job(self, job: BatchJob):
        """Process a single job"""
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now()
        
        try:
            handler = self.handlers.get(job.job_type)
            if not handler:
                raise ValueError(f"No handler for job type: {job.job_type}")
            
            # Load input images
            input_images = []
            for img_path in job.input_images:
                if Path(img_path).exists():
                    input_images.append(Image.open(img_path))
            
            # Create progress callback
            def progress_callback(progress: float):
                job.progress = progress
            
            # Execute handler
            result = handler(
                images=input_images,
                params=job.params,
                progress_callback=progress_callback,
            )
            
            # Save output images
            output_dir = Path(self.config.output_dir) / job.id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_paths = []
            if isinstance(result, list):
                for i, img in enumerate(result):
                    if isinstance(img, Image.Image):
                        out_path = output_dir / f"output_{i}.png"
                        img.save(out_path)
                        output_paths.append(str(out_path))
            elif isinstance(result, Image.Image):
                out_path = output_dir / "output.png"
                result.save(out_path)
                output_paths.append(str(out_path))
            
            job.output_images = output_paths
            job.result = {"output_count": len(output_paths)}
            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            
            logger.info(f"Job {job.id} completed: {len(output_paths)} outputs")
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            logger.error(f"Job {job.id} failed: {e}")
        
        finally:
            job.completed_at = datetime.now()
    
    def cleanup_old_jobs(self, hours: Optional[int] = None):
        """Clean up old completed/failed jobs"""
        hours = hours or self.config.cleanup_after_hours
        cutoff = datetime.now().timestamp() - (hours * 3600)
        
        to_remove = []
        for job_id, job in self.jobs.items():
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                if job.completed_at and job.completed_at.timestamp() < cutoff:
                    to_remove.append(job_id)
        
        for job_id in to_remove:
            del self.jobs[job_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old jobs")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        status_counts = {}
        for job in self.jobs.values():
            status = job.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_jobs": len(self.jobs),
            "queue_size": self.queue.qsize(),
            "running": self._running,
            "status_counts": status_counts,
        }


# =============================================================================
# Batch Handlers
# =============================================================================

def register_default_handlers(processor: BatchProcessor):
    """Register default batch handlers"""
    
    def handle_generate(images, params, progress_callback):
        """Handle batch generation"""
        from .pipeline import get_pipeline_manager
        
        pipeline = get_pipeline_manager()
        results = []
        
        for i, _ in enumerate(range(params.get("count", 1))):
            result = pipeline.generate(
                prompt=params["prompt"],
                negative_prompt=params.get("negative_prompt", ""),
                model=params.get("model", "sdxl"),
                width=params.get("width", 1024),
                height=params.get("height", 1024),
                num_inference_steps=params.get("steps", 30),
                guidance_scale=params.get("guidance_scale", 7.5),
                seed=params.get("seed"),
            )
            results.append(result)
            progress_callback((i + 1) / params.get("count", 1))
        
        return results
    
    def handle_edit(images, params, progress_callback):
        """Handle batch editing"""
        from .pipeline import get_pipeline_manager
        
        pipeline = get_pipeline_manager()
        results = []
        
        for i, img in enumerate(images):
            result = pipeline.edit(
                image=img,
                prompt=params["prompt"],
                strength=params.get("strength", 0.7),
            )
            results.append(result)
            progress_callback((i + 1) / len(images))
        
        return results
    
    def handle_upscale(images, params, progress_callback):
        """Handle batch upscaling"""
        from .upscaler import get_upscaler
        
        upscaler = get_upscaler()
        results = []
        
        for i, img in enumerate(images):
            result = upscaler.upscale(
                image=img,
                scale=params.get("scale", 4),
                model=params.get("model", "realesrgan"),
            )
            results.append(result)
            progress_callback((i + 1) / len(images))
        
        return results
    
    def handle_face_swap(images, params, progress_callback):
        """Handle batch face swap"""
        from .instantid import get_instantid_pipeline
        
        pipeline = get_instantid_pipeline()
        results = []
        
        source_face = Image.open(params["source_face"]) if isinstance(params["source_face"], str) else params["source_face"]
        
        for i, img in enumerate(images):
            result = pipeline.swap_face(
                target_image=img,
                source_face=source_face,
                strength=params.get("strength", 0.8),
            )
            results.append(result.image)
            progress_callback((i + 1) / len(images))
        
        return results
    
    # Register handlers
    processor.register_handler("generate", handle_generate)
    processor.register_handler("edit", handle_edit)
    processor.register_handler("upscale", handle_upscale)
    processor.register_handler("face_swap", handle_face_swap)
    
    logger.info("Default batch handlers registered")


# Singleton
def get_batch_processor() -> BatchProcessor:
    """Get batch processor singleton"""
    processor = BatchProcessor()
    
    # Register handlers if not done
    if not processor.handlers:
        register_default_handlers(processor)
    
    return processor
