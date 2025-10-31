# 🔧 Hướng dẫn Reorganize Project

## ⚠️ QUAN TRỌNG: Đọc trước khi thực hiện!

Quá trình này sẽ:
- ✅ Tạo backup tự động
- ✅ Di chuyển files vào cấu trúc mới
- ✅ Xóa các file duplicate
- ✅ Làm gọn project

**Thời gian**: ~5-10 phút  
**Backup**: Tự động tạo trong `BACKUP_REORGANIZE/`

---

## 🚀 Cách thực hiện

### Bước 1: Backup thủ công (khuyến nghị)

```bash
# Tạo backup toàn bộ project
xcopy /E /I /Y "I:\1000 bài code thiếu nhi\Speech2Text" "I:\1000 bài code thiếu nhi\Speech2Text_BACKUP"
```

### Bước 2: Chạy reorganization scripts

```bash
# 1. Reorganize root level
.\reorganize.bat

# 2. Clean app directory
.\reorganize_app.bat
```

### Bước 3: Verify kết quả

```bash
# Kiểm tra cấu trúc mới
tree /F /A

# Test Web UI
.\scripts\start_webui.bat
```

### Bước 4: Update README

```bash
# Replace old README with new one
move /Y README_NEW.md README.md
```

---

## 📁 Cấu trúc SAU khi reorganize

```
Speech2Text/
├── 📂 scripts/              ← Tất cả .bat files
│   ├── start_webui.bat
│   ├── setup.bat
│   └── ...
│
├── 📂 docker/               ← Docker configs (moved from app/docker/)
│   ├── docker-compose.yml
│   ├── docker-compose.windows.yml
│   ├── Dockerfile
│   └── README_WINDOWS.md
│
├── 📂 tools/                ← Development tools (moved from app/tools/)
│   ├── test_cuda.py
│   ├── system_check.py
│   └── ...
│
├── 📂 docs/                 ← All documentation
│   ├── QUICKSTART.md       (was QUICKSTART_v3.5.md)
│   ├── INSTALLATION.md     (was INSTALLATION_SUCCESS.md)
│   ├── SUMMARY_VI.md
│   └── CONTRIBUTING.md
│
├── 📂 app/                  ← Cleaned application code
│   ├── web_ui.py
│   ├── core/
│   ├── api/
│   ├── config/
│   ├── templates/
│   └── tests/
│
├── 📂 data/                 ← Data (gitignored)
│   ├── audio/
│   ├── results/
│   ├── cache/
│   └── logs/
│
├── 📂 BACKUP_REORGANIZE/   ← Auto backup
│
├── .env
├── .gitignore
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## 🗑️ Files bị XÓA (duplicates)

- ❌ `audio/` (root) - duplicate với `data/audio/`
- ❌ `input_audio/` - duplicate
- ❌ `output/` (root) - duplicate với `data/results/`
- ❌ `core/` (root) - duplicate với `app/core/`
- ❌ `check.py` - duplicate với `app/scripts/check.py`
- ❌ `app/tools/web_ui.py` - duplicate với `app/web_ui.py`

---

## ✅ Files được DI CHUYỂN

### Scripts → scripts/
- `setup.bat`
- `start_webui.bat`
- `start_diarization.bat`
- `run_diarization_cli.bat`
- `fix_webui.bat`
- `install_webui_deps.bat`
- `rebuild_project.bat`

### Documentation → docs/
- `QUICKSTART_v3.5.md` → `docs/QUICKSTART.md`
- `INSTALLATION_SUCCESS.md` → `docs/INSTALLATION.md`
- `SUMMARY_VI.md` → `docs/SUMMARY_VI.md`
- `CONTRIBUTING.md` → `docs/CONTRIBUTING.md`
- `VERSION_3.5_UPGRADE_GUIDE.py` → `docs/`

### Docker → docker/
- `app/docker/*` → `docker/`

### Tools → tools/
- `app/tools/test_*.py` → `tools/`
- `app/tools/download_*.py` → `tools/`
- `app/tools/system_*.py` → `tools/`
- `app/tools/fix_*.py` → `tools/`
- `app/tools/patch_*.py` → `tools/`

---

## 🔄 Cần UPDATE sau khi reorganize

### 1. Update imports trong scripts/

Các file `.bat` trong `scripts/` cần update paths:

```batch
REM OLD
call app\s2t\Scripts\activate

REM NEW
call ..\app\s2t\Scripts\activate
```

### 2. Update Docker paths

File `docker/docker-compose.yml`:

```yaml
# OLD
context: ../../
dockerfile: app/docker/Dockerfile

# NEW
context: ../
dockerfile: docker/Dockerfile
```

### 3. Update README paths

Kiểm tra tất cả links trong README.md

---

## 🧪 Testing sau reorganize

```bash
# 1. Test virtual environment
.\app\s2t\Scripts\activate
python -c "import torch; print(torch.cuda.is_available())"

# 2. Test Web UI
.\scripts\start_webui.bat

# 3. Test Docker (if using)
cd docker
.\docker-manage.bat

# 4. Test imports
python -c "from app.core.llm import WhisperClient; print('OK')"
```

---

## 🆘 Rollback nếu có vấn đề

```bash
# Stop mọi thứ đang chạy
# Ctrl+C các terminals

# Restore from backup
rmdir /S /Q "I:\1000 bài code thiếu nhi\Speech2Text"
xcopy /E /I /Y "I:\1000 bài code thiếu nhi\Speech2Text_BACKUP" "I:\1000 bài code thiếu nhi\Speech2Text"
```

---

## ✅ Checklist hoàn thành

- [ ] Backup toàn bộ project
- [ ] Chạy `reorganize.bat`
- [ ] Chạy `reorganize_app.bat`
- [ ] Verify cấu trúc mới
- [ ] Update README.md
- [ ] Test Web UI
- [ ] Test Docker (nếu dùng)
- [ ] Commit changes
- [ ] Push to Git

---

## 💡 Tips

1. **Git commit từng bước**: Commit sau mỗi script để dễ rollback
2. **Test ngay sau mỗi bước**: Đừng đợi đến cuối
3. **Keep backup**: Giữ backup ít nhất 1 tuần
4. **Update documentation**: Cập nhật docs nếu thêm thay đổi

---

## 📞 Support

Nếu gặp vấn đề, kiểm tra:
1. Backup còn không? → Restore
2. Files bị thiếu? → Check BACKUP_REORGANIZE/
3. Import errors? → Update sys.path trong Python

---

**Chúc may mắn! 🚀**
