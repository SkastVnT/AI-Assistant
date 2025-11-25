"""
Quick script to upload files/folders to Google Drive
Usage: python scripts/upload_to_drive.py [options]
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.google_drive_uploader import (
    GoogleDriveUploader,
    quick_upload_docs,
    quick_upload_scripts,
    quick_upload_database
)


def main():
    parser = argparse.ArgumentParser(
        description='Upload files and folders to Google Drive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload docs folder
  python scripts/upload_to_drive.py --docs
  
  # Upload scripts folder
  python scripts/upload_to_drive.py --scripts
  
  # Upload database folder
  python scripts/upload_to_drive.py --database
  
  # Upload all
  python scripts/upload_to_drive.py --all
  
  # Upload specific file
  python scripts/upload_to_drive.py --file README.md
  
  # Upload specific folder
  python scripts/upload_to_drive.py --folder examples
  
  # Create backup folder and upload
  python scripts/upload_to_drive.py --all --backup-folder "AI-Assistant-Backup-2025-11-25"
        """
    )
    
    parser.add_argument('--docs', action='store_true', help='Upload docs folder')
    parser.add_argument('--scripts', action='store_true', help='Upload scripts folder')
    parser.add_argument('--database', action='store_true', help='Upload database folder')
    parser.add_argument('--all', action='store_true', help='Upload docs, scripts, and database')
    parser.add_argument('--file', type=str, help='Upload specific file')
    parser.add_argument('--folder', type=str, help='Upload specific folder')
    parser.add_argument('--backup-folder', type=str, help='Create backup folder in Drive')
    parser.add_argument('--list', action='store_true', help='List files in Drive')
    
    args = parser.parse_args()
    
    # Show help if no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    try:
        print("🚀 Google Drive Upload Tool")
        print("=" * 60)
        
        # Initialize uploader
        uploader = GoogleDriveUploader()
        
        # Create backup folder if specified
        backup_folder_id = None
        if args.backup_folder:
            print(f"\n📁 Creating backup folder: {args.backup_folder}")
            backup_folder_id = uploader.create_folder(args.backup_folder)
            print(f"✅ Backup folder created (ID: {backup_folder_id})")
        
        # List files
        if args.list:
            print("\n📂 Listing files in Drive:")
            uploader.list_files(backup_folder_id)
        
        # Upload specific file
        if args.file:
            file_path = project_root / args.file
            print(f"\n📤 Uploading file: {file_path}")
            result = uploader.upload_file(str(file_path), backup_folder_id)
            print(f"✅ Upload complete!")
            print(f"   Link: {result.get('webViewLink')}")
        
        # Upload specific folder
        if args.folder:
            folder_path = project_root / args.folder
            print(f"\n📤 Uploading folder: {folder_path}")
            result = uploader.upload_folder(str(folder_path), backup_folder_id)
            print(f"✅ Upload complete! {result['total_files']} files uploaded")
        
        # Upload docs
        if args.docs or args.all:
            print("\n📚 Uploading docs folder...")
            result = quick_upload_docs(uploader)
            if backup_folder_id and result.get('folder_id'):
                # Move to backup folder (optional enhancement)
                pass
            print(f"✅ Docs uploaded! {result['total_files']} files")
        
        # Upload scripts
        if args.scripts or args.all:
            print("\n🔧 Uploading scripts folder...")
            result = quick_upload_scripts(uploader)
            print(f"✅ Scripts uploaded! {result['total_files']} files")
        
        # Upload database
        if args.database or args.all:
            print("\n🗄️  Uploading database folder...")
            result = quick_upload_database(uploader)
            print(f"✅ Database uploaded! {result['total_files']} files")
        
        print("\n" + "=" * 60)
        print("✅ All uploads completed successfully!")
        print("🔗 Access your files at: https://drive.google.com")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Setup Instructions:")
        print("1. Go to Google Cloud Console: https://console.cloud.google.com")
        print("2. Create a new project or select existing")
        print("3. Enable Google Drive API")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download credentials JSON")
        print("6. Save as: config/google_oauth_credentials.json")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
