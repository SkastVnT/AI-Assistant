# 📐 DIAGRAM UPDATES - November 11, 2025

> **Comprehensive update of all system diagrams based on current codebase**  
> **Status:** ✅ Complete - Ready for integration into README.md

---

## 📋 Summary of Changes

### Updated Diagrams:
1. ✅ **Use Case Diagram** - Updated to 32 use cases (was 24)
2. ✅ **System Architecture** - Added MongoDB, Redis, expanded APIs
3. ✅ **Component Diagram** - Detailed service dependencies
4. ✅ **Database Design** - MongoDB Atlas + PostgreSQL + ClickHouse
5. ✅ **Deployment Diagram** - 5 options (Local → Kubernetes)

### Key Additions:
- **ChatBot v2.0 features:** Auto-file analysis, Stop generation, Message versions
- **Text2SQL v2.0 features:** AI Learning, Deep Thinking, Auto-gen questions
- **Speech2Text v3.6+:** Dual-model fusion, 98%+ accuracy
- **MongoDB Integration:** 6 collections for ChatBot
- **Extended APIs:** Google Search, GitHub, ImgBB cloud storage

---

## 🎯 Updated System Architecture (for README.md)

```mermaid
graph TB
    subgraph "🌐 Client Layer"
        Web[Web Browser<br/>Chrome/Firefox/Edge]
        Mobile[Mobile App<br/>Future React Native]
        API[API Clients<br/>Python/cURL/Postman]
    end
    
    subgraph "🎯 Gateway Layer"
        Hub[Hub Gateway<br/>Port 3000<br/>Flask Router]
        Auth[Authentication<br/>JWT Future]
        Limit[Rate Limiter<br/>Redis Future]
    end
    
    subgraph "⚙️ Service Layer"
        CB[ChatBot v2.0<br/>Port 5001<br/>Auto-Analysis + Stop]
        T2S[Text2SQL v2.0<br/>Port 5002<br/>AI Learning + Deep Think]
        S2T[Speech2Text v3.6+<br/>Port 7860<br/>Dual-Model 98pc]
        SD[Stable Diffusion<br/>Port 7861<br/>LoRA + VAE]
    end
    
    subgraph "💾 Data Layer"
        Mongo[(MongoDB Atlas<br/>ChatBot 6 Collections)]
        PG[(PostgreSQL<br/>Text2SQL 15 Tables)]
        CH[(ClickHouse<br/>Analytics OLAP)]
        FS[File Storage<br/>Local + Cloud]
        Redis[(Redis<br/>Cache Future)]
    end
    
    subgraph "🔌 External Services"
        Gemini[Gemini 2.0<br/>Primary FREE]
        GPT4[GPT-4<br/>Advanced]
        DeepSeek[DeepSeek<br/>Cost-effective]
        HF[HuggingFace<br/>Models]
        GSearch[Google Search]
        GitHub[GitHub API]
        ImgBB[ImgBB Storage]
    end
    
    Web --> Hub
    Mobile --> Hub
    API --> Hub
    
    Hub --> Auth
    Auth --> Limit
    
    Limit --> CB
    Limit --> T2S
    Limit --> S2T
    Limit --> SD
    
    CB --> Mongo
    CB --> FS
    CB --> Redis
    CB --> Gemini
    CB --> GPT4
    CB --> DeepSeek
    CB --> GSearch
    CB --> GitHub
    CB --> ImgBB
    CB -.Image Gen.-> SD
    
    T2S --> PG
    T2S --> CH
    T2S --> Redis
    T2S --> Gemini
    T2S --> GPT4
    
    S2T --> FS
    S2T --> HF
    
    SD --> FS
    SD --> HF
    SD --> ImgBB
    
    style Hub fill:#6366F1,stroke:#4F46E5,color:#fff
    style Auth fill:#10B981,stroke:#059669,color:#fff
    style Limit fill:#F59E0B,stroke:#D97706,color:#fff
    style CB fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style T2S fill:#3B82F6,stroke:#2563EB,color:#fff
    style S2T fill:#EF4444,stroke:#DC2626,color:#fff
    style SD fill:#EC4899,stroke:#DB2777,color:#fff
```

---

## 🔄 Service Integration Flow (Enhanced)

```mermaid
graph TB
    A[👤 User Request] --> B{🎯 Service Router}
    
    B -->|Chat + Files| C1[🤖 ChatBot v2.0]
    B -->|Natural Language| C2[📊 Text2SQL v2.0]
    B -->|Audio File| C3[🎙️ Speech2Text v3.6]
    B -->|Image Prompt| C4[🎨 Stable Diffusion]
    
    C1 -->|Auto-Analysis| D1[📎 File Processing]
    C1 -->|Stop Button| D2[⏹️ Keep Partial Output]
    C1 -->|Need Image| C4
    C4 -->|Generated Image| C1
    C1 -->|Save| E1[💾 MongoDB Atlas]
    
    C2 -->|Check KB| F1[📚 Knowledge Base]
    F1 -->|Found| C2
    C2 -->|Deep Think| F2[🧠 Enhanced Reasoning]
    C2 -->|Connect DB| F3[🔌 ClickHouse/Mongo]
    F3 -->|Execute| F4[📊 Query Results]
    
    C3 -->|Diarize| G1[👥 pyannote 3.1]
    G1 -->|Transcribe| G2[📝 Whisper + PhoWhisper]
    G2 -->|Enhance| G3[✨ Qwen 2.5]
    G3 -->|Export| G4[📥 TXT/JSON/Timeline]
    
    C4 -->|LoRA/VAE| H1[🎭 Style Models]
    C4 -->|Upload| H2[🖼️ ImgBB Cloud]
    
    E1 --> I[✅ Response to User]
    F4 --> I
    G4 --> I
    H2 --> I
    
    style B fill:#6366F1,stroke:#4F46E5,color:#fff
    style C1 fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style C2 fill:#3B82F6,stroke:#2563EB,color:#fff
    style C3 fill:#EF4444,stroke:#DC2626,color:#fff
    style C4 fill:#EC4899,stroke:#DB2777,color:#fff
    style I fill:#10B981,stroke:#059669,color:#fff
```

---

## 📊 ChatBot Processing Pipeline (v2.0 NEW)

```mermaid
graph TB
    A[👤 User Input] --> B{📎 Has File?}
    
    B -->|Yes - Upload| C[📁 File Validation<br/>Max 50MB]
    B -->|No - Text Only| D[💬 Text Processing]
    
    C -->|Valid| E[🤖 Auto-File Analysis<br/>No prompt needed]
    C -->|Invalid| F[❌ Error: Size/Type]
    
    E --> G{📝 File Type?}
    
    G -->|Code| H1[💻 Code Analysis<br/>Syntax + Issues + Tips]
    G -->|Document| H2[📄 Doc Analysis<br/>Summary + Q&A]
    G -->|Image| H3[🖼️ Image Recognition<br/>Description + OCR]
    
    H1 --> I[📊 AI Response]
    H2 --> I
    H3 --> I
    D --> I
    
    I --> J{⏹️ Stop Pressed?}
    
    J -->|No| K[✅ Full Response]
    J -->|Yes| L[⏸️ Partial Response<br/>Keep Output]
    
    K --> M[💾 Save to MongoDB]
    L --> M
    
    M --> N{🎨 Generate Image?}
    
    N -->|Yes| O[🔄 Call SD API]
    N -->|No| P[📥 Export Options]
    
    O --> Q[🖼️ Image Ready]
    Q --> R[☁️ Upload to ImgBB]
    R --> P
    
    P --> S[👤 Display to User]
    
    style A fill:#10B981,stroke:#059669,color:#fff
    style B fill:#6366F1,stroke:#4F46E5,color:#fff
    style E fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style I fill:#3B82F6,stroke:#2563EB,color:#fff
    style J fill:#F59E0B,stroke:#D97706,color:#fff
    style M fill:#10B981,stroke:#059669,color:#fff
    style O fill:#EC4899,stroke:#DB2777,color:#fff
    style S fill:#10B981,stroke:#059669,color:#fff
```

---

## 🧠 Text2SQL AI Learning System (v2.0 NEW)

```mermaid
graph TB
    A[👤 User Question] --> B{📋 Has Schema?}
    
    B -->|No| C[📤 Upload Schema<br/>File or DB Connect]
    B -->|Yes| D[💡 Auto-Gen 5 Questions<br/>with SQL examples]
    
    C --> D
    
    D --> E{🔍 Search Knowledge Base}
    
    E -->|Found Match| F[⚡ Return Saved SQL<br/>0.3s Fast]
    E -->|Not Found| G{🧠 Deep Thinking?}
    
    G -->|Yes| H[🤔 Enhanced Reasoning<br/>5-10s Complex]
    G -->|No| I[🤖 Standard Gen<br/>2-3s Simple]
    
    H --> J[📝 Generated SQL]
    I --> J
    
    J --> K[👤 Show to User]
    
    K --> L{👍 Feedback}
    
    L -->|Correct ✅| M[💾 Save to KB<br/>AI Learns]
    L -->|Wrong ❌| N[🔄 Regenerate]
    L -->|Skip| O[📊 Execute if DB Connected]
    
    M --> O
    N --> G
    
    O --> P[📈 Display Results]
    
    style A fill:#10B981,stroke:#059669,color:#fff
    style E fill:#6366F1,stroke:#4F46E5,color:#fff
    style F fill:#10B981,stroke:#059669,color:#fff
    style G fill:#F59E0B,stroke:#D97706,color:#fff
    style H fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style M fill:#3B82F6,stroke:#2563EB,color:#fff
    style P fill:#10B981,stroke:#059669,color:#fff
```

---

## 🎙️ Speech2Text Dual-Model Pipeline (v3.6+ NEW)

```mermaid
graph TB
    A[🎤 Audio Upload<br/>MP3/WAV/M4A/FLAC] --> B[🔊 Preprocessing<br/>16kHz Mono WAV]
    
    B --> C[⚡ Voice Activity Detection<br/>Silero VAD<br/>30-50% speedup]
    
    C --> D[👥 Speaker Diarization<br/>pyannote.audio 3.1<br/>95-98% accuracy]
    
    D --> E{🔄 Parallel Processing}
    
    E --> F1[🌍 Whisper large-v3<br/>99 languages<br/>Global ASR]
    E --> F2[🇻🇳 PhoWhisper-large<br/>Vietnamese specialist<br/>98%+ accuracy]
    
    F1 --> G[🤝 Model Fusion<br/>Smart combination]
    F2 --> G
    
    G --> H[✨ Qwen Enhancement<br/>Grammar + Punctuation<br/>Speaker labels]
    
    H --> I{📥 Export Format}
    
    I -->|Timeline| J1[📊 Timeline TXT<br/>with timestamps]
    I -->|Speaker| J2[👥 Speaker-separated<br/>Role labels]
    I -->|JSON| J3[🗂️ JSON Metadata<br/>full details]
    
    J1 --> K[✅ Download Results]
    J2 --> K
    J3 --> K
    
    style A fill:#10B981,stroke:#059669,color:#fff
    style C fill:#F59E0B,stroke:#D97706,color:#fff
    style D fill:#EC4899,stroke:#DB2777,color:#fff
    style E fill:#6366F1,stroke:#4F46E5,color:#fff
    style G fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style H fill:#3B82F6,stroke:#2563EB,color:#fff
    style K fill:#10B981,stroke:#059669,color:#fff
```

---

## 🗄️ Database Architecture (Complete)

```mermaid
graph TB
    subgraph "ChatBot Data - MongoDB Atlas"
        M1[conversations<br/>chat metadata + settings]
        M2[messages<br/>user + AI messages + files]
        M3[chatbot_memory<br/>AI learning + tags]
        M4[uploaded_files<br/>file tracking + analysis]
        M5[users<br/>user accounts future]
        M6[user_settings<br/>preferences]
    end
    
    subgraph "Text2SQL Data - PostgreSQL"
        P1[schemas<br/>uploaded DB schemas]
        P2[knowledge_base<br/>learned SQL queries]
        P3[query_history<br/>generation logs]
        P4[feedback<br/>user ratings]
        P5[db_connections<br/>saved connections]
    end
    
    subgraph "Analytics - ClickHouse"
        C1[query_logs<br/>execution metrics]
        C2[performance_stats<br/>benchmarks]
        C3[user_analytics<br/>usage patterns]
    end
    
    subgraph "File Storage"
        F1[Local Storage<br/>ChatBot/Storage]
        F2[Cloud Storage<br/>ImgBB/PostImages]
        F3[Audio Files<br/>Speech2Text/results]
        F4[SD Outputs<br/>Generated images]
    end
    
    M1 --> M2
    M2 --> M3
    M2 --> M4
    M5 --> M6
    
    P1 --> P2
    P2 --> P3
    P3 --> P4
    P1 --> P5
    
    P3 --> C1
    C1 --> C2
    C2 --> C3
    
    M2 -.files.-> F1
    M2 -.images.-> F2
    P1 -.schemas.-> F1
    
    style M1 fill:#10B981,stroke:#059669,color:#fff
    style M2 fill:#10B981,stroke:#059669,color:#fff
    style M3 fill:#10B981,stroke:#059669,color:#fff
    style P1 fill:#3B82F6,stroke:#2563EB,color:#fff
    style P2 fill:#3B82F6,stroke:#2563EB,color:#fff
    style C1 fill:#F59E0B,stroke:#D97706,color:#fff
    style F2 fill:#EC4899,stroke:#DB2777,color:#fff
```

---

## 📈 Statistics Summary

| Category | Count | Details |
|:---------|:------|:--------|
| **Services** | 6 | Hub + ChatBot + Text2SQL + Speech2Text + SD + Admin |
| **Use Cases** | 32 | Comprehensive coverage |
| **AI Models** | 10+ | Gemini, GPT-4, Whisper, PhoWhisper, Qwen, SD, etc. |
| **Databases** | 3 types | MongoDB Atlas, PostgreSQL, ClickHouse |
| **Collections/Tables** | 20+ | 6 MongoDB + 15+ PostgreSQL |
| **API Endpoints** | 70+ | RESTful APIs across services |
| **External APIs** | 8+ | Gemini, OpenAI, HF, Search, GitHub, ImgBB |
| **Deployment Options** | 5 | Local, Docker, Azure, AWS, K8s |
| **Total Documentation** | 18 diagrams | Complete system coverage |

---

## 🔧 Implementation Notes

### ChatBot v2.0 Features
- ✅ Auto-file analysis (up to 50MB)
- ✅ Stop generation mid-response
- ✅ Message version history
- ✅ Full-screen ChatGPT-like UI
- ✅ Smart storage management (5 recent chats)
- ✅ MongoDB Atlas integration (6 collections)
- ✅ Image cloud upload (ImgBB)

### Text2SQL v2.0 Features
- ✅ AI Learning from feedback
- ✅ Knowledge Base with semantic search
- ✅ Auto-generate 5 sample questions
- ✅ Deep Thinking mode for complex queries
- ✅ Multi-database support (ClickHouse, MongoDB, PostgreSQL)
- ✅ Deploy FREE on Render.com
- ✅ Vietnamese + English support

### Speech2Text v3.6+ Features
- ✅ Dual-model fusion (Whisper + PhoWhisper)
- ✅ 95-98% diarization accuracy
- ✅ 98%+ Vietnamese transcription
- ✅ VAD for 30-50% speedup
- ✅ Qwen AI enhancement
- ✅ Professional WebUI with real-time progress
- ✅ Multi-format export (TXT/JSON/Timeline)

### Stable Diffusion Features
- ✅ AUTOMATIC1111 WebUI
- ✅ Text-to-Image + Image-to-Image
- ✅ 100+ LoRA models
- ✅ VAE support
- ✅ ControlNet integration
- ✅ REST API enabled
- ✅ CUDA 12.1 optimized

---

## 🚀 Next Steps

1. ✅ **Diagram Updates Complete** - All diagrams updated in `/diagram/`
2. ⏳ **README.md Integration** - Manually integrate diagrams (encoding issues)
3. ⏳ **Class Diagram Expansion** - Detail 50+ classes
4. ⏳ **Sequence Diagrams** - Add 2 more workflows
5. ⏳ **API Documentation** - Complete 70+ endpoint docs

---

<div align="center">

**📐 Documentation Updated: November 11, 2025**

[⬅️ Back to Diagram Index](README.md) | [📖 Main README](../README.md)

</div>
