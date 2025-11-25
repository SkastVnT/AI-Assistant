# 🔐 Google Drive Upload Setup Guide

## 📋 Overview

This guide shows you how to setup and use Google Drive API to upload files from AI-Assistant project.

## 🎯 Features

- ✅ Upload single files or entire folders
- ✅ OAuth 2.0 authentication (secure)
- ✅ Automatic folder creation
- ✅ Exclude patterns (skip cache, logs, etc.)
- ✅ Progress tracking
- ✅ Command-line interface
- ✅ Python API for custom scripts

## 🔧 Setup Instructions

### Step 1: Enable Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Navigate to **APIs & Services** → **Enable APIs and Services**
4. Search for "Google Drive API" and enable it

### Step 2: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. If prompted, configure OAuth consent screen:
   - User Type: **External**
   - App name: **AI-Assistant Drive Uploader**
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Leave default
   - Test users: Add your email
4. Back to Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: **AI-Assistant Desktop**
5. Click **CREATE**
6. Download the JSON file

### Step 3: Save Credentials

1. Rename the downloaded file to `google_oauth_credentials.json`
2. Move it to: `config/google_oauth_credentials.json`

```bash
# Example
mv ~/Downloads/client_secret_*.json config/google_oauth_credentials.json
```

### Step 4: Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Or install manually
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Step 5: First Run (Authentication)

```bash
python scripts/upload_to_drive.py --list
```

This will:
1. Open your browser
2. Ask you to login to Google
3. Grant permissions to the app
4. Save authentication token for future use

## 📖 Usage

### Command Line Interface

```bash
# Upload docs folder
python scripts/upload_to_drive.py --docs

# Upload scripts folder
python scripts/upload_to_drive.py --scripts

# Upload database folder
python scripts/upload_to_drive.py --database

# Upload all (docs + scripts + database)
python scripts/upload_to_drive.py --all

# Upload specific file
python scripts/upload_to_drive.py --file README.md

# Upload specific folder
python scripts/upload_to_drive.py --folder examples

# Create backup folder and upload
python scripts/upload_to_drive.py --all --backup-folder "AI-Assistant-Backup-2025-11-25"

# List files in Drive
python scripts/upload_to_drive.py --list
```

### Python API

```python
from src.utils.google_drive_uploader import GoogleDriveUploader

# Initialize
uploader = GoogleDriveUploader()

# Upload single file
result = uploader.upload_file("README.md")
print(f"Link: {result['webViewLink']}")

# Create folder and upload
folder_id = uploader.create_folder("My Backup")
uploader.upload_file("README.md", folder_id)

# Upload entire folder
result = uploader.upload_folder(
    "docs",
    exclude_patterns=['archives', '*.pyc', '__pycache__']
)
print(f"Uploaded {result['total_files']} files")
```

### Examples

See `examples/google_drive_upload.py` for 8 detailed examples:

```bash
python examples/google_drive_upload.py
```

## 🔒 Security

### Files Protected by .gitignore

These files are automatically ignored by git:

- ✅ `config/google_oauth_credentials.json` (OAuth credentials)
- ✅ `config/token.pickle` (Saved authentication)
- ✅ `config/credentials.json`
- ✅ `config/client_secret*.json`
- ✅ All `*_credentials.json` files

**Never commit these files to git!**

### Best Practices

1. **Keep credentials local** - Never share or commit
2. **Use test accounts** - During development
3. **Rotate credentials** - If compromised
4. **Limit scopes** - Only use `drive.file` scope (not full drive access)

## 📁 What Gets Uploaded

### Excluded by Default

The uploader automatically excludes:

- ✅ `__pycache__/` - Python cache
- ✅ `*.pyc` - Compiled Python
- ✅ `*.log` - Log files
- ✅ `venv*` - Virtual environments
- ✅ `.git/` - Git repository
- ✅ Archives (when uploading docs)

### Recommended Uploads

```bash
# 1. Documentation (without archives)
python scripts/upload_to_drive.py --docs

# 2. Scripts (without venv)
python scripts/upload_to_drive.py --scripts

# 3. Database (without logs)
python scripts/upload_to_drive.py --database

# 4. Create organized backup
python scripts/upload_to_drive.py --all --backup-folder "Backup-$(date +%Y-%m-%d)"
```

## 🎯 Common Use Cases

### 1. Daily Backup

```bash
# Create daily backup
python scripts/upload_to_drive.py --all --backup-folder "Daily-Backup-2025-11-25"
```

### 2. Share Documentation

```bash
# Upload only docs
python scripts/upload_to_drive.py --docs
```

### 3. Code Backup

```bash
# Upload scripts and examples
python scripts/upload_to_drive.py --scripts
python scripts/upload_to_drive.py --folder examples
```

### 4. Full Project Backup

```python
# Custom script for full backup
from src.utils.google_drive_uploader import GoogleDriveUploader
from datetime import datetime

uploader = GoogleDriveUploader()
backup_name = f"AI-Assistant-Full-{datetime.now().strftime('%Y%m%d')}"
backup_id = uploader.create_folder(backup_name)

# Upload important folders
for folder in ['docs', 'scripts', 'database', 'config', 'src']:
    result = uploader.upload_folder(folder, backup_id)
    print(f"✅ {folder}: {result['total_files']} files")
```

## ❓ Troubleshooting

### Error: Credentials not found

```bash
# Make sure file exists
ls config/google_oauth_credentials.json

# If not, download from Google Cloud Console
```

### Error: Invalid grant

```bash
# Delete saved token and re-authenticate
rm config/token.pickle
python scripts/upload_to_drive.py --list
```

### Error: Access denied

Make sure you:
1. Enabled Google Drive API in Cloud Console
2. Added your email as test user (if app not published)
3. Granted permissions during OAuth flow

### Browser doesn't open

```python
# Manual authentication
from src.utils.google_drive_uploader import GoogleDriveUploader
uploader = GoogleDriveUploader()
# Follow the link in terminal
```

## 📊 API Limits

Google Drive API has quotas:

- **Queries per day**: 1,000,000,000
- **Queries per 100 seconds**: 20,000
- **Queries per user per 100 seconds**: 1,000

For normal use, you won't hit these limits.

## 🔗 Resources

- [Google Drive API Documentation](https://developers.google.com/drive/api/v3/about-sdk)
- [OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [Python Quickstart](https://developers.google.com/drive/api/v3/quickstart/python)

## 📝 Notes

- First run requires browser authentication
- Token saved in `config/token.pickle` for future use
- Files uploaded have same name as local files
- Use `--backup-folder` to organize uploads
- Check Google Drive quota: [drive.google.com/settings/storage](https://drive.google.com/settings/storage)

---

**Setup Date**: November 25, 2025  
**Client ID**: 848804452532-4q60nntrkv81veih92s8hn4v0ns55u7v.apps.googleusercontent.com  
**Status**: ✅ Ready to use
