# Cache Troubleshooting - VistralS2T

## ❌ Vấn Đề: Transcript Vẫn Có Nhiễu Sau Khi Cập Nhật Prompt

### Triệu chứng
- Transcript vẫn chứa: "Hãy subscribe", "Đăng ký kênh", "Like share"
- Không có phân vai người nói rõ ràng (Hệ thống:/Nhân viên:/Khách hàng:)
- Kết quả không thay đổi dù đã cập nhật prompt trong `app/core/prompts/templates.py`

### Nguyên nhân

**2 tầng cache:**

1. **Client-side (localStorage):**
   - Web UI lưu kết quả vào localStorage
   - Khi refresh trang → tự động restore kết quả cũ
   - Thời gian sống: 1 giờ

2. **Server-side (session folders):**
   - Kết quả lưu trong `app/data/results/sessions/session_YYYYMMDD_HHMMSS/`
   - Nếu xử lý lại cùng file → có thể dùng cached segments
   - Qwen model có thể bị skip do lỗi → dùng kết quả cũ

### ✅ Giải pháp: Clear Cache Đúng Cách

**Bước 1: Clear Server Cache** (Quan trọng nhất!)
```
1. Mở Web UI: http://localhost:5000
2. Click nút "💥 Clear Server" (màu tím, góc phải trên)
3. Xác nhận: "FORCE CLEAR tất cả session trên server?"
4. Đợi thông báo: "Server cache cleared! Deleted X session(s)"
```

**Bước 2: Clear Client Cache**
```
1. Click nút "🗑️ Clear Cache" (màu đỏ, bên trái nút Clear Server)
2. Xác nhận: "Xóa toàn bộ cache và reset Web UI?"
3. UI sẽ reset về trạng thái ban đầu
```

**Bước 3: Upload & Process**
```
1. Upload lại file audio
2. Click "🚀 Start Processing"
3. Đợi hoàn thành (khoảng 5-10 phút tùy file)
4. Kiểm tra kết quả:
   ✅ KHÔNG còn "subscribe", "đăng ký kênh"
   ✅ CÓ phân vai: "Hệ thống:", "Nhân viên:", "Khách hàng:"
```

---

## 🔍 Kiểm Tra Cache

### Xem Sessions Hiện Tại
```powershell
# PowerShell
Get-ChildItem -Path "app\data\results\sessions" -Directory | Select-Object Name, LastWriteTime

# CMD
dir app\data\results\sessions\ /b
```

### Xóa Thủ Công (Nếu cần)
```powershell
# PowerShell
Remove-Item -Path "app\data\results\sessions\*" -Recurse -Force

# CMD
rmdir /s /q app\data\results\sessions
mkdir app\data\results\sessions
```

### Xem localStorage (Browser DevTools)
```javascript
// F12 → Console
localStorage.getItem('vistral_s2t_state')

// Clear manually
localStorage.clear()
```

---

## 🐛 Debug: Tại Sao Qwen Bị Skip?

### Triệu chứng
- Session folder không có `enhanced_transcript.txt`
- Chỉ có `timeline_transcript.txt`
- Kết quả không có enhancement

### Kiểm tra
```powershell
# List files trong session
Get-ChildItem "app\data\results\sessions\session_YYYYMMDD_HHMMSS"

# Expected files:
# - preprocessed_*.wav
# - timeline_transcript.txt
# - enhanced_transcript.txt  ← Phải có file này!
# - processing_summary.txt
# - pipeline.log
```

### Nguyên nhân thường gặp

**1. GPU Out of Memory**
- Qwen model yêu cầu ~2-3GB VRAM
- Nếu Whisper + PhoWhisper + Diarization đã dùng hết VRAM → Qwen fail
- Solution: Giảm batch_size hoặc dùng CPU

**2. Import Error**
```python
# Check trong web_ui.py
from core.prompts.templates import PromptTemplates  # ← Phải có dòng này

# Nếu lỗi import → Qwen bị skip
```

**3. Prompt Build Error**
```python
# web_ui.py dòng 251-257
prompt = PromptTemplates.build_qwen_prompt(
    whisper_text=timeline_text,
    phowhisper_text=dual_text
)
# Nếu function không tồn tại → Exception → skip
```

---

## 📊 Workflow Tổng Quan

```
┌─────────────────────────────────────────────────────────────┐
│  USER UPLOADS FILE                                           │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
   ┌─────────────────────┐
   │  processAudioFile() │
   │  - clearState()     │ ← Xóa localStorage
   │  - Upload file      │
   └────────┬────────────┘
            │
            ▼
   ┌────────────────────────────────────────┐
   │  BACKEND PROCESSING                    │
   │  1. Preprocess audio                   │
   │  2. Diarization (speaker detection)    │
   │  3. Segment audio                      │
   │  4. Whisper transcription              │
   │  5. PhoWhisper transcription           │
   │  6. Qwen enhancement ← PROMPT MỚI      │
   └────────┬───────────────────────────────┘
            │
            ▼
   ┌─────────────────────────────────────┐
   │  SAVE RESULTS                       │
   │  - Server: data/results/sessions/   │ ← Session folder
   │  - Client: localStorage             │ ← For restore
   └────────┬────────────────────────────┘
            │
            ▼
   ┌─────────────────────────┐
   │  DISPLAY ON WEB UI      │
   │  - Timeline transcript  │
   │  - Enhanced transcript  │ ← Kết quả Qwen
   │  - Model badges         │
   └─────────────────────────┘
```

---

## ⚙️ Cấu hình Cache

### Thay đổi thời gian cache localStorage

```javascript
// app/templates/index.html
function loadState() {
    // ...
    if (Date.now() - state.timestamp < 3600000) {  // 1 hour = 3600000ms
        return state;
    }
    // ...
}

// Thay đổi thành 30 phút:
if (Date.now() - state.timestamp < 1800000) {
    return state;
}
```

### Disable cache hoàn toàn (Testing)

```javascript
// Comment out restore logic
// window.addEventListener('load', () => {
//     const savedState = loadState();
//     if (savedState) {
//         // ... restore logic
//     }
// });
```

---

## 📝 Checklist Khi Update Prompt

- [ ] Cập nhật `app/core/prompts/templates.py`
- [ ] Kiểm tra syntax: `python -m py_compile app/core/prompts/templates.py`
- [ ] Click **💥 Clear Server** để xóa sessions cũ
- [ ] Click **🗑️ Clear Cache** để xóa localStorage
- [ ] Upload lại file audio
- [ ] Kiểm tra kết quả:
  - [ ] Không còn nhiễu/quảng cáo
  - [ ] Có phân vai rõ ràng
  - [ ] File `enhanced_transcript.txt` tồn tại

---

## 🆘 Still Not Working?

### Check 1: Prompt có được load không?
```python
# Test trong Python console
from app.core.prompts.templates import PromptTemplates

# Print prompt để xem nội dung
prompt = PromptTemplates.build_qwen_prompt("test whisper", "test pho")
print(prompt)

# Phải thấy:
# - "Loại bỏ hoàn toàn các nội dung nhiễu"
# - "Hãy subscribe", "Đăng ký kênh"
```

### Check 2: Web UI có gọi đúng không?
```python
# Thêm debug trong web_ui.py line 252
from core.prompts.templates import PromptTemplates
prompt = PromptTemplates.build_qwen_prompt(...)
print(f"[DEBUG] Prompt length: {len(prompt)}")  # ← Add this
print(f"[DEBUG] Prompt preview: {prompt[:500]}")  # ← Add this
```

### Check 3: Qwen có chạy không?
```python
# Check logs
cat app/data/results/sessions/session_*/pipeline.log

# Phải thấy:
# - Diarization: XX.XXs
# - Whisper: XX.XXs
# - PhoWhisper: XX.XXs  ← Phải có
# - Qwen: XX.XXs        ← Phải có
```

---

## 🎯 Best Practices

1. **Sau mỗi lần update prompt:**
   - Clear server cache
   - Clear client cache
   - Test với 1 file ngắn trước (< 1 phút)

2. **Khi test prompt engineering:**
   - Tắt localStorage restore (để tránh nhầm lẫn)
   - Xóa session folders thường xuyên
   - Check `enhanced_transcript.txt` trực tiếp

3. **Production deployment:**
   - Không disable cache (cần cho UX tốt)
   - Monitor session folder size (tự động cleanup sau 7 ngày)
   - Backup prompts trước khi thay đổi

---

*Last updated: October 27, 2025*
*Version: 3.6.1*
