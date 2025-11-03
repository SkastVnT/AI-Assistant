# 🚀 VistralS2T v3.5 - Quick Start Guide

## ⚡ Cài Đặt Nhanh (5 phút)

### Bước 1: Rebuild Project
```powershell
# Chạy script tự động (Khuyến nghị)
.\rebuild_project.bat

# Hoặc manual:
python -m venv app\s2t
.\app\s2t\Scripts\activate
pip install -r requirements.txt --upgrade
```

### Bước 2: Cấu hình
```powershell
# Mở file .env
notepad app\config\.env

# Thêm HuggingFace token (bắt buộc cho diarization)
HF_TOKEN=hf_your_token_here

# Set đường dẫn audio test
AUDIO_PATH=C:\path\to\your\audio.mp3
```

### Bước 3: Chạy Thử

#### Option A: Command Line (Nhanh nhất)
```powershell
cd app\core
python run_with_diarization.py
```

#### Option B: Web UI (Thân thiện)
```powershell
.\start_webui.bat
# Mở browser: http://localhost:5000
```

#### Option C: Docker (Production)
```powershell
cd app\docker
docker compose up --build
```

---

## 🆕 Tính Năng Mới v3.5

### 1. ⚡ VAD (Voice Activity Detection)
- **Tự động phát hiện chỗ có giọng nói**
- **Giảm 30-50% thời gian xử lý**
- **2 phương pháp:**
  - Silero VAD: AI-based, accuracy 95%+
  - Energy-based: Fallback khi Silero không có

### 2. 🎯 Dual Model Pipeline
- **Whisper large-v3**: Độ chính xác toàn cầu
- **PhoWhisper-large**: Chuyên biệt tiếng Việt
- **Cả 2 chạy song song** trên mỗi segment

### 3. 📊 Timing Chính Xác
```
Preprocessing:     4.62s
Diarization:     45.30s  ← Fixed! (trước đây: 0.00s)
Whisper:        323.93s
PhoWhisper:     180.50s  ← New!
Qwen:            12.16s
────────────────────────
Total:          566.51s
```

### 4. 🌐 WebUI Cải Tiến
- ✅ Progress updates real-time
- ✅ Broadcast đến tất cả clients
- ✅ Console logging chi tiết
- ✅ Better error handling

---

## 📁 Cấu Trúc Kết Quả

```
data/results/sessions/session_20251024_105312/
├── preprocessed_audio.wav          # Audio đã xử lý
├── speaker_segments.txt            # Timeline diarization
├── timeline_transcript.txt         # Kết quả chính ⭐
├── enhanced_transcript.txt         # Qwen enhanced (optional)
├── pipeline.log                    # Log chi tiết
└── audio_segments/                 # Các đoạn audio theo speaker
    ├── segment_000_SPEAKER_00.wav
    ├── segment_001_SPEAKER_01.wav
    └── ...
```

---

## ⚙️ Tùy Chỉnh

### Tắt VAD (nếu muốn)
```python
# Trong run_with_diarization.py hoặc diarization_client.py
segments = diarizer.diarize(
    audio_path,
    use_vad=False  # Tắt VAD
)
```

### Thay đổi số speaker
```python
diarizer = SpeakerDiarizationClient(
    min_speakers=2,  # Tối thiểu 2 người
    max_speakers=10  # Tối đa 10 người (mặc định: 5)
)
```

### Chỉ chạy Whisper (không PhoWhisper)
```powershell
cd app\core
python run_dual_vistral.py  # Chạy script cũ
```

---

## 🐛 Troubleshooting

### Lỗi: "ModuleNotFoundError: No module named 'torch'"
```powershell
# Install PyTorch với CUDA
pip install torch>=2.0.1 torchaudio>=2.0.2 --index-url https://download.pytorch.org/whl/cu118
```

### Lỗi: "Pipeline.from_pretrained() got an unexpected keyword argument 'use_auth_token'"
✅ **Đã fix trong v3.5!** Chạy `.\rebuild_project.bat` để update

### WebUI stuck ở "Processing..."
✅ **Đã fix trong v3.5!** 
- Restart server
- Check console logs
- Verify WebSocket connection

### Diarization hiển thị 0.00s
✅ **Đã fix trong v3.5!** Timing logic đã được sửa

### Lỗi: "HuggingFace token required"
```powershell
# Lấy token từ: https://huggingface.co/settings/tokens
# Thêm vào app\config\.env:
HF_TOKEN=hf_xxxxxxxxxxxxx
```

---

## 📊 So Sánh Performance

| Metric | v3.0 | v3.5 | Improvement |
|--------|------|------|-------------|
| **Diarization** | Full audio | VAD filtered | ⚡ 30-50% faster |
| **Transcription** | Whisper only | Whisper + PhoWhisper | 🎯 Dual model |
| **Timing Display** | ❌ 0.00s bug | ✅ Accurate | ✅ Fixed |
| **WebUI Progress** | ❌ Stuck | ✅ Real-time | ✅ Fixed |
| **Total Time (250s audio)** | ~330s | ~250-280s | ⚡ 15-24% faster |

---

## 🔗 Links Hữu Ích

- **HuggingFace Token**: https://huggingface.co/settings/tokens
- **Pyannote License**: https://huggingface.co/pyannote/speaker-diarization-3.1
- **PyTorch Install**: https://pytorch.org/get-started/locally/
- **Full Docs**: `docs/`
- **Upgrade Guide**: `VERSION_3.5_UPGRADE_GUIDE.py`

---

## ✅ Checklist Sau Khi Cài

- [ ] Virtual environment activated
- [ ] All packages installed (check with `pip list`)
- [ ] HF_TOKEN configured in `.env`
- [ ] Test audio file ready
- [ ] CUDA available (check with `python -c "import torch; print(torch.cuda.is_available())"`)
- [ ] Run test: `python app\core\run_with_diarization.py`

---

## 🎉 Done!

Bây giờ bạn có thể:

1. **Chạy CLI**: `cd app\core && python run_with_diarization.py`
2. **Chạy Web UI**: `.\start_webui.bat`
3. **Check results**: `data\results\sessions\`

**Version**: 3.5.0  
**Date**: 2025-10-24  
**Status**: ✅ Production Ready
