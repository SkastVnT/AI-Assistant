"""
T5 Model Service - Microservice for T5 AI Fusion
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import sys
import time
import logging
import torch
import gc

# Add parent directory to path to import our models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="T5 Model Service", version="1.0.0")

class TranscriptionRequest(BaseModel):
    audio_path: str
    language: str = "vi"

class TranscriptionResponse(BaseModel):
    transcript: str
    processing_time: float
    model: str = "t5"

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "t5-model",
        "timestamp": time.time(),
        "gpu_available": torch.cuda.is_available()
    }

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(request: TranscriptionRequest):
    """Transcribe audio using T5 model"""
    try:
        start_time = time.time()
        
        # Import and run T5 t5_model.py
        sys.path.append('/app/src')
        from t5_model import main as t5_main
        
        logger.info(f"Starting T5 transcription for: {request.audio_path}")
        
        # Run T5 transcription
        result = t5_main(request.audio_path)
        
        processing_time = time.time() - start_time
        
        # Clean up GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        
        logger.info(f"T5 transcription completed in {processing_time:.2f}s")
        
        return TranscriptionResponse(
            transcript=result.get("fused_transcript", ""),
            processing_time=processing_time,
            model="t5"
        )
        
    except Exception as e:
        logger.error(f"T5 transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "T5 Model Service",
        "version": "1.0.0",
        "description": "T5 AI fusion for Vietnamese speech-to-text",
        "endpoints": ["/transcribe", "/health"]
    }

if __name__ == "__main__":
    uvicorn.run("t5_service:app", host="0.0.0.0", port=8001, reload=False)