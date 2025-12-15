"""
PyTest Configuration & Shared Fixtures
Provides common fixtures for all test modules
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# Environment Setup Fixtures
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables and configurations"""
    # Set test environment
    os.environ["TESTING"] = "True"
    os.environ["FLASK_ENV"] = "testing"
    
    # Mock API keys to avoid leaking real credentials
    os.environ["GEMINI_API_KEY"] = "test-gemini-key-12345"
    os.environ["OPENAI_API_KEY"] = "test-openai-key-12345"
    os.environ["GROQ_API_KEY"] = "test-groq-key-12345"
    os.environ["DEEPSEEK_API_KEY"] = "test-deepseek-key-12345"
    os.environ["IMGBB_API_KEY"] = "test-imgbb-key-12345"
    
    # Database settings
    os.environ["MONGODB_ENABLED"] = "False"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    # Cache settings
    os.environ["ENABLE_CACHE"] = "False"
    
    yield
    
    # Cleanup after all tests
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests"""
    return tmp_path


@pytest.fixture
def sample_data_dir(temp_dir):
    """Create sample data directory structure"""
    data_dir = temp_dir / "data"
    data_dir.mkdir()
    
    (data_dir / "input").mkdir()
    (data_dir / "output").mkdir()
    (data_dir / "cache").mkdir()
    
    return data_dir


# ============================================================================
# Flask App Fixtures
# ============================================================================

@pytest.fixture
def hub_app():
    """Create Hub Gateway Flask app for testing"""
    # Add services/hub-gateway to path
    hub_path = project_root / "services" / "hub-gateway"
    if str(hub_path) not in sys.path:
        sys.path.insert(0, str(hub_path))
    
    try:
        from hub import app
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        return app
    except ImportError:
        pytest.skip("Hub Gateway app not available")


@pytest.fixture
def hub_client(hub_app):
    """Create test client for Hub Gateway"""
    return hub_app.test_client()


@pytest.fixture
def chatbot_app():
    """Create ChatBot Flask app for testing"""
    # Add services/chatbot to path
    chatbot_path = project_root / "services" / "chatbot"
    if str(chatbot_path) not in sys.path:
        sys.path.insert(0, str(chatbot_path))
    
    try:
        # Mock MongoDB to avoid actual DB connection
        with patch('app.MONGODB_ENABLED', False):
            with patch('app.mongodb_client'):
                from app import app
                app.config['TESTING'] = True
                app.config['DEBUG'] = False
                return app
    except ImportError:
        pytest.skip("ChatBot app not available")


@pytest.fixture
def chatbot_client(chatbot_app):
    """Create test client for ChatBot"""
    return chatbot_app.test_client()


@pytest.fixture
def text2sql_app():
    """Create Text2SQL Flask app for testing"""
    # Add services/text2sql to path
    text2sql_path = project_root / "services" / "text2sql"
    if str(text2sql_path) not in sys.path:
        sys.path.insert(0, str(text2sql_path))
    
    try:
        from app_simple import app
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        return app
    except ImportError:
        pytest.skip("Text2SQL app not available")


@pytest.fixture
def text2sql_client(text2sql_app):
    """Create test client for Text2SQL"""
    return text2sql_app.test_client()


# ============================================================================
# Mock External Services
# ============================================================================

@pytest.fixture
def mock_gemini_model():
    """Mock Google Gemini API"""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a mocked Gemini response"
    mock_model.generate_content.return_value = mock_response
    
    with patch('google.generativeai.GenerativeModel', return_value=mock_model):
        yield mock_model


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI API"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="This is a mocked OpenAI response"))
    ]
    mock_client.chat.completions.create.return_value = mock_response
    
    with patch('openai.OpenAI', return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB connections"""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    
    # Setup mock chain
    mock_client.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    mock_collection.find.return_value = []
    mock_collection.insert_one.return_value = MagicMock(inserted_id="mock_id_123")
    
    with patch('pymongo.MongoClient', return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_requests():
    """Mock requests library for HTTP calls"""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        
        # Setup successful responses
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "success", "data": {}}
        )
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "success", "data": {}}
        )
        
        yield {"get": mock_get, "post": mock_post}


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_conversation():
    """Sample conversation data"""
    return {
        "id": "conv_12345",
        "user_id": "user_123",
        "title": "Test Conversation",
        "messages": [
            {
                "role": "user",
                "content": "Hello, how are you?",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant",
                "content": "I'm doing well, thank you!",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


@pytest.fixture
def sample_schema():
    """Sample database schema for Text2SQL"""
    return """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(100),
        age INTEGER,
        created_at TIMESTAMP
    );
    
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        product VARCHAR(100),
        amount DECIMAL(10,2),
        status VARCHAR(20),
        created_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """


@pytest.fixture
def sample_sql_questions():
    """Sample SQL questions for testing"""
    return [
        "Show all users",
        "Find users older than 25",
        "Get total orders by user",
        "List pending orders",
        "Show users who made orders in the last month"
    ]


@pytest.fixture
def sample_image_base64():
    """Sample base64 encoded image"""
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


@pytest.fixture
def sample_audio_file(temp_dir):
    """Create a sample audio file for testing"""
    audio_path = temp_dir / "sample.wav"
    # Create a minimal valid WAV file
    audio_path.write_bytes(b'RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00data\x00\x00\x00\x00')
    return audio_path


# ============================================================================
# Cache & Database Fixtures
# ============================================================================

@pytest.fixture
def mock_cache():
    """Mock cache manager"""
    cache = MagicMock()
    cache.get.return_value = None
    cache.set.return_value = True
    cache.delete.return_value = True
    cache.clear.return_value = 0
    return cache


@pytest.fixture
def mock_database():
    """Mock database manager"""
    db = MagicMock()
    db.query.return_value = []
    db.insert.return_value = "mock_id_123"
    db.update.return_value = True
    db.delete.return_value = True
    return db


# ============================================================================
# Service Configuration Fixtures
# ============================================================================

@pytest.fixture
def hub_config():
    """Hub Gateway configuration"""
    from config.model_config import HubConfig
    return HubConfig


@pytest.fixture
def service_configs(hub_config):
    """All service configurations"""
    return hub_config.get_all_services()


# ============================================================================
# Helper Functions for Tests
# ============================================================================

@pytest.fixture
def assert_response_ok():
    """Helper to assert successful API response"""
    def _assert(response, expected_status=200):
        assert response.status_code == expected_status
        if response.content_type == 'application/json':
            data = response.get_json()
            assert data is not None
            return data
        return response.data
    return _assert


@pytest.fixture
def assert_response_error():
    """Helper to assert error API response"""
    def _assert(response, expected_status=400):
        assert response.status_code >= expected_status
        if response.content_type == 'application/json':
            data = response.get_json()
            assert 'error' in data or 'message' in data
            return data
        return response.data
    return _assert


# ============================================================================
# Markers Setup
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "smoke: Smoke tests")
