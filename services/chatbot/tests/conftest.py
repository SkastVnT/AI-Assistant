"""
PyTest Configuration for ChatBot Service
"""
import pytest
import sys
from pathlib import Path

# Ensure services/chatbot/ is at sys.path[0] so that local packages like
# `src` are always resolved to the correct location, even when other modules
# (e.g. core/__init__.py) manipulate sys.path during test collection.
_CHATBOT_DIR = str(Path(__file__).parent.parent.resolve())
if _CHATBOT_DIR in sys.path:
    sys.path.remove(_CHATBOT_DIR)
sys.path.insert(0, _CHATBOT_DIR)

# Pre-import src to cache the correct package in sys.modules before any
# other import can displace it (core/__init__.py manipulates sys.path).
import src  # noqa: E402


@pytest.fixture
def app():
    """Create application instance for testing"""
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['DEBUG'] = False
    return flask_app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()

@pytest.fixture
def sample_message():
    """Sample chat message"""
    return {
        'message': 'Hello, how are you?',
        'model': 'gemini',
        'context': 'casual'
    }

@pytest.fixture
def sample_file():
    """Sample file data"""
    return {
        'name': 'test.py',
        'content': 'print("Hello World")',
        'type': 'code',
        'size': 25
    }

@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response"""
    return "Hello! I'm doing well, thank you for asking. How can I help you today?"

@pytest.fixture
def sample_image_params():
    """Sample image generation parameters"""
    return {
        'prompt': 'A beautiful sunset over mountains',
        'negative_prompt': 'blurry, low quality',
        'steps': 30,
        'cfg_scale': 7.5,
        'width': 512,
        'height': 512,
        'sampler': 'Euler a'
    }


@pytest.fixture(autouse=True)
def _reset_skill_singletons():
    """Reset skill system singletons between tests to prevent state leakage."""
    import core.skills.registry as _reg
    import core.skills.router as _rtr
    import core.skills.session as _ses

    # Save original state
    old_registry = _reg._registry
    old_router = _rtr._router
    old_store = _ses._store

    # Reset to None so each test gets a fresh singleton (or the test builds its own)
    _reg._registry = None
    _rtr._router = None
    _ses._store = None

    yield

    # Restore original state (in case a test relies on process-level singletons)
    _reg._registry = old_registry
    _rtr._router = old_router
    _ses._store = old_store
