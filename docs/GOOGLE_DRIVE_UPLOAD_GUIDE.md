# 📤 Google Drive Upload Guide

## Tổng quan

Script `upload_docs_to_drive.py` cho phép upload toàn bộ documentation từ tất cả các service trong dự án lên Google Drive một cách tự động và thông minh.

## ✨ Tính năng

### 1. **Upload thông minh (Smart Upload)**
- ✅ Tự động kiểm tra file đã tồn tại
- ✅ Chỉ upload file mới hoặc đã thay đổi
- ✅ Tránh upload trùng lặp
- ✅ Tiết kiệm thời gian và băng thông

### 2. **Đặt tên folder theo ngày**
- ✅ Format: `{folder_name}_{YYYY-MM-DD}`
- ✅ Dễ dàng theo dõi lịch sử upload
- ✅ Tránh trùng tên folder
- ✅ Ví dụ: `docs_2025-12-01`, `ChatBot_docs_2025-12-01`

### 3. **Bảo mật với .env**
- ✅ Google Drive URL được lưu trong `.env`
- ✅ Không hardcode link trong source code
- ✅ Dễ dàng thay đổi folder đích

### 4. **Upload nhiều service**
Upload docs từ tất cả các service:
- `docs/` - Main Documentation
- `ChatBot/docs/` - ChatBot Documentation
- `Speech2Text Services/docs/` - Speech2Text Documentation
- `Text2SQL Services/docs/` - Text2SQL Documentation
- `train_LoRA_tool/docs/` - Train LoRA Tool Documentation

## 🚀 Cài đặt

### Bước 1: Cấu hình .env

Thêm Google Drive URL vào file `.env`:

```bash
# Google Drive Upload Configuration
GOOGLE_DRIVE_UPLOAD_URL=https://drive.google.com/drive/folders/...YOUR_FOLDER_ID...
```

**Cách lấy folder ID:**
1. Mở folder trong Google Drive
2. URL sẽ có dạng: `https://drive.google.com/drive/folders/YOUR_FOLDER_ID`
3. Copy toàn bộ URL hoặc chỉ FOLDER_ID

### Bước 2: Cấu hình Google OAuth

Xem hướng dẫn chi tiết tại: [GOOGLE_DRIVE_SETUP.md](./GOOGLE_DRIVE_SETUP.md)

Tóm tắt:
1. Tạo project trong Google Cloud Console
2. Enable Google Drive API
3. Tạo OAuth 2.0 credentials
4. Download file `credentials.json`
5. Đổi tên thành `google_oauth_credentials.json`
6. Đặt vào thư mục `config/`

### Bước 3: Cài đặt dependencies

```bash
pip install -r requirements.txt
```

Đảm bảo có các package:
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `google-api-python-client`
- `python-dotenv`

## 📖 Sử dụng

### Upload tất cả docs

```bash
python upload_docs_to_drive.py
```

### Kết quả

```
🚀 Uploading all docs folders to Google Drive
============================================================
📁 Target folder ID: 1xnBv3jswbmQXRg7Vlob5RYFnXQXQfYMa
✅ Authenticated with Google Drive

📤 Uploading Main Documentation...
   Source: docs
   Target: https://drive.google.com/drive/folders/...YOUR_FOLDER
📁 Created folder: docs_2025-12-01
✅ Uploaded: README.md (0.05 MB)
⏭️  Skipped (exists): API_DOCUMENTATION.md
   ✅ 15 files uploaded, 8 skipped from docs_2025-12-01

📤 Uploading ChatBot Documentation...
   Source: ChatBot/docs
   ✅ 12 files uploaded, 3 skipped from docs_2025-12-01

============================================================
✅ Upload complete!

📊 Summary:
   • Main Documentation: 15 uploaded, 8 skipped
   • ChatBot Documentation: 12 uploaded, 3 skipped
   • Speech2Text Documentation: 8 uploaded, 2 skipped
   • Text2SQL Documentation: 10 uploaded, 5 skipped
   • Train LoRA Tool Documentation: 18 uploaded, 7 skipped

   Total files uploaded: 63

🔗 View at: https://drive.google.com/drive/folders/...YOUR_FOLDER_ID...
```

## 🔧 Tùy chỉnh

### Thay đổi folder đích

Chỉnh sửa trong `.env`:

```bash
GOOGLE_DRIVE_UPLOAD_URL=https://drive.google.com/drive/folders/NEW_FOLDER_ID
```

### Thêm service mới

Chỉnh sửa file `upload_docs_to_drive.py`:

```python
docs_folders = [
    ("docs", "Main Documentation"),
    ("ChatBot/docs", "ChatBot Documentation"),
    ("YourNewService/docs", "Your New Service Documentation"),  # Thêm dòng này
]
```

### Tùy chỉnh exclude patterns

```python
result = uploader.upload_folder_smart(
    folder_path,
    parent_folder_id=target_folder_id,
    custom_folder_name=folder_name,
    exclude_patterns=['__pycache__', '*.pyc', '*.log', 'venv*', '*.git*', '*.tmp']  # Thêm pattern
)
```

## 🛡️ Bảo mật

### File .env
- ✅ Đã được thêm vào `.gitignore`
- ✅ Không commit lên Git
- ✅ Chỉ lưu local

### OAuth Token
- ✅ Token được lưu tại `config/token.pickle`
- ✅ Tự động refresh khi hết hạn
- ✅ Không cần login lại mỗi lần

## 🐛 Xử lý lỗi

### Lỗi: GOOGLE_DRIVE_UPLOAD_URL not found

```bash
❌ Error: GOOGLE_DRIVE_UPLOAD_URL not found in .env file
   Please add: GOOGLE_DRIVE_UPLOAD_URL=https://drive.google.com/drive/folders/YOUR_FOLDER_ID
```

**Giải pháp:** Thêm config vào file `.env`

### Lỗi: Google OAuth credentials not found

```bash
❌ Google OAuth credentials not found at: config/google_oauth_credentials.json
```

**Giải pháp:** Xem [GOOGLE_DRIVE_SETUP.md](./GOOGLE_DRIVE_SETUP.md)

### Lỗi: Permission denied

**Giải pháp:** 
1. Kiểm tra quyền truy cập folder trên Google Drive
2. Đảm bảo account đã được share quyền edit/upload

## 📝 API Reference

### GoogleDriveUploader Methods

#### `upload_folder_smart()`

Upload folder với kiểm tra file tồn tại:

```python
result = uploader.upload_folder_smart(
    folder_path="docs",                    # Đường dẫn folder local
    parent_folder_id="FOLDER_ID",          # ID folder đích trên Drive
    custom_folder_name="docs_2025-12-01", # Tên custom (optional)
    exclude_patterns=['*.pyc', 'venv*'],   # Patterns bỏ qua
    skip_existing=True                     # Skip file đã tồn tại
)
```

**Returns:**
```python
{
    'folder_id': 'CREATED_FOLDER_ID',
    'folder_name': 'docs_2025-12-01',
    'uploaded_files': [...],           # List file đã upload
    'skipped_files': [...],            # List file bỏ qua
    'total_files': 15,                 # Tổng file upload
    'total_skipped': 8                 # Tổng file skip
}
```

#### `get_existing_files()`

Lấy danh sách file đã có trong folder:

```python
existing = uploader.get_existing_files(folder_id="FOLDER_ID")
# Returns: {'filename.txt': {...file_metadata...}, ...}
```

## 🎯 Best Practices

1. **Upload định kỳ**
   - Upload docs sau mỗi update lớn
   - Tự động backup định kỳ

2. **Kiểm tra kết quả**
   - Xem summary sau mỗi lần upload
   - Verify trên Google Drive

3. **Quản lý folder**
   - Xóa folder cũ không cần thiết
   - Giữ 2-3 version gần nhất

4. **Bảo mật**
   - Không share `.env` file
   - Không commit `token.pickle`
   - Giữ credentials an toàn

## 📚 Tài liệu liên quan

- [GOOGLE_DRIVE_SETUP.md](./GOOGLE_DRIVE_SETUP.md) - Cấu hình Google Drive API
- [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) - Cấu trúc dự án
- [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - API documentation

## ❓ FAQ

**Q: Mỗi lần chạy có tạo folder mới không?**  
A: Có, mỗi ngày sẽ tạo folder mới với suffix ngày tháng (ví dụ: `docs_2025-12-01`)

**Q: Làm sao biết file nào đã upload?**  
A: Script tự động kiểm tra dựa trên tên và size file. File giống nhau sẽ bị skip.

**Q: Có thể upload chỉ 1 service không?**  
A: Có, chỉnh sửa list `docs_folders` trong script.

**Q: Upload có tốn quota Google Drive không?**  
A: Có, nhưng với smart upload, chỉ upload file mới nên tiết kiệm quota.

## 🔄 Changelog

### v2.0 - 2025-12-01
- ✨ Thêm smart upload với check file tồn tại
- ✨ Đặt tên folder theo ngày
- ✨ Config qua .env
- ✨ Support upload nhiều service

### v1.0 - 2025-11-30
- 🎉 Initial release
- ✅ Basic upload functionality
