# 📄 Document Intelligence Service

> **AI-Powered Document Processing & OCR Service**  
> Vietnamese-optimized document understanding với FREE models (Gemini 2.0 Flash)

## 🎯 Features

### ✅ Phase 1.5 (Current - AI Enhanced)
- 📸 **OCR Text Extraction** - PaddleOCR Vietnamese support
- 🧠 **AI Document Analysis** - Gemini 2.0 Flash FREE integration
- 🏷️ **Auto Classification** - Intelligent document type detection
- 🔍 **Smart Extraction** - Extract key information with AI
- 📝 **AI Summarization** - Content summarization
- 💬 **Q&A over Documents** - Ask questions about content
- 🌐 **AI Translation** - Translate to 8+ languages
- 💡 **Insights Generation** - Deep document analysis
- 🖼️ **Image Upload** - Drag & drop interface
- 💾 **Export** - TXT, JSON formats

### 🚧 Phase 2 (Planned)
- 📊 **Table Extraction** - Detect and parse tables
- 📑 **Multi-page PDF** - Batch processing
- 📐 **Layout Analysis** - Structure understanding
- ⚡ **GPU Acceleration** - Faster processing

### 🔮 Phase 3 (Future)
- 🎯 **Named Entity Recognition** - Extract names, dates, numbers
- 📋 **Form Auto-fill** - Intelligent form completion
- 🔍 **Document Search** - Semantic search across documents
- 📸 **Camera Capture** - Direct capture support

## 🏗️ Architecture

```
Document Intelligence Service/
├── app.py                 # Main Flask application (v1.5.0)
├── .env                   # Environment config (AI keys)
├── config/
│   └── __init__.py       # Configuration with AI settings
├── src/
│   ├── ai/
│   │   ├── gemini_client.py    # Gemini 2.0 Flash integration
│   │   └── document_analyzer.py # AI document analysis
│   ├── ocr/
│   │   ├── paddle_ocr.py # PaddleOCR engine
│   │   └── processor.py  # OCR processing
│   └── utils/
│       ├── file_handler.py
│       └── format_converter.py
├── static/
│   ├── css/
│   │   └── style.css     # Modern UI with AI components
│   ├── js/
│   │   └── app.js        # Frontend with AI integration
│   └── uploads/          # Temporary uploads
├── templates/
│   └── index.html        # WebUI with AI features
├── output/               # Processed results
└── requirements.txt      # Includes google-generativeai
```

## 🚀 Quick Start

### 1. Setup Environment
```bash
cd "Document Intelligence Service"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure AI (Optional)
```bash
# Copy .env.example to .env
copy .env.example .env

# Edit .env and add your Gemini API key (FREE from https://ai.google.dev)
GEMINI_API_KEY=your_api_key_here
ENABLE_AI_ENHANCEMENT=True
```

**Note:** Service works without AI key (OCR only mode)

### 3. Run Service
```bash
python app.py
```

### 4. Open Browser
```
http://localhost:5003
```

## 🛠️ Tech Stack

| Component | Technology | Why |
|:----------|:-----------|:----|
| **AI Model** | Gemini 2.0 Flash Exp | FREE, fast, multilingual support |
| **OCR Engine** | PaddleOCR 2.7.3 | FREE, Vietnamese support, high accuracy |
| **Backend** | Flask 3.0.0 | Lightweight, easy integration |
| **Frontend** | HTML/CSS/JS | Modern responsive UI |
| **Image Processing** | Pillow/OpenCV | Standard tools |
| **PDF Handling** | PyMuPDF (fitz) | Fast PDF processing |

## 📊 Supported Formats

**Input:**
- 🖼️ Images: JPG, PNG, BMP, TIFF, WEBP
- 📄 Documents: PDF (will extract to images)
- 📸 Camera: Direct capture (Phase 2)

**Output:**
- 📝 Plain Text (TXT)
- 📊 JSON (structured data)
- 📑 Markdown (formatted)
- 📋 Excel (tables - Phase 2)

## 🤖 AI Features

### Document Classification
Automatically identify document types:
- ID Cards (CMND/CCCD)
- Invoices/Receipts
- Contracts
- Forms
- Letters
- And more...

### Smart Information Extraction
Extract key data with AI understanding:
- Names, dates, addresses
- Amounts, invoice numbers
- Key terms and clauses
- Custom fields

### AI Q&A
Ask questions about your documents:
- "Tên người trong document là gì?"
- "Invoice này bao nhiêu tiền?"
- "Ngày hết hạn là khi nào?"

### Translation Support
Translate documents to 8+ languages:
- English, Vietnamese, Chinese
- Japanese, Korean, French
- German, Spanish

### Insights Generation
Get deep analysis:
- Document purpose and summary
- Key points extraction
- Entity recognition
- Recommendations

## 🎯 Use Cases

1. **CMND/CCCD Extraction** - Extract info from ID cards with AI validation
2. **Invoice Processing** - Parse invoices + auto-classify + extract amounts
3. **Contract Analysis** - Extract key terms + summarize + Q&A
4. **Form Digitization** - Convert paper forms + smart field extraction
5. **Receipt OCR** - Extract transaction details + categorization
6. **Multi-language Docs** - OCR + translate in one step

## 🔧 Configuration

### OCR Settings
Edit `config/__init__.py`:
```python
# OCR Settings
OCR_LANGUAGE = 'vi'  # Vietnamese
OCR_DETECTION = True
OCR_RECOGNITION = True

# Upload Settings
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'bmp', 'tiff'}
```

### AI Settings
Edit `.env`:
```bash
# Gemini AI Configuration (FREE)
GEMINI_API_KEY=your_api_key_here
ENABLE_AI_ENHANCEMENT=True
AI_MODEL=gemini-2.0-flash-exp

# AI Feature Flags
ENABLE_CLASSIFICATION=True
ENABLE_EXTRACTION=True
ENABLE_SUMMARY=True
ENABLE_QA=True
ENABLE_TRANSLATION=True
```

**Get FREE Gemini API Key:**
1. Visit https://ai.google.dev
2. Click "Get API Key"
3. Create new key (FREE tier available)
4. Copy to `.env` file

## 📈 Roadmap

- [x] Phase 1: Basic OCR & WebUI
- [x] Phase 1.5: AI Enhancement (Gemini 2.0 Flash)
- [ ] Phase 2: Table Extraction & Batch Processing
- [ ] Phase 3: Advanced Layout Analysis
- [ ] Phase 4: GPU Acceleration & Performance Optimization

## 📝 License

MIT License - Free to use

## 🤝 Integration

Works seamlessly with other AI-Assistant services:
- **ChatBot**: Send OCR results for AI processing
- **Text2SQL**: Store extracted data in database
- **Speech2Text**: Combine with audio transcription

---

**Port:** `5003` | **Status:** 🟢 Active Development
