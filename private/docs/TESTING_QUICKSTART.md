# 🚀 Quick Start Guide - Testing AI-Assistant

## 📦 Cài Đặt Nhanh (5 phút)

### Bước 1: Cài đặt dependencies

```bash
# Kích hoạt virtual environment
.\venv\Scripts\activate  # Windows
# hoặc
source venv/bin/activate  # Linux/Mac

# Cài đặt test dependencies
pip install -r requirements-test.txt
```

### Bước 2: Chạy tests

**Cách Đơn Giản Nhất:**

```bash
# Windows
.\run-tests.bat

# Linux/Mac
./run-tests.sh
```

✅ Xong! Script sẽ tự động:
- Cài đặt dependencies
- Chạy tất cả tests
- Tạo coverage report
- Mở report trong browser

---

## 🎯 Các Lệnh Thường Dùng

### Chạy Tất Cả Tests

```bash
pytest
```

### Chạy Tests Theo Loại

```bash
# Unit tests (nhanh)
pytest -m unit

# Integration tests
pytest -m integration

# Smoke tests (kiểm tra cơ bản)
pytest -m smoke
```

### Chạy Tests Theo Service

```bash
# Hub Gateway tests
pytest tests/unit/test_hub.py

# ChatBot tests
pytest tests/unit/test_chatbot.py

# Text2SQL tests
pytest tests/unit/test_text2sql.py
```

### Với Coverage Report

```bash
pytest --cov=src --cov=ChatBot/src --cov-report=html
```

Xem report: Mở `htmlcov/index.html`

---

## 🎭 Mock Testing - Không Cần API Keys!

**Tất cả external services đều được mock:**

✅ Google Gemini API  
✅ OpenAI API  
✅ MongoDB  
✅ Stable Diffusion  
✅ ImgBB Upload  

**Bạn KHÔNG cần:**
- ❌ API keys thật
- ❌ Kết nối database
- ❌ Chạy các services
- ❌ Internet connection (cho unit tests)

**Tests chạy hoàn toàn offline và an toàn!**

---

## 📊 Hiểu Kết Quả Tests

### Kết quả PASSED

```
tests/unit/test_hub.py::TestHubGateway::test_index_route PASSED     [ 10%]
tests/unit/test_hub.py::TestHubGateway::test_api_services PASSED    [ 20%]
...
==================== 45 passed in 2.34s ====================
```

✅ **Tất cả OK!** Code hoạt động đúng với mock data.

### Kết quả FAILED

```
tests/unit/test_hub.py::TestHubGateway::test_something FAILED       [ 10%]

FAILED tests/unit/test_hub.py::TestHubGateway::test_something
AssertionError: assert 404 == 200
```

❌ **Test thất bại** - Cần fix code hoặc test.

### Coverage Report

```
Name                          Stmts   Miss  Cover
-------------------------------------------------
src/hub.py                       50      5    90%
src/handlers/error_handler.py    30      2    93%
src/utils/cache.py              45      8    82%
-------------------------------------------------
TOTAL                          125     15    88%
```

📊 **88% coverage** - Code được test tốt!

---

## 🎪 Ví Dụ: Khi Đã Có Tests, Làm Gì Tiếp?

### Scenario 1: Tests Pass ✅

```bash
$ pytest
==================== 45 passed in 2.34s ====================
```

**Bước tiếp theo:**

1. ✅ **Code đúng với mock data** - Tốt!
2. 🔄 **Test với real APIs** - Cấu hình .env với API keys thật
3. 🚀 **Deploy lên staging** - Test trong môi trường thực
4. 👥 **User testing** - Cho người dùng thử

### Scenario 2: Tests Fail ❌

```bash
$ pytest
FAILED tests/unit/test_hub.py::test_index_route
```

**Cách debug:**

```bash
# Chạy test với verbose để xem chi tiết
pytest -vv tests/unit/test_hub.py::test_index_route

# Hoặc chạy với pdb (debugger)
pytest --pdb tests/unit/test_hub.py::test_index_route
```

**Kiểm tra:**
1. ❓ Code có đúng logic không?
2. ❓ Test có expect đúng kết quả không?
3. ❓ Mock có setup đúng không?

### Scenario 3: Thêm Feature Mới

**Workflow chuẩn:**

```bash
# 1. Viết test trước (TDD - Test Driven Development)
# Tạo file: tests/unit/test_new_feature.py

# 2. Chạy test - Sẽ fail (vì chưa có code)
pytest tests/unit/test_new_feature.py

# 3. Viết code để pass test
# Edit: src/new_feature.py

# 4. Chạy lại test
pytest tests/unit/test_new_feature.py

# 5. Pass! ✅ Refactor nếu cần
```

---

## 🔧 Troubleshooting

### Lỗi: Module not found

```bash
# Đảm bảo đang ở thư mục gốc project
cd AI-Assistant

# Cài lại dependencies
pip install -r requirements.txt -r requirements-test.txt
```

### Lỗi: MongoDB connection failed

**Đây là bình thường!** Tests dùng mock MongoDB, không cần database thật.

Nếu vẫn lỗi, check `conftest.py` có patch MongoDB đúng chưa.

### Lỗi: API key invalid

**Đây cũng là bình thường!** Tests dùng mock API keys.

Environment variables trong tests được set tự động trong `conftest.py`.

---

## 📚 Tài Liệu Đầy Đủ

Xem chi tiết hơn:
- 📖 `tests/README.md` - Hướng dẫn đầy đủ
- 📄 `pytest.ini` - Cấu hình pytest
- 🔧 `tests/conftest.py` - Fixtures và setup

---

## 💡 Best Practices

### ✅ DO:

- ✅ Chạy tests trước khi commit code
- ✅ Viết tests cho mọi feature mới
- ✅ Duy trì coverage > 80%
- ✅ Test cả success và error cases
- ✅ Sử dụng mock cho external services

### ❌ DON'T:

- ❌ Commit code nếu tests fail
- ❌ Skip tests vì "lười"
- ❌ Test với API keys thật trong unit tests
- ❌ Để coverage giảm xuống
- ❌ Viết tests quá phức tạp

---

## 🎉 Kết Luận

**Test suite này giúp bạn:**

✅ Phát hiện bugs sớm  
✅ Tự tin refactor code  
✅ Tài liệu code (tests là documentation)  
✅ Dễ onboard developers mới  
✅ CI/CD ready  

**Chỉ cần 30 giây để chạy tất cả tests!**

```bash
.\run-tests.bat  # và chờ kết quả!
```

**Happy Testing! 🚀**
