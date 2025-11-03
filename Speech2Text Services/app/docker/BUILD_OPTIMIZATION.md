# Docker Build Tối Ưu - Giải Pháp Build Nhanh

## ❌ VẤN ĐỀ CŨ
- Docker build mất **15-20 phút** vì cài đặt tất cả dependencies trong build
- Build thường bị timeout hoặc fail
- Mỗi lần rebuild lại mất thời gian tương tự

## ✅ GIẢI PHÁP MỚI
**Build 2 giai đoạn:**

### Giai đoạn 1: Build image cơ bản (nhanh ~2-3 phút)
- Chỉ cài essential packages: torch, transformers, flask, faster-whisper
- Image nhẹ, build nhanh, dễ rebuild

### Giai đoạn 2: Install full dependencies (sau khi container chạy)
- Cài pyannote.audio, pytorch-lightning và các packages nặng
- Chỉ cần làm 1 lần, không mất thời gian mỗi khi rebuild

---

## 🚀 HƯỚNG DẪN SỬ DỤNG

### Bước 1: Build image cơ bản (lần đầu tiên)
```powershell
cd "I:\1000 bài code thiếu nhi\Speech2Text\app\docker"
.\docker-manage.bat
# Chọn option 1: Build Docker image
```

⏱️ **Thời gian:** 2-3 phút (thay vì 15-20 phút)

---

### Bước 2: Start container
```powershell
.\docker-manage.bat
# Chọn option 2: Start containers
```

---

### Bước 3: Install full dependencies (chỉ 1 lần)
```powershell
.\docker-manage.bat
# Chọn option 4: Install full dependencies
```

⏱️ **Thời gian:** 5-10 phút  
📝 **Lưu ý:** Chỉ cần làm 1 lần, dependencies được lưu trong container

---

## 📋 MENU MỚI

```
========================================
 Choose an option:
========================================
 1. Build Docker image (fast - essential deps only)
 2. Start containers (docker compose up -d)
 3. Build and start (build + up)
 4. Install full dependencies (pyannote, etc.)
 5. Stop containers (docker compose down)
 6. View logs (docker compose logs -f)
 7. Check status (docker ps)
========================================
```

---

## 🎯 LUỒNG SỬ DỤNG

### Lần đầu tiên setup:
```
1. Build image (option 1) → 2-3 phút
2. Start containers (option 2) → 10 giây
3. Install full deps (option 4) → 5-10 phút

TỔNG: ~10 phút (thay vì 20 phút)
```

### Lần sau rebuild (sau khi sửa code):
```
1. Stop containers (option 5)
2. Build image (option 1) → 2-3 phút (NHANH!)
3. Start containers (option 2) → 10 giây

TỔNG: ~3 phút (không cần install lại deps!)
```

---

## ✨ LỢI ÍCH

✅ **Build nhanh hơn 5-7 lần** (3 phút thay vì 20 phút)  
✅ **Không bị timeout** khi build  
✅ **Dependencies được cache** trong container  
✅ **Dễ debug** nếu build fail  
✅ **Flexible:** Có thể skip pyannote nếu không cần diarization

---

## 🔧 TROUBLESHOOTING

### Build bị lỗi?
```powershell
# Clean cache và rebuild
docker system prune -a
.\docker-manage.bat
# Option 1: Build lại
```

### Container chạy nhưng thiếu dependencies?
```powershell
# Install lại full dependencies
.\docker-manage.bat
# Option 4: Install full dependencies
```

### Muốn install dependencies thủ công?
```powershell
docker exec -it s2t-system bash
pip3 install pyannote.audio==3.1.1
```

---

## 📦 PACKAGES ĐƯỢC CÀI

### Essential (trong build):
- torch==2.7.1
- torchaudio==2.7.1
- faster-whisper>=1.0.3
- transformers>=4.40.0
- flask>=3.0.0
- flask-socketio>=5.3.0
- librosa, soundfile, pydub

### Full (sau khi start container):
- pyannote.audio==3.1.1
- pyannote.core==5.0.0
- pyannote.pipeline==3.0.1
- pytorch-lightning==2.0.9.post0
- lightning==2.0.9.post0
- openai
- google-generativeai

---

## 🎓 KẾT LUẬN

Giải pháp này giúp:
- **Development nhanh hơn:** Rebuild chỉ 3 phút
- **CI/CD tối ưu:** Build image nhẹ, test nhanh
- **Production ready:** Full dependencies có sẵn khi cần

Chỉ cần nhớ: **Build nhanh (option 1) → Start (option 2) → Install full deps (option 4)** ✨
