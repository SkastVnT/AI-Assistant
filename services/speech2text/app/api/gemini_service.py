"""
Gemini Proxy Service - Cloud AI Integration
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import time
import logging
from google import genai
import redis
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gemini Proxy Service", version="1.0.0")

# Initialize Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("Gemini AI initialized successfully")
else:
    logger.warning("GEMINI_API_KEY not found")
    client = None

# Redis for caching
redis_client = None
try:
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url, decode_responses=True)
    logger.info("Redis connected successfully")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")

class FusionRequest(BaseModel):
    whisper_transcript: str
    phowhisper_transcript: str
    language: str = "vi"

class FusionResponse(BaseModel):
    fused_transcript: str
    processing_time: float
    model: str = "gemini"
    cached: bool = False

class TranscriptionRequest(BaseModel):
    audio_path: str
    language: str = "vi"

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    gemini_status = "available" if client else "unavailable"
    redis_status = "available" if redis_client else "unavailable"
    
    return {
        "status": "healthy",
        "service": "grok-proxy",
        "timestamp": time.time(),
        "grok": gemini_status,
        "redis": redis_status
    }

@app.post("/fuse", response_model=FusionResponse)
async def fuse_transcripts(request: FusionRequest):
    """Fuse two transcripts using Gemini AI"""
    if not client:
        raise HTTPException(status_code=503, detail="Gemini API not available")
    
    try:
        start_time = time.time()
        
        # Create cache key
        cache_key = f"fusion:{hash(request.whisper_transcript + request.phowhisper_transcript)}"
        
        # Check cache first
        if redis_client:
            try:
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    logger.info("Returning cached fusion result")
                    result = json.loads(cached_result)
                    result["cached"] = True
                    result["processing_time"] = time.time() - start_time
                    return FusionResponse(**result)
            except Exception as e:
                logger.warning(f"Cache error: {e}")
        
        # Prepare prompt for Vietnamese fusion
        prompt = f"""
B[?]n l[?] chuy[?]n gia nh[?]n d[?]ng gi[?]ng n[?]i ti[?]ng Vi[?]t. H[?]y k[?]t h[?]p 2 b[?]n transcript sau d[?] t[?]o ra 1 b[?]n ch[?]nh x[?]c nh[?]t:

TRANSCRIPT 1 (Whisper):
{request.whisper_transcript}

TRANSCRIPT 2 (PhoWhisper):  
{request.phowhisper_transcript}

Y[?]U C[?]U:
- K[?]t h[?]p th[?]ng minh d[?] t[?]o transcript ch[?]nh x[?]c nh[?]t
- [?]u ti[?]n c[?]c t[?] ti[?]ng Vi[?]t ch[?]nh x[?]c h[?]n
- S[?]a l[?]i ch[?]nh t[?] v[?] ng[?] ph[?]p
- Gi[?] nguy[?]n [?] ngh[?]a v[?] ng[?] c[?]nh
- Ch[?] tr[?] v[?] text d[?] k[?]t h[?]p, kh[?]ng gi[?]i th[?]ch

TRANSCRIPT CU[?]I:"""

        # Call GROK API
        response = client.models.generate_content(
            model='grok-3',
            contents=prompt
        )
        fused_text = response.text.strip()
        
        processing_time = time.time() - start_time
        
        # Cache result
        if redis_client:
            try:
                cache_data = {
                    "fused_transcript": fused_text,
                    "model": "gemini",
                    "cached": False
                }
                redis_client.setex(cache_key, 3600, json.dumps(cache_data))  # 1 hour cache
            except Exception as e:
                logger.warning(f"Cache save error: {e}")
        
        logger.info(f"Gemini fusion completed in {processing_time:.2f}s")
        
        return FusionResponse(
            fused_transcript=fused_text,
            processing_time=processing_time,
            model="gemini",
            cached=False
        )
        
    except Exception as e:
        logger.error(f"Gemini fusion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe")
async def transcribe(request: TranscriptionRequest):
    """For compatibility - just return placeholder"""
    raise HTTPException(
        status_code=501, 
        detail="This service only provides fusion. Use /fuse endpoint instead."
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Gemini Proxy Service",
        "version": "1.0.0",
        "description": "Cloud AI fusion using Google Gemini 1.5-flash",
        "endpoints": ["/fuse", "/health"],
        "status": "available" if client else "unavailable"
    }

if __name__ == "__main__":
    uvicorn.run("gemini_service:app", host="0.0.0.0", port=8004, reload=False)