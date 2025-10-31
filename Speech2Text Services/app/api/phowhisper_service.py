"""
PhoWhisper Model Service - Microservice for Vietnamese Specialized Model
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

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PhoWhisper Model Service", version="1.0.0")

class TranscriptionRequest(BaseModel):
    audio_path: str
    language: str = "vi"

class TranscriptionResponse(BaseModel):
    transcript: str
    processing_time: float
    model: str = "phowhisper"

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "phowhisper-model",
        "timestamp": time.time(),
        "gpu_available": torch.cuda.is_available()
    }

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(request: TranscriptionRequest):
    """Transcribe audio using PhoWhisper model"""
    try:
        start_time = time.time()
        
        # Import and run PhoWhisper
        sys.path.append('/app/src')
        from gemini_model import main as phowhisper_main
        
        logger.info(f"Starting PhoWhisper transcription for: {request.audio_path}")
        
        # Run ultra-optimized PhoWhisper
        result = phowhisper_main(request.audio_path)
        
        processing_time = time.time() - start_time
        
        # Clean up GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        
        logger.info(f"PhoWhisper transcription completed in {processing_time:.2f}s")
        
        return TranscriptionResponse(
            transcript=result.get("fused_transcript", ""),
            processing_time=processing_time,
            model="phowhisper"
        )
        
    except Exception as e:
        logger.error(f"PhoWhisper transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PhoWhisper Model Service", 
        "version": "1.0.0",
        "description": "Ultra-optimized Vietnamese PhoWhisper with Gemini fusion",
        "endpoints": ["/transcribe", "/health"]
    }

if __name__ == "__main__":
    uvicorn.run("phowhisper_service:app", host="0.0.0.0", port=8002, reload=False)