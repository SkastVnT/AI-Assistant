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
    print("🚀 Uploading all docs folders to Google Drive")
    print("=" * 60)
    
    # Target folder ID from Google Drive link
    target_folder_id = "1xnBv3jswbmQXRg7Vlob5RYFnXQXQfYMa"
    
    # Define all docs folders to upload
    docs_folders = [
        ("docs", "Main Documentation"),
        ("ChatBot/docs", "ChatBot Documentation"),
        ("Speech2Text Services/docs", "Speech2Text Documentation"),
        ("Text2SQL Services/docs", "Text2SQL Documentation"),
        ("train_LoRA_tool/docs", "Train LoRA Tool Documentation"),
    ]
    
    try:
        # Initialize uploader
        uploader = GoogleDriveUploader()
        
        total_files_uploaded = 0
        successful_uploads = []
        
        # Upload each docs folder
        for folder_path, description in docs_folders:
            full_path = project_root / folder_path
            
            # Check if folder exists
            if not full_path.exists():
                print(f"\n⚠️  Skipping {description}: folder not found at {folder_path}")
                continue
            
            print(f"\n📤 Uploading {description}...")
            print(f"   Source: {folder_path}")
            print(f"   Target: https://drive.google.com/drive/folders/{target_folder_id}")
            
            try:
                result = uploader.upload_folder(
                    folder_path,
                    parent_folder_id=target_folder_id,
                    exclude_patterns=['__pycache__', '*.pyc', '*.log', 'venv*', '*.git*']
                )
                
                total_files_uploaded += result['total_files']
                successful_uploads.append({
                    'description': description,
                    'folder': result['folder_name'],
                    'files': result['total_files']
                })
                
                print(f"   ✅ {result['total_files']} files uploaded from {result['folder_name']}")
                
            except Exception as e:
                print(f"   ❌ Error uploading {description}: {e}")
                continue
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"✅ Upload complete!")
        print(f"\n📊 Summary:")
        for upload in successful_uploads:
            print(f"   • {upload['description']}: {upload['files']} files")
        print(f"\n   Total files uploaded: {total_files_uploaded}")
        print(f"\n🔗 View at: https://drive.google.com/drive/folders/{target_folder_id}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
