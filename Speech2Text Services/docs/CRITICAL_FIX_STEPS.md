# 🚨 CRITICAL FIX - Làm Theo Từng Bước

## ❌ VẤN ĐỀ HIỆN TẠI

1. Session mới nhất: `session_20251024_111124` (3 NGÀY TRƯỚC!)
2. Không có `enhanced_transcript.txt` → Qwen bị skip
3. Web UI hiện kết quả cũ từ localStorage
4. Vẫn còn "SPEAKER_00:", vẫn có "subscribe"

## ✅ GIẢI PHÁP (THEO ĐÚNG THỨ TỰ)

### Bước 1: Start Web UI

```powershell
cd D:\WORK\s2t
.\start_webui.bat
```

**Đợi thấy:** `Running on http://127.0.0.1:5000`

### Bước 2: Mở Browser

```
http://localhost:5000
```

### Bước 3: CLEAR SERVER CACHE (QUAN TRỌNG NHẤT!)

```
1. Nhìn góc phải trên cùng
2. Click nút "💥 Clear Server" (màu tím)
3. Confirm dialog: "FORCE CLEAR tất cả session?"
4. Click OK
5. Đợi notification: "Server cache cleared! Deleted 6 session(s)"
```

**Verify:**
```powershell
# Mở terminal mới
cd D:\WORK\s2t
Get-ChildItem "app\data\results\sessions" -Directory

# Phải thấy: FOLDER RỖNG hoặc chỉ có .gitkeep
```

### Bước 4: CLEAR CLIENT CACHE

```
1. Click nút "🗑️ Clear Cache" (màu đỏ, bên trái nút Clear Server)
2. Confirm dialog: "Xóa toàn bộ cache?"
3. Click OK
4. UI sẽ reset về trạng thái mới
```

### Bước 5: UPLOAD FILE AUDIO

```
1. Click "Click to upload" hoặc drag & drop
2. Chọn file audio (cùng file cũ hoặc file mới đều được)
3. Thấy: "Selected: filename.mp3"
4. Nút "🚀 Start Processing" sẽ enable
```

### Bước 6: START PROCESSING

```
1. Click "🚀 Start Processing"
2. Đợi upload (vài giây)
3. Theo dõi progress:
   - Preprocessing...
   - Diarization... (1-2 phút)
   - Whisper... (3-5 phút)
   - PhoWhisper... (2-3 phút)
   - Qwen... (1-2 phút) ← PHẢI CÓ BƯỚC NÀY!
4. Tổng: ~8-12 phút
```

### Bước 7: VERIFY KẾT QUẢ

**Check 1: Enhanced Transcript Section**
```
Cuộn xuống phần "✨ Enhanced Transcript"
```

**Phải thấy:**
```
Hệ thống: Cảm ơn quý khách đã gọi đến giao hàng nhanh. 
Cước phí cuộc gọi là 1000 đồng một phút.

Nhân viên: Dạ, nhân viên hỗ trợ khách hàng. Em xin nghe ạ.

Khách hàng: Nhờ em hỗ trợ dùm chị cái đơn hàng là G-I-V-B-B-B-B-B-I-6-9-F...
```

**KHÔNG ĐƯỢC THẤY:**
- ❌ "SPEAKER_00:"
- ❌ "Hãy subscribe cho kênh La La School"
- ❌ "Hãy subscribe cho kênh Ghiền Mì Gõ"

**Check 2: Session Folder**
```powershell
# Terminal
cd D:\WORK\s2t
$latest = Get-ChildItem "app\data\results\sessions" -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-ChildItem $latest.FullName | Select-Object Name
```

**Phải thấy:**
```
preprocessed_*.wav
timeline_transcript.txt
enhanced_transcript.txt  ← PHẢI CÓ FILE NÀY!
processing_summary.txt
pipeline.log
audio_segments/
```

**Check 3: Enhanced Transcript File**
```powershell
# Đọc file enhanced
$latest = Get-ChildItem "app\data\results\sessions" -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content "$($latest.FullName)\enhanced_transcript.txt" -Head 30
```

**Phải thấy:**
- ✅ "Hệ thống:", "Nhân viên:", "Khách hàng:"
- ❌ KHÔNG có "subscribe", "SPEAKER_00"

---

## 🐛 NẾU VẪN BỊ

### Case 1: Qwen vẫn bị skip

**Triệu chứng:**
- Không có `enhanced_transcript.txt`
- Progress bar không có step "Qwen enhancement"

**Check logs:**
```powershell
$latest = Get-ChildItem "app\data\results\sessions" -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content "$($latest.FullName)\pipeline.log"
```

**Phải thấy:**
```
Preprocessing: X.XXs
Diarization: X.XXs
Whisper: X.XXs
PhoWhisper: X.XXs  ← PHẢI CÓ
Qwen: X.XXs        ← PHẢI CÓ
```

**Nếu không có Qwen → Check terminal output:**
```
Tìm dòng:
[QWEN] Loading Qwen model...
[QWEN] Enhancement complete

Nếu không thấy → Qwen bị lỗi
```

### Case 2: Web UI vẫn hiện kết quả cũ

**Giải pháp:**
```
1. F12 → Console
2. Gõ: localStorage.clear()
3. Refresh trang: F5
4. Upload lại
```

### Case 3: Vẫn có "SPEAKER_00:"

**Nghĩa là đang xem Timeline Transcript, KHÔNG PHẢI Enhanced Transcript!**

```
Cuộn xuống tìm phần:
"✨ Enhanced Transcript (PhoWhisper-large + Qwen2.5-1.5B)"

Click vào badge "Qwen: Qwen2.5-1.5B-Instruct" để jump đến đúng section
```

---

## 📊 Timeline Debug

```
[Before v3.6.3 Update]
├─ Prompt có noise filtering rules ✅
├─ Prompt có speaker role detection ✅
└─ VERSION = "3.6.3" ✅

[After Update - User Test]
├─ Start webui ✅
├─ Clear server cache? ❌ CHƯA LÀM
├─ Upload new file? ❌ CHƯA LÀM
└─ Kết quả vẫn bị ← localStorage restore kết quả cũ từ 3 ngày trước!

[Expected Flow]
1. ✅ Clear server (xóa 6 sessions cũ)
2. ✅ Clear client (xóa localStorage)
3. ✅ Upload file
4. ✅ Process with Qwen v3.6.3
5. ✅ Verify output có phân vai rõ
```

---

## ⚡ QUICK TEST

```powershell
# Test 1: Check sessions
Get-ChildItem "app\data\results\sessions" -Directory | Measure-Object | Select-Object Count
# Expected: Count = 0 (sau khi clear)

# Test 2: Start webui
.\start_webui.bat
# Expected: Server running on port 5000

# Test 3: Clear cache (trong browser)
# Click 💥 Clear Server + 🗑️ Clear Cache

# Test 4: Upload & process
# Upload file → Click Start Processing

# Test 5: Wait & verify
# Đợi 10 phút → Check enhanced transcript
```

---

## 🎯 SUCCESS CRITERIA

Kết quả đúng khi thấy:

```
✨ Enhanced Transcript (PhoWhisper-large + Qwen2.5-1.5B)

Hệ thống: Cảm ơn quý khách đã gọi đến giao hàng nhanh. 
Cước phí cuộc gọi là 1000 đồng một phút.

Nhân viên: Dạ, nhân viên hỗ trợ khách hàng, quý vị xin nghe. 
Em hỗ trợ cho anh chị.

Khách hàng: Nhờ em hỗ trợ dùm chị cái đơn hàng là 
G-I-V-B-B-B-B-B-I-6-9-F, F là S.

Nhân viên: Dạ, em xin tên chị.

Khách hàng: Chị Hoàng Đông.
```

✅ Có "Hệ thống:", "Nhân viên:", "Khách hàng:"
✅ Không có "SPEAKER_00:"
✅ Không có "Hãy subscribe"
✅ Nội dung cuộc gọi giữ nguyên 100%

---

**CÁC BƯỚC KHÔNG ĐƯỢC BỎ QUA:**
1. ☑️ Clear Server
2. ☑️ Clear Cache
3. ☑️ Upload file
4. ☑️ Đợi Qwen chạy (quan trọng!)
5. ☑️ Xem Enhanced Transcript (không phải Timeline!)

---

*Last Updated: October 27, 2025*
*Version: Critical Fix Guide*
