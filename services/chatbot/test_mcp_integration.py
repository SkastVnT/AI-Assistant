"""
Test MCP Integration
====================
Script để test MCP integration trong ChatBot
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import MCP client
from services.chatbot.src.utils.mcp_integration import get_mcp_client, inject_code_context


def test_mcp_client():
    """Test MCP Client functionality"""
    print("=" * 60)
    print("🧪 TESTING MCP CLIENT")
    print("=" * 60)
    
    # Get client
    mcp = get_mcp_client()
    print(f"✅ MCP Client created: {mcp}")
    
    # Test enable (without server)
    print("\n📝 Test 1: Enable MCP")
    try:
        # Note: This will fail if MCP Server not running, but that's OK
        result = mcp.enable()
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   ⚠️  Expected error (no MCP Server): {e}")
        print(f"   ℹ️  MCP Client can work without MCP Server!")
        # Force enable for testing
        mcp.enabled = True
    
    # Test add folder
    print("\n📝 Test 2: Add Folder")
    test_folder = str(project_root / "services" / "chatbot")
    result = mcp.add_folder(test_folder)
    print(f"   Folder: {test_folder}")
    print(f"   Result: {result}")
    print(f"   Selected folders: {mcp.selected_folders}")
    
    # Test list files
    print("\n📝 Test 3: List Files")
    files = mcp.list_files_in_folder()
    print(f"   Total files found: {len(files)}")
    if files:
        print(f"   Sample files:")
        for f in files[:5]:
            print(f"      - {f['relative_path']} ({f['size']} bytes)")
    
    # Test search files
    print("\n📝 Test 4: Search Files")
    search_query = "app"
    results = mcp.search_files(search_query, file_type="py")
    print(f"   Query: '{search_query}' (type: py)")
    print(f"   Results: {len(results)}")
    if results:
        for r in results[:3]:
            print(f"      - {r['name']}")
    
    # Test read file
    print("\n📝 Test 5: Read File")
    if results:
        test_file = results[0]['path']
        content = mcp.read_file(test_file, max_lines=20)
        if content and 'content' in content:
            print(f"   File: {content['name']}")
            print(f"   Lines: {content['returned_lines']}/{content['total_lines']}")
            print(f"   Preview:")
            preview = content['content'].split('\n')[:5]
            for line in preview:
                print(f"      {line}")
    
    # Test get code context
    print("\n📝 Test 6: Get Code Context")
    user_message = "Explain how the Flask app works"
    context = mcp.get_code_context(user_message)
    if context:
        print(f"   Message: {user_message}")
        print(f"   Context length: {len(context)} chars")
        print(f"   Preview:")
        preview = context[:300] + "..." if len(context) > 300 else context
        print(f"      {preview}")
    else:
        print(f"   No context generated")
    
    # Test inject code context
    print("\n📝 Test 7: Inject Code Context")
    enhanced_message = inject_code_context(user_message, mcp)
    print(f"   Original: {user_message}")
    print(f"   Enhanced length: {len(enhanced_message)} chars")
    if enhanced_message != user_message:
        print(f"   ✅ Context was injected!")
    else:
        print(f"   ℹ️  No context injected (expected if no relevant files)")
    
    # Test status
    print("\n📝 Test 8: Get Status")
    status = mcp.get_status()
    print(f"   Status: {status}")
    
    # Test disable
    print("\n📝 Test 9: Disable MCP")
    mcp.disable()
    print(f"   Enabled: {mcp.enabled}")
    print(f"   Folders: {mcp.selected_folders}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)


def test_api_routes():
    """Test API routes (requires Flask app running)"""
    print("\n" + "=" * 60)
    print("🌐 TESTING API ROUTES")
    print("=" * 60)
    print("⚠️  This test requires ChatBot Flask app to be running")
    print("   Start with: python app.py")
    print("   Then run this test again")
    
    import requests
    
    base_url = "http://localhost:5000"
    
    try:
        # Test health
        print("\n📝 Test API: Health Check")
        response = requests.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        
        # Test MCP enable
        print("\n📝 Test API: Enable MCP")
        response = requests.post(f"{base_url}/api/mcp/enable")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test MCP add folder
        print("\n📝 Test API: Add Folder")
        response = requests.post(
            f"{base_url}/api/mcp/add-folder",
            json={'folder_path': str(project_root / "services" / "chatbot")}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test MCP status
        print("\n📝 Test API: Get Status")
        response = requests.get(f"{base_url}/api/mcp/status")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test MCP list files
        print("\n📝 Test API: List Files")
        response = requests.get(f"{base_url}/api/mcp/list-files")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Files count: {data.get('count', 0)}")
        
        # Test MCP disable
        print("\n📝 Test API: Disable MCP")
        response = requests.post(f"{base_url}/api/mcp/disable")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        print("\n✅ API TESTS COMPLETED")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to Flask app")
        print("   Please start ChatBot first: python app.py")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


if __name__ == '__main__':
    # Test MCP Client
    test_mcp_client()
    
    # Test API routes (optional)
    print("\n\nWould you like to test API routes? (requires Flask app running)")
    print("Press Enter to skip, or type 'yes' to test:")
    user_input = input().strip().lower()
    
    if user_input in ['yes', 'y']:
        test_api_routes()
    else:
        print("\n⏭️  Skipping API tests")
    
    print("\n🎉 ALL TESTS DONE!")
