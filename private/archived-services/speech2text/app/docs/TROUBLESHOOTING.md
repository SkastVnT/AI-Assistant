# 🛠️ TROUBLESHOOTING GUIDE

## ❌ Lỗi Thường Gặp và Cách Khắc Phục

### 1. Lỗi cuDNN DLL

**Triệu chứng:**
```
Could not locate cudnn_ops64_9.dll
Invalid handle. Cannot load symbol cudnnCreateTensorDescriptor
```

**Nguyên nhân:** PyTorch phiên bản CPU-only đang được sử dụng thay vì CUDA.

**Giải pháp:**
```powershell
# Gỡ PyTorch hiện tại
pip uninstall torch torchaudio torchvision -y

# Cài PyTorch với CUDA support
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# Kiểm tra
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

---

### 2. Lỗi torch.load Security (CVE-2025-32434)

**Triệu chứng:**
```
ValueError: Due to a serious vulnerability issue in `torch.load`
we now require users to upgrade torch to at least v2.6
```

**Nguyên nhân:** PyTorch 2.5.1 chưa đủ mới, transformers yêu cầu 2.6+

**Giải pháp:** Code đã được cập nhật để:
- Sử dụng `use_safetensors=False` khi cần
- Tự động fallback giữa safetensors và PyTorch format
- Bỏ qua cảnh báo với `HF_HUB_DISABLE_SAFETENSORS_LOAD_WARNING`

---

### 3. Lỗi Hugging Face 403 Forbidden (Discussions)

**Triệu chứng:**
```
403 Forbidden: Discussions are disabled for this repo.
Cannot access content at: https://huggingface.co/api/models/vinai/PhoWhisper-large/discussions
```

**Nguyên nhân:** Transformers cố truy cập discussions để check safetensors conversion PR

**Giải pháp:** Code đã được cập nhật với:
```python
# Tải với safetensors nếu có, không thì dùng PyTorch format
try:
    model = WhisperForConditionalGeneration.from_pretrained(
        "vinai/PhoWhisper-large",
        use_safetensors=True,
        resume_download=True
    )
except:
    model = WhisperForConditionalGeneration.from_pretrained(
        "vinai/PhoWhisper-large",
        use_safetensors=False  # Fallback
    )
```

---

### 4. Lỗi ModuleNotFoundError: No module named 'librosa'

**Triệu chứng:**
```
ModuleNotFoundError: No module named 'librosa'
```

**Nguyên nhân:** Virtual environment chưa được kích hoạt

**Giải pháp:**
```powershell
# Kích hoạt virtual environment
.\s2t\Scripts\Activate.ps1

# Hoặc chạy trực tiếp với Python của venv
.\s2t\Scripts\python.exe run_dual_models.py

# Cài đặt dependencies
pip install -r requirements.txt
```

---

### 5. Lỗi CUDA Out of Memory

**Triệu chứng:**
```
torch.cuda.OutOfMemoryError: CUDA out of memory
```

**Giải pháp:**

1. **Giảm batch size / chunk size:**
```python
# Trong run_dual_models.py, dòng ~205
chunk_duration = 20  # Giảm từ 30 xuống 20
```

2. **Dùng compute_type nhẹ hơn:**
```python
# Whisper
whisper_model = WhisperModel("large-v3", device="cuda", compute_type="int8")

# PhoWhisper - không dùng half precision
pho_model = WhisperForConditionalGeneration.from_pretrained(
    "vinai/PhoWhisper-large",
    torch_dtype=torch.float32  # Thay vì float16
)
```

3. **Fallback sang CPU:**
```python
device = "cpu"
```

---

### 6. Script Chạy Chậm

**Tối ưu hóa:**

1. **Bật GPU acceleration:**
```powershell
# Kiểm tra GPU
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

2. **Giảm beam_size:**
```python
# Whisper - dòng ~122
beam_size=3  # Giảm từ 5 xuống 3

# PhoWhisper - dòng ~223
num_beams=5  # Giảm từ 8 xuống 5
```

3. **Tắt preprocessing nếu audio đã sạch:**
```python
cleaned_path = AUDIO_PATH  # Bỏ qua preprocessing
preprocessing_time = 0
```

---

## 🚀 Quick Fix Command

Nếu gặp bất kỳ lỗi nào, chạy lệnh này:

```powershell
# Kích hoạt venv và chạy script
.\s2t\Scripts\Activate.ps1
.\s2t\Scripts\python.exe run_dual_models.py
```

---

## 📞 Liên Hệ Support

Nếu vẫn gặp lỗi, hãy:
1. Copy toàn bộ error message
2. Chạy `python test_cuda.py` để kiểm tra hệ thống
3. Kiểm tra version: `pip list | findstr "torch transformers faster-whisper"`

---

**Cập nhật:** 14/10/2025
