"""
Test script for Document Intelligence Service
Test upload and OCR functionality
"""
import requests
import json
from pathlib import Path

# Configuration
BASE_URL = "http://127.0.0.1:5003"
TEST_IMAGE = "test_image.png"  # Replace with your test image path

def test_health():
    """Test health check endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/api/health")
    
    if response.status_code == 200:
        print("✅ Health check passed")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Health check failed: {response.status_code}")
    
    return response.status_code == 200

def test_upload(image_path: str):
    """Test file upload and OCR"""
    print(f"\nTesting upload with: {image_path}")
    
    # Check if file exists
    if not Path(image_path).exists():
        print(f"❌ Test file not found: {image_path}")
        print("Please provide a valid test image path")
        return False
    
    # Prepare file
    with open(image_path, 'rb') as f:
        files = {'file': (Path(image_path).name, f, 'image/png')}
        
        # Optional: Add processing options
        data = {
            'options': json.dumps({
                'save_output': True,
                'include_blocks': True,
                'ai_classify': True,
                'ai_extract': True,
                'ai_summary': True
            })
        }
        
        # Upload
        response = requests.post(f"{BASE_URL}/api/upload", files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        
        if result.get('success'):
            print("✅ Upload and OCR successful!")
            print(f"\nStatistics:")
            print(f"  - Total blocks: {result.get('statistics', {}).get('total_blocks', 0)}")
            print(f"  - Average confidence: {result.get('statistics', {}).get('average_confidence', 0):.2%}")
            print(f"  - Total characters: {result.get('statistics', {}).get('total_chars', 0)}")
            
            print(f"\nExtracted Text Preview:")
            text = result.get('text', '')
            print(text[:500] if len(text) > 500 else text)
            
            # Check AI enhancements
            if 'ai_classification' in result:
                print(f"\n🤖 AI Classification:")
                print(f"  - Type: {result['ai_classification'].get('category', 'N/A')}")
            
            if 'ai_extraction' in result:
                print(f"\n🤖 AI Extraction: Available")
            
            if 'ai_summary' in result:
                print(f"\n🤖 AI Summary:")
                print(f"  {result['ai_summary'].get('summary', 'N/A')}")
            
            return True
        else:
            print(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
            return False
    else:
        print(f"❌ Upload request failed: {response.status_code}")
        print(response.text)
        return False

def test_formats():
    """Test get supported formats"""
    print("\nTesting formats endpoint...")
    response = requests.get(f"{BASE_URL}/api/formats")
    
    if response.status_code == 200:
        print("✅ Formats endpoint working")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Formats endpoint failed: {response.status_code}")

if __name__ == "__main__":
    print("=" * 60)
    print("Document Intelligence Service - Test Suite")
    print("=" * 60)
    
    # Test 1: Health check
    if not test_health():
        print("\n⚠️ Service is not running or not healthy")
        print("Please start the service with: python app.py")
        exit(1)
    
    # Test 2: Get formats
    test_formats()
    
    # Test 3: Upload test (requires test image)
    print("\n" + "=" * 60)
    print("Upload Test")
    print("=" * 60)
    
    # Try to find a test image in output folder
    output_folder = Path(__file__).parent / "output"
    test_images = list(output_folder.glob("*.png")) + list(output_folder.glob("*.jpg"))
    
    if test_images:
        print(f"\nFound test image: {test_images[0].name}")
        test_upload(str(test_images[0]))
    else:
        print("\n⚠️ No test images found")
        print("Please provide a test image path:")
        print("  python test_upload.py <path_to_image>")
        
        import sys
        if len(sys.argv) > 1:
            test_upload(sys.argv[1])
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
