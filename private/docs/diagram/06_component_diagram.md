# 6️⃣ COMPONENT DIAGRAM

> **Biểu đồ thành phần hệ thống AI-Assistant**  
> Mô tả kiến trúc tổng thể, services, dependencies, và communication

---

## 📋 Mô tả

Component Diagram thể hiện:
- **Components:** 4 services + Hub Gateway + External dependencies
- **Interfaces:** RESTful APIs, WebSockets, File I/O
- **Dependencies:** Libraries, AI models, cloud services
- **Communication:** HTTP, WebSocket, gRPC (future)

---

## 🎯 System Architecture Overview

```mermaid
graph TB
    subgraph Client Layer
        WebUI[🌐 Web UI<br/>HTML/CSS/JS]
        MobileApp[📱 Mobile App<br/>React Native]
        API_Client[🔌 API Clients<br/>Python/cURL]
    end
    
    subgraph API Gateway Layer
        Hub[🎯 Hub Gateway<br/>Port 3000<br/>Flask]
        Auth[🔐 Authentication<br/>JWT/OAuth2]
        RateLimit[⚡ Rate Limiter<br/>Redis]
        LoadBalancer[⚖️ Load Balancer<br/>Nginx]
    end
    
    subgraph Service Layer
        ChatBot[🤖 ChatBot Service<br/>Port 5001<br/>Flask + AI Models]
        Text2SQL[📊 Text2SQL Service<br/>Port 5002<br/>Flask + Gemini]
        Speech2Text[🎙️ Speech2Text Service<br/>Port 7860<br/>Gradio + Models]
        StableDiff[🎨 Stable Diffusion<br/>Port 7861<br/>AUTOMATIC1111]
    end
    
    subgraph Data Layer
        PostgreSQL[(🗄️ PostgreSQL<br/>Main Database)]
        MongoDB[(🍃 MongoDB<br/>ChatBot Storage)]
        Redis[(⚡ Redis<br/>Cache & Queue)]
        FileStorage[📁 File Storage<br/>Local/S3]
    end
    
    subgraph External Services
        GeminiAPI[🔷 Google Gemini API]
        OpenAI_API[🟣 OpenAI GPT-4 API]
        DeepSeek[🔵 DeepSeek API]
        HuggingFace[🤗 HuggingFace Hub]
        GoogleSearch[🔍 Google Search API]
        GitHubAPI[🐙 GitHub API]
        ImgBB[🖼️ ImgBB Cloud Storage]
    end
    
    WebUI --> LoadBalancer
    MobileApp --> LoadBalancer
    API_Client --> LoadBalancer
    
    LoadBalancer --> Hub
    Hub --> Auth
    Hub --> RateLimit
    
    Auth --> ChatBot
    Auth --> Text2SQL
    Auth --> Speech2Text
    Auth --> StableDiff
    
    ChatBot --> PostgreSQL
    ChatBot --> MongoDB
    ChatBot --> Redis
    ChatBot --> FileStorage
    ChatBot --> GeminiAPI
    ChatBot --> OpenAI_API
    ChatBot --> DeepSeek
    ChatBot --> GoogleSearch
    ChatBot --> GitHubAPI
    ChatBot --> ImgBB
    ChatBot --> StableDiff
    
    Text2SQL --> PostgreSQL
    Text2SQL --> Redis
    Text2SQL --> GeminiAPI
    
    Speech2Text --> PostgreSQL
    Speech2Text --> FileStorage
    Speech2Text --> HuggingFace
    
    StableDiff --> FileStorage
    StableDiff --> HuggingFace
    
    style Hub fill:#6366F1,stroke:#4F46E5,color:#fff
    style ChatBot fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style Text2SQL fill:#3B82F6,stroke:#2563EB,color:#fff
    style Speech2Text fill:#EF4444,stroke:#DC2626,color:#fff
    style StableDiff fill:#EC4899,stroke:#DB2777,color:#fff
```

---

## 🧩 Component Details

### 1. 🎯 Hub Gateway Component

**Vai trò:** API Gateway & Service Orchestrator

```mermaid
graph TB
    subgraph Hub Gateway
        Router[🔀 Request Router]
        ServiceRegistry[📋 Service Registry]
        HealthCheck[💓 Health Monitor]
        Logger[📝 Request Logger]
        
        Router --> ServiceRegistry
        Router --> HealthCheck
        Router --> Logger
    end
    
    Clients[👥 Clients] --> Router
    Router --> ChatBot[🤖 ChatBot Service]
    Router --> Text2SQL[📊 Text2SQL Service]
    Router --> Speech2Text[🎙️ Speech2Text Service]
    Router --> StableDiff[🎨 Stable Diffusion]
```

**Dependencies:**
- **Framework:** Flask 3.0+
- **Routing:** Flask-RESTful
- **CORS:** Flask-CORS
- **Logging:** Python logging + File rotation

**Interfaces:**
```python
# Provided interfaces
GET  /health                    # Health check all services
POST /api/route                 # Route request to service
GET  /api/services              # List all services
GET  /api/logs                  # Get system logs

# Required interfaces
- ChatBot API: http://localhost:5001
- Text2SQL API: http://localhost:5002
- Speech2Text API: http://localhost:7860
- Stable Diffusion API: http://localhost:7861
```

**Current Implementation:**
- ✅ Basic routing
- ✅ Health check
- ⚠️ No authentication yet
- ⚠️ No rate limiting yet

---

### 2. 🤖 ChatBot Service Component

**Vai trò:** Multi-model AI conversational interface with file analysis

```mermaid
graph TB
    subgraph ChatBot Service
        API[Flask API Layer]
        Engine[ChatBot Engine]
        ModelMgr[Model Manager]
        FileMgr[File Manager]
        Memory[Memory System]
        ImageGen[Image Generator]
        SearchTool[Search Tools]
        
        API --> Engine
        Engine --> ModelMgr
        Engine --> FileMgr
        Engine --> Memory
        Engine --> ImageGen
        Engine --> SearchTool
    end
    
    API --> MongoDB[(MongoDB)]
    Memory --> MongoDB
    FileMgr --> FileStorage[(File Storage)]
    ImageGen --> StableDiff[Stable Diffusion API]
    SearchTool --> GoogleAPI[Google Search API]
    SearchTool --> GitHubAPI[GitHub API]
    ModelMgr --> GeminiAPI[Gemini API]
    ModelMgr --> OpenAI[OpenAI API]
    ModelMgr --> DeepSeek[DeepSeek API]
```

**Dependencies:**
```yaml
Core Framework:
  - Flask 3.0+
  - Flask-CORS
  - python-dotenv
  
AI Models:
  - google-generativeai (Gemini 2.0 Flash)
  - openai (GPT-4, GPT-3.5)
  - anthropic (Claude 3.5 - optional)
  
Database:
  - pymongo >= 4.6.0
  - dnspython >= 2.4.0
  
File Processing:
  - PyPDF2
  - Pillow (PIL)
  - python-magic
  - markdown-it-py
  
Image Generation:
  - requests (for SD API)
  
Search & Tools:
  - google-api-python-client
  - PyGithub
  
Export:
  - reportlab (PDF export)
  - weasyprint (alternative)
```

**Interfaces:**
```python
# Provided REST APIs
POST /chat                      # Send message to AI
POST /upload                    # Upload & analyze file
POST /stop-generation           # Stop AI generation
POST /api/generate-image        # Generate image with SD
GET  /api/conversations         # Get conversations
GET  /api/conversation/<id>     # Get conversation details
DELETE /api/conversation/<id>   # Delete conversation
GET  /api/models                # List available models
POST /api/export-pdf            # Export chat to PDF
GET  /api/search                # Google/GitHub search

# Required APIs
- MongoDB: mongodb+srv://...
- Gemini API: https://generativelanguage.googleapis.com
- OpenAI API: https://api.openai.com
- Stable Diffusion: http://localhost:7861/sdapi/v1
- Google Search: https://www.googleapis.com/customsearch
- GitHub: https://api.github.com
```

**File Structure:**
```
ChatBot/
├── app.py                      # Main Flask app
├── src/
│   ├── chatbot_engine.py       # Core engine
│   ├── model_manager.py        # AI model switcher
│   ├── file_handler.py         # File upload/analysis
│   └── tools/
│       ├── search_google.py
│       └── search_github.py
├── config/
│   ├── mongodb_config.py       # MongoDB client
│   ├── mongodb_helpers.py      # CRUD operations
│   └── mongodb_schema.py       # Schema docs
├── Storage/
│   ├── conversations/          # JSON files (backup)
│   ├── uploaded_files/         # User uploads
│   └── generated_images/       # SD images
└── templates/
    └── index.html              # WebUI
```

**Current Status:**
- ✅ Multi-model support (5+ models)
- ✅ Auto-file analysis (up to 50MB)
- ✅ Stop generation
- ✅ Message versioning
- ✅ MongoDB integration
- ✅ Image generation
- ✅ Google/GitHub search
- ✅ PDF export
- ⚠️ No streaming responses yet
- ⚠️ No voice input/output yet

---

### 3. 📊 Text2SQL Service Component

**Vai trò:** Natural Language to SQL Query Generation with AI Learning

```mermaid
graph TB
    subgraph Text2SQL Service
        API[Flask API Layer]
        SchemaParser[Schema Parser]
        KnowledgeBase[Knowledge Base]
        QueryGen[Query Generator]
        DBConnector[DB Connector]
        AILearner[AI Learning System]
        
        API --> SchemaParser
        API --> KnowledgeBase
        API --> QueryGen
        API --> DBConnector
        API --> AILearner
        
        QueryGen --> KnowledgeBase
        AILearner --> KnowledgeBase
    end
    
    SchemaParser --> ClickHouse[(ClickHouse)]
    SchemaParser --> MongoDB[(MongoDB)]
    SchemaParser --> PostgreSQL[(PostgreSQL)]
    
    DBConnector --> ClickHouse
    DBConnector --> MongoDB
    DBConnector --> PostgreSQL
    
    QueryGen --> GeminiAPI[Gemini API]
    
    KnowledgeBase --> LocalFiles[(JSON Files)]
```

**Dependencies:**
```yaml
Core Framework:
  - Flask 3.0+
  - Flask-CORS
  - python-dotenv
  
AI Models:
  - google-generativeai (Gemini 2.0 Flash)
  
Database Drivers:
  - clickhouse-driver
  - pymongo
  - psycopg2-binary (PostgreSQL)
  - mysql-connector-python
  
Schema Parsing:
  - sqlparse
  - json
  - pandas (for data preview)
  
Knowledge Base:
  - sentence-transformers (embeddings)
  - faiss-cpu (similarity search)
  
Utilities:
  - hashlib (schema hashing)
  - re (regex for SQL parsing)
```

**Interfaces:**
```python
# Provided REST APIs
POST /upload-schema             # Upload schema file
POST /parse-schema              # Parse schema from text
GET  /sample-questions          # Generate sample questions
POST /chat                      # Generate SQL from question
POST /execute-query             # Execute SQL query
POST /feedback                  # Save correct/wrong feedback
GET  /knowledge-base            # Get KB statistics
GET  /databases                 # List connected databases
POST /connect-database          # Add DB connection

# Required APIs
- Gemini API: https://generativelanguage.googleapis.com
- ClickHouse: tcp://localhost:9000
- MongoDB: mongodb://localhost:27017
- PostgreSQL: postgresql://localhost:5432
```

**File Structure:**
```
Text2SQL Services/
├── app_simple.py               # Main Flask app
├── src/
│   ├── schema_parser.py        # Parse schema
│   ├── query_generator.py      # Generate SQL
│   ├── knowledge_base.py       # AI learning
│   └── db_connector.py         # DB connections
├── data/
│   ├── knowledge_base/         # Saved queries
│   │   ├── clickhouse.jsonl
│   │   ├── mongodb.jsonl
│   │   └── postgresql.jsonl
│   └── schemas/                # Uploaded schemas
└── templates/
    └── index.html              # WebUI
```

**Current Status:**
- ✅ Multi-database support (ClickHouse, MongoDB, PostgreSQL, MySQL)
- ✅ AI learning system with Knowledge Base
- ✅ Sample question generation
- ✅ Deep thinking mode
- ✅ Vietnamese + English support
- ✅ Deploy on Render.com FREE tier
- ⚠️ No vector DB yet (using simple similarity)
- ⚠️ No query optimization suggestions

---

### 4. 🎙️ Speech2Text Service Component

**Vai trò:** Dual-model audio transcription with speaker diarization

```mermaid
graph TB
    subgraph Speech2Text Service
        GradioUI[Gradio Web UI]
        Preprocessor[Audio Preprocessor]
        Diarization[Speaker Diarization]
        WhisperEngine[Whisper Engine]
        PhoWhisperEngine[PhoWhisper Engine]
        Merger[Transcript Merger]
        Enhancer[Qwen Enhancer]
        
        GradioUI --> Preprocessor
        Preprocessor --> Diarization
        Diarization --> WhisperEngine
        Diarization --> PhoWhisperEngine
        WhisperEngine --> Merger
        PhoWhisperEngine --> Merger
        Merger --> Enhancer
    end
    
    WhisperEngine --> WhisperModel[(Whisper large-v3)]
    PhoWhisperEngine --> PhoWhisperModel[(PhoWhisper base)]
    Diarization --> PyannoteModel[(pyannote-diarization)]
    Enhancer --> QwenModel[(Qwen2.5-1.5B)]
    
    Enhancer --> FileStorage[(Output Files)]
```

**Dependencies:**
```yaml
Core Framework:
  - gradio >= 4.0
  - fastapi (Gradio uses)
  
Audio Processing:
  - librosa >= 0.10.0
  - soundfile >= 0.12.0
  - pydub >= 0.25.0
  - ffmpeg-python
  
ASR Models:
  - openai-whisper
  - transformers >= 4.36.0
  - torch >= 2.0.0
  - torchaudio
  
Diarization:
  - pyannote.audio >= 3.1.0
  - speechbrain >= 0.5.0
  
Enhancement:
  - transformers (Qwen2.5)
  
Utilities:
  - numpy
  - scipy
  - python-dotenv
```

**Interfaces:**
```python
# Gradio UI (Web Interface)
- Input: Audio file upload (MP3/WAV/M4A/FLAC)
- Output: Transcript with speaker labels
- Settings: Model selection, VAD, enhancement

# Internal Functions (Future REST API)
POST /transcribe                # Transcribe audio
GET  /models                    # List available models
GET  /transcription/<id>        # Get transcription result
DELETE /transcription/<id>      # Delete result
```

**File Structure:**
```
Speech2Text Services/
├── app.py                      # Gradio app
├── s2t/
│   ├── core/
│   │   ├── transcriber.py      # Whisper transcription
│   │   ├── diarization.py      # Speaker diarization
│   │   └── enhancer.py         # Qwen enhancement
│   └── utils/
│       ├── audio_utils.py      # Audio preprocessing
│       └── text_utils.py       # Text formatting
├── models/                     # Downloaded models
│   ├── whisper-large-v3/
│   ├── phowhisper-base/
│   ├── pyannote-diarization/
│   └── qwen2.5-1.5b/
├── output/                     # Transcription results
└── data/                       # Input audio files
```

**Current Status:**
- ✅ Dual-model fusion (Whisper + PhoWhisper)
- ✅ Speaker diarization (pyannote.audio)
- ✅ Vietnamese fine-tuned (PhoWhisper)
- ✅ AI enhancement (Qwen2.5)
- ✅ VAD optimization (Silero VAD)
- ✅ GPU acceleration (CUDA)
- ✅ Multiple audio formats
- ⚠️ No real-time streaming yet
- ⚠️ No custom vocabulary training

---

### 5. 🎨 Stable Diffusion Service Component

**Vai trò:** AI Image Generation (Text-to-Image, Image-to-Image)

```mermaid
graph TB
    subgraph Stable Diffusion WebUI
        GradioUI[Gradio Web Interface]
        API[REST API]
        ModelLoader[Model Loader]
        LoRAManager[LoRA Manager]
        VAELoader[VAE Loader]
        Sampler[Sampler Engine]
        Upscaler[Upscaler]
        ControlNet[ControlNet]
        
        GradioUI --> ModelLoader
        API --> ModelLoader
        ModelLoader --> LoRAManager
        ModelLoader --> VAELoader
        ModelLoader --> Sampler
        Sampler --> Upscaler
        Sampler --> ControlNet
    end
    
    ModelLoader --> SDModels[(SD Models<br/>v1.5/SDXL)]
    LoRAManager --> LoRAFiles[(LoRA Models<br/>100+)]
    VAELoader --> VAEFiles[(VAE Models)]
    ControlNet --> ControlNetModels[(ControlNet<br/>15+ models)]
    
    Upscaler --> Output[(Generated Images)]
```

**Dependencies:**
```yaml
Core Framework:
  - gradio >= 3.50.0
  - fastapi
  
SD Core:
  - torch >= 2.0.0
  - torchvision
  - diffusers >= 0.21.0
  - transformers >= 4.36.0
  
Acceleration:
  - xformers >= 0.0.21
  - accelerate >= 0.24.0
  
Image Processing:
  - opencv-python
  - Pillow >= 10.0.0
  - numpy
  
Models:
  - safetensors >= 0.4.0
  - omegaconf
  
Utilities:
  - tqdm
  - einops
  - kornia
```

**Interfaces:**
```python
# Gradio UI
- Text-to-Image tab
- Image-to-Image tab
- Extras (upscaling, face restoration)
- Settings

# REST API (AUTOMATIC1111 API)
POST /sdapi/v1/txt2img          # Text to image
POST /sdapi/v1/img2img          # Image to image
GET  /sdapi/v1/sd-models        # List models
POST /sdapi/v1/options          # Set options
GET  /sdapi/v1/progress         # Get progress
POST /sdapi/v1/interrupt        # Stop generation
GET  /sdapi/v1/loras            # List LoRAs
GET  /sdapi/v1/samplers         # List samplers
```

**File Structure:**
```
stable-diffusion-webui/
├── webui.py                    # Main entry point
├── modules/
│   ├── api/                    # REST API
│   ├── processing.py           # Image generation
│   ├── sd_models.py            # Model management
│   ├── sd_samplers.py          # Samplers
│   └── extras.py               # Upscaling, etc.
├── extensions/
│   └── sd-webui-controlnet/    # ControlNet
├── models/
│   ├── Stable-diffusion/       # Base models
│   ├── Lora/                   # LoRA models
│   ├── VAE/                    # VAE models
│   └── ControlNet/             # ControlNet models
└── outputs/
    └── txt2img-images/         # Generated images
```

**Current Status:**
- ✅ Text-to-Image generation
- ✅ Image-to-Image modification
- ✅ LoRA support (100+ models)
- ✅ VAE support
- ✅ ControlNet (15+ models)
- ✅ Multiple samplers
- ✅ Upscaling (4x)
- ✅ Face restoration
- ✅ REST API enabled
- ✅ CUDA 12.1 optimized
- ⚠️ No batch processing UI
- ⚠️ No training support yet

---

## 🔗 Communication Patterns

### 1. Client-Server (REST APIs)

```mermaid
sequenceDiagram
    Client->>Hub: HTTP Request
    Hub->>Service: Forward request
    Service->>External API: Call if needed
    External API-->>Service: Response
    Service-->>Hub: JSON response
    Hub-->>Client: JSON response
```

**Protocol:** HTTP/1.1  
**Format:** JSON  
**Authentication:** None (future: JWT)  
**Rate Limit:** None (future: Redis-based)

---

### 2. Service-to-Service (Internal)

```mermaid
sequenceDiagram
    ChatBot->>Stable Diffusion: POST /sdapi/v1/txt2img
    Stable Diffusion-->>ChatBot: {image_url, seed}
    ChatBot->>ImgBB: Upload image
    ImgBB-->>ChatBot: {cloud_url}
    ChatBot->>MongoDB: Save metadata
```

**Protocol:** HTTP (localhost)  
**Format:** JSON  
**Timeout:** 60s (configurable)

---

### 3. Database Access

```mermaid
graph LR
    Service[Service] --> Driver[DB Driver]
    Driver --> Pool[Connection Pool]
    Pool --> DB[(Database)]
    
    style Service fill:#8B5CF6,color:#fff
    style DB fill:#3B82F6,color:#fff
```

**Pattern:** Connection Pooling  
**Libraries:** pymongo, psycopg2, clickhouse-driver  
**Max Connections:** 10-50 per service

---

## 📦 Deployment Architecture

### Option 1: Local Development (Current)

```mermaid
graph TB
    subgraph Local Machine
        subgraph Python Environments
            venv1[venv_chatbot]
            venv2[Text2SQL]
            venv3[venv_s2t]
            venv4[venv_sd]
        end
        
        subgraph Processes
            P1[ChatBot :5001]
            P2[Text2SQL :5002]
            P3[Speech2Text :7860]
            P4[Stable Diffusion :7861]
            P5[Hub :3000]
        end
        
        subgraph Data
            Files[(Local Files)]
            MongoDB[(MongoDB Atlas)]
        end
        
        venv1 --> P1
        venv2 --> P2
        venv3 --> P3
        venv4 --> P4
        
        P1 --> Files
        P1 --> MongoDB
        P2 --> Files
        P3 --> Files
        P4 --> Files
    end
    
    Browser[🌐 Browser] --> P5
    P5 --> P1
    P5 --> P2
    P5 --> P3
    P5 --> P4
```

**Pros:** ✅ Easy setup, full control  
**Cons:** ❌ Not scalable, manual process management

---

### Option 2: Docker Compose (Recommended)

```mermaid
graph TB
    subgraph Docker Host
        subgraph Containers
            C1[chatbot:5001]
            C2[text2sql:5002]
            C3[speech2text:7860]
            C4[stable-diffusion:7861]
            C5[hub:3000]
            C6[nginx:80]
            C7[redis:6379]
        end
        
        subgraph Volumes
            V1[chatbot_data]
            V2[text2sql_data]
            V3[speech2text_data]
            V4[sd_models]
        end
        
        Network[docker_network]
        
        C1 -.-> Network
        C2 -.-> Network
        C3 -.-> Network
        C4 -.-> Network
        C5 -.-> Network
        C6 -.-> Network
        C7 -.-> Network
        
        C1 --> V1
        C2 --> V2
        C3 --> V3
        C4 --> V4
    end
    
    Internet[🌐 Internet] --> C6
    C6 --> C5
```

**Pros:** ✅ Easy deployment, isolation, portability  
**Cons:** ⚠️ Resource overhead, learning curve

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  hub:
    build: ./src
    ports: ["3000:3000"]
    depends_on: [chatbot, text2sql]
  
  chatbot:
    build: ./ChatBot
    ports: ["5001:5001"]
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - chatbot_data:/app/Storage
  
  # ... other services
```

---

### Option 3: Cloud Deployment (Production)

```mermaid
graph TB
    subgraph Cloud Provider - Azure/AWS/GCP
        subgraph Load Balancer
            LB[Azure Load Balancer]
        end
        
        subgraph App Services
            AS1[ChatBot VM]
            AS2[Text2SQL VM]
            AS3[Speech2Text VM]
            AS4[Stable Diffusion GPU VM]
        end
        
        subgraph Storage
            Blob[Azure Blob Storage]
            SQL[Azure PostgreSQL]
            Cache[Azure Redis Cache]
        end
        
        subgraph CDN
            CDN[Azure CDN]
        end
        
        LB --> AS1
        LB --> AS2
        LB --> AS3
        LB --> AS4
        
        AS1 --> SQL
        AS1 --> Blob
        AS1 --> Cache
        
        AS2 --> SQL
        AS2 --> Cache
        
        AS3 --> Blob
        AS4 --> Blob
        
        CDN --> Blob
    end
    
    Users[🌍 Users] --> CDN
    Users --> LB
```

**Estimated Cost (Azure - 1K users):**
- VMs: $200-500/month
- Storage: $50-100/month
- Database: $100-200/month
- Bandwidth: $50-100/month
- **Total:** ~$400-900/month

---

## 🔐 Security Components

### 1. Authentication & Authorization (Future)

```mermaid
graph TB
    User[👤 User] --> Login[🔐 Login]
    Login --> JWT[Generate JWT]
    JWT --> Client[Client stores token]
    Client --> Request[Authenticated Request]
    Request --> Verify[Verify JWT]
    Verify --> Service[Access Service]
    
    style Login fill:#10B981,color:#fff
    style Verify fill:#EF4444,color:#fff
```

**Implementation Plan:**
- Library: `PyJWT`, `Flask-JWT-Extended`
- Token expiry: 24 hours
- Refresh token: 7 days

---

### 2. Rate Limiting (Future)

```mermaid
graph TB
    Request[📨 Request] --> Redis[⚡ Redis Counter]
    Redis --> Check{Under limit?}
    Check -->|Yes| Allow[✅ Process]
    Check -->|No| Reject[❌ 429 Too Many Requests]
    
    style Allow fill:#10B981,color:#fff
    style Reject fill:#EF4444,color:#fff
```

**Limits:**
- Free tier: 100 req/hour
- Paid tier: 1000 req/hour
- Enterprise: Unlimited

---

## 📈 Scalability Strategies

### Horizontal Scaling

```mermaid
graph TB
    LB[Load Balancer] --> S1[Service Instance 1]
    LB --> S2[Service Instance 2]
    LB --> S3[Service Instance 3]
    
    S1 --> DB[(Shared Database)]
    S2 --> DB
    S3 --> DB
    
    S1 --> Cache[(Redis Cluster)]
    S2 --> Cache
    S3 --> Cache
```

**Benefits:**
- Handle more concurrent users
- Fault tolerance (if one instance fails)
- Auto-scaling based on load

---

## 📝 Monitoring & Observability (Future)

### Proposed Stack:

```mermaid
graph TB
    subgraph Services
        S1[ChatBot]
        S2[Text2SQL]
        S3[Speech2Text]
        S4[Stable Diffusion]
    end
    
    subgraph Monitoring
        Prometheus[📊 Prometheus<br/>Metrics Collection]
        Grafana[📈 Grafana<br/>Visualization]
        Loki[📝 Loki<br/>Log Aggregation]
        Jaeger[🔍 Jaeger<br/>Distributed Tracing]
    end
    
    S1 --> Prometheus
    S2 --> Prometheus
    S3 --> Prometheus
    S4 --> Prometheus
    
    Prometheus --> Grafana
    
    S1 --> Loki
    S2 --> Loki
    S3 --> Loki
    S4 --> Loki
    
    S1 --> Jaeger
    S2 --> Jaeger
    S3 --> Jaeger
    S4 --> Jaeger
```

**Metrics to track:**
- Request rate (req/sec)
- Response time (p50, p95, p99)
- Error rate (%)
- CPU/Memory usage
- Active connections
- Model inference time

---

## 🎯 Summary

| Aspect | Count | Status |
|:-------|:------|:-------|
| **Core Services** | 4 | ✅ Production |
| **Gateway** | 1 | ⚠️ Basic |
| **Databases** | 3 | ✅ Active |
| **External APIs** | 7 | ✅ Integrated |
| **Deployment Options** | 3 | ✅ Documented |
| **Authentication** | 0 | 🚧 Planned |
| **Monitoring** | 0 | 🚧 Planned |

---

<div align="center">

[⬅️ Previous: ER Diagram](05_er_diagram.md) | [Back to Index](README.md) | [➡️ Next: Activity Diagram](07_activity_diagram.md)

</div>
