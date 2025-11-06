"""
Quick test for Gemini API Key
"""
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Get API key
api_key = os.getenv('GEMINI_API_KEY')

print("=" * 60)
print("GEMINI API KEY TEST")
print("=" * 60)

if not api_key:
    print("❌ GEMINI_API_KEY not found in .env!")
    print("\nPlease add to .env:")
    print("GEMINI_API_KEY=your_api_key_here")
else:
    print(f"✅ API Key found: {api_key[:20]}...{api_key[-10:]}")
    print(f"   Length: {len(api_key)} characters")
    
    # Try to use it
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        print("\n🧪 Testing API...")
        response = model.generate_content("Hello, reply with: API works!")
        
        print(f"✅ API Test Success!")
        print(f"   Response: {response.text[:100]}")
        print("\n🎉 GEMINI API IS READY TO USE!")
        
    except Exception as e:
        print(f"\n❌ API Test Failed: {e}")
        print("\nPossible issues:")
        print("1. Invalid API key")
        print("2. No internet connection")
        print("3. API quota exceeded")
        print("4. google-generativeai not installed")

print("=" * 60)
