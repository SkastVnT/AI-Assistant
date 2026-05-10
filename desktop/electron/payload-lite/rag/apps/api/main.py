"""FastAPI application factory."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import health, ingest, query
from libs.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    logger = logging.getLogger("rag.api")
    logger.info("RAG API starting up")
    yield
    # Shutdown — dispose engine
    from libs.core.database import engine

    logger.info("RAG API shutting down")
    await engine.dispose()


def create_app() -> FastAPI:
    setup_logging("rag.api")

    app = FastAPI(
        title="RAG System API",
        version="0.1.0",
        description="Production-ready Retrieval-Augmented Generation system",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(ingest.router, prefix="/api/v1")
    app.include_router(query.router, prefix="/api/v1")

    return app


app = create_app()
