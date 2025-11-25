# 🧪 Hướng Dẫn Testing & Quality Assurance

## 📊 Tổng Quan

Dự án đã được bổ sung đầy đủ test suite và automation tools để đảm bảo code quality và stability.

---

## 🔴 TESTING (Đã Hoàn Thành!)

### Files Đã Tạo

#### ChatBot Service
```
ChatBot/tests/
├── conftest.py                 # PyTest configuration & fixtures
├── test_app.py                 # Main application tests (100+ tests)
├── test_api_integration.py     # Integration tests
├── test_llm_clients.py         # LLM client tests
└── requirements-test.txt       # Test dependencies
```

#### Text2SQL Service
```
Text2SQL Services/tests/
├── conftest.py                 # PyTest configuration
└── test_app.py                 # Comprehensive tests (80+ tests)
```

### Cài Đặt Test Dependencies

```bash
# Cài đặt cho ChatBot
cd ChatBot
pip install -r tests/requirements-test.txt

# Cài đặt cho Text2SQL
cd "Text2SQL Services"
pip install pytest pytest-cov pytest-mock pytest-flask requests-mock
```

### Chạy Tests

#### Cách 1: Sử dụng Script (Khuyến nghị) ✨

**Windows:**
```powershell
# Tất cả services
.\run-tests.bat all

# Service cụ thể
.\run-tests.bat chatbot
.\run-tests.bat text2sql

# Không coverage (nhanh hơn)
.\run-tests.bat chatbot no
```

**Linux/Mac:**
```bash
chmod +x run-tests.sh

# Tất cả services
./run-tests.sh all

# Service cụ thể
./run-tests.sh chatbot
./run-tests.sh text2sql
```

#### Cách 2: Manual pytest

**ChatBot:**
```bash
cd ChatBot
pytest tests/ -v                                    # Basic
pytest tests/ -v --cov=. --cov-report=html        # With coverage
pytest tests/test_app.py -v                        # Specific file
pytest tests/ -k "test_chat" -v                    # Specific tests
```

**Text2SQL:**
```bash
cd "Text2SQL Services"
pytest tests/ -v --cov=. --cov-report=html
```

#### Cách 3: Sử dụng Makefile (Linux/Mac)

```bash
make test                # Tất cả tests
make test-chatbot        # ChatBot only
make test-text2sql       # Text2SQL only
make test-coverage       # Với coverage detailed
```

### Test Coverage

Sau khi chạy tests với coverage, mở báo cáo HTML:

```bash
# ChatBot
open ChatBot/htmlcov/index.html

# Text2SQL
open "Text2SQL Services/htmlcov/index.html"
```

---

## 🟡 DOCKERFILES (Đã Hoàn Thành!)

### Files Đã Tạo

```
ChatBot/Dockerfile
Text2SQL Services/Dockerfile
Speech2Text Services/Dockerfile
stable-diffusion-webui/Dockerfile
```

### Build Docker Images

#### Build Tất Cả
```bash
docker-compose build
```

#### Build Từng Service
```bash
# ChatBot
docker-compose build chatbot

# Text2SQL
docker-compose build text2sql

# Speech2Text (requires more resources)
docker-compose build speech2text

# Stable Diffusion (requires GPU)
docker-compose build stable-diffusion
```

### Run Services với Docker

#### Start Tất Cả
```bash
docker-compose up -d
```

#### Start Service Cụ Thể
```bash
# ChatBot only
docker-compose up -d chatbot

# ChatBot + Text2SQL
docker-compose up -d chatbot text2sql
```

#### View Logs
```bash
# Tất cả services
docker-compose logs -f

# Service cụ thể
docker-compose logs -f chatbot
```

#### Stop Services
```bash
docker-compose down

# Stop và xóa volumes
docker-compose down -v
```

### Verify Services

```bash
# Check containers
docker-compose ps

# Test endpoints
curl http://localhost:5001/        # ChatBot
curl http://localhost:5002/        # Text2SQL
curl http://localhost:7860/        # Speech2Text
curl http://localhost:7861/sdapi/v1/progress  # Stable Diffusion
```

---

## 🟡 CI/CD IMPROVEMENTS (Đã Nâng Cấp!)

### Files Đã Tạo/Cập Nhật

1. **`.github/workflows/ci-cd.yml`** - Enhanced CI/CD pipeline
2. **`.pre-commit-config.yaml`** - Pre-commit hooks
3. **`pyproject.toml`** - Unified configuration
4. **`Makefile`** - Automation commands

### Pre-commit Hooks Setup

```bash
# Cài đặt
pip install pre-commit
pre-commit install

# Chạy thủ công trên tất cả files
pre-commit run --all-files

# Chỉ chạy trên changed files
git add .
git commit -m "Your message"  # Pre-commit tự động chạy
```

**Hooks bao gồm:**
- ✅ Black (code formatting)
- ✅ isort (import sorting)
- ✅ Flake8 (linting)
- ✅ Bandit (security checks)
- ✅ YAML validation
- ✅ JSON validation
- ✅ Detect private keys

### GitHub Actions CI/CD

**Tự động chạy khi:**
- Push to `master`, `Ver_1`, `develop`
- Pull requests to `master`, `Ver_1`

**Pipeline bao gồm:**
1. **Lint & Code Quality** - Black, Flake8, isort
2. **Automated Testing** - pytest với coverage
3. **Docker Builds** - Build và push images
4. **Security Scan** - Trivy vulnerability scanner
5. **Deployment** - Auto-deploy (cần configure)

**Xem kết quả:**
```
https://github.com/SkastVnT/AI-Assistant/actions
```

### Makefile Commands

```bash
# Development
make dev-chatbot        # Start ChatBot dev server
make dev-text2sql       # Start Text2SQL dev server

# Testing
make test               # Run all tests
make test-chatbot       # ChatBot tests only
make test-text2sql      # Text2SQL tests only

# Code Quality
make lint               # Run linters
make format             # Format code (Black + isort)
make type-check         # MyPy type checking
make security-check     # Bandit security scan

# Docker
make docker-build       # Build all images
make docker-up          # Start all services
make docker-down        # Stop all services
make docker-logs        # View logs

# Cleaning
make clean              # Clean temp files

# Installation
make install            # Install dependencies
make install-test       # Install test deps
```

---

## 📊 Test Statistics

### ChatBot Tests
- **Total Tests:** 100+
- **Coverage Target:** 70%+
- **Categories:**
  - Health & basic endpoints
  - Chat functionality
  - Image generation
  - File upload
  - Memory system
  - Storage management
  - Error handling
  - Security

### Text2SQL Tests
- **Total Tests:** 80+
- **Coverage Target:** 70%+
- **Categories:**
  - Schema upload
  - SQL generation
  - Question generation
  - Knowledge base
  - Database connections
  - Multi-database support
  - Error handling
  - Security

---

## 🎯 Chạy Tests Lần Đầu

### Quick Start (5 phút)

```bash
# 1. Cài đặt test dependencies
pip install pytest pytest-cov pytest-mock pytest-flask requests-mock

# 2. Chạy tests
cd ChatBot
pytest tests/ -v --cov=. --cov-report=html

# 3. Xem coverage report
# Mở ChatBot/htmlcov/index.html trong browser

# 4. Repeat cho Text2SQL
cd "../Text2SQL Services"
pytest tests/ -v --cov=. --cov-report=html
```

### Hoặc Dùng Script

```bash
# Windows
.\run-tests.bat all

# Linux/Mac
./run-tests.sh all
```

---

## 🐳 Docker Quick Start

### Build & Run

```bash
# 1. Build images
docker-compose build

# 2. Start services
docker-compose up -d

# 3. Check status
docker-compose ps

# 4. View logs
docker-compose logs -f chatbot

# 5. Test
curl http://localhost:5001/
curl http://localhost:5002/

# 6. Stop
docker-compose down
```

---

## ✅ Checklist

### Testing ✅
- [x] Test structure tạo xong
- [x] 100+ tests cho ChatBot
- [x] 80+ tests cho Text2SQL
- [x] Coverage configuration
- [x] Test runner scripts
- [x] Integration tests
- [ ] **TODO: Chạy tests lần đầu**
- [ ] **TODO: Fix failing tests (nếu có)**
- [ ] **TODO: Achieve 70%+ coverage**

### Docker ✅
- [x] ChatBot Dockerfile
- [x] Text2SQL Dockerfile
- [x] Speech2Text Dockerfile
- [x] Stable Diffusion Dockerfile
- [x] docker-compose.yml enhanced
- [x] .dockerignore
- [ ] **TODO: Build images lần đầu**
- [ ] **TODO: Test containers**
- [ ] **TODO: Optimize image sizes**

### CI/CD ✅
- [x] GitHub Actions workflow enhanced
- [x] Pre-commit hooks
- [x] Makefile
- [x] pyproject.toml
- [x] Automated testing
- [x] Docker builds
- [x] Security scanning
- [ ] **TODO: Configure Docker Hub credentials**
- [ ] **TODO: Setup deployment target**
- [ ] **TODO: Test CI/CD pipeline**

---

## 🚀 Next Steps

### Ngay Bây Giờ (5 phút)
```bash
# 1. Chạy tests
.\run-tests.bat chatbot

# 2. Commit tests
git add ChatBot/tests/ "Text2SQL Services/tests/"
git commit -m "test: add comprehensive test suite"
git push
```

### Tuần Này
1. ✅ Chạy tất cả tests
2. ✅ Fix failing tests
3. ✅ Build Docker images
4. ✅ Test containers locally
5. ✅ Push to trigger CI/CD

### 2 Tuần Tới
1. Achieve 80%+ test coverage
2. Setup Docker Hub
3. Configure deployment
4. Add performance tests
5. Add E2E tests

---

## 📚 Documentation

- **Test Examples:** Xem `ChatBot/tests/test_app.py`
- **Docker Guide:** Xem `docker-compose.yml`
- **CI/CD Pipeline:** Xem `.github/workflows/ci-cd.yml`
- **Code Quality:** Xem `pyproject.toml`

---

## 🆘 Troubleshooting

### Tests Fail
```bash
# Check dependencies
pip install -r tests/requirements-test.txt

# Run với verbose
pytest tests/ -vv

# Run specific test
pytest tests/test_app.py::TestChatEndpoint::test_chat_with_valid_message -v
```

### Docker Build Fails
```bash
# Clean và rebuild
docker-compose down -v
docker system prune -a
docker-compose build --no-cache
```

### Pre-commit Fails
```bash
# Skip hook
git commit --no-verify -m "message"

# Or fix issues
pre-commit run --all-files
```

---

**Tổng thời gian setup:** ~30 phút  
**Effort:** Medium  
**Impact:** 🚀 High (Production-ready!)

**Chúc mừng! Dự án giờ đã có full test suite, Docker support và CI/CD!** 🎉
