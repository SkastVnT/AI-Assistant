"""
Delete duplicate folders and re-upload docs with fixed structure
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.google_drive_uploader import GoogleDriveUploader

def main():
    print("🗑️  Cleaning up and re-uploading docs")
    print("=" * 60)
    
    # Target folder ID from Google Drive link
    target_folder_id = "1xnBv3jswbmQXRg7Vlob5RYFnXQXQfYMa"
    
    try:
        # Initialize uploader
        uploader = GoogleDriveUploader()
        
        # List current files in target folder
        print("\n📂 Listing current files...")
        files = uploader.list_files(target_folder_id, max_results=100)
        
        # Delete all items in target folder
        print(f"\n🗑️  Deleting {len(files)} duplicate items...")
        for file in files:
            try:
                uploader.service.files().delete(fileId=file['id']).execute()
                print(f"   ✅ Deleted: {file['name']}")
            except Exception as e:
                print(f"   ⚠️  Skip: {file['name']} - {e}")
        
        # Upload docs folder to target folder with fixed code
        print(f"\n📤 Uploading docs folder (fixed version)...")
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
