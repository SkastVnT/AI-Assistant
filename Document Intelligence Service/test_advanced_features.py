"""
Test script for Advanced Features v1.6.0
"""
import requests
import json

BASE_URL = "http://localhost:5003"

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/api/health")
    data = response.json()
    print(f"   Status: {data['status']}")
    print(f"   Version: {data['version']}")
    print(f"   AI: {data['ai_model'] or 'Disabled'}")
    print()

def test_templates():
    """Test templates endpoint"""
    print("🔖 Testing templates...")
    response = requests.get(f"{BASE_URL}/api/templates")
    data = response.json()
    if data['success']:
        print(f"   ✅ Found {len(data['templates'])} templates:")
        for name in data['templates'].keys():
            icon = data['templates'][name]['icon']
            print(f"      {icon} {name}")
    print()

def test_history():
    """Test history endpoint"""
    print("📜 Testing history...")
    response = requests.get(f"{BASE_URL}/api/history")
    data = response.json()
    if data['success']:
        print(f"   ✅ Found {data['count']} history entries")
        if data['count'] > 0:
            print(f"   Latest: {data['history'][0]['filename']}")
    else:
        print("   ℹ️ No history yet")
    print()

def test_quick_actions():
    """Test quick actions"""
    print("⚡ Testing quick actions...")
    
    test_text = """Hello  World  
    This is   a test.
    This is   a test.
    Another line."""
    
    # Test clean
    response = requests.post(
        f"{BASE_URL}/api/quick-actions/clean",
        json={'text': test_text}
    )
    data = response.json()
    if data['success']:
        print(f"   ✅ Clean: Saved {data['stats']['saved_chars']} chars, removed {data['stats']['removed_lines']} lines")
    
    # Test extract
    test_text_info = "Contact: email@example.com, phone: 0912-345-678, date: 01/01/2024"
    response = requests.post(
        f"{BASE_URL}/api/quick-actions/extract",
        json={'text': test_text_info}
    )
    data = response.json()
    if data['success']:
        print(f"   ✅ Extract: {len(data.get('emails', []))} emails, {len(data.get('phones', []))} phones, {len(data.get('dates', []))} dates")
    
    # Test format
    response = requests.post(
        f"{BASE_URL}/api/quick-actions/format",
        json={'text': 'hello world. this is a test.', 'action': 'capitalize'}
    )
    data = response.json()
    if data['success']:
        print(f"   ✅ Capitalize: {data['text'][:50]}...")
    
    print()

def main():
    """Run all tests"""
    print("=" * 50)
    print("🧪 TESTING ADVANCED FEATURES v1.6.0")
    print("=" * 50)
    print()
    
    try:
        test_health()
        test_templates()
        test_history()
        test_quick_actions()
        
        print("=" * 50)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 50)
        print()
        print("🚀 Ready to use:")
        print("   1. Batch Processing: Upload multiple files")
        print("   2. Templates: CMND, Invoice, Contract, etc.")
        print("   3. History: Track all processed documents")
        print("   4. Quick Actions: Clean, Extract, Format text")
        print()
        
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Service not running!")
        print("   Start with: python app.py")
        print()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()

if __name__ == "__main__":
    main()
