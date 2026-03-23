# Document Intelligence Service - Phase 1 Setup Guide

## 📋 Prerequisites

- Python 3.10 or higher
- 4GB+ RAM
- Windows/Linux/macOS
- Internet connection (for downloading PaddleOCR models)

## 🚀 Quick Start

### Windows

1. **Run Setup:**
   ```bash
   setup.bat
   ```
   This will:
   - Create virtual environment
   - Install all dependencies
   - Create .env file

2. **Start Service:**
   ```bash
   start_service.bat
   ```

3. **Open Browser:**
   ```
   http://localhost:5003
   ```

### Linux/macOS

1. **Create Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create .env:**
   ```bash
   cp .env.example .env
   ```

4. **Start Service:**
   ```bash
   python app.py
   ```

## ⚙️ Configuration

Edit `.env` file to customize:

```bash
# Server
PORT=5003
HOST=0.0.0.0

# OCR Settings
OCR_LANGUAGE=vi  # Vietnamese
OCR_USE_GPU=False  # Set True if you have CUDA

# File Upload
MAX_FILE_SIZE=20971520  # 20MB
```

## 📝 Usage

1. **Upload Document:**
   - Drag & drop file to upload area
   - Or click "Chọn File" button

2. **Configure Options:**
   - Auto rotate: Automatically detect and fix image orientation
   - Include confidence: Show confidence scores for each text block
   - Save output: Save results to output/ folder
   - Min confidence: Filter results by confidence threshold

3. **Process:**
   - Click "Xử lý Document" button
   - Wait for OCR processing

4. **View Results:**
   - **Text tab:** Plain text output
   - **Blocks tab:** Structured text blocks with confidence scores
   - **JSON tab:** Full JSON response

5. **Export:**
   - Copy to clipboard
   - Download as TXT
   - Download as JSON

## 🔧 Troubleshooting

### PaddleOCR Installation Issues

If you encounter errors during installation:

```bash
# Try installing paddlepaddle separately
pip install paddlepaddle==2.6.0 -i https://mirror.baidu.com/pypi/simple

# Then install paddleocr
pip install paddleocr==2.7.3
```

### Memory Issues

If you get out-of-memory errors:
- Close other applications
- Reduce image size before uploading
- Use CPU mode (set OCR_USE_GPU=False)

### Port Already in Use

If port 5003 is already in use:
- Change PORT in .env file
- Or stop the service using that port

## 📊 Performance

**Processing Times (CPU):**
- Single image (A4): 2-5 seconds
- PDF (10 pages): 20-50 seconds
- Large image (4K): 5-10 seconds

**With GPU (CUDA):**
- 3-5x faster processing

## 🎯 Next Steps

### Phase 2 Features (Coming Soon):
- Table extraction
- Layout analysis
- Multi-page batch processing
- Document classification

### Phase 3 Features (Planned):
- Named Entity Recognition
- Form auto-fill
- Document comparison
- Advanced search

### Phase 4 Features (Future):
- AI understanding with Qwen
- Smart data extraction
- Question answering
- Integration with ChatBot

## 📚 API Documentation

### Health Check
```bash
GET /api/health
```

### Upload & Process
```bash
POST /api/upload
Content-Type: multipart/form-data

file: [file]
options: {
  "save_output": true,
  "include_blocks": true,
  "min_confidence": 0.5
}
```

### Get Supported Formats
```bash
GET /api/formats
```

## 🤝 Integration

### With ChatBot Service:
```python
# Send OCR result to ChatBot for AI processing
import requests

# 1. OCR the document
ocr_result = requests.post('http://localhost:5003/api/upload', 
                           files={'file': open('document.jpg', 'rb')})

# 2. Send to ChatBot
text = ocr_result.json()['text']
chat_result = requests.post('http://localhost:5001/api/chat',
                           json={'message': f'Analyze this: {text}'})
```

## 📞 Support

- Check README.md for detailed documentation
- View logs in terminal for errors
- Open issue on GitHub for bugs

---

**Service:** Document Intelligence v1.0.0 (Phase 1)  
**Engine:** PaddleOCR (FREE)  
**Port:** 5003
