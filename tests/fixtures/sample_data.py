"""
Sample Test Fixtures and Data
Provides reusable test data for all test modules
"""

import json
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================================
# Sample Conversations
# ============================================================================

SAMPLE_CONVERSATIONS = [
    {
        "id": "conv_001",
        "user_id": "user_001",
        "title": "Python Programming Help",
        "messages": [
            {
                "role": "user",
                "content": "How do I read a file in Python?",
                "timestamp": "2025-12-10T09:00:00"
            },
            {
                "role": "assistant",
                "content": "You can read a file using the open() function:\n\n```python\nwith open('file.txt', 'r') as f:\n    content = f.read()\n```",
                "timestamp": "2025-12-10T09:00:05"
            }
        ],
        "created_at": "2025-12-10T09:00:00",
        "updated_at": "2025-12-10T09:00:05"
    },
    {
        "id": "conv_002",
        "user_id": "user_002",
        "title": "Database Design Questions",
        "messages": [
            {
                "role": "user",
                "content": "What's the difference between SQL and NoSQL?",
                "timestamp": "2025-12-10T10:00:00"
            },
            {
                "role": "assistant",
                "content": "SQL databases are relational with structured schemas, while NoSQL databases are more flexible and can handle unstructured data.",
                "timestamp": "2025-12-10T10:00:03"
            }
        ],
        "created_at": "2025-12-10T10:00:00",
        "updated_at": "2025-12-10T10:00:03"
    }
]


# ============================================================================
# Sample Database Schemas
# ============================================================================

SAMPLE_SCHEMA_ECOMMERCE = """
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2),
    status VARCHAR(20) DEFAULT 'pending',
    shipping_address TEXT
);

CREATE TABLE order_items (
    item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id),
    product_id INTEGER REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);
"""

SAMPLE_SCHEMA_BLOG = """
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    bio TEXT,
    avatar_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE posts (
    post_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    slug VARCHAR(200) UNIQUE,
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE comments (
    comment_id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(post_id),
    user_id INTEGER REFERENCES users(user_id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    tag_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE post_tags (
    post_id INTEGER REFERENCES posts(post_id),
    tag_id INTEGER REFERENCES tags(tag_id),
    PRIMARY KEY (post_id, tag_id)
);
"""


# ============================================================================
# Sample SQL Questions and Answers
# ============================================================================

SAMPLE_SQL_QA = [
    {
        "question": "Show all customers",
        "sql": "SELECT * FROM customers ORDER BY created_at DESC LIMIT 100;",
        "difficulty": "easy"
    },
    {
        "question": "Find customers who made orders in the last month",
        "sql": """
        SELECT DISTINCT c.customer_id, c.first_name, c.last_name, c.email
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.order_date >= CURRENT_DATE - INTERVAL '1 month'
        ORDER BY c.last_name
        LIMIT 100;
        """,
        "difficulty": "medium"
    },
    {
        "question": "Get total revenue by product category",
        "sql": """
        SELECT p.category, SUM(oi.quantity * oi.unit_price) as total_revenue
        FROM products p
        JOIN order_items oi ON p.product_id = oi.product_id
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.status = 'completed'
        GROUP BY p.category
        ORDER BY total_revenue DESC
        LIMIT 100;
        """,
        "difficulty": "hard"
    },
    {
        "question": "List top 10 customers by order count",
        "sql": """
        SELECT c.customer_id, c.first_name, c.last_name, COUNT(o.order_id) as order_count
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.first_name, c.last_name
        ORDER BY order_count DESC
        LIMIT 10;
        """,
        "difficulty": "medium"
    },
    {
        "question": "Find products that are out of stock",
        "sql": "SELECT * FROM products WHERE stock_quantity = 0 LIMIT 100;",
        "difficulty": "easy"
    }
]


# ============================================================================
# Sample API Responses
# ============================================================================

SAMPLE_GEMINI_RESPONSE = {
    "text": "This is a sample response from Gemini AI. It demonstrates natural language understanding and generation capabilities.",
    "model": "gemini-pro",
    "timestamp": "2025-12-10T10:00:00"
}

SAMPLE_OPENAI_RESPONSE = {
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "This is a sample response from OpenAI's GPT model."
            },
            "finish_reason": "stop",
            "index": 0
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 15,
        "total_tokens": 25
    }
}

SAMPLE_SD_RESPONSE = {
    "images": ["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="],
    "info": json.dumps({
        "prompt": "A beautiful landscape",
        "steps": 20,
        "sampler": "Euler a",
        "seed": 123456789
    })
}


# ============================================================================
# Sample Image Data
# ============================================================================

# 1x1 pixel PNG (red)
SAMPLE_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="

SAMPLE_IMAGE_DATA_URL = f"data:image/png;base64,{SAMPLE_IMAGE_BASE64}"


# ============================================================================
# Sample User Data
# ============================================================================

SAMPLE_USERS = [
    {
        "id": "user_001",
        "username": "john_doe",
        "email": "john@example.com",
        "created_at": "2025-01-01T10:00:00",
        "settings": {
            "theme": "dark",
            "language": "en",
            "notifications": True
        }
    },
    {
        "id": "user_002",
        "username": "jane_smith",
        "email": "jane@example.com",
        "created_at": "2025-01-02T11:00:00",
        "settings": {
            "theme": "light",
            "language": "vi",
            "notifications": False
        }
    }
]


# ============================================================================
# Helper Functions
# ============================================================================

def create_sample_file(temp_dir: Path, filename: str, content: str):
    """Create a sample file in temp directory"""
    file_path = temp_dir / filename
    file_path.write_text(content)
    return file_path


def create_sample_schema_file(temp_dir: Path, schema_type: str = "ecommerce"):
    """Create a sample schema file"""
    schema_content = SAMPLE_SCHEMA_ECOMMERCE if schema_type == "ecommerce" else SAMPLE_SCHEMA_BLOG
    return create_sample_file(temp_dir, f"schema_{schema_type}.sql", schema_content)


def create_sample_knowledge_base(temp_dir: Path):
    """Create sample knowledge base entries"""
    kb_dir = temp_dir / "knowledge_base"
    kb_dir.mkdir(exist_ok=True)
    
    for i, qa in enumerate(SAMPLE_SQL_QA):
        entry = {
            "id": f"kb_{i+1:03d}",
            "question": qa["question"],
            "sql": qa["sql"],
            "difficulty": qa["difficulty"],
            "created_at": datetime.now().isoformat()
        }
        
        kb_file = kb_dir / f"kb_{i+1:03d}.json"
        kb_file.write_text(json.dumps(entry, indent=2))
    
    return kb_dir


def get_sample_conversation_messages(conv_id: str = "conv_001"):
    """Get messages for a sample conversation"""
    for conv in SAMPLE_CONVERSATIONS:
        if conv["id"] == conv_id:
            return conv["messages"]
    return []


# ============================================================================
# Test Data Export
# ============================================================================

__all__ = [
    'SAMPLE_CONVERSATIONS',
    'SAMPLE_SCHEMA_ECOMMERCE',
    'SAMPLE_SCHEMA_BLOG',
    'SAMPLE_SQL_QA',
    'SAMPLE_GEMINI_RESPONSE',
    'SAMPLE_OPENAI_RESPONSE',
    'SAMPLE_SD_RESPONSE',
    'SAMPLE_IMAGE_BASE64',
    'SAMPLE_IMAGE_DATA_URL',
    'SAMPLE_USERS',
    'create_sample_file',
    'create_sample_schema_file',
    'create_sample_knowledge_base',
    'get_sample_conversation_messages'
]
