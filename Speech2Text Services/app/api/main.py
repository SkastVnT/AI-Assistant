"""
FastAPI Main Application - Speech-to-Text Web Service
Provides REST API endpoints for all transcription models
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import json
import time
import uuid
import asyncio
import redis
import logging
from pathlib import Path
from typing import Optional, List
import mimetypes
import requests

# Import our transcription models
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.run_dual_smart import main as smart_transcribe
from core.run_dual_fast import main as fast_transcribe

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Vietnamese Speech-to-Text API",
    description="Professional Vietnamese speech recognition system with multiple AI models",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
redis_client = None
try:
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url, decode_responses=True)
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")

# Directories
AUDIO_DIR = Path("/app/audio")
RESULT_DIR = Path("/app/result")
AUDIO_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def is_audio_file(filename: str) -> bool:
    """Check if file is supported audio format"""
    audio_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma']
    return any(filename.lower().endswith(ext) for ext in audio_extensions)

def get_job_status(job_id: str) -> dict:
    """Get job status from Redis"""
    if not redis_client:
        return {"status": "unknown", "message": "Redis not available"}
    
    try:
        status = redis_client.get(f"job:{job_id}")
        if status:
            return json.loads(status)
        return {"status": "not_found"}
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return {"status": "error", "message": str(e)}

def update_job_status(job_id: str, status: dict):
    """Update job status in Redis"""
    if redis_client:
        try:
            redis_client.setex(f"job:{job_id}", 3600, json.dumps(status))  # 1 hour TTL
        except Exception as e:
            logger.error(f"Error updating job status: {e}")

async def process_transcription(
    job_id: str,
    audio_path: str,
    model: str,
    language: str = "vi"
):
    """Background task to process transcription"""
    try:
        # Update status to processing
        update_job_status(job_id, {
            "status": "processing",
            "progress": 10,
            "message": f"Starting {model} transcription...",
            "timestamp": time.time()
        })

        start_time = time.time()
        
        # Call appropriate model
        if model == "smart":
            # Call smart dual model
            result = await asyncio.get_event_loop().run_in_executor(
                None, smart_transcribe, audio_path
            )
        elif model == "fast":
            # Call fast dual model  
            result = await asyncio.get_event_loop().run_in_executor(
                None, fast_transcribe, audio_path
            )
        elif model == "t5":
            # Call T5 service
            response = requests.post(
                "http://t5-service:8001/transcribe",
                json={"audio_path": audio_path, "language": language},
                timeout=1800  # 30 minutes
            )
            result = response.json()
        elif model == "phowhisper":
            # Call PhoWhisper service
            response = requests.post(
                "http://phowhisper-service:8002/transcribe",
                json={"audio_path": audio_path, "language": language},
                timeout=1800  # 30 minutes
            )
            result = response.json()
        elif model == "whisper":
            # Call Whisper service
            response = requests.post(
                "http://whisper-service:8003/transcribe",
                json={"audio_path": audio_path, "language": language},
                timeout=1800  # 30 minutes
            )
            result = response.json()
        elif model == "gemini":
            # Call Gemini proxy service
            response = requests.post(
                "http://gemini-proxy:8004/transcribe",
                json={"audio_path": audio_path, "language": language},
                timeout=1800  # 30 minutes
            )
            result = response.json()
        else:
            raise ValueError(f"Unknown model: {model}")

        processing_time = time.time() - start_time
        
        # Update status to completed
        update_job_status(job_id, {
            "status": "completed",
            "progress": 100,
            "result": result,
            "processing_time": processing_time,
            "message": "Transcription completed successfully",
            "timestamp": time.time()
        })
        
        logger.info(f"Job {job_id} completed in {processing_time:.2f}s")
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        update_job_status(job_id, {
            "status": "failed",
            "progress": 0,
            "error": str(e),
            "message": f"Transcription failed: {str(e)}",
            "timestamp": time.time()
        })

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Vietnamese Speech-to-Text API",
        "version": "2.0.0",
        "status": "running",
        "models": ["smart", "fast", "t5", "phowhisper", "whisper", "gemini"],
        "docs": "/docs",
        "endpoints": {
            "upload": "/upload",
            "transcribe": "/transcribe",
            "status": "/status/{job_id}",
            "download": "/download/{job_id}",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {}
    }
    
    # Check Redis
    if redis_client:
        try:
            redis_client.ping()
            health["services"]["redis"] = "healthy"
        except:
            health["services"]["redis"] = "unhealthy"
    else:
        health["services"]["redis"] = "unavailable"
    
    # Check model services
    model_services = [
        ("t5", "http://t5-service:8001/health"),
        ("phowhisper", "http://phowhisper-service:8002/health"),
        ("whisper", "http://whisper-service:8003/health"),
        ("gemini", "http://gemini-proxy:8004/health")
    ]
    
    for service_name, url in model_services:
        try:
            response = requests.get(url, timeout=5)
            health["services"][service_name] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            health["services"][service_name] = "unhealthy"
    
    return health

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Upload audio file for transcription"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not is_audio_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Supported: mp3, wav, m4a, flac, aac, ogg, wma"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    saved_filename = f"{file_id}{file_extension}"
    file_path = AUDIO_DIR / saved_filename
    
    try:
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"File uploaded: {file.filename} -> {saved_filename}")
        
        return {
            "file_id": file_id,
            "filename": file.filename,
            "saved_as": saved_filename,
            "size": len(content),
            "message": "File uploaded successfully"
        }
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.post("/transcribe")
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    file_id: str,
    model: str = "smart",
    language: str = "vi"
):
    """Start transcription job"""
    
    # Validate model
    available_models = ["smart", "fast", "t5", "phowhisper", "whisper", "gemini"]
    if model not in available_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model. Available: {', '.join(available_models)}"
        )
    
    # Find audio file
    audio_files = list(AUDIO_DIR.glob(f"{file_id}.*"))
    if not audio_files:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    audio_path = str(audio_files[0])
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    update_job_status(job_id, {
        "status": "queued",
        "progress": 0,
        "model": model,
        "language": language,
        "audio_file": audio_path,
        "message": "Job queued for processing",
        "timestamp": time.time()
    })
    
    # Start background processing
    background_tasks.add_task(
        process_transcription,
        job_id, audio_path, model, language
    )
    
    logger.info(f"Transcription job {job_id} started for {audio_path} using {model}")
    
    return {
        "job_id": job_id,
        "status": "queued",
        "model": model,
        "language": language,
        "message": "Transcription job started"
    }

@app.get("/status/{job_id}")
async def get_transcription_status(job_id: str):
    """Get transcription job status"""
    status = get_job_status(job_id)
    
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    
    return status

@app.get("/download/{job_id}")
async def download_result(job_id: str):
    """Download transcription result"""
    status = get_job_status(job_id)
    
    if status.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    # Return result as JSON
    return status.get("result", {})

@app.get("/models")
async def get_available_models():
    """Get list of available models with descriptions"""
    return {
        "models": {
            "smart": {
                "name": "Smart Dual",
                "description": "Rule-based fusion, offline, 8-15 min",
                "accuracy": "[?][?][?][?][?]",
                "speed": "Fast"
            },
            "fast": {
                "name": "Fast Dual", 
                "description": "Simple fusion, offline, 2-5 min",
                "accuracy": "[?][?][?][?][?]", 
                "speed": "Very Fast"
            },
            "t5": {
                "name": "T5 AI Fusion",
                "description": "T5 AI model, offline, 10-20 min",
                "accuracy": "[?][?][?][?][?]",
                "speed": "Medium"
            },
            "phowhisper": {
                "name": "PhoWhisper",
                "description": "Vietnamese specialized, 5-10 min",
                "accuracy": "[?][?][?][?][?]",
                "speed": "Fast"
            },
            "whisper": {
                "name": "Whisper Large-v3",
                "description": "OpenAI Whisper, 5-15 min",
                "accuracy": "[?][?][?][?][?]",
                "speed": "Fast"
            },
            "gemini": {
                "name": "Gemini AI Fusion",
                "description": "Cloud AI fusion, 8-15 min",
                "accuracy": "[?][?][?][?][?]",
                "speed": "Fast"
            }
        }
    }

@app.get("/results")
async def list_results():
    """List all result files"""
    try:
        results = []
        for file_path in RESULT_DIR.rglob("*"):
            if file_path.is_file():
                results.append({
                    "filename": file_path.name,
                    "path": str(file_path.relative_to(RESULT_DIR)),
                    "size": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime
                })
        
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/results/{filename}")
async def download_result_file(filename: str):
    """Download specific result file"""
    file_path = RESULT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )