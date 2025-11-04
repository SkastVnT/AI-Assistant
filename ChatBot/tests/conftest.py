"""
PyTest Configuration for ChatBot Service
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
