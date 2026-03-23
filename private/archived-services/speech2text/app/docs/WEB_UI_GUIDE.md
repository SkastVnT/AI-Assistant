# Web UI Guide - VistralS2T v3.1

## 🌐 Overview

**Web UI** cho phép bạn sử dụng VistralS2T qua trình duyệt với giao diện thân thiện.

### Features

✅ **Drag & Drop Upload** - Kéo thả file audio vào trình duyệt  
✅ **Real-time Progress** - Theo dõi tiến trình xử lý trực tiếp  
✅ **Speaker Diarization** - Tự động phân tách người nói  
✅ **Dual Model Transcription** - Whisper + PhoWhisper + Qwen  
✅ **Live Results** - Xem kết quả ngay khi hoàn thành  
✅ **Download** - Tải về file transcript  

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Activate virtual environment
call app\s2t\Scripts\activate.bat

# Install web packages
pip install flask flask-cors flask-socketio python-socketio eventlet

# Optional: Speaker diarization
pip install pyannote.audio
```

### 2. Accept Pyannote License

**Important for diarization feature:**

1. Visit: https://huggingface.co/pyannote/speaker-diarization-3.1
2. Click "Agree and access repository"
3. Set `HF_TOKEN` in `app/config/.env`

### 3. Launch Web UI

```bash
run_webui.bat
```

### 4. Open Browser

Navigate to: **http://localhost:5000**

## 📖 Usage

### Step-by-Step

1. **Upload Audio**
   - Click upload area or drag & drop file
   - Supported: MP3, WAV, M4A, FLAC (max 500MB)

2. **Start Processing**
   - Click "🚀 Start Processing"
   - Watch real-time progress updates

3. **View Results**
   - Timeline transcript with speaker labels
   - Enhanced transcript by Qwen
   - Statistics (duration, speakers, segments)

4. **Download**
   - Timeline Transcript (raw diarization)
   - Enhanced Transcript (Qwen-improved)
   - Speaker Segments (diarization data)

## 🎨 UI Features

### Progress Tracking

Real-time updates for each step:
- 🎵 **Preprocessing** - Audio loading and resampling
- 🔍 **Diarization** - Speaker detection (pyannote.audio)
- ✂️ **Segmentation** - Cutting audio by speaker
- 🎤 **Whisper** - Global ASR transcription
- 🇻🇳 **PhoWhisper** - Vietnamese ASR transcription
- 📝 **Timeline** - Building chronological transcript
- ✨ **Qwen** - Enhancement and formatting

### Results Display

**Statistics Panel:**
- Audio duration
- Number of speakers detected
- Total segments

**Timeline Transcript:**
```
[0.00s - 12.34s] SPEAKER_00:
  Cảm ơn quý khách đã gọi đến tổng đài...

[12.34s - 25.67s] SPEAKER_01:
  Chào em, cho tôi hỏi về đơn hàng...
```

**Enhanced Transcript:**
```
Hệ thống: Cảm ơn quý khách đã gọi đến tổng đài Giao Hàng Nhanh.

Khách hàng: Chào em, cho tôi hỏi về đơn hàng mã GHN12345.

Nhân viên: Dạ, anh vui lòng chờ em kiểm tra thông tin.
```

## 🔧 Configuration

### Environment Variables

`app/config/.env`:
```env
# Required for speaker diarization
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx

# Flask configuration
SECRET_KEY=your-secret-key-here

# Optional: Change port
FLASK_PORT=5000
```

### Server Settings

Edit `app/web_ui.py`:
```python
# Port
socketio.run(app, port=5000)

# Host (0.0.0.0 = all interfaces)
socketio.run(app, host='0.0.0.0', port=5000)

# Max file size (default 500MB)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
```

## 🏗️ Architecture

### Backend (Flask + Socket.IO)

```
Flask App (web_ui.py)
├── Routes
│   ├── /             → index.html
│   ├── /upload       → Handle file upload
│   ├── /status       → Processing status
│   └── /download/... → Download results
│
├── WebSocket Events
│   ├── progress      → Emit progress updates
│   ├── complete      → Emit final results
│   └── error         → Emit error messages
│
└── Processing Thread
    ├── Diarization   → SpeakerDiarizationClient
    ├── Whisper       → WhisperClient
    ├── PhoWhisper    → PhoWhisperClient
    └── Qwen          → QwenClient
```

### Frontend (HTML + JavaScript + Socket.IO)

```
index.html
├── Upload UI
│   ├── Drag & Drop area
│   └── File selection
│
├── Progress Display
│   ├── Progress bar
│   ├── Step indicators
│   └── Loading spinner
│
├── Results Display
│   ├── Statistics cards
│   ├── Timeline transcript
│   ├── Enhanced transcript
│   └── Download buttons
│
└── Socket.IO Client
    ├── Listen: progress
    ├── Listen: complete
    └── Listen: error
```

## 📊 Processing Pipeline

```
1. User uploads audio
   ↓
2. Flask saves to app/data/audio/raw/
   ↓
3. Background thread starts processing:
   
   a) Preprocessing (16kHz)
      ↓
   b) Speaker Diarization (pyannote)
      → Detect who speaks when
      ↓
   c) Segmentation
      → Cut audio by speaker
      ↓
   d) Whisper Transcription
      → Transcribe each segment
      ↓
   e) PhoWhisper Transcription
      → Vietnamese-optimized
      ↓
   f) Build Timeline
      → Chronological transcript
      ↓
   g) Qwen Enhancement
      → Grammar, formatting, role labeling
      ↓
4. Results saved to app/data/results/sessions/session_TIMESTAMP/
   ↓
5. Display in browser + download links
```

## 🔌 API Reference

### POST /upload

Upload audio file and start processing.

**Request:**
```http
POST /upload HTTP/1.1
Content-Type: multipart/form-data

file: <audio_file>
```

**Response:**
```json
{
  "message": "Upload successful, processing started",
  "session_id": "session_20251024_123456",
  "filename": "audio.mp3"
}
```

### GET /status

Get current processing status.

**Response:**
```json
{
  "is_processing": true,
  "current_step": "whisper",
  "progress": 65,
  "session_id": "session_20251024_123456",
  "error": null
}
```

### GET /download/:session_id/:file_type

Download result file.

**Parameters:**
- `session_id`: Session identifier
- `file_type`: `timeline` | `enhanced` | `segments`

**Response:** File download

### WebSocket Events

**Emit: progress**
```javascript
{
  step: "whisper",
  progress: 65,
  message: "Transcribing segment 5/10..."
}
```

**Emit: complete**
```javascript
{
  session_id: "session_20251024_123456",
  duration: 120.5,
  num_speakers: 2,
  num_segments: 15,
  timeline: "...",
  enhanced: "...",
  files: { ... }
}
```

**Emit: error**
```javascript
{
  message: "Error description"
}
```

## 🎯 Use Cases

### 1. Call Center QA

Upload cuộc gọi → Tự động phân tách nhân viên/khách hàng → Review transcript

### 2. Meeting Transcription

Upload meeting audio → Detect speakers → Timeline transcript

### 3. Interview Transcription

Upload phỏng vấn → Phân tách người phỏng vấn/người được phỏng vấn

### 4. Podcast Transcription

Upload podcast → Multi-speaker diarization → Full transcript

## 🔧 Troubleshooting

### Port Already in Use

```bash
# Check what's using port 5000
netstat -ano | findstr :5000

# Kill the process
taskkill /PID <PID> /F

# Or change port in web_ui.py
socketio.run(app, port=5001)
```

### Upload Fails

**Cause:** File too large or invalid format

**Solution:**
- Check file size (max 500MB by default)
- Ensure format is supported (mp3, wav, m4a, flac)
- Increase `MAX_CONTENT_LENGTH` in `web_ui.py`

### Diarization Not Working

**Cause:** pyannote.audio not installed or HF_TOKEN missing

**Solution:**
```bash
pip install pyannote.audio
```

Set HF_TOKEN in `.env`:
```env
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
```

Accept license: https://huggingface.co/pyannote/speaker-diarization-3.1

### WebSocket Connection Failed

**Cause:** CORS or firewall issue

**Solution:**
- Check if server is running: http://localhost:5000
- Disable browser extensions that block WebSocket
- Check firewall settings

### Slow Processing

**Tips to improve:**
- Use GPU (CUDA) if available
- Reduce audio quality before upload
- Skip Qwen enhancement (faster)
- Use smaller segments (adjust diarization parameters)

## 📱 Mobile Access

### Access from Phone/Tablet

1. Find your PC's local IP:
   ```bash
   ipconfig
   # Look for IPv4 Address (e.g., 192.168.1.100)
   ```

2. Start server with `host='0.0.0.0'`:
   ```python
   socketio.run(app, host='0.0.0.0', port=5000)
   ```

3. Open on mobile: `http://192.168.1.100:5000`

### Responsive Design

UI automatically adapts to mobile screens:
- Stacked layout on small screens
- Touch-friendly buttons
- Mobile-optimized file picker

## 🚀 Production Deployment

### Using Gunicorn + Nginx

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5000 app.web_ui:app
```

### Docker Deployment

```dockerfile
FROM python:3.10

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/

CMD ["python", "app/web_ui.py"]
```

### Security Considerations

1. **Enable HTTPS** in production
2. **Add authentication** for sensitive data
3. **Limit file size** appropriately
4. **Validate uploads** to prevent malicious files
5. **Set SECRET_KEY** to secure random value
6. **Use reverse proxy** (Nginx/Apache)

## 📚 Resources

- **Flask Documentation:** https://flask.palletsprojects.com/
- **Socket.IO:** https://socket.io/
- **pyannote.audio:** https://github.com/pyannote/pyannote-audio

## 🆕 What's Next?

**Future enhancements:**
- [ ] User authentication
- [ ] Session history
- [ ] Batch processing
- [ ] API key management
- [ ] Custom model selection
- [ ] Export to multiple formats (SRT, VTT, JSON)
- [ ] Audio playback with sync highlighting
- [ ] Speaker identification (name labeling)

## 💡 Tips & Tricks

1. **Bookmark sessions:** Note session IDs for later access
2. **Use Chrome/Edge:** Best WebSocket support
3. **Clear cache:** If UI doesn't update properly
4. **Check console:** F12 → Console for debug info
5. **Test with short files first:** Verify setup before long processing

---

**Need help?** Check logs in `app/logs/` or run with `debug=True` for detailed output.
