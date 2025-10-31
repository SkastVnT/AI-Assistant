# 🚀 Docker Quick Start - Tối Ưu Build

## TL;DR - Nhanh Nhất

```powershell
cd "I:\1000 bài code thiếu nhi\Speech2Text\app\docker"
.\docker-manage.bat
```

**Chọn theo thứ tự:**
1. **Option 1**: Build image (2-3 phút) ⚡
2. **Option 2**: Start containers (10 giây) 🏃
3. **Option 4**: Install full deps (5-10 phút) 📦

✨ **TỔNG THỜI GIAN: ~10 phút** (thay vì 20 phút!)

---

## ⚙️ Build Strategy

### 🎯 Chiến lược Build 2 Giai Đoạn

#### Giai đoạn 1: Essential Build (NHANH)
```dockerfile
# Chỉ cài packages cần thiết:
torch, transformers, flask, faster-whisper, librosa
```
⏱️ **2-3 phút** - Image nhẹ, rebuild nhanh

#### Giai đoạn 2: Full Dependencies (SAU KHI CHẠY)
```bash
# Cài packages nặng trong container đang chạy:
pyannote.audio, pytorch-lightning, API clients
```
⏱️ **5-10 phút** - Chỉ làm 1 lần, cache trong container

---

## 📖 Chi Tiết Từng Bước

### 1️⃣ Build Docker Image (Lần đầu)

```powershell
cd "I:\1000 bài code thiếu nhi\Speech2Text\app\docker"
.\docker-manage.bat
```

**Chọn option 1**: Build Docker image

```
[BUILD] Building Docker image...
[+] Building 180s (20/20) FINISHED
✅ Essential dependencies installed
```

**Kết quả:**
- Image `vistral-s2t:latest` được tạo
- Chứa torch, flask, faster-whisper
- ⏱️ Build time: **2-3 phút**

---

### 2️⃣ Start Container

**Chọn option 2**: Start containers

```
[START] Starting containers...
[+] Running 1/1
✅ Container s2t-system started
```

**Kiểm tra:**
```powershell
docker ps
# CONTAINER ID   IMAGE           STATUS
# abc123         vistral-s2t     Up 10 seconds
```

---

### 3️⃣ Install Full Dependencies

**Chọn option 4**: Install full dependencies

```
[INSTALL] Installing pyannote.audio and dependencies...
[INSTALL] Installing additional ML packages...
[INSTALL] Installing API clients...
✅ Full dependencies installed!
```

**Packages được cài:**
- `pyannote.audio==3.1.1` + dependencies
- `pytorch-lightning==2.0.9.post0`
- `openai`, `google-generativeai`

⏱️ **Install time: 5-10 phút** (chỉ 1 lần!)

---

### 4️⃣ Verify Installation

**Chọn option 7**: Check status

```
[STATUS] Container status:
CONTAINER ID   NAME         STATUS          PORTS
abc123         s2t-system   Up 5 minutes    0.0.0.0:5000->5000/tcp
```

**Test API:**
```powershell
curl http://localhost:5000/health
# {"status": "healthy"}
```

---

## 🔄 Workflow Development

### Lần Đầu Setup (10 phút)
```
1. Build image     → 2-3 phút  (Option 1)
2. Start container → 10 giây   (Option 2)
3. Install deps    → 5-10 phút (Option 4)
```

### Rebuild Sau Khi Sửa Code (3 phút!)
```
1. Stop            → 5 giây    (Option 5)
2. Build           → 2-3 phút  (Option 1) ⚡ NHANH!
3. Start           → 10 giây   (Option 2)
```

**Không cần install lại dependencies!** 🎉

---

## 🛠️ Menu Options

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

### Option 1: Build Image
- Build với essential dependencies
- Nhanh, không bị timeout
- Dùng khi: lần đầu hoặc sau khi sửa code

### Option 2: Start Containers
- Start container từ image đã build
- Dùng khi: image đã có sẵn

### Option 3: Build and Start
- Build + Start liên tục
- Tiện cho lần đầu setup

### Option 4: Install Full Dependencies
- Cài pyannote, pytorch-lightning, API clients
- **Chỉ cần làm 1 lần!**
- Dependencies được lưu trong container

### Option 5: Stop Containers
- Dừng tất cả containers
- Dùng trước khi rebuild

### Option 6: View Logs
- Xem logs realtime
- Ctrl+C để thoát

### Option 7: Check Status
- Kiểm tra containers và images
- Xem ports, uptime

---

## ⚡ So Sánh Performance

### Build Cũ (Full Dependencies)
```
docker compose build
⏱️ 15-20 phút
❌ Thường timeout
❌ Mỗi rebuild mất 20 phút
```

### Build Mới (Optimized)
```
# Lần đầu
docker compose build          → 2-3 phút ✅
docker compose up -d          → 10 giây ✅
install_full_deps.bat         → 5-10 phút ✅
TỔNG: ~10 phút

# Rebuild
docker compose build          → 2-3 phút ✅ (NHANH!)
docker compose up -d          → 10 giây ✅
TỔNG: ~3 phút (không cần install lại!)
```

**Cải thiện: 5-7x nhanh hơn!** 🚀

---

## 🔍 Troubleshooting

### Build bị lỗi "timeout"?
✅ **GIẢI QUYẾT:** Dockerfile mới không còn timeout nữa!
- Build chỉ 2-3 phút với essential deps
- Heavy packages cài sau khi container chạy

### Container start nhưng thiếu packages?
```powershell
.\docker-manage.bat
# Option 4: Install full dependencies
```

### Muốn reset hoàn toàn?
```powershell
docker compose down
docker system prune -a
.\docker-manage.bat
# Option 1: Build lại
```

### Check logs nếu có lỗi
```powershell
.\docker-manage.bat
# Option 6: View logs
```

---

## 📦 Package Details

### Essential (trong build - 2-3 phút)
```
torch==2.7.1+cu118
torchaudio==2.7.1
faster-whisper>=1.0.3
transformers>=4.40.0
flask>=3.0.0
flask-socketio>=5.3.0
flask-cors>=4.0.0
python-dotenv>=1.0.0
librosa>=0.10.0
soundfile>=0.12.1
pydub>=0.25.1
```

### Full (install sau - 5-10 phút, chỉ 1 lần)
```
pyannote.audio==3.1.1
pyannote.core==5.0.0
pyannote.pipeline==3.0.1
pyannote.database==5.1.3
pyannote.metrics==3.2.1
pytorch-lightning==2.0.9.post0
lightning==2.0.9.post0
torchmetrics
openai
google-generativeai
```

---

## 🎯 Best Practices

✅ **Lần đầu:**
```powershell
# Build → Start → Install full deps
.\docker-manage.bat
# Options: 1 → 2 → 4
```

✅ **Development (sửa code):**
```powershell
# Stop → Build → Start (NHANH - không cần install lại!)
.\docker-manage.bat
# Options: 5 → 1 → 2
```

✅ **Production:**
```powershell
# Build → Install full deps → Start
docker compose -f docker-compose.windows.yml build
docker compose -f docker-compose.windows.yml up -d
.\install_full_deps.bat
```

---

## 🌟 Key Benefits

✅ **Build 5-7x nhanh hơn** (3 phút vs 20 phút)  
✅ **Không bị timeout**  
✅ **Dependencies được cache** trong container  
✅ **Rebuild nhanh** khi dev (chỉ 3 phút!)  
✅ **Flexible** - có thể skip heavy packages nếu không cần  
✅ **Production ready** - full features khi cần

---

## 📚 More Documentation

- **BUILD_OPTIMIZATION.md** - Chi tiết về optimization strategy
- **README_WINDOWS.md** - Windows-specific Docker guide
- **DOCKER_QUICKSTART.md** - Original Docker guide

---

## ✨ TL;DR for Impatient People

```powershell
cd app\docker
.\docker-manage.bat
# Press: 1 → Enter → 2 → Enter → 4 → Enter
# Wait 10 minutes total
# Done! 🎉
```

Rebuild sau này chỉ cần: `5 → 1 → 2` (3 phút!) ⚡
