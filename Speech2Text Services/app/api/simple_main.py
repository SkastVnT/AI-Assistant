# -*- coding: utf-8 -*-
"""
Simple FastAPI for Testing - Minimal Dependencies
"""

from fastapi import FastAPI
import time
import os

app = FastAPI(
    title="Vietnamese Speech-to-Text API - Test",
    description="Simple test API for Docker deployment",
    version="2.0.0-test"
)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Vietnamese Speech-to-Text API",
        "version": "2.0.0-test",
        "status": "running",
        "message": "[MIC] Docker deployment successful!",
        "timestamp": time.time(),
        "environment": {
            "GEMINI_API_KEY": "configured" if os.getenv('GEMINI_API_KEY') else "not_configured",
            "working_directory": os.getcwd(),
            "python_path": os.getenv('PYTHONPATH', 'default')
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "s2t-api-test"
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {
        "message": "[SUCCESS] API is working perfectly!",
        "docker": "[OK] Container running",
        "fastapi": "[OK] Framework loaded",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)