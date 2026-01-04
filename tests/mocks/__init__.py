"""
Mock Objects for External Services
Provides reusable mocks for testing
"""

from unittest.mock import Mock, MagicMock
from datetime import datetime


class MockGrokModel:
    """Mock GROK AI Model"""
    
    def __init__(self, response_text="Mocked GROK response"):
        self.response_text = response_text
        self.call_count = 0
    
    def generate_content(self, prompt, **kwargs):
        """Mock generate_content method"""
        self.call_count += 1
        
        response = MagicMock()
        response.text = self.response_text
        response.parts = [MagicMock(text=self.response_text)]
        
        return response
    
    def count_tokens(self, text):
        """Mock token counting"""
        return MagicMock(total_tokens=len(text) // 4)


class MockOpenAIClient:
    """Mock OpenAI Client"""
    
    def __init__(self, response_text="Mocked OpenAI response"):
        self.response_text = response_text
        self.call_count = 0
        self.chat = self._ChatCompletions()
    
    class _ChatCompletions:
        def __init__(self):
            self.completions = self._Completions()
        
        class _Completions:
            def create(self, **kwargs):
                """Mock create completion"""
                response = MagicMock()
                message = MagicMock()
                message.content = "Mocked OpenAI response"
                
                choice = MagicMock()
                choice.message = message
                
                response.choices = [choice]
                response.usage = MagicMock(
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30
                )
                
                return response


class MockMongoDBClient:
    """Mock MongoDB Client"""
    
    def __init__(self):
        self.databases = {}
        self.connected = False
    
    def connect(self):
        """Mock connection"""
        self.connected = True
        return True
    
    def __getitem__(self, db_name):
        """Mock database access"""
        if db_name not in self.databases:
            self.databases[db_name] = MockMongoDatabase(db_name)
        return self.databases[db_name]
    
    def close(self):
        """Mock close connection"""
        self.connected = False


class MockMongoDatabase:
    """Mock MongoDB Database"""
    
    def __init__(self, name):
        self.name = name
        self.collections = {}
    
    def __getitem__(self, collection_name):
        """Mock collection access"""
        if collection_name not in self.collections:
            self.collections[collection_name] = MockMongoCollection(collection_name)
        return self.collections[collection_name]


class MockMongoCollection:
    """Mock MongoDB Collection"""
    
    def __init__(self, name):
        self.name = name
        self.documents = []
        self.insert_count = 0
    
    def find(self, query=None, **kwargs):
        """Mock find operation"""
        if query is None:
            return self.documents
        
        # Simple query matching
        results = []
        for doc in self.documents:
            match = True
            for key, value in query.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                results.append(doc)
        return results
    
    def find_one(self, query):
        """Mock find_one operation"""
        results = self.find(query)
        return results[0] if results else None
    
    def insert_one(self, document):
        """Mock insert_one operation"""
        self.insert_count += 1
        doc_id = f"mock_id_{self.insert_count}"
        document['_id'] = doc_id
        self.documents.append(document)
        
        result = MagicMock()
        result.inserted_id = doc_id
        return result
    
    def insert_many(self, documents):
        """Mock insert_many operation"""
        ids = []
        for doc in documents:
            result = self.insert_one(doc)
            ids.append(result.inserted_id)
        
        result = MagicMock()
        result.inserted_ids = ids
        return result
    
    def update_one(self, query, update, **kwargs):
        """Mock update_one operation"""
        doc = self.find_one(query)
        if doc:
            if '$set' in update:
                doc.update(update['$set'])
            
            result = MagicMock()
            result.modified_count = 1
            return result
        
        result = MagicMock()
        result.modified_count = 0
        return result
    
    def delete_one(self, query):
        """Mock delete_one operation"""
        doc = self.find_one(query)
        if doc:
            self.documents.remove(doc)
            result = MagicMock()
            result.deleted_count = 1
            return result
        
        result = MagicMock()
        result.deleted_count = 0
        return result
    
    def count_documents(self, query):
        """Mock count_documents"""
        return len(self.find(query))


class MockRequestsResponse:
    """Mock requests Response object"""
    
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.content = text.encode('utf-8')
    
    def json(self):
        """Return JSON data"""
        return self._json_data
    
    def raise_for_status(self):
        """Mock raise_for_status"""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code} Error")


class MockStableDiffusionAPI:
    """Mock Stable Diffusion WebUI API"""
    
    def __init__(self):
        self.call_count = 0
        self.last_prompt = None
    
    def txt2img(self, prompt, **kwargs):
        """Mock text-to-image generation"""
        self.call_count += 1
        self.last_prompt = prompt
        
        # Return mock base64 image
        return {
            "images": ["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="],
            "info": '{"prompt": "' + prompt + '"}',
            "parameters": kwargs
        }


class MockImgBBUploader:
    """Mock ImgBB Image Uploader"""
    
    def __init__(self):
        self.upload_count = 0
    
    def upload(self, image_data, **kwargs):
        """Mock image upload"""
        self.upload_count += 1
        
        return {
            "success": True,
            "data": {
                "url": "https://i.ibb.co/mock123/test.png",
                "display_url": "https://i.ibb.co/mock123/test.png",
                "delete_url": "https://ibb.co/mock123/delete"
            }
        }


class MockCacheManager:
    """Mock Cache Manager"""
    
    def __init__(self):
        self.cache = {}
        self.enabled = True
    
    def get(self, key):
        """Get from cache"""
        return self.cache.get(key)
    
    def set(self, key, value, ttl=None):
        """Set cache value"""
        self.cache[key] = value
        return True
    
    def delete(self, key):
        """Delete from cache"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self):
        """Clear all cache"""
        count = len(self.cache)
        self.cache.clear()
        return count


class MockDatabaseManager:
    """Mock Database Manager"""
    
    def __init__(self):
        self.data = {}
        self.enabled = True
    
    def query(self, table, filters=None):
        """Mock query"""
        if table not in self.data:
            return []
        
        if filters is None:
            return self.data[table]
        
        # Simple filtering
        results = []
        for item in self.data[table]:
            match = True
            for key, value in filters.items():
                if item.get(key) != value:
                    match = False
                    break
            if match:
                results.append(item)
        return results
    
    def insert(self, table, data):
        """Mock insert"""
        if table not in self.data:
            self.data[table] = []
        
        data['id'] = len(self.data[table]) + 1
        self.data[table].append(data)
        return data['id']
    
    def update(self, table, id, data):
        """Mock update"""
        if table not in self.data:
            return False
        
        for item in self.data[table]:
            if item.get('id') == id:
                item.update(data)
                return True
        return False
    
    def delete(self, table, id):
        """Mock delete"""
        if table not in self.data:
            return False
        
        self.data[table] = [item for item in self.data[table] if item.get('id') != id]
        return True


def create_mock_conversation(conv_id="conv_123", user_id="user_123"):
    """Create a mock conversation object"""
    return {
        "id": conv_id,
        "user_id": user_id,
        "title": "Test Conversation",
        "messages": [
            {
                "role": "user",
                "content": "Hello",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant",
                "content": "Hi there!",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


def create_mock_schema():
    """Create a mock database schema"""
    return """
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100),
        email VARCHAR(100),
        created_at TIMESTAMP
    );
    
    CREATE TABLE posts (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        title VARCHAR(200),
        content TEXT,
        created_at TIMESTAMP
    );
    """
