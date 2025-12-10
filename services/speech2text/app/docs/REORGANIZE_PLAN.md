# Project Reorganization Plan
## Mục tiêu: Làm gọn và tổ chức lại cấu trúc project

### 🎯 Cấu trúc MỚI đề xuất:

```
Speech2Text/
├── 📁 app/                          # Application source code
│   ├── __init__.py
│   ├── web_ui.py                    # Web UI entry point
│   │
│   ├── 📁 core/                     # Core business logic
│   │   ├── __init__.py
│   │   ├── 📁 llm/                  # LLM clients
│   │   │   ├── whisper_client.py
│   │   │   ├── phowhisper_client.py
│   │   │   ├── qwen_client.py
│   │   │   └── diarization_client.py
│   │   ├── 📁 utils/                # Utilities
│   │   ├── 📁 handlers/             # Error handlers
│   │   └── 📁 prompt_engineering/   # Prompt templates
│   │
│   ├── 📁 api/                      # API services (microservices)
│   ├── 📁 config/                   # Configuration files
│   ├── 📁 templates/                # HTML templates for Web UI
│   └── 📁 tests/                    # Unit tests
│
├── 📁 scripts/                      # Deployment & management scripts
│   ├── setup.bat                    # Initial setup
│   ├── start_webui.bat             # Start web UI
│   ├── run_diarization.bat         # Run CLI tools
│   └── docker-manage.bat           # Docker management
│
├── 📁 docker/                       # Docker configuration
│   ├── docker-compose.yml
│   ├── docker-compose.windows.yml
│   ├── Dockerfile
│   ├── .env
│   └── README_WINDOWS.md
│
├── 📁 docs/                         # Documentation
│   ├── README.md                    # Main docs
│   ├── QUICKSTART.md
│   ├── API_GUIDE.md
│   └── TROUBLESHOOTING.md
│
├── 📁 data/                         # Data directories (gitignored)
│   ├── audio/                       # Input audio files
│   ├── results/                     # Output results
│   ├── cache/                       # Model cache
│   └── logs/                        # Application logs
│
├── 📁 models/                       # Downloaded models (gitignored)
├── 📁 tools/                        # Development tools
│   ├── download_models.py
│   ├── test_cuda.py
│   └── system_check.py
│
├── .env                             # Environment variables
├── .gitignore                       # Git ignore rules
├── requirements.txt                 # Python dependencies
├── pytest.ini                       # Test configuration
└── README.md                        # Project overview
```

---

## 🗂️ Hành động cần thực hiện:

### 1. DI CHUYỂN FILES

#### A. Gộp các script vào thư mục `scripts/`
```
✅ MOVE: *.bat → scripts/
   - setup.bat
   - start_webui.bat
   - start_diarization.bat
   - run_diarization_cli.bat
   - fix_webui.bat
   - install_webui_deps.bat
   - rebuild_project.bat
```

#### B. Gộp documentation vào `docs/`
```
✅ MOVE: docs related files → docs/
   - QUICKSTART_v3.5.md → docs/QUICKSTART.md
   - INSTALLATION_SUCCESS.md → docs/INSTALLATION.md
   - SUMMARY_VI.md → docs/SUMMARY_VI.md
   - CONTRIBUTING.md → docs/CONTRIBUTING.md
```

#### C. Di chuyển Docker files
```
✅ MOVE: app/docker/ → docker/
   - Đưa docker config ra root level để dễ quản lý
```

#### D. Gộp tools
```
✅ MOVE: app/tools/*.py → tools/
   - Các utility scripts như test_cuda.py, system_check.py, etc.
```

#### E. Cleanup deprecated code
```
✅ DELETE or ARCHIVE:
   - deprecated/ → BACKUP_BEFORE_CLEANUP/deprecated/
   - core/ (root level, duplicate with app/core/)
   - app/src/ (nếu không dùng)
   - VERSION_3.5_UPGRADE_GUIDE.py (move to docs/)
```

### 2. XÓA FILES KHÔNG CẦN THIẾT

```
❌ DELETE:
   - audio/ (root level - duplicate)
   - input_audio/ (duplicate với data/audio/)
   - output/ (duplicate với data/results/)
   - check.py (duplicate với app/scripts/check.py)
   - app/tools/web_ui.py (duplicate với app/web_ui.py)
```

### 3. CẬP NHẬT IMPORTS

Sau khi di chuyển, cần update imports trong các file:
- Update paths in .bat scripts
- Update imports trong Python files
- Update Docker paths

### 4. CẬP NHẬT .GITIGNORE

```gitignore
# Add to .gitignore
data/audio/*
data/results/*
data/cache/*
data/logs/*
models/*
*.pyc
__pycache__/
.pytest_cache/
app/s2t/
.env
```

---

## 📊 Kết quả mong đợi:

- ✅ Cấu trúc rõ ràng, dễ navigate
- ✅ Không có duplicate files
- ✅ Scripts được tổ chức tốt
- ✅ Documentation tập trung
- ✅ Docker config ở root level
- ✅ Data folders được gitignore
- ✅ Dễ dàng onboard developers mới

---

## ⚠️ Lưu ý:

1. **Backup trước khi thực hiện**: BACKUP_BEFORE_CLEANUP/ đã có
2. **Test sau khi di chuyển**: Chạy lại Web UI và các scripts
3. **Update documentation**: Cập nhật paths trong README
4. **Git commit từng bước**: Commit sau mỗi nhóm thay đổi

---

**Bạn có muốn tôi thực hiện reorganization này không?**
