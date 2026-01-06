# 4️⃣ CLASS DIAGRAM - ChatBot Service với MongoDB

> **Biểu đồ lớp hệ thống ChatBot AI-Assistant**  
> Cấu trúc OOP với MongoDB integration và AI model management

---

## 📋 Mô tả

Class Diagram thể hiện:
- **Core Classes:** Flask app, MongoDB client, AI models
- **Database Helpers:** ConversationDB, MessageDB, MemoryDB, FileDB
- **Utilities:** Cache, Streaming, File upload, Image upload
- **Relationships:** Inheritance, Composition, Aggregation

---

## 🎯 Kiến trúc phân lớp (Layered Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                            │
│                     (Flask Web App)                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                             │
│          (Business Logic & Service Orchestration)               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   DATA ACCESS LAYER                             │
│              (Repository Pattern - MongoDB)                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   DATABASE LAYER                                │
│                  (MongoDB Atlas - 6 Collections)                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 ROOT LEVEL - System Architecture Overview

### Tổng quan hệ thống theo các layer

```mermaid
graph TB
    subgraph "Layer 1: Presentation Layer"
        A[FlaskApp<br/>Web Application Controller]
    end
    
    subgraph "Layer 2: Application/Business Logic Layer"
        B[AIModelManager<br/>AI Service Orchestrator]
        C[CacheManager<br/>Performance Cache]
        D[StreamingHandler<br/>Real-time SSE]
    end
    
    subgraph "Layer 3: Data Access Layer - Repository Pattern"
        E[MongoDBClient<br/>Singleton DB Connection]
        F[ConversationDB<br/>Conversations Repository]
        G[MessageDB<br/>Messages Repository]
        H[MemoryDB<br/>AI Memory Repository]
        I[FileDB<br/>Files Repository]
        J[UserSettingsDB<br/>Settings Repository]
    end
    
    subgraph "Layer 4: External Services Integration"
        K[GROKModel<br/>GROK API]
        L[OpenAIModel<br/>GPT-4/GPT-4o API]
        M[DeepSeekModel<br/>DeepSeek API]
        N[LocalModelLoader<br/>Qwen/BloomVN Local]
        O[StableDiffusionClient<br/>Image Generation]
        P[PostImagesAPI<br/>Cloud Image Storage]
        Q[GoogleSearchAPI<br/>Web Search]
        R[GitHubAPI<br/>Code Search]
    end
    
    subgraph "Layer 5: Database - MongoDB Atlas"
        S[(conversations)]
        T[(messages)]
        U[(chatbot_memory)]
        V[(uploaded_files)]
        W[(users)]
        X[(user_settings)]
    end
    
    %% Layer 1 to Layer 2
    A -->|uses| B
    A -->|uses| C
    A -->|uses| D
    
    %% Layer 1 & 2 to Layer 3
    A -->|uses| E
    B -->|uses| E
    
    %% Layer 3 internal
    E -->|provides| F
    E -->|provides| G
    E -->|provides| H
    E -->|provides| I
    E -->|provides| J
    
    %% Layer 2 to Layer 4
    B -->|manages| K
    B -->|manages| L
    B -->|manages| M
    B -->|uses| N
    A -->|uses| O
    A -->|uses| P
    A -->|uses| Q
    A -->|uses| R
    
    %% Layer 3 to Layer 5
    F -->|CRUD| S
    G -->|CRUD| T
    H -->|CRUD| U
    I -->|CRUD| V
    J -->|CRUD| W
    J -->|CRUD| X
    
    style A fill:#667eea,stroke:#764ba2,stroke-width:3px,color:#fff
    style E fill:#f093fb,stroke:#f5576c,stroke-width:3px,color:#fff
```

---

## 🔷 LEVEL 1 - Presentation Layer (Flask Web App)

### FlaskApp - Main Application Controller

```mermaid
classDiagram
    class FlaskApp {
        <<Controller>>
        -app: Flask
        -secret_key: str
        -mongodb_client: MongoDBClient
        -model_manager: AIModelManager
        -cache: CacheManager
        -streaming: StreamingHandler
        -static_folder: Path
        
        +__init__()
        +setup_routes() void
        +run(host: str, port: int, debug: bool) void
        +before_request() void
        +after_request(response) Response
        
        %% Route handlers
        +index() str
        +chat() dict
        +upload_file() dict
        +generate_image() dict
        +save_memory() dict
        +export_pdf() bytes
    }
    
    class Flask {
        <<Framework>>
        +route(path, methods)
        +before_request(func)
        +after_request(func)
        +run(host, port, debug)
    }
    
    FlaskApp --> Flask : inherits/uses
    
    note for FlaskApp "Entry point của application\nXử lý HTTP requests/responses\nOrchestrate business logic"
```

**Vai trò:**
- ✅ Entry point của toàn bộ hệ thống
- ✅ Route HTTP requests đến đúng handlers
- ✅ Orchestrate các services (AI, DB, Cache)
- ✅ Return JSON responses cho frontend

**File thực tế:** `ChatBot/app.py`

---

## 🔷 LEVEL 1.1 - Application Layer (Business Logic & Services)

### Core Services

```mermaid
classDiagram
    class AIModelManager {
        <<Service>>
        -models: Dict~str,AIModel~
        -current_model: str
        -api_keys: Dict~str,str~
        
        +__init__()
        +switch_model(model_name: str) bool
        +get_available_models() List~str~
        +chat(messages: List, model: str, temp: float) str
        +chat_stream(messages: List, model: str) Generator
        +get_model_info(model_name: str) dict
        -_validate_model(model_name: str) bool
    }
    
    class CacheManager {
        <<Service>>
        -cache: Dict~str,CacheEntry~
        -ttl: int
        -enabled: bool
        -max_size: int
        
        +__init__(ttl: int)
        +get(key: str) any
        +set(key: str, value: any, ttl: int) void
        +delete(key: str) void
        +clear() void
        +get_stats() dict
        -_cleanup_expired() void
    }
    
    class StreamingHandler {
        <<Service>>
        -chunk_size: int
        -active_streams: Dict~str,Stream~
        
        +__init__(chunk_size: int)
        +stream_response(generator: Generator) Generator
        +create_sse_message(data: dict) str
        +handle_stop_signal(stream_id: str) void
        +get_active_count() int
    }
    
    FlaskApp --> AIModelManager : uses
    FlaskApp --> CacheManager : uses
    FlaskApp --> StreamingHandler : uses
    
    note for AIModelManager "Factory Pattern\nQuản lý 8+ AI models\nDynamic model switching"
    note for CacheManager "Singleton Pattern\nReduce API latency\nTTL-based expiration"
    note for StreamingHandler "Observer Pattern\nServer-Sent Events\nReal-time streaming"
```

---

## 🔷 LEVEL 2 - Data Access Layer (Repository Pattern)

### MongoDB Client & Repositories

```mermaid
classDiagram
    class MongoDBClient {
        <<Singleton>>
        -_instance: MongoDBClient
        -_client: MongoClient
        -_db: Database
        -uri: str
        -database_name: str
        
        +__new__(cls) MongoDBClient
        +connect() bool
        +close() void
        +db: Database
        +conversations: Collection
        +messages: Collection
        +memory: Collection
        +uploaded_files: Collection
        +users: Collection
        +settings: Collection
        -_create_indexes() void
        -_setup_validation() void
    }
    
    class ConversationDB {
        <<Repository>>
        -db: Database
        -collection: Collection
        
        +__init__(db: Database)
        +create(user_id, model, title) ObjectId
        +get_by_id(conversation_id) dict
        +get_by_user(user_id, limit) List~dict~
        +update(conversation_id, data) bool
        +delete(conversation_id) bool
        +archive(conversation_id) bool
        +increment_stats(conv_id, tokens) bool
        +get_statistics(user_id) dict
    }
    
    class MessageDB {
        <<Repository>>
        -db: Database
        -collection: Collection
        
        +__init__(db: Database)
        +add(conv_id, role, content) ObjectId
        +get_by_conversation(conv_id, limit) List~dict~
        +update(message_id, content) bool
        +delete(message_id) bool
        +add_image(msg_id, image_data) bool
        +add_file(msg_id, file_data) bool
        +create_version(msg_id, content, parent) ObjectId
        +get_versions(parent_id) List~dict~
    }
    
    class MemoryDB {
        <<Repository>>
        -db: Database
        -collection: Collection
        
        +__init__(db: Database)
        +save(user_id, question, answer, tags) ObjectId
        +search(user_id, query, tags) List~dict~
        +get_by_id(memory_id) dict
        +update_rating(memory_id, rating) bool
        +add_tags(memory_id, tags) bool
        +delete(memory_id) bool
        +get_popular(user_id, limit) List~dict~
    }
    
    class FileDB {
        <<Repository>>
        -db: Database
        -collection: Collection
        
        +__init__(db: Database)
        +save(user_id, conv_id, file_info) ObjectId
        +get_by_id(file_id) dict
        +get_by_conversation(conv_id) List~dict~
        +update_analysis(file_id, analysis) bool
        +delete(file_id) bool
        +get_statistics(user_id) dict
    }
    
    class UserSettingsDB {
        <<Repository>>
        -db: Database
        -collection: Collection
        
        +__init__(db: Database)
        +get(user_id) dict
        +update(user_id, settings) bool
        +get_default_model(user_id) str
        +update_chatbot(user_id, settings) bool
        +update_ui(user_id, settings) bool
    }
    
    MongoDBClient "1" -- "1" ConversationDB : provides
    MongoDBClient "1" -- "1" MessageDB : provides
    MongoDBClient "1" -- "1" MemoryDB : provides
    MongoDBClient "1" -- "1" FileDB : provides
    MongoDBClient "1" -- "1" UserSettingsDB : provides
    
    FlaskApp --> MongoDBClient : uses
    AIModelManager --> MongoDBClient : uses
    
    note for MongoDBClient "Singleton Pattern\nConnection Pooling\nIndex Management\nSchema Validation"
```

**File thực tế:** 
- `ChatBot/config/mongodb_config.py`
- `ChatBot/config/mongodb_helpers.py`

---

## 🔷 LEVEL 3 - AI Models Integration Layer

### AI Service Providers

```mermaid
classDiagram
    class AIModel {
        <<Interface>>
        +chat_completion(messages) str
        +chat_completion_stream(messages) Generator
        +count_tokens(text) int
    }
    
    class GROKModel {
        -api_key: str
        -model: GenerativeModel
        -generation_config: dict
        -safety_settings: dict
        
        +__init__(api_key, model_name)
        +generate_content(prompt, images) str
        +generate_stream(prompt) Generator
        +count_tokens(text) int
        +analyze_file(file_path) str
        +upload_file(file_path) File
    }
    
    class OpenAIModel {
        -api_key: str
        -client: OpenAI
        -model: str
        -organization: str
        
        +__init__(api_key, model_name)
        +chat_completion(messages) str
        +chat_stream(messages) Generator
        +count_tokens(text) int
        +create_embedding(text) List~float~
        +moderate_content(text) dict
    }
    
    class DeepSeekModel {
        -api_key: str
        -base_url: str
        -client: OpenAI
        -model: str
        
        +__init__(api_key)
        +chat_completion(messages) str
        +chat_stream(messages) Generator
        +count_tokens(text) int
    }
    
    class QwenModel {
        -api_key: str
        -model: str
        -endpoint: str
        
        +__init__(api_key, model_name)
        +chat_completion(messages) str
        +generate(prompt) str
        +count_tokens(text) int
    }
    
    class LocalModelLoader {
        -models_dir: Path
        -loaded_models: Dict~str,Model~
        -device: str
        -max_memory: int
        
        +__init__(models_dir)
        +load_model(model_name) Model
        +unload_model(model_name) bool
        +get_loaded() List~str~
        +generate(model_name, prompt) str
        -_check_memory() bool
        -_optimize_model(model) Model
    }
    
    AIModel <|.. GROKModel : implements
    AIModel <|.. OpenAIModel : implements
    AIModel <|.. DeepSeekModel : implements
    AIModel <|.. QwenModel : implements
    
    AIModelManager "1" o-- "*" GROKModel : manages
    AIModelManager "1" o-- "*" OpenAIModel : manages
    AIModelManager "1" o-- "*" DeepSeekModel : manages
    AIModelManager "1" o-- "*" QwenModel : manages
    AIModelManager "1" --> "1" LocalModelLoader : uses
    
    note for AIModel "Strategy Pattern\nPolymorphic interface\nInterchangeable algorithms"
```

**Supported Models:**
- GROK: `grok-3`
- OpenAI: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`
- DeepSeek: `deepseek-chat`, `deepseek-coder`
- Qwen: `qwen-turbo`, `qwen-plus`
- Local: `Qwen2.5-14B-Instruct`, `BloomVN-8B-chat`

---

## 🔷 LEVEL 4 - Utility & Helper Services

### File Management & Cloud Services

```mermaid
classDiagram
    class FileUploader {
        <<Utility>>
        -upload_dir: Path
        -max_size: int
        -allowed_types: Set~str~
        -temp_dir: Path
        
        +__init__(upload_dir, max_size)
        +upload(file: File) dict
        +validate(file: File) bool
        +save(file, filename) Path
        +delete(file_path) bool
        +get_info(file_path) dict
        -_generate_filename() str
        -_check_mime_type(file) str
    }
    
    class ImageUploader {
        <<Utility>>
        -storage_dir: Path
        -cloud_service: PostImagesAPI
        -fallback_service: ImgBBAPI
        -max_size: int
        
        +__init__(storage_dir)
        +save_local(image) Path
        +upload_to_cloud(image_path) dict
        +delete_from_cloud(delete_url) bool
        +get_info(image_path) dict
        -_compress(image) Image
        -_generate_thumbnail(image) Image
    }
    
    class PostImagesAPI {
        <<External Service>>
        -api_key: str
        -base_url: str
        -session: Session
        
        +__init__(api_key)
        +upload(image_path) dict
        +delete(delete_url) bool
        +get_image(image_url) bytes
        -_prepare_upload(image_path) dict
        -_handle_error(response) Exception
    }
    
    class StableDiffusionClient {
        <<External Service>>
        -api_url: str
        -timeout: int
        -default_params: dict
        
        +__init__(api_url)
        +text2img(prompt, params) bytes
        +img2img(image, prompt, params) bytes
        +check_status() bool
        +get_models() List~str~
        +get_loras() List~str~
        +set_model(model_name) bool
    }
    
    class GoogleSearchAPI {
        <<External Service>>
        -api_key: str
        -cse_id: str
        -session: Session
        
        +__init__(api_key, cse_id)
        +search(query, num) List~dict~
        +search_images(query) List~dict~
        -_format_results(results) List~dict~
    }
    
    class GitHubAPI {
        <<External Service>>
        -token: str
        -base_url: str
        -session: Session
        
        +__init__(token)
        +search_repos(query) List~dict~
        +search_code(query) List~dict~
        +search_issues(query) List~dict~
        +get_repo(owner, repo) dict
        -_make_request(endpoint, params) dict
    }
    
    FlaskApp --> FileUploader : uses
    FlaskApp --> ImageUploader : uses
    FlaskApp --> StableDiffusionClient : uses
    FlaskApp --> GoogleSearchAPI : uses
    FlaskApp --> GitHubAPI : uses
    
    ImageUploader --> PostImagesAPI : primary
    ImageUploader --> FileDB : saves metadata
    FileUploader --> FileDB : saves metadata
    
    note for ImageUploader "Hybrid Storage:\nLocal + Cloud\nFallback mechanism"
```

---

## 🔷 LEVEL 5 - Domain Models (Data Entities)

### MongoDB Document Models

```mermaid
classDiagram
    class Conversation {
        <<Entity>>
        +id: ObjectId
        +user_id: str
        +model: str
        +title: str
        +system_prompt: str
        +total_messages: int
        +total_tokens: int
        +is_archived: bool
        +metadata: dict
        +created_at: datetime
        +updated_at: datetime
        
        +to_dict() dict
        +from_dict(data) Conversation
        +validate() bool
    }
    
    class Message {
        <<Entity>>
        +id: ObjectId
        +conversation_id: ObjectId
        +role: str
        +content: str
        +images: List~Image~
        +files: List~File~
        +metadata: dict
        +version: int
        +parent_message_id: ObjectId
        +is_edited: bool
        +is_stopped: bool
        +created_at: datetime
        
        +to_dict() dict
        +from_dict(data) Message
        +add_image(image) void
        +add_file(file) void
    }
    
    class Memory {
        <<Entity>>
        +id: ObjectId
        +user_id: str
        +conversation_id: ObjectId
        +question: str
        +answer: str
        +context: str
        +images: List~dict~
        +rating: int
        +tags: List~str~
        +is_public: bool
        +metadata: dict
        +created_at: datetime
        
        +to_dict() dict
        +from_dict(data) Memory
        +add_tag(tag) void
        +update_rating(rating) void
    }
    
    class UploadedFile {
        <<Entity>>
        +id: ObjectId
        +user_id: str
        +conversation_id: ObjectId
        +original_filename: str
        +stored_filename: str
        +file_path: str
        +file_type: str
        +file_size: int
        +mime_type: str
        +analysis_result: str
        +metadata: dict
        +created_at: datetime
        
        +to_dict() dict
        +from_dict(data) UploadedFile
        +get_extension() str
    }
    
    class Image {
        <<Value Object>>
        +url: str
        +cloud_url: str
        +delete_url: str
        +caption: str
        +size: int
        +mime_type: str
        +generated: bool
        +service: str
        
        +to_dict() dict
        +from_dict(data) Image
    }
    
    class File {
        <<Value Object>>
        +name: str
        +path: str
        +type: str
        +size: int
        +mime_type: str
        +analysis_result: str
        
        +to_dict() dict
        +from_dict(data) File
    }
    
    Conversation "1" -- "*" Message : has
    Message "1" *-- "*" Image : contains
    Message "1" *-- "*" File : contains
    Memory "1" -- "0..1" Conversation : references
    UploadedFile "*" -- "1" Conversation : belongs to
    
    ConversationDB ..> Conversation : CRUD
    MessageDB ..> Message : CRUD
    MemoryDB ..> Memory : CRUD
    FileDB ..> UploadedFile : CRUD
    
    note for Conversation "Aggregate Root\nControls message lifecycle"
    note for Message "Entity with versioning\nSupports edit history"
    note for Image "Embedded in Message\nHybrid storage refs"
    note for File "Embedded in Message\nMetadata only"
```

---

## 📊 Chi tiết Classes

### 1️⃣ Core Application Classes

#### FlaskApp
**Vai trò:** Main application controller

```python
class FlaskApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.mongodb_client = MongoDBClient()
        self.model_manager = AIModelManager()
        self.cache = CacheManager()
        self.streaming = StreamingHandler()
        
    def setup_routes(self):
        """Register all routes"""
        @self.app.route('/')
        def index():
            return render_template('index.html')
            
        @self.app.route('/api/chat', methods=['POST'])
        def chat():
            # Handle chat request
            pass
```

**File thực tế:** `ChatBot/app.py`

---

#### MongoDBClient (Singleton)
**Vai trò:** Database connection và collection management

```python
class MongoDBClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def connect(self) -> bool:
        """Establish MongoDB connection"""
        self._client = MongoClient(MONGODB_URI, server_api=ServerApi('1'))
        self._db = self._client[DATABASE_NAME]
        self._create_indexes()
        return True
    
    def _create_indexes(self):
        """Create indexes for performance"""
        self.conversations.create_index([("user_id", 1)])
        self.conversations.create_index([("created_at", -1)])
        # ... more indexes
```

**File thực tế:** `ChatBot/config/mongodb_config.py`

---

### 2️⃣ Database Helper Classes

#### ConversationDB
**Vai trò:** CRUD operations cho conversations collection

```python
class ConversationDB:
    def create_conversation(
        self, 
        user_id: str, 
        model: str, 
        title: str = "New Chat"
    ) -> ObjectId:
        """Create new conversation"""
        doc = {
            "user_id": user_id,
            "model": model,
            "title": title,
            "total_messages": 0,
            "total_tokens": 0,
            "is_archived": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.collection.insert_one(doc)
        return result.inserted_id
    
    def get_user_conversations(
        self, 
        user_id: str, 
        limit: int = 20
    ) -> List[dict]:
        """Get user's conversations (latest first)"""
        return list(
            self.collection
            .find({"user_id": user_id, "is_archived": False})
            .sort("updated_at", -1)
            .limit(limit)
        )
```

**File thực tế:** `ChatBot/config/mongodb_helpers.py`

---

#### MessageDB
**Vai trò:** CRUD operations cho messages collection

```python
class MessageDB:
    def add_message(
        self,
        conversation_id: ObjectId,
        role: str,
        content: str,
        images: List[dict] = None,
        files: List[dict] = None,
        metadata: dict = None
    ) -> ObjectId:
        """Add message to conversation"""
        doc = {
            "conversation_id": conversation_id,
            "role": role,  # 'user' or 'assistant'
            "content": content,
            "images": images or [],
            "files": files or [],
            "metadata": metadata or {},
            "version": 1,
            "is_edited": False,
            "is_stopped": False,
            "created_at": datetime.utcnow()
        }
        result = self.collection.insert_one(doc)
        return result.inserted_id
    
    def edit_message(
        self,
        message_id: ObjectId,
        new_content: str,
        parent_id: ObjectId = None
    ) -> ObjectId:
        """Edit message (create new version)"""
        # Get original message
        original = self.collection.find_one({"_id": message_id})
        
        # Create new version
        new_doc = original.copy()
        new_doc.pop("_id")
        new_doc["content"] = new_content
        new_doc["version"] = original.get("version", 1) + 1
        new_doc["parent_message_id"] = parent_id or message_id
        new_doc["is_edited"] = True
        new_doc["created_at"] = datetime.utcnow()
        
        result = self.collection.insert_one(new_doc)
        return result.inserted_id
```

**File thực tế:** `ChatBot/config/mongodb_helpers.py`

---

#### MemoryDB
**Vai trò:** AI learning và memory management

```python
class MemoryDB:
    def save_memory(
        self,
        user_id: str,
        question: str,
        answer: str,
        tags: List[str] = None,
        rating: int = 0,
        conversation_id: ObjectId = None
    ) -> ObjectId:
        """Save conversation to memory"""
        doc = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "question": question,
            "answer": answer,
            "tags": tags or [],
            "rating": rating,
            "is_public": False,
            "created_at": datetime.utcnow()
        }
        result = self.collection.insert_one(doc)
        return result.inserted_id
    
    def search_memory(
        self,
        user_id: str,
        query: str = None,
        tags: List[str] = None,
        limit: int = 10
    ) -> List[dict]:
        """Search memories by query/tags"""
        filter_query = {"user_id": user_id}
        
        if tags:
            filter_query["tags"] = {"$in": tags}
        
        if query:
            # Text search
            filter_query["$text"] = {"$search": query}
        
        return list(
            self.collection
            .find(filter_query)
            .sort("created_at", -1)
            .limit(limit)
        )
```

**File thực tế:** `ChatBot/config/mongodb_helpers.py`

---

### 3️⃣ AI Model Classes

#### AIModelManager
**Vai trò:** Manage multiple AI models

```python
class AIModelManager:
    def __init__(self):
        self.models = {
            'grok-3': GROKModel(api_key=GROK_API_KEY),
            'grok-3-pro': GROKModel(api_key=GROK_API_KEY, model='grok-3'),,
            'gpt-4o': OpenAIModel(api_key=OPENAI_API_KEY, model='gpt-4o'),
            'gpt-4o-mini': OpenAIModel(api_key=OPENAI_API_KEY, model='gpt-4o-mini'),
            'deepseek-chat': DeepSeekModel(api_key=DEEPSEEK_API_KEY),
            'qwen-turbo': QwenModel(api_key=QWEN_API_KEY),
            # Local models
            'qwen-local': LocalModelLoader().load_model('Qwen2.5-14B-Instruct'),
            'bloom-vn': LocalModelLoader().load_model('BloomVN-8B-chat')
        }
        self.current_model = 'grok-3'
    
    def chat(
        self,
        messages: List[dict],
        model: str = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Union[str, Generator]:
        """Chat with specified model"""
        model_name = model or self.current_model
        model_instance = self.models.get(model_name)
        
        if not model_instance:
            raise ValueError(f"Model {model_name} not found")
        
        if stream:
            return model_instance.chat_completion_stream(messages)
        else:
            return model_instance.chat_completion(messages)
```

**File thực tế:** `ChatBot/src/model_manager.py` (cần tạo)

---

#### GROKModel
**Vai trò:** GROK API wrapper

```python
class GROKModel:
    def __init__(self, api_key: str, model: str = 'grok-3'):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.generation_config = {
            'temperature': 0.7,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 8192
        }
    
    def generate_content(
        self,
        prompt: str,
        images: List[Image] = None
    ) -> str:
        """Generate content with text/images"""
        if images:
            response = self.model.generate_content([prompt] + images)
        else:
            response = self.model.generate_content(prompt)
        return response.text
    
    def generate_content_stream(self, prompt: str) -> Generator:
        """Stream generated content"""
        response = self.model.generate_content(
            prompt,
            generation_config=self.generation_config,
            stream=True
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
    
    def analyze_file(self, file_path: str) -> str:
        """Analyze uploaded file"""
        # Upload file to GROK
        uploaded_file = genai.upload_file(file_path)
        
        # Generate analysis
        response = self.model.generate_content([
            "Analyze this file and provide a detailed summary:",
            uploaded_file
        ])
        
        return response.text
```

**File thực tế:** Integrated in `ChatBot/app.py`

---

### 4️⃣ Utility Classes

#### CacheManager
**Vai trò:** Response caching cho performance

```python
class CacheManager:
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl
        self.enabled = True
    
    def get(self, key: str) -> any:
        """Get cached value"""
        if not self.enabled:
            return None
        
        entry = self.cache.get(key)
        if not entry:
            return None
        
        # Check expiration
        if datetime.now() > entry['expires']:
            del self.cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: any, ttl: int = None):
        """Set cached value"""
        if not self.enabled:
            return
        
        self.cache[key] = {
            'value': value,
            'expires': datetime.now() + timedelta(seconds=ttl or self.ttl)
        }
```

**File thực tế:** `ChatBot/src/utils/cache_manager.py`

---

#### ImageUploader
**Vai trò:** Image upload to local + cloud

```python
class ImageUploader:
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.cloud_service = PostImagesAPI()
    
    def save_local(self, image: bytes, filename: str) -> Path:
        """Save image to local storage"""
        file_path = self.storage_dir / filename
        with open(file_path, 'wb') as f:
            f.write(image)
        return file_path
    
    def upload_to_cloud(self, image_path: Path) -> dict:
        """Upload image to PostImages"""
        result = self.cloud_service.upload(str(image_path))
        return {
            'url': str(image_path),
            'cloud_url': result['url'],
            'delete_url': result['delete_url'],
            'service': 'postimages',
            'size': image_path.stat().st_size
        }
```

**File thực tế:** `ChatBot/src/utils/imgbb_uploader.py` (tương tự)

---

## 🔗 Relationships

### Inheritance (Kế thừa)
Không có inheritance hierarchy phức tạp - sử dụng composition instead

### Composition (Has-A - Chặt)
```
FlaskApp HAS MongoDBClient (1:1)
FlaskApp HAS AIModelManager (1:1)
FlaskApp HAS CacheManager (1:1)
MongoDBClient HAS ConversationDB (1:1)
MongoDBClient HAS MessageDB (1:1)
AIModelManager HAS GROKModel (1:N)
Message HAS Image (1:N)
Message HAS File (1:N)
```

### Aggregation (Uses-A - Lỏng)
```
ConversationDB USES Conversation (CRUD)
MessageDB USES Message (CRUD)
MemoryDB USES Memory (CRUD)
ImageUploader USES PostImagesAPI (upload)
FlaskApp USES StableDiffusionClient (tool)
FlaskApp USES GoogleSearchAPI (tool)
```

---

## 📈 Design Patterns

| Pattern | Sử dụng ở đâu | Mục đích |
|:--------|:--------------|:---------|
| **Singleton** | MongoDBClient | Đảm bảo chỉ 1 DB connection |
| **Factory** | AIModelManager | Create AI model instances |
| **Strategy** | AI Models (GROK/GPT/DeepSeek) | Interchangeable algorithms |
| **Repository** | ConversationDB, MessageDB, MemoryDB | Data access abstraction |
| **Facade** | FlaskApp | Simplified interface to complex subsystems |
| **Decorator** | Flask @route decorators | Add functionality to routes |
| **Observer** | StreamingHandler | Real-time updates (SSE) |

---

## 🚀 Class Interaction Example

### Scenario: User chats với AI và save to memory

```python
# 1. User sends message
@app.route('/api/chat', methods=['POST'])
def chat():
    # 2. Get or create conversation
    conv_db = ConversationDB(mongodb_client.db)
    conversation_id = conv_db.create_conversation(
        user_id=session['user_id'],
        model='grok-3',
        title='AI Chat'
    )
    
    # 3. Save user message
    msg_db = MessageDB(mongodb_client.db)
    msg_db.add_message(
        conversation_id=conversation_id,
        role='user',
        content=request.json['message']
    )
    
    # 4. Get AI response
    model_manager = AIModelManager()
    response = model_manager.chat(
        messages=[{'role': 'user', 'content': request.json['message']}],
        model='grok-3'
    )
    
    # 5. Save AI response
    msg_db.add_message(
        conversation_id=conversation_id,
        role='assistant',
        content=response
    )
    
    # 6. Update conversation stats
    conv_db.increment_message_count(
        conversation_id=conversation_id,
        tokens=count_tokens(response)
    )
    
    # 7. Save to memory (if user clicks "Save")
    memory_db = MemoryDB(mongodb_client.db)
    memory_db.save_memory(
        user_id=session['user_id'],
        question=request.json['message'],
        answer=response,
        tags=['ai-chat'],
        conversation_id=conversation_id
    )
    
    return jsonify({'response': response})
```

---

<div align="center">

**Total Classes:** 30+  
**Design Patterns:** 7  
**Database Collections:** 6

[⬅️ Back: Use Case Diagram](03_usecase_diagram.md) | [➡️ Next: ER Diagram](05_er_diagram.md)

</div>
