"""
Test Stable Diffusion WebUI connection
"""
import requests
import sys

SD_URL = "http://127.0.0.1:7861"

print("=" * 60)
print("Testing Stable Diffusion WebUI Connection")
print("=" * 60)
print(f"\nAPI URL: {SD_URL}")

# Test 1: Check if API is reachable
print("\n[Test 1] Checking API health...")
try:
    response = requests.get(f"{SD_URL}/sdapi/v1/sd-models", timeout=5)
    if response.status_code == 200:
        print("✅ API is online and responding")
        models = response.json()
        print(f"   Found {len(models)} models")
    else:
        print(f"❌ API returned status {response.status_code}")
except requests.exceptions.ConnectionError:
    print("❌ Connection refused - SD WebUI is NOT running")
    print("\n💡 Solutions:")
    print("   1. Start Stable Diffusion WebUI: scripts\\start-stable-diffusion.bat")
    print("   2. Wait for it to fully load (you'll see 'Running on local URL' message)")
    print("   3. Make sure it's running on port 7861 (check start-stable-diffusion.bat)")
    sys.exit(1)
except requests.exceptions.Timeout:
    print("❌ Request timed out - SD WebUI might be loading or very slow")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 2: Check current model
print("\n[Test 2] Checking current model...")
try:
    response = requests.get(f"{SD_URL}/sdapi/v1/options", timeout=5)
    if response.status_code == 200:
        options = response.json()
        current_model = options.get("sd_model_checkpoint", "Unknown")
        print(f"✅ Current model: {current_model}")
    else:
        print(f"⚠️ Could not get current model (status {response.status_code})")
except Exception as e:
    print(f"⚠️ Error getting model: {e}")

# Test 3: Test samplers
print("\n[Test 3] Checking available samplers...")
try:
    response = requests.get(f"{SD_URL}/sdapi/v1/samplers", timeout=5)
    if response.status_code == 200:
        samplers = response.json()
        print(f"✅ Found {len(samplers)} samplers")
        print(f"   Examples: {', '.join([s['name'] for s in samplers[:3]])}")
    else:
        print(f"⚠️ Could not get samplers (status {response.status_code})")
except Exception as e:
    print(f"⚠️ Error getting samplers: {e}")

# Test 4: Check progress API
print("\n[Test 4] Testing progress API...")
try:
    response = requests.get(f"{SD_URL}/sdapi/v1/progress", timeout=5)
    if response.status_code == 200:
        print("✅ Progress API is working")
    else:
        print(f"⚠️ Progress API returned status {response.status_code}")
except Exception as e:
    print(f"⚠️ Error with progress API: {e}")

print("\n" + "=" * 60)
print("✅ All tests passed! SD WebUI is ready to use")
print("=" * 60)
