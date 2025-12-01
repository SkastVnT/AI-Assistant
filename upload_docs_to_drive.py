"""
Upload docs to specific Google Drive folder
"""

import sys
import os
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from src.utils.google_drive_uploader import GoogleDriveUploader

def extract_folder_id(url: str) -> str:
    """Extract folder ID from Google Drive URL"""
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return url  # Assume it's already an ID

def main():
    print("🚀 Uploading all docs folders to Google Drive")
    print("=" * 60)
    
    # Get target folder ID from environment variable
    drive_url = os.getenv('GOOGLE_DRIVE_UPLOAD_URL')
    if not drive_url:
        print("❌ Error: GOOGLE_DRIVE_UPLOAD_URL not found in .env file")
        print("   Please add: GOOGLE_DRIVE_UPLOAD_URL=https://drive.google.com/drive/folders/YOUR_FOLDER_ID")
        sys.exit(1)
    
    target_folder_id = extract_folder_id(drive_url)
    print(f"📁 Target folder ID: {target_folder_id}")
    
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
        
        # Get current date for folder naming
        current_date = datetime.now().strftime("%Y-%m-%d")
        
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
                # Create folder name with date
                folder_name = f"{Path(folder_path).name}_{current_date}"
                
                result = uploader.upload_folder_smart(
                    folder_path,
                    parent_folder_id=target_folder_id,
                    custom_folder_name=folder_name,
                    exclude_patterns=['__pycache__', '*.pyc', '*.log', 'venv*', '*.git*']
                )
                
                total_files_uploaded += result['total_files']
                successful_uploads.append({
                    'description': description,
                    'folder': result['folder_name'],
                    'files': result['total_files'],
                    'skipped': result['total_skipped']
                })
                
                print(f"   ✅ {result['total_files']} files uploaded, {result['total_skipped']} skipped from {result['folder_name']}")
                
            except Exception as e:
                print(f"   ❌ Error uploading {description}: {e}")
                continue
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"✅ Upload complete!")
        print(f"\n📊 Summary:")
        for upload in successful_uploads:
            print(f"   • {upload['description']}: {upload['files']} uploaded, {upload['skipped']} skipped")
        print(f"\n   Total files uploaded: {total_files_uploaded}")
        print(f"\n🔗 View at: https://drive.google.com/drive/folders/{target_folder_id}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
