"""
AI Fusion Service - Uses DeepSeek/OpenAI for transcript fusion
Replaces deprecated Gemini service
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import time
import logging
import openai
import redis
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Fusion Service", version="2.0.0")

# Load API keys
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_BASE = "https://api.deepseek.com"

# Initialize clients
deepseek_client = None
openai_client = None

if DEEPSEEK_API_KEY:
    deepseek_client = openai.OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_API_BASE
    )
    logger.info("DeepSeek AI initialized successfully")

if OPENAI_API_KEY:
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    logger.info("OpenAI initialized successfully")

if not deepseek_client and not openai_client:
    logger.warning("No AI API keys found (DEEPSEEK_API_KEY or OPENAI_API_KEY)")

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
    model: str = "deepseek"
    cached: bool = False


class TranscriptionRequest(BaseModel):
    audio_path: str
    language: str = "vi"


def get_active_client():
    """Get the first available AI client"""
    if deepseek_client:
        return deepseek_client, "deepseek-chat", "deepseek"
    if openai_client:
        return openai_client, "gpt-4o-mini", "openai"
    return None, None, None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    client, _, model_name = get_active_client()
    ai_status = "available" if client else "unavailable"
    redis_status = "available" if redis_client else "unavailable"
    
    return {
        "status": "healthy",
        "service": "ai-fusion",
        "timestamp": time.time(),
        "ai_model": model_name or "none",
        "ai_status": ai_status,
        "redis": redis_status
    }


@app.post("/fuse", response_model=FusionResponse)
async def fuse_transcripts(request: FusionRequest):
    """Fuse two transcripts using DeepSeek/OpenAI"""
    client, model, model_name = get_active_client()
    
    if not client:
        raise HTTPException(status_code=503, detail="No AI API available")
    
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
        prompt = f"""Bạn là chuyên gia nhận dạng giọng nói tiếng Việt. Hãy kết hợp 2 bản transcript sau để tạo ra 1 bản chính xác nhất:

TRANSCRIPT 1 (Whisper):
{request.whisper_transcript}

TRANSCRIPT 2 (PhoWhisper):  
{request.phowhisper_transcript}

YÊU CẦU:
- Kết hợp thông minh để tạo transcript chính xác nhất
- Ưu tiên các từ tiếng Việt chính xác hơn
- Sửa lỗi chính tả và ngữ pháp
- Giữ nguyên ý nghĩa và ngữ cảnh
- Chỉ trả về text đã kết hợp, không giải thích

TRANSCRIPT CUỐI:"""

        # Call AI API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia xử lý ngôn ngữ tiếng Việt. Chỉ trả về kết quả, không giải thích."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        fused_text = response.choices[0].message.content.strip()
        
        processing_time = time.time() - start_time
        
        # Cache result
        if redis_client:
            try:
                cache_data = {
                    "fused_transcript": fused_text,
                    "model": model_name,
                    "cached": False
                }
                redis_client.setex(cache_key, 3600, json.dumps(cache_data))
            except Exception as e:
                logger.warning(f"Cache save error: {e}")
        
        logger.info(f"AI fusion completed in {processing_time:.2f}s using {model_name}")
        
        return FusionResponse(
            fused_transcript=fused_text,
            processing_time=processing_time,
            model=model_name,
            cached=False
        )
        
    except Exception as e:
        logger.error(f"AI fusion error: {e}")
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
    client, _, model_name = get_active_client()
    return {
        "service": "AI Fusion Service",
        "version": "2.0.0",
        "description": "Cloud AI fusion using DeepSeek/OpenAI",
        "endpoints": ["/fuse", "/health"],
        "model": model_name or "none",
        "status": "available" if client else "unavailable"
    }


if __name__ == "__main__":
    uvicorn.run("ai_fusion_service:app", host="0.0.0.0", port=8004, reload=False)
