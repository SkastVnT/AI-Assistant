"""
Core modules for Edit Image Service.

Uses lazy imports to handle potential numpy/diffusers import issues.
"""

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Always available - config has no heavy dependencies
from .config import Settings, get_settings

# Lazy loading for modules with heavy dependencies
_pipeline_manager = None
_search_manager = None
_post_processor = None
_imports_checked = False


def get_pipeline_manager():
    """Get or create the pipeline manager (lazy loading)"""
    global _pipeline_manager
    if _pipeline_manager is None:
        try:
            from .pipeline import PipelineManager
            _pipeline_manager = PipelineManager()
        except ImportError as e:
            logger.warning(f"Pipeline manager unavailable: {e}")
            return None
        except Exception as e:
            logger.warning(f"Pipeline manager error: {e}")
            return None
    return _pipeline_manager


def get_search_manager():
    """Get or create the search manager (lazy loading)"""
    global _search_manager
    if _search_manager is None:
        try:
            from .search import WebSearchManager
            _search_manager = WebSearchManager()
        except ImportError as e:
            logger.warning(f"Search manager unavailable: {e}")
            return None
        except Exception as e:
            logger.warning(f"Search manager error: {e}")
            return None
    return _search_manager


def get_post_processor():
    """Get or create the post processor (lazy loading)"""
    global _post_processor
    if _post_processor is None:
        try:
            from .upscaler import PostProcessor
            _post_processor = PostProcessor()
        except ImportError as e:
            logger.warning(f"Post processor unavailable: {e}")
            return None
        except Exception as e:
            logger.warning(f"Post processor error: {e}")
            return None
    return _post_processor


# Placeholder classes for backwards compatibility when imports fail
class PipelineManagerPlaceholder:
    """Placeholder when actual PipelineManager is unavailable."""
    def __init__(self, *args, **kwargs):
        raise ImportError("diffusers is not available. Please check numpy/cv2 compatibility.")


class WebSearchManagerPlaceholder:
    """Placeholder when actual WebSearchManager is unavailable."""
    def __init__(self, *args, **kwargs):
        raise ImportError("Search manager dependencies are not available.")


class PostProcessorPlaceholder:
    """Placeholder when actual PostProcessor is unavailable."""
    def __init__(self, *args, **kwargs):
        raise ImportError("Post processor dependencies are not available.")


# Set default placeholders
PipelineManager = PipelineManagerPlaceholder
WebSearchManager = WebSearchManagerPlaceholder
PostProcessor = PostProcessorPlaceholder


__all__ = [
    "Settings",
    "get_settings",
    "PipelineManager",
    "get_pipeline_manager",
    "WebSearchManager",
    "get_search_manager",
    "PostProcessor",
    "get_post_processor",
]
