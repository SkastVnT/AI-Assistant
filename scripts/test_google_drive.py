"""
Test Google Drive Upload
Quick test to verify setup is working
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_setup():
    """Test if Google Drive setup is correct"""
    print("🧪 Testing Google Drive Upload Setup")
    print("=" * 60)
    
    # Check credentials file
    credentials_path = project_root / "config" / "google_oauth_credentials.json"
    if not credentials_path.exists():
        print("❌ Credentials file not found!")
        print(f"   Expected: {credentials_path}")
        print("\n💡 Please download credentials from Google Cloud Console")
        return False
    else:
        print(f"✅ Credentials file found: {credentials_path.name}")
    
    # Check module
    try:
        from src.utils.google_drive_uploader import GoogleDriveUploader
        print("✅ Google Drive uploader module loaded")
    except ImportError as e:
        print(f"❌ Failed to import module: {e}")
        print("\n💡 Install dependencies:")
        print("   pip install google-auth google-auth-oauthlib google-api-python-client")
        return False
    
    # Try to authenticate
    try:
        print("\n🔐 Testing authentication...")
        print("   (Browser will open for first-time setup)")
        uploader = GoogleDriveUploader()
        print("✅ Authentication successful!")
        
        # Try listing files
        print("\n📂 Testing file listing...")
        files = uploader.list_files(max_results=5)
        print(f"✅ Can access Drive ({len(files)} files found)")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! Google Drive upload is ready to use!")
        print("\n📖 Quick commands:")
        print("   python scripts/upload_to_drive.py --docs")
        print("   python scripts/upload_to_drive.py --all")
        print("   python examples/google_drive_upload.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Enable Google Drive API in Cloud Console")
        print("   2. Create OAuth credentials (Desktop app)")
        print("   3. Download and save as config/google_oauth_credentials.json")
        print("   4. Add your email as test user")
        return False


if __name__ == "__main__":
    success = test_setup()
    sys.exit(0 if success else 1)
