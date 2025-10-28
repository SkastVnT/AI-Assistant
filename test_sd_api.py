"""Test script để kiểm tra Stable Diffusion API"""
import requests
import json

SD_API_URL = "http://127.0.0.1:7860"

def test_health():
    """Test API health"""
    try:
        response = requests.get(f"{SD_API_URL}/sdapi/v1/sd-models", timeout=5)
        print(f"✓ Health check: {response.status_code}")
        if response.status_code == 200:
            models = response.json()
            print(f"  Found {len(models)} models")
            if models:
                print(f"  First model: {models[0].get('title', 'N/A')}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_txt2img():
    """Test txt2img endpoint"""
    payload = {
        "prompt": "a beautiful girl, beautiful, blue hair",
        "negative_prompt": "bad quality, nsfw",
        "width": 512,
        "height": 512,
        "steps": 20,
        "cfg_scale": 7.0,
        "sampler_name": "DPM++ 2M Karras",
        "seed": -1,
        "batch_size": 1,
        "restore_faces": False,
        "enable_hr": False,
        "save_images": False
    }
    
    try:
        print("\n[TEST] Sending txt2img request...")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{SD_API_URL}/sdapi/v1/txt2img",
            json=payload,
            timeout=120
        )
        
        print(f"\n[RESPONSE] Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Success! Generated {len(result.get('images', []))} images")
            return True
        else:
            print(f"✗ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Timeout - request took too long")
        return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("STABLE DIFFUSION API TEST")
    print("=" * 60)
    
    if test_health():
        test_txt2img()
    else:
        print("\n✗ API is not healthy, skipping txt2img test")
    
    print("\n" + "=" * 60)
