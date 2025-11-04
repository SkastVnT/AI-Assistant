"""
PyTest Configuration for Text2SQL Service
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture
def app():
    """Create application instance"""
    try:
        from app_simple import app as flask_app
        flask_app.config['TESTING'] = True
        return flask_app
    except ImportError:
        from app import app as flask_app
        flask_app.config['TESTING'] = True
        return flask_app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def sample_schema():
    """Sample database schema"""
    return """
    CREATE TABLE customers (
        customer_id INT PRIMARY KEY,
        customer_name VARCHAR(100),
        email VARCHAR(100)
    );
    
    CREATE TABLE orders (
        order_id INT PRIMARY KEY,
        customer_id INT,
        order_date DATE,
        total_amount DECIMAL(10,2)
    );
    """

@pytest.fixture
def sample_question():
    """Sample natural language question"""
    return {
        'question': 'Show top 10 customers by total revenue',
        'database_type': 'clickhouse'
    }

@pytest.fixture
def sample_clickhouse_config():
    """Sample ClickHouse configuration"""
    return {
        'host': 'localhost',
        'port': 9000,
        'database': 'default',
        'username': 'default',
        'password': ''
    }

@pytest.fixture
def sample_mongodb_config():
    """Sample MongoDB configuration"""
    return {
        'uri': 'mongodb://localhost:27017',
        'database': 'testdb'
    }
