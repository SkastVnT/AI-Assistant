"""
Edit Image Service - Main Application Entry Point.

This module initializes and runs the FastAPI application with Gradio UI.
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import __version__
from app.core.config import get_settings, load_settings
from app.core.pipeline import get_pipeline_manager
from app.api.routes import router as api_router
from app.api.grok_routes import router as grok_router
from app.ui.gradio_app import create_gradio_app


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("=" * 60)
    logger.info(f"Edit Image Service v{__version__} starting...")
    logger.info("=" * 60)
    
    # Load settings
    settings = get_settings()
    logger.info(f"Configuration loaded from: config/settings.yaml")
    logger.info(f"Device: {settings.inference.device}")
    logger.info(f"Default model: {settings.models.default}")
    
    # Initialize pipeline manager (lazy loading)
    manager = get_pipeline_manager()
    logger.info(f"Pipeline manager initialized on {manager.device}")
    
    # Create output directory
    output_dir = Path(settings.output.directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir.absolute()}")
    
    # Create logs directory
    log_dir = Path(settings.logging.file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Service ready!")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Edit Image Service...")
    manager.clear_cache()
    logger.info("Cleanup complete. Goodbye!")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    settings = get_settings()
    
    app = FastAPI(
        title="Edit Image Service",
        description="""
        AI-powered image generation and editing service.
        
        ## Features
        
        - **Text-to-Image**: Generate images from text descriptions
        - **Image-to-Image**: Transform existing images
        - **Edit**: Natural language instruction-based editing
        - **Inpaint**: Fill in or modify parts of images
        - **ControlNet**: Guided generation with poses, edges, depth maps
        - **Anime**: Specialized anime/manga style generation
        
        ## Models
        
        - SDXL, FLUX.1, SD3
        - Animagine XL, Anything V5
        - InstructPix2Pix
        
        ## API Documentation
        
        - Swagger UI: `/docs`
        - ReDoc: `/redoc`
        """,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router)
    app.include_router(grok_router)
    
    # Mount Gradio app
    gradio_app = create_gradio_app()
    app = gr.mount_gradio_app(app, gradio_app, path="/")
    
    # Mount static files for outputs
    output_dir = Path(settings.output.directory)
    if output_dir.exists():
        app.mount("/outputs", StaticFiles(directory=str(output_dir)), name="outputs")
    
    return app


# Import gradio for mounting
import gradio as gr

# Create the application instance
app = create_app()


def main():
    """Run the application."""
    settings = get_settings()
    
    logger.info(f"Starting server on {settings.server.host}:{settings.server.port}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        workers=settings.server.workers,
        log_level=settings.server.log_level,
    )


if __name__ == "__main__":
    main()
