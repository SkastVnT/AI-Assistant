"""
Google Drive Upload Examples
Demonstrates various ways to use the Google Drive uploader
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.google_drive_uploader import GoogleDriveUploader


def example_1_upload_single_file():
    """Example 1: Upload a single file to Drive root"""
    print("\n" + "="*60)
    print("Example 1: Upload single file")
    print("="*60)
    
    uploader = GoogleDriveUploader()
    
    # Upload README to Drive root
    result = uploader.upload_file("README.md")
    print(f"✅ File uploaded!")
    print(f"   Name: {result['name']}")
    print(f"   Link: {result['webViewLink']}")


def example_2_create_folder_and_upload():
    """Example 2: Create a folder and upload files to it"""
    print("\n" + "="*60)
    print("Example 2: Create folder and upload")
    print("="*60)
    
    uploader = GoogleDriveUploader()
    
    # Create backup folder
    folder_id = uploader.create_folder("AI-Assistant-Backup")
    
    # Upload files to that folder
    uploader.upload_file("README.md", folder_id)
    uploader.upload_file("requirements.txt", folder_id)
    
    print(f"✅ Files uploaded to folder!")


def example_3_upload_entire_folder():
    """Example 3: Upload entire folder structure"""
    print("\n" + "="*60)
    print("Example 3: Upload entire folder")
    print("="*60)
    
    uploader = GoogleDriveUploader()
    
    # Upload docs folder (excluding archives)
    result = uploader.upload_folder(
        "docs",
        exclude_patterns=['archives', '__pycache__', '*.pyc', '*.log']
    )
    
    print(f"✅ Folder uploaded!")
    print(f"   Folder: {result['folder_name']}")
    print(f"   Files: {result['total_files']}")
    print(f"   Folder ID: {result['folder_id']}")


def example_4_upload_with_custom_name():
    """Example 4: Upload file with custom name"""
    print("\n" + "="*60)
    print("Example 4: Upload with custom name")
    print("="*60)
    
    uploader = GoogleDriveUploader()
    
    # Upload with different name
    result = uploader.upload_file(
        "README.md",
        file_name="AI-Assistant-README-2025-11-25.md"
    )
    
    print(f"✅ File uploaded with custom name!")
    print(f"   Name: {result['name']}")


def example_5_organized_backup():
    """Example 5: Create organized backup structure"""
    print("\n" + "="*60)
    print("Example 5: Organized backup")
    print("="*60)
    
    uploader = GoogleDriveUploader()
    
    # Create main backup folder with date
    from datetime import datetime
    backup_name = f"AI-Assistant-Backup-{datetime.now().strftime('%Y-%m-%d')}"
    main_folder_id = uploader.create_folder(backup_name)
    
    # Create subfolders
    docs_folder_id = uploader.create_folder("docs", main_folder_id)
    scripts_folder_id = uploader.create_folder("scripts", main_folder_id)
    config_folder_id = uploader.create_folder("config", main_folder_id)
    
    # Upload to respective folders
    print("\n📚 Uploading docs...")
    docs_result = uploader.upload_folder("docs", docs_folder_id)
    
    print("\n🔧 Uploading scripts...")
    scripts_result = uploader.upload_folder("scripts", scripts_folder_id)
    
    print(f"\n✅ Organized backup complete!")
    print(f"   Main folder: {backup_name}")
    print(f"   Docs: {docs_result['total_files']} files")
    print(f"   Scripts: {scripts_result['total_files']} files")


def example_6_list_files():
    """Example 6: List files in Drive"""
    print("\n" + "="*60)
    print("Example 6: List files")
    print("="*60)
    
    uploader = GoogleDriveUploader()
    
    # List all files
    files = uploader.list_files(max_results=20)
    
    print(f"\n📂 Found {len(files)} files")


def example_7_upload_database():
    """Example 7: Upload database folder"""
    print("\n" + "="*60)
    print("Example 7: Upload database")
    print("="*60)
    
    uploader = GoogleDriveUploader()
    
    # Upload database folder
    result = uploader.upload_folder(
        "database",
        exclude_patterns=['__pycache__', '*.pyc', '*.log', '*.tmp']
    )
    
    print(f"✅ Database uploaded!")
    print(f"   Files: {result['total_files']}")


def example_8_bulk_upload():
    """Example 8: Upload multiple folders at once"""
    print("\n" + "="*60)
    print("Example 8: Bulk upload")
    print("="*60)
    
    uploader = GoogleDriveUploader()
    
    # Create backup folder
    backup_folder_id = uploader.create_folder("AI-Assistant-Full-Backup")
    
    folders_to_upload = ['docs', 'scripts', 'database', 'examples']
    
    total_files = 0
    for folder in folders_to_upload:
        folder_path = Path(folder)
        if folder_path.exists():
            print(f"\n📤 Uploading {folder}...")
            result = uploader.upload_folder(str(folder), backup_folder_id)
            total_files += result['total_files']
            print(f"   ✅ {result['total_files']} files uploaded")
    
    print(f"\n✅ Bulk upload complete! Total: {total_files} files")


if __name__ == "__main__":
    print("🚀 Google Drive Upload Examples")
    print("=" * 60)
    
    # Choose which example to run
    examples = {
        '1': ('Upload single file', example_1_upload_single_file),
        '2': ('Create folder and upload', example_2_create_folder_and_upload),
        '3': ('Upload entire folder', example_3_upload_entire_folder),
        '4': ('Upload with custom name', example_4_upload_with_custom_name),
        '5': ('Organized backup', example_5_organized_backup),
        '6': ('List files', example_6_list_files),
        '7': ('Upload database', example_7_upload_database),
        '8': ('Bulk upload', example_8_bulk_upload),
    }
    
    print("\nAvailable examples:")
    for key, (description, _) in examples.items():
        print(f"  {key}. {description}")
    
    print("\nUsage:")
    print("  python examples/google_drive_upload.py")
    print("  Then uncomment the example you want to run below")
    print("\nOr use the script:")
    print("  python scripts/upload_to_drive.py --help")
    
    # Uncomment the example you want to run:
    # example_1_upload_single_file()
    # example_2_create_folder_and_upload()
    # example_3_upload_entire_folder()
    # example_4_upload_with_custom_name()
    # example_5_organized_backup()
    # example_6_list_files()
    # example_7_upload_database()
    # example_8_bulk_upload()
    
    print("\n💡 Tip: Uncomment an example function above to run it")
