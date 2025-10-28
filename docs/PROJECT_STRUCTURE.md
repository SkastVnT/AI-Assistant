# 🏗️ AI Assistant - Project Structure

## Overview

Project được tổ chức theo **Generative AI Template** chuẩn, đảm bảo:
- ✅ Code organization rõ ràng
- ✅ Separation of concerns
- ✅ Easy maintenance và scalability
- ✅ Best practices cho production

---

## 📁 Root Structure

```
AI-Assistant/
├── config/                    # Hub Gateway configuration
│   ├── __init__.py
│   ├── model_config.py       # Service configurations
│   └── logging_config.py     # Logging setup
│
├── src/                       # Hub Gateway source code
│   ├── __init__.py
│   ├── hub.py                # Main application
│   ├── handlers/             # Request handlers
│   │   ├── __init__.py
│   │   └── error_handler.py # Error handling
│   └── utils/                # Utility functions
│       ├── __init__.py
│       ├── cache.py          # Caching utilities
│       ├── rate_limiter.py   # Rate limiting
│       └── token_counter.py  # Token counting
│
├── data/                      # Hub data storage
│   ├── cache/                # Response cache
│   ├── prompts/              # Prompt templates
│   └── outputs/              # Output files
│
├── examples/                  # Usage examples
│   ├── basic_completion.py   # Basic API usage
│   └── chain_prompts.py      # Service chaining
│
├── notebooks/                 # Jupyter notebooks
│   └── (analysis notebooks)
│
├── templates/                 # HTML templates
│   └── index.html            # Hub dashboard
│
├── logs/                      # Log files
│   └── hub.log
│
├── ChatBot/                   # ChatBot service →
├── Speech2Text Services/      # Speech2Text service →
├── Text2SQL Services/         # Text2SQL service →
│
├── hub.py                     # Entry point
├── setup.py                   # Package setup
├── requirements.txt           # Dependencies
├── Dockerfile                 # Docker configuration
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
├── LICENSE                    # MIT License
├── README.md                  # Main documentation
├── HUB_README.md             # Hub detailed docs
├── QUICKSTART.md             # Quick start guide
└── PROJECT_STRUCTURE.md      # This file
```

---

## 🤖 ChatBot Service Structure

```
ChatBot/
├── config/                    # Configuration files
│   ├── __init__.py
│   ├── model_config.py       # LLM configurations
│   └── prompt_templates.py   # System prompts
│
├── src/                       # Source code
│   ├── __init__.py
│   ├── llm/                  # LLM clients
│   │   ├── __init__.py
│   │   ├── base_client.py    # Base LLM client
│   │   ├── gemini_client.py  # Gemini client
│   │   ├── openai_client.py  # OpenAI client
│   │   └── deepseek_client.py # DeepSeek client
│   │
│   ├── prompt_engineering/   # Prompt management
│   │   ├── __init__.py
│   │   ├── templates.py      # Prompt templates
│   │   ├── few_shot.py       # Few-shot examples
│   │   └── chainer.py        # Prompt chaining
│   │
│   ├── handlers/             # Request handlers
│   │   ├── __init__.py
│   │   └── chat_handler.py   # Chat endpoint handler
│   │
│   └── utils/                # Utilities
│       ├── __init__.py
│       ├── logger.py         # Logging
│       └── validator.py      # Input validation
│
├── data/                      # Data storage
│   └── conversations/        # Chat histories
│
├── examples/                  # Usage examples
│   ├── simple_chat.py        # Simple chat example
│   └── multi_model.py        # Multi-model usage
│
├── notebooks/                 # Analysis notebooks
│
├── logs/                      # Log files
│
├── templates/                 # HTML templates
│   └── index.html            # Chat interface
│
├── app.py                     # Main application
├── requirements.txt           # Dependencies
├── .env.example              # Environment template
└── README.md                  # Service documentation
```

**Key Components:**
- `llm/` - LLM client implementations (Gemini, GPT, DeepSeek)
- `prompt_engineering/` - Prompt templates và management
- `data/conversations/` - Chat history storage

---

## 🎤 Speech2Text Service Structure

```
Speech2Text Services/
├── config/                    # Configuration files
│   ├── __init__.py
│   ├── model_config.py       # Model configurations
│   └── audio_config.py       # Audio processing settings
│
├── src/                       # Source code
│   ├── __init__.py
│   ├── models/               # Model wrappers
│   │   ├── __init__.py
│   │   ├── whisper_model.py  # Whisper wrapper
│   │   └── phowhisper_model.py # PhoWhisper wrapper
│   │
│   ├── processors/           # Audio processing
│   │   ├── __init__.py
│   │   ├── audio_processor.py # Audio preprocessing
│   │   └── diarization.py    # Speaker diarization
│   │
│   ├── handlers/             # Request handlers
│   │   ├── __init__.py
│   │   └── transcribe_handler.py
│   │
│   └── utils/                # Utilities
│       ├── __init__.py
│       └── file_utils.py     # File operations
│
├── data/                      # Data storage
│   ├── audio/                # Uploaded audio files
│   ├── outputs/              # Transcription results
│   └── cache/                # Model cache
│
├── examples/                  # Usage examples
│   └── transcribe_file.py    # File transcription example
│
├── notebooks/                 # Analysis notebooks
│   └── model_evaluation.ipynb
│
├── logs/                      # Log files
│
├── app/                       # Original app code (legacy)
│   └── web_ui.py             # Web interface
│
├── requirements.txt           # Dependencies
├── .env.example              # Environment template
└── README.md                  # Service documentation
```

**Key Components:**
- `models/` - Whisper và PhoWhisper model wrappers
- `processors/` - Audio preprocessing và diarization
- `data/audio/` - Uploaded audio files
- `data/outputs/` - Transcription results

---

## 💾 Text2SQL Service Structure

```
Text2SQL Services/
├── config/                    # Configuration files
│   ├── __init__.py
│   ├── model_config.py       # Gemini configuration
│   └── database_config.py    # Database schemas
│
├── src/                       # Source code
│   ├── __init__.py
│   ├── generator/            # SQL generation
│   │   ├── __init__.py
│   │   ├── base_generator.py # Base SQL generator
│   │   └── gemini_generator.py # Gemini-based generator
│   │
│   ├── validators/           # SQL validation
│   │   ├── __init__.py
│   │   └── sql_validator.py  # SQL syntax checker
│   │
│   ├── handlers/             # Request handlers
│   │   ├── __init__.py
│   │   └── query_handler.py  # Query endpoint handler
│   │
│   └── utils/                # Utilities
│       ├── __init__.py
│       ├── schema_parser.py  # Schema parsing
│       └── memory.py         # Query memory/history
│
├── data/                      # Data storage
│   ├── schemas/              # Database schemas
│   ├── queries/              # Generated queries
│   └── cache/                # Query cache
│
├── examples/                  # Usage examples
│   ├── simple_query.py       # Simple query generation
│   └── schema_learning.py    # Schema learning example
│
├── notebooks/                 # Analysis notebooks
│   └── query_analysis.ipynb  # Query analysis
│
├── logs/                      # Log files
│
├── knowledge_base/           # Knowledge base
│   └── memory/               # Query memory storage
│
├── app.py                     # Main application
├── requirements.txt           # Dependencies
├── .env.example              # Environment template
└── README.md                  # Service documentation
```

**Key Components:**
- `generator/` - SQL query generation with Gemini
- `validators/` - SQL syntax validation
- `knowledge_base/memory/` - Learning from query history
- `data/schemas/` - Database schema definitions

---

## 🔑 Key Design Principles

### 1. Separation of Concerns
- **config/**: All configuration in one place
- **src/**: Application logic
- **data/**: Data storage
- **examples/**: Usage demonstrations
- **notebooks/**: Analysis và experiments

### 2. Modularity
- Each service is self-contained
- Clear interfaces between components
- Easy to test và maintain

### 3. Scalability
- Services run independently
- Easy to add new services
- Hub Gateway for centralized routing

### 4. Best Practices
- Type hints for better IDE support
- Docstrings for documentation
- Error handling at all levels
- Logging for debugging

---

## 🚀 Running Services

### Hub Gateway
```bash
cd AI-Assistant
python hub.py
# Runs on http://localhost:3000
```

### ChatBot
```bash
cd "AI-Assistant/ChatBot"
python app.py
# Runs on http://localhost:5000
```

### Speech2Text
```bash
cd "AI-Assistant/Speech2Text Services/app"
python web_ui.py
# Runs on http://localhost:5001
```

### Text2SQL
```bash
cd "AI-Assistant/Text2SQL Services"
python app.py
# Runs on http://localhost:5002
```

### All Services at Once
```bash
# Windows
start_all.bat

# Linux/Mac
./start_all.sh
```

---

## 📦 Dependencies

Each service has its own `requirements.txt`:

- **Hub Gateway**: Flask, Flask-CORS, python-dotenv
- **ChatBot**: Flask, openai, google-generativeai
- **Speech2Text**: Flask, whisper, pyannote.audio, torch
- **Text2SQL**: Flask, google-generativeai, sqlparse

---

## 🔄 Migration Guide

### Old Structure → New Structure

**Before:**
```
Service/
├── app.py
├── utils.py
├── config.py
└── templates/
```

**After:**
```
Service/
├── config/
│   └── model_config.py
├── src/
│   ├── handlers/
│   └── utils/
├── data/
├── examples/
├── notebooks/
└── app.py
```

**Migration Steps:**
1. Create new directory structure
2. Move configuration → `config/`
3. Move business logic → `src/`
4. Move utilities → `src/utils/`
5. Update imports
6. Test functionality

---

## 📚 Documentation

- **README.md**: Project overview
- **HUB_README.md**: Hub Gateway detailed docs
- **QUICKSTART.md**: Quick start guide
- **PROJECT_STRUCTURE.md**: This file
- **Service READMEs**: Each service has its own README

---

## 🤝 Contributing

When adding new features:

1. **Configuration**: Add to `config/model_config.py`
2. **Business Logic**: Add to `src/`
3. **Utilities**: Add to `src/utils/`
4. **Examples**: Add to `examples/`
5. **Tests**: Add to `tests/` (future)
6. **Documentation**: Update relevant README

---

## 📝 Notes

- All services follow the same structure pattern
- Easy to understand and navigate
- Production-ready organization
- Follows Python best practices
- Based on Generative AI project template

---

**Last Updated**: October 28, 2025
**Version**: 2.0.0
**Template**: Generative AI Project Structure
