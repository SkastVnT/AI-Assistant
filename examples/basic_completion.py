# Example: Basic Hub Gateway Usage

"""
This example demonstrates how to use the Hub Gateway API.
"""

import requests
import json

# Hub Gateway URL
HUB_URL = "http://localhost:8080"


def test_health_check():
    """Test health check endpoint."""
    print("=" * 50)
    print("Testing Health Check")
    print("=" * 50)
    
    response = requests.get(f"{HUB_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_get_all_services():
    """Test get all services endpoint."""
    print("=" * 50)
    print("Getting All Services")
    print("=" * 50)
    
    response = requests.get(f"{HUB_URL}/api/services")
    print(f"Status: {response.status_code}")
    
    services = response.json()
    for key, service in services.items():
        print(f"\n{service['icon']} {service['name']}")
        print(f"   URL: {service['url']}")
        print(f"   Description: {service['description']}")
    print()


def test_get_specific_service(service_name):
    """Test get specific service endpoint."""
    print("=" * 50)
    print(f"Getting Service: {service_name}")
    print("=" * 50)
    
    response = requests.get(f"{HUB_URL}/api/services/{service_name}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        service = response.json()
        print(f"\n{service['icon']} {service['name']}")
        print(f"Description: {service['description']}")
        print(f"URL: {service['url']}")
        print(f"Features:")
        for feature in service['features']:
            print(f"  • {feature}")
    else:
        print(f"Error: {response.json()}")
    print()


def test_get_stats():
    """Test get statistics endpoint."""
    print("=" * 50)
    print("Getting Hub Statistics")
    print("=" * 50)
    
    response = requests.get(f"{HUB_URL}/api/stats")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


if __name__ == "__main__":
    print("\n🚀 AI Assistant Hub - API Testing Example\n")
    
    try:
        # Run tests
        test_health_check()
        test_get_all_services()
        test_get_specific_service("chatbot")
        test_get_specific_service("speech2text")
        test_get_stats()
        
        print("✅ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to Hub Gateway")
        print("   Make sure the hub is running on http://localhost:8080")
    except Exception as e:
        print(f"❌ Error: {e}")
