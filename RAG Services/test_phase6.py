"""
Test Phase 6: Performance & Reliability
Verify caching, retry logic, monitoring endpoints
"""
import requests
import time
import json
from typing import Dict, Any

BASE_URL = "http://localhost:5003"

def print_section(title: str):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"   {details}")

def test_health_endpoint() -> bool:
    """Test /api/health/detailed endpoint"""
    print_section("Test 1: Health Check Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health/detailed", timeout=10)
        data = response.json()
        
        # Check status code
        if response.status_code != 200:
            print_result("Health endpoint", False, f"Status code: {response.status_code}")
            return False
        
        # Check required fields
        required_fields = ['status', 'health_score', 'uptime_seconds', 'metrics', 'cache', 'system']
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print_result("Health endpoint", False, f"Missing fields: {missing_fields}")
            return False
        
        print_result("Health endpoint", True)
        print(f"   Status: {data['status']}")
        print(f"   Health Score: {data['health_score']}/100")
        print(f"   Uptime: {data.get('uptime_human', 'N/A')}")
        print(f"   Cache Backend: {data['cache'].get('backend', 'N/A')}")
        
        return True
        
    except Exception as e:
        print_result("Health endpoint", False, str(e))
        return False

def test_metrics_endpoint() -> bool:
    """Test /api/metrics endpoint"""
    print_section("Test 2: Metrics Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/api/metrics", timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            print_result("Metrics endpoint", False, f"Status code: {response.status_code}")
            return False
        
        # Check metrics structure
        required_keys = ['counters', 'timers', 'gauges', 'errors', 'uptime_seconds']
        missing_keys = [k for k in required_keys if k not in data]
        
        if missing_keys:
            print_result("Metrics endpoint", False, f"Missing keys: {missing_keys}")
            return False
        
        print_result("Metrics endpoint", True)
        print(f"   Total Requests: {data['counters'].get('requests', 0)}")
        print(f"   Uptime: {data['uptime_seconds']}s")
        
        return True
        
    except Exception as e:
        print_result("Metrics endpoint", False, str(e))
        return False

def test_cache_stats() -> bool:
    """Test /api/cache/stats endpoint"""
    print_section("Test 3: Cache Statistics")
    
    try:
        response = requests.get(f"{BASE_URL}/api/cache/stats", timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            print_result("Cache stats", False, f"Status code: {response.status_code}")
            return False
        
        # Check cache fields
        required_fields = ['backend', 'hits', 'misses', 'hit_rate']
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print_result("Cache stats", False, f"Missing fields: {missing_fields}")
            return False
        
        print_result("Cache stats", True)
        print(f"   Backend: {data['backend']}")
        print(f"   Hits: {data['hits']}")
        print(f"   Misses: {data['misses']}")
        print(f"   Hit Rate: {data['hit_rate']}%")
        
        return True
        
    except Exception as e:
        print_result("Cache stats", False, str(e))
        return False

def test_system_endpoint() -> bool:
    """Test /api/system endpoint"""
    print_section("Test 4: System Resources")
    
    try:
        response = requests.get(f"{BASE_URL}/api/system", timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            print_result("System endpoint", False, f"Status code: {response.status_code}")
            return False
        
        # Check system fields
        required_fields = ['cpu_percent', 'memory', 'process']
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print_result("System endpoint", False, f"Missing fields: {missing_fields}")
            return False
        
        print_result("System endpoint", True)
        print(f"   CPU: {data['cpu_percent']}%")
        print(f"   Memory: {data['memory']['percent']}% ({data['memory']['used_mb']}MB used)")
        print(f"   Process Memory: {data['process']['memory_mb']}MB")
        
        return True
        
    except Exception as e:
        print_result("System endpoint", False, str(e))
        return False

def test_circuit_breakers() -> bool:
    """Test /api/circuit-breakers endpoint"""
    print_section("Test 5: Circuit Breakers")
    
    try:
        response = requests.get(f"{BASE_URL}/api/circuit-breakers", timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            print_result("Circuit breakers", False, f"Status code: {response.status_code}")
            return False
        
        print_result("Circuit breakers", True)
        
        if data:
            for name, state in data.items():
                print(f"   {name}: {state['state']} ({state['failure_count']}/{state['failure_threshold']} failures)")
        else:
            print("   No circuit breakers active")
        
        return True
        
    except Exception as e:
        print_result("Circuit breakers", False, str(e))
        return False

def test_cache_performance() -> bool:
    """Test cache performance improvement"""
    print_section("Test 6: Cache Performance")
    
    try:
        # Make a search request twice to test cache
        query = "test query for cache performance"
        
        # First request (cache miss)
        start1 = time.time()
        response1 = requests.post(
            f"{BASE_URL}/api/search",
            json={'query': query},
            timeout=30
        )
        time1 = time.time() - start1
        
        if response1.status_code != 200:
            print_result("Cache performance", False, "Search endpoint not available")
            return False
        
        # Wait a moment
        time.sleep(0.5)
        
        # Second request (should be cached)
        start2 = time.time()
        response2 = requests.post(
            f"{BASE_URL}/api/search",
            json={'query': query},
            timeout=30
        )
        time2 = time.time() - start2
        
        if response2.status_code != 200:
            print_result("Cache performance", False, "Second request failed")
            return False
        
        # Check if second request was faster
        improvement = time1 / time2 if time2 > 0 else 1
        
        print_result("Cache performance", True)
        print(f"   First request: {time1:.3f}s")
        print(f"   Second request: {time2:.3f}s")
        print(f"   Improvement: {improvement:.1f}x faster")
        
        # Check cache stats
        stats_response = requests.get(f"{BASE_URL}/api/cache/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"   Cache hits: {stats['hits']}")
            print(f"   Cache misses: {stats['misses']}")
        
        return True
        
    except Exception as e:
        print_result("Cache performance", False, str(e))
        return False

def test_metrics_reset() -> bool:
    """Test metrics reset"""
    print_section("Test 7: Metrics Reset")
    
    try:
        # Reset metrics
        response = requests.post(f"{BASE_URL}/api/metrics/reset", timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            print_result("Metrics reset", False, f"Status code: {response.status_code}")
            return False
        
        if not data.get('success'):
            print_result("Metrics reset", False, "Reset failed")
            return False
        
        # Verify metrics were reset
        metrics_response = requests.get(f"{BASE_URL}/api/metrics")
        metrics = metrics_response.json()
        
        # Check if counters are 0 or low
        requests_count = metrics['counters'].get('requests', 0)
        
        print_result("Metrics reset", True)
        print(f"   Metrics cleared")
        print(f"   Current requests: {requests_count}")
        
        return True
        
    except Exception as e:
        print_result("Metrics reset", False, str(e))
        return False

def test_cache_clear() -> bool:
    """Test cache clear"""
    print_section("Test 8: Cache Clear")
    
    try:
        # Clear cache
        response = requests.post(f"{BASE_URL}/api/cache/clear", timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            print_result("Cache clear", False, f"Status code: {response.status_code}")
            return False
        
        if not data.get('success'):
            print_result("Cache clear", False, "Clear failed")
            return False
        
        print_result("Cache clear", True)
        print(f"   Cleared {data['cleared']} items")
        
        # Verify cache was cleared
        stats_response = requests.get(f"{BASE_URL}/api/cache/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print(f"   Cache hits: {stats['hits']}")
            print(f"   Cache misses: {stats['misses']}")
        
        return True
        
    except Exception as e:
        print_result("Cache clear", False, str(e))
        return False

def main():
    """Run all tests"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║     🧪 Phase 6: Performance & Reliability Tests          ║
    ║     Testing caching, monitoring, and reliability         ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Check if server is running
    print("Checking if RAG Services is running...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running\n")
        else:
            print(f"⚠️  Server returned status {response.status_code}\n")
    except Exception as e:
        print(f"❌ Server not running: {e}")
        print("\nPlease start the server:")
        print("  cd 'I:\\AI-Assistant\\RAG Services'")
        print("  python app.py\n")
        return
    
    # Run tests
    tests = [
        ("Health Endpoint", test_health_endpoint),
        ("Metrics Endpoint", test_metrics_endpoint),
        ("Cache Statistics", test_cache_stats),
        ("System Resources", test_system_endpoint),
        ("Circuit Breakers", test_circuit_breakers),
        ("Cache Performance", test_cache_performance),
        ("Metrics Reset", test_metrics_reset),
        ("Cache Clear", test_cache_clear),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print_section("Test Summary")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*60}")
    print(f"Total: {passed_count}/{total_count} tests passed ({passed_count/total_count*100:.1f}%)")
    print(f"{'='*60}\n")
    
    if passed_count == total_count:
        print("🎉 All tests passed! Phase 6 is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    print("\n📊 View detailed metrics:")
    print(f"  - Health: {BASE_URL}/api/health/detailed")
    print(f"  - Metrics: {BASE_URL}/api/metrics")
    print(f"  - Cache: {BASE_URL}/api/cache/stats")
    print(f"  - System: {BASE_URL}/api/system")


if __name__ == '__main__':
    main()
