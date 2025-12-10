# 🔧 Scripts Directory

Utility scripts and tools for AI Assistant project.

## 📁 Structure

```
scripts/
├── check_system.py           # System requirements checker
├── utilities/                # Utility scripts
│   └── upload_docs_to_drive.py  # Google Drive uploader
├── archive/                  # Old scripts (deprecated)
└── deprecated/               # Legacy test scripts
```

## 📜 Active Scripts

### check_system.py
System requirements and environment checker.

**Usage:**
```bash
python scripts/check_system.py
```

**Checks:**
- Python version
- CUDA availability
- Required packages
- Disk space
- Memory

### utilities/upload_docs_to_drive.py
Upload documentation to Google Drive.

**Usage:**
```bash
python scripts/utilities/upload_docs_to_drive.py
```

## 📦 Archived Scripts

Old startup and setup scripts have been moved to:
- `archive/` - Old startup scripts
- `deprecated/` - Legacy test scripts

These are kept for reference but are no longer actively used.

## 🚀 New Script System

All service management scripts are now in the **root directory**:

- Individual service launchers: `start-*.bat`
- Batch operations: `start-all.bat`, `stop-all.bat`
- Utilities: `menu.bat`, `setup-all.bat`, `test-all.bat`, `clean-logs.bat`

See [SCRIPTS_GUIDE.md](../SCRIPTS_GUIDE.md) for complete documentation.

---

**Note:** This directory is now minimal and focused. Most operational scripts have been moved to the root for easier access.
