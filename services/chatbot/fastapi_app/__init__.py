"""
FastAPI Application - Chatbot Service
Migrated from Flask monolith for native async support and better performance.
"""
import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# Ensure paths
CHATBOT_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = CHATBOT_DIR.parent.parent

if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(1, str(ROOT_DIR))

from core.config import IMAGE_STORAGE_DIR, MEMORY_DIR
from core.extensions import MONGODB_ENABLED, logger

# Import routers
from fastapi_app.routers import (
    chat,
    council_stream,
    xai_native_stream,
    stream,
    conversations,
    memory,
    images,
    video,
    rag,
)

logger = logging.getLogger("chatbot.fastapi")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 FastAPI Chatbot starting up...")

    # Ensure storage directories
    IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if MONGODB_ENABLED:
        logger.info("✅ MongoDB connection available")
    else:
        logger.warning("⚠️ MongoDB not available — some features disabled")

    yield

    logger.info("🛑 FastAPI Chatbot shutting down...")


def create_app() -> FastAPI:
    """Application factory"""
    app = FastAPI(
        title="AI Assistant Chatbot",
        description="Multi-model AI chatbot with streaming, video generation, and more",
        version="2.0.0",
        lifespan=lifespan,
    )

    # --- Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    secret = os.getenv("SESSION_SECRET", os.urandom(32).hex())
    app.add_middleware(SessionMiddleware, secret_key=secret)

    # --- Static files ---
    static_dir = CHATBOT_DIR / "Static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    storage_dir = IMAGE_STORAGE_DIR
    if storage_dir.exists():
        app.mount(
            "/storage/images",
            StaticFiles(directory=str(storage_dir)),
            name="image_storage",
        )

    # --- Routers ---
    app.include_router(chat.router, tags=["Chat"])
    app.include_router(council_stream.router, tags=["Council Streaming"])
    app.include_router(xai_native_stream.router, tags=["xAI Native Streaming"])
    app.include_router(stream.router, tags=["Streaming"])
    app.include_router(conversations.router, prefix="/api", tags=["Conversations"])
    app.include_router(memory.router, prefix="/api/memory", tags=["Memory"])
    app.include_router(images.router, tags=["Images"])
    app.include_router(video.router, prefix="/api/video", tags=["Video Generation"])
    app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])

    # --- Root health check ---
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "chatbot",
            "framework": "fastapi",
            "mongodb": MONGODB_ENABLED,
        }

    return app
