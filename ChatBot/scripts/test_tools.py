"""
Test script for Tools Integration
Run: python test_tools.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_google_search():
    """Test Google Custom Search API"""
    print("\n🔍 Testing Google Search...")
    
    # Check if API keys exist
    api_key = os.getenv('GOOGLE_API_KEY')
    cse_id = os.getenv('GOOGLE_CSE_ID')
    
    if not api_key or not cse_id:
        print("❌ Google API credentials not found in .env")
        print("   Add: GOOGLE_API_KEY and GOOGLE_CSE_ID")
        return False
    
    try:
        from googleapiclient.discovery import build
        
        service = build("customsearch", "v1", developerKey=api_key)
        result = service.cse().list(q="Python web frameworks", cx=cse_id, num=3).execute()
        
        print("✅ Google Search working!")
        for item in result.get('items', [])[:3]:
            print(f"   - {item['title']}")
            print(f"     {item['link']}")
        
        return True
        
    except ImportError:
        print("❌ google-api-python-client not installed")
        print("   Run: pip install google-api-python-client")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_github():
    """Test GitHub API"""
    print("\n🐙 Testing GitHub API...")
    
    token = os.getenv('GITHUB_TOKEN')
    
    if not token:
        print("❌ GitHub token not found in .env")
        print("   Add: GITHUB_TOKEN")
        return False
    
    try:
        from github import Github
        
        g = Github(token)
        repos = g.search_repositories(query="python web framework")
        
        print("✅ GitHub API working!")
        for repo in list(repos)[:3]:
            print(f"   - {repo.full_name} ⭐ {repo.stargazers_count}")
            print(f"     {repo.html_url}")
        
        return True
        
    except ImportError:
        print("❌ PyGithub not installed")
        print("   Run: pip install PyGithub")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_gemini():
    """Test Gemini API"""
    print("\n🤖 Testing Gemini API...")
    
    api_key = os.getenv('GEMINI_API_KEY_1')
    
    if not api_key:
        print("❌ Gemini API key not found")
        return False
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        response = model.generate_content("Hello! Say hi in Vietnamese")
        print("✅ Gemini API working!")
        print(f"   Response: {response.text[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("  🔧 ChatBot Tools Integration Test")
    print("=" * 60)
    
    results = {
        'Google Search': test_google_search(),
        'GitHub API': test_github(),
        'Gemini API': test_gemini()
    }
    
    print("\n" + "=" * 60)
    print("  📊 Test Results")
    print("=" * 60)
    
    for tool, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {tool}: {'PASS' if status else 'FAIL'}")
    
    print("\n" + "=" * 60)
    
    if all(results.values()):
        print("🎉 All tools working! Ready to integrate.")
    else:
        print("⚠️  Some tools failed. Check the guide:")
        print("   TOOLS_INTEGRATION_GUIDE.md")
    
    print("=" * 60)
