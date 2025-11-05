# 📄 Document Intelligence Service

> **AI-Powered Document Processing & OCR Service**  
> Vietnamese-optimized document understanding với FREE models

## 🎯 Features

### ✅ Phase 1 (Current)
- 📸 **OCR Text Extraction** - PaddleOCR Vietnamese support
- 🖼️ **Image Upload** - Drag & drop interface
- 📝 **Text Display** - Formatted output
- 💾 **Export** - TXT, JSON formats

### 🚧 Phase 2 (Planned)
- 📊 **Table Extraction** - Detect and parse tables
- 📑 **Multi-page PDF** - Batch processing
- 🏷️ **Document Classification** - Auto-detect document types
- 📐 **Layout Analysis** - Structure understanding

### 🔮 Phase 3 (Future)
- 🎯 **Named Entity Recognition** - Extract names, dates, numbers
- 📋 **Form Auto-fill** - Intelligent form completion
- 🔍 **Document Search** - Semantic search across documents
- 🤖 **AI Q&A** - Ask questions about documents

## 🏗️ Architecture

```
Document Intelligence Service/
├── app.py                 # Main Flask application
├── config/
│   └── __init__.py       # Configuration
├── src/
│   ├── ocr/
│   │   ├── paddle_ocr.py # PaddleOCR engine
│   │   └── processor.py  # OCR processing
│   └── utils/
│       ├── file_handler.py
│       └── format_converter.py
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── uploads/          # Temporary uploads
├── templates/
│   └── index.html        # WebUI
├── output/               # Processed results
└── requirements.txt
```

## 🚀 Quick Start

### 1. Setup Environment
```bash
cd "Document Intelligence Service"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Service
```bash
python app.py
```

### 3. Open Browser
```
http://localhost:5003
```

## 🛠️ Tech Stack

| Component | Technology | Why |
|:----------|:-----------|:----|
| **OCR Engine** | PaddleOCR | FREE, Vietnamese support, high accuracy |
| **Backend** | Flask | Lightweight, easy integration |
| **Frontend** | HTML/CSS/JS + Tailwind | Modern UI like ChatBot |
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

## 🎯 Use Cases

1. **CMND/CCCD Extraction** - Extract info from ID cards
2. **Invoice Processing** - Parse invoices automatically
3. **Contract Analysis** - Extract key terms
4. **Form Digitization** - Convert paper forms to digital
5. **Receipt OCR** - Extract transaction details

## 🔧 Configuration

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

## 📈 Roadmap

- [x] Phase 1: Basic OCR & WebUI
- [ ] Phase 2: Document Understanding
- [ ] Phase 3: Advanced Features
- [ ] Phase 4: AI Integration with Qwen

## 📝 License

MIT License - Free to use

## 🤝 Integration

Works seamlessly with other AI-Assistant services:
- **ChatBot**: Send OCR results for AI processing
- **Text2SQL**: Store extracted data in database
- **Speech2Text**: Combine with audio transcription

---

**Port:** `5003` | **Status:** 🟢 Active Development
