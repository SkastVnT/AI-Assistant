# 📤 Quick Start: Google Drive Upload

Upload your docs, scripts, and database to Google Drive in 3 steps!

## 🚀 Quick Setup

### 1. Get credentials from your browser downloads:
```bash
# File already moved to correct location
# config/google_oauth_credentials.json ✅
```

### 2. Install dependencies:
```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

### 3. Upload!
```bash
# Upload docs
python scripts/upload_to_drive.py --docs

# Upload scripts
python scripts/upload_to_drive.py --scripts

# Upload database
python scripts/upload_to_drive.py --database

# Upload all
python scripts/upload_to_drive.py --all
```

## 📚 Examples

```bash
# Create backup with date
python scripts/upload_to_drive.py --all --backup-folder "Backup-2025-11-25"

# Upload specific file
python scripts/upload_to_drive.py --file README.md

# Upload specific folder
python scripts/upload_to_drive.py --folder examples

# List files in Drive
python scripts/upload_to_drive.py --list
```

## 🔒 Security

Your credentials are protected:
- ✅ Added to `.gitignore`
- ✅ Never committed to git
- ✅ OAuth 2.0 secure authentication

## 📖 Full Documentation

See [GOOGLE_DRIVE_UPLOAD_GUIDE.md](docs/guides/GOOGLE_DRIVE_UPLOAD_GUIDE.md) for complete guide.

## 💡 Python API

```python
from src.utils.google_drive_uploader import GoogleDriveUploader

uploader = GoogleDriveUploader()

# Upload file
uploader.upload_file("README.md")

# Upload folder
uploader.upload_folder("docs")

# Create folder
folder_id = uploader.create_folder("My Backup")
```

---

**Ready to use!** 🎉
