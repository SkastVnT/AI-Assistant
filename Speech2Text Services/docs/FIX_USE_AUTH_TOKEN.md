# 🔧 FIXED: use_auth_token Error

## ✅ Đã sửa lỗi

### Lỗi gốc:
```
Pipeline.from_pretrained() got an unexpected keyword argument 'use_auth_token'
```

### Nguyên nhân:
- `use_auth_token` đã deprecated trong pyannote.audio mới
- Phải dùng `token` thay thế

### File đã fix:
- ✅ `app/core/llm/diarization_client.py` - line 102

### Thay đổi:
```python
# ❌ CŨ (deprecated):
self.pipeline = Pipeline.from_pretrained(
    self.model_name,
    use_auth_token=self.hf_token  # ❌ Lỗi
)

# ✅ MỚI (correct):
self.pipeline = Pipeline.from_pretrained(
    self.model_name,
    token=self.hf_token  # ✅ Đúng
)
```

---

## 🚀 Test lại

### 1. Restart server
```powershell
# Stop server (Ctrl+C)
# Start lại
cd "Speech2Text Services"
python app/web_ui.py
```

### 2. Test diarization
```powershell
# Upload audio file vào UI tại http://localhost:5001/chatbot
# Hoặc test trực tiếp:
python -c "from app.core.llm import SpeakerDiarizationClient; d = SpeakerDiarizationClient(hf_token='YOUR_TOKEN'); d.load(); print('✅ OK')"
```

### 3. Kiểm tra log
Khi upload audio, log phải hiển thị:
```
[DIARIZATION] Loading pyannote/speaker-diarization-3.1...
[OK] Diarization pipeline loaded in X.XXs
[DIARIZATION] Processing: audio.wav
[OK] Diarization completed in X.XXs
```

**KHÔNG còn lỗi:** `unexpected keyword argument 'use_auth_token'`

---

## ℹ️ Lưu ý về CUDA

### Vấn đề từ log của bạn:
```
[Whisper] CUDA not available, using CPU
[Qwen] CUDA not available, using CPU
```

### Nguyên nhân:
- PyTorch không nhận ra CUDA
- Có thể đã cài PyTorch CPU-only

### Kiểm tra:
```powershell
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('PyTorch version:', torch.__version__)"
```

### Fix (nếu CUDA không available):
```powershell
# Uninstall PyTorch hiện tại
pip uninstall torch torchaudio torchvision

# Cài PyTorch với CUDA 11.8 (hoặc CUDA version của bạn)
pip install torch==2.2.0+cu118 torchaudio==2.2.0+cu118 --index-url https://download.pytorch.org/whl/cu118

# Hoặc CUDA 12.1:
pip install torch==2.2.0+cu121 torchaudio==2.2.0+cu121 --index-url https://download.pytorch.org/whl/cu121
```

### Kiểm tra lại:
```powershell
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

**Kết quả mong đợi:**
```
CUDA: True
Device: NVIDIA GeForce RTX XXXX
```

---

## 🔧 Lỗi torchcodec (Non-critical)

### Vấn đề:
```
Could not load libtorchcodec. Likely causes: FFmpeg is not properly installed
```

### Giải pháp:
Lỗi này **KHÔNG quan trọng** vì:
- PhoWhisper có fallback mechanism
- Vẫn chạy được với torchvision hoặc librosa
- **Không ảnh hưởng** đến transcription

### Nếu muốn fix (optional):
```powershell
# Install FFmpeg
# Download từ: https://ffmpeg.org/download.html
# Hoặc dùng chocolatey:
choco install ffmpeg

# Sau đó restart terminal và test:
ffmpeg -version
```

---

## ✅ Tổng kết

### Đã fix:
1. ✅ `use_auth_token` → `token` trong diarization_client.py
2. ✅ Code đã update, sẵn sàng chạy

### Vẫn cần làm (optional):
1. ⚠️ Cài PyTorch CUDA để tăng tốc (nếu có GPU)
2. ℹ️ Cài FFmpeg để dùng torchcodec (non-critical)

### Kết quả:
- ✅ Diarization sẽ chạy được
- ✅ Không còn lỗi `use_auth_token`
- ⏱️ CPU mode sẽ chậm hơn nhưng vẫn hoạt động

**Restart server và test ngay!** 🚀
