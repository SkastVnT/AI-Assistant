"""
Test PostImages Upload
Quick test to verify PostImages integration
NO API KEY REQUIRED!
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.postimages_uploader import PostImagesUploader
import logging

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
    """Test PostImages upload"""
    
    print("\n" + "="*70)
    print("🧪 POSTIMAGES UPLOAD TEST")
    print("="*70)
    print("📌 Service: PostImages.org")
    print("🔑 API Key: NOT REQUIRED (Free anonymous upload)")
    print("="*70 + "\n")
    
    # Find test image
    if not image_path:
        image_path = find_test_image()
        
        if not image_path:
            print("❌ No test images found in Storage/Image_Gen/")
            print("\n💡 Solutions:")
            print("   1. Generate an image first via /api/generate-image")
            print("   2. Or specify image path: python test_postimages.py <path>")
            print()
            return False
    
    image_path = Path(image_path)
    
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}\n")
        return False
    
    # Display file info
    file_size = image_path.stat().st_size
    print(f"📁 Test Image: {image_path.name}")
    print(f"📦 File Size:  {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print(f"📂 Location:   {image_path.parent}")
    print()
    
    # Upload
    print("☁️  Uploading to PostImages...")
    print("-" * 70)
    
    result = PostImagesUploader.upload_image(str(image_path))
    
    if result:
        print("\n" + "="*70)
        print("✅ UPLOAD SUCCESS!")
        print("="*70)
        print(f"🔗 Image URL:      {result['url']}")
        print(f"🌐 Page URL:       {result['page_url']}")
        print(f"🖼️  Thumbnail URL:  {result['thumbnail_url']}")
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
        test_result_file = image_path.parent / "test_upload_result.txt"
        with open(test_result_file, 'w', encoding='utf-8') as f:
            f.write(f"PostImages Upload Test Result\n")
            f.write(f"{'='*70}\n")
            f.write(f"Test Date: {Path(__file__).stat().st_mtime}\n")
            f.write(f"Image: {image_path.name}\n")
            f.write(f"Image URL: {result['url']}\n")
            f.write(f"Delete URL: {result['delete_url']}\n")
            f.write(f"Page URL: {result['page_url']}\n")
        
        print(f"📝 Test result saved: {test_result_file}\n")
        return True
    else:
        print("\n" + "="*70)
        print("❌ UPLOAD FAILED!")
        print("="*70)
        print("\n🔍 Troubleshooting:")
        print("   1. Check your internet connection")
        print("   2. Verify image file is valid (PNG, JPG, etc.)")
        print("   3. Try a smaller image (< 5MB recommended)")
        print("   4. Check logs above for error details")
        print()
        return False


def main():
    """Main test function"""
    
    # Check if image path provided via command line
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        success = test_upload(image_path)
    else:
        success = test_upload()
    
    if success:
        print("🎉 PostImages integration is working!\n")
        sys.exit(0)
    else:
        print("❌ Test failed. Check errors above.\n")
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
