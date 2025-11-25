"""
Upload docs to specific Google Drive folder
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.google_drive_uploader import GoogleDriveUploader

def main():
    print("🚀 Uploading docs to Google Drive")
    print("=" * 60)
    
    # Target folder ID from Google Drive link
    target_folder_id = "1xnBv3jswbmQXRg7Vlob5RYFnXQXQfYMa"
    
    try:
        # Initialize uploader
        uploader = GoogleDriveUploader()
        
        # Upload docs folder to target folder
        print(f"\n📤 Uploading docs folder...")
        print(f"   Target: https://drive.google.com/drive/folders/{target_folder_id}")
        
        result = uploader.upload_folder(
            "docs",
            parent_folder_id=target_folder_id,
            exclude_patterns=['__pycache__', '*.pyc', '*.log']
        )
        
        print("\n" + "=" * 60)
        print(f"✅ Upload complete!")
        print(f"   Folder: {result['folder_name']}")
        print(f"   Files uploaded: {result['total_files']}")
        print(f"\n🔗 View at: https://drive.google.com/drive/folders/{target_folder_id}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
