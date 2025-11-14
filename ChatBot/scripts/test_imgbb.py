"""
Test ImgBB Upload
Quick test to verify ImgBB integration
Required: IMGBB_API_KEY in .env

Get API key (1 minute):
1. Visit: https://api.imgbb.com/
2. Click "Get API Key"
3. Sign up (email + password)
4. Copy API key
5. Add to .env: IMGBB_API_KEY=your_key
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.imgbb_uploader import ImgBBUploader
import logging
from dotenv import load_dotenv

# Load .env
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def find_test_image():
    """Find a test image in Storage/Image_Gen"""
    storage_path = Path(__file__).parent.parent / "Storage" / "Image_Gen"
    
    if not storage_path.exists():
        print(f"⚠️  Creating storage directory: {storage_path}")
        storage_path.mkdir(parents=True, exist_ok=True)
        return None
    
    # Get first PNG image
    images = list(storage_path.glob("*.png"))
    
    if images:
        return images[0]
    
    return None


def test_upload(image_path=None):
    """Test ImgBB upload"""
    
    print("\n" + "="*70)
    print("🧪 IMGBB UPLOAD TEST")
    print("="*70)
    print("📌 Service: ImgBB.com")
    print("🔑 API Key: Required (Free, easy to get)")
    print("="*70 + "\n")
    
    # Check API key
    api_key = os.getenv('IMGBB_API_KEY')
    
    if not api_key:
        print("❌ ImgBB API key not found!")
        print("\n" + "="*70)
        print("📝 SETUP INSTRUCTIONS (1 minute)")
        print("="*70)
        print("\n1. Visit: https://api.imgbb.com/")
        print("2. Click the big blue button: 'Get API Key'")
        print("3. Sign up with:")
        print("   - Email: your@email.com")
        print("   - Password: (create one)")
        print("   - Username: (optional)")
        print("\n4. After login, you'll see:")
        print("   'Your API key: abc123xyz456'")
        print("\n5. Copy that key")
        print("\n6. Open file: ChatBot\\.env")
        print("   Add this line:")
        print("   IMGBB_API_KEY=abc123xyz456")
        print("\n7. Run test again: python scripts\\test_imgbb.py")
        print("\n" + "="*70 + "\n")
        return False
    
    # Find test image
    if not image_path:
        image_path = find_test_image()
        
        if not image_path:
            print("❌ No test images found in Storage/Image_Gen/")
            print("\n💡 Solutions:")
            print("   1. Generate an image first via /api/generate-image")
            print("   2. Or specify image path: python test_imgbb.py <path>")
            print()
            return False
    
    image_path = Path(image_path)
    
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}\n")
        return False
    
    # Display file info
    file_size = image_path.stat().st_size
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
    print(f"\n📁 Test Image: {image_path.name}")
    print(f"📦 File Size:  {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print(f"📂 Location:   {image_path.parent}")
    print()
    
    # Upload
    print("☁️  Uploading to ImgBB...")
    print("-" * 70)
    
    try:
        uploader = ImgBBUploader(api_key)
        result = uploader.upload_image(str(image_path), title=image_path.stem)
        
        if result:
            print("\n" + "="*70)
            print("✅ UPLOAD SUCCESS!")
            print("="*70)
            print(f"🔗 Direct URL:     {result['url']}")
            print(f"📱 Display URL:    {result['display_url']}")
            print(f"🖼️  Thumbnail:      {result['thumbnail']}")
            print(f"📊 Medium Size:    {result['medium']}")
            print(f"🗑️  Delete URL:     {result['delete_url']}")
            print(f"📦 Size:           {result['size']:,} bytes")
            print(f"📝 Service:        {result['service']}")
            print("="*70)
            
            print("\n💡 NEXT STEPS:")
            print(f"   1. Copy this URL: {result['url']}")
            print("   2. Paste into browser to view your image")
            print("   3. Share the URL with anyone!")
            print()
            
            # Save test result
            test_result_file = image_path.parent / "test_imgbb_result.txt"
            with open(test_result_file, 'w', encoding='utf-8') as f:
                f.write(f"ImgBB Upload Test Result\n")
                f.write(f"{'='*70}\n")
                f.write(f"Image: {image_path.name}\n")
                f.write(f"Direct URL: {result['url']}\n")
                f.write(f"Display URL: {result['display_url']}\n")
                f.write(f"Delete URL: {result['delete_url']}\n")
                f.write(f"Thumbnail: {result['thumbnail']}\n")
            
            print(f"📝 Test result saved: {test_result_file}\n")
            return True
        else:
            print("\n" + "="*70)
            print("❌ UPLOAD FAILED!")
            print("="*70)
            print("\n🔍 Troubleshooting:")
            print("   1. Check API key is correct")
            print("   2. Verify internet connection")
            print("   3. Try a smaller image (< 32MB)")
            print("   4. Check logs above for error details")
            print()
            return False
            
    except ValueError as e:
        print(f"\n❌ Error: {e}\n")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    
    print("\n" + "="*70)
    print("ImgBB Cloud Storage Test")
    print("="*70)
    print("📚 Documentation: https://api.imgbb.com/")
    print("🆓 Free Tier: 32MB/image, unlimited uploads")
    print("⏱️  Setup Time: ~1 minute")
    print("="*70)
    
    # Check if image path provided via command line
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        success = test_upload(image_path)
    else:
        success = test_upload()
    
    if success:
        print("🎉 ImgBB integration is working perfectly!\n")
        print("💡 Now update app.py to use ImgBBUploader instead of PostImagesUploader")
        print()
        sys.exit(0)
    else:
        print("❌ Test failed. Follow setup instructions above.\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
