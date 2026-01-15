"""
Health Check Module

Provides health check endpoints for monitoring service status.
Supports liveness, readiness, and detailed health checks.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health status constants"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthChecker:
    """
    Centralized health checker for the chatbot service.
    Checks database, cache, and other dependencies.
    """
    
    _instance = None
    _start_time = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._start_time = datetime.utcnow()
        return cls._instance
    
    def __init__(self):
        self._checks = {}
        self._last_check_time = None
        self._last_check_result = None
        self._cache_duration = 5  # Cache health check for 5 seconds
    
    def register_check(self, name: str, check_func):
        """Register a health check function"""
        self._checks[name] = check_func
    
    def _run_check(self, name: str, check_func) -> Dict[str, Any]:
        """Run a single health check with timing"""
        start = time.perf_counter()
        try:
            result = check_func()
            elapsed = (time.perf_counter() - start) * 1000
            return {
                "status": HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                "latency_ms": round(elapsed, 2),
                "message": "OK" if result else "Check failed"
            }
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning(f"Health check '{name}' failed: {e}")
            return {
                "status": HealthStatus.UNHEALTHY,
                "latency_ms": round(elapsed, 2),
                "message": str(e)
            }
    
    def liveness(self) -> Dict[str, Any]:
        """
        Liveness probe - is the service running?
        Used by Kubernetes/Docker to determine if container should be restarted.
        """
        return {
            "status": HealthStatus.HEALTHY,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds()
        }
    
    def readiness(self) -> Dict[str, Any]:
        """
        Readiness probe - is the service ready to accept traffic?
        Checks critical dependencies (database, cache).
        """
        results = {}
        overall_status = HealthStatus.HEALTHY
        
        # Check database
        db_result = self._check_database()
        results["database"] = db_result
        if db_result["status"] != HealthStatus.HEALTHY:
            overall_status = HealthStatus.UNHEALTHY
        
        # Check cache
        cache_result = self._check_cache()
        results["cache"] = cache_result
        if cache_result["status"] != HealthStatus.HEALTHY:
            # Cache is optional, so mark as degraded not unhealthy
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results
        }
    
    def detailed(self) -> Dict[str, Any]:
        """
        Detailed health check with all system information.
        """
        # Use cached result if available and fresh
        now = datetime.utcnow()
        if (self._last_check_result and self._last_check_time and 
            (now - self._last_check_time).total_seconds() < self._cache_duration):
            return self._last_check_result
        
        results = {}
        overall_status = HealthStatus.HEALTHY
        
        # Run all registered checks
        for name, check_func in self._checks.items():
            results[name] = self._run_check(name, check_func)
            if results[name]["status"] == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif results[name]["status"] == HealthStatus.DEGRADED:
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        # Add standard checks
        results["database"] = self._check_database()
        results["cache"] = self._check_cache()
        
        # Determine overall status
        if results["database"]["status"] == HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.UNHEALTHY
        elif results["cache"]["status"] != HealthStatus.HEALTHY:
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        result = {
            "status": overall_status,
            "timestamp": now.isoformat(),
            "uptime_seconds": round((now - self._start_time).total_seconds(), 2),
            "version": self._get_version(),
            "checks": results,
            "system": self._get_system_info()
        }
        
        # Cache result
        self._last_check_time = now
        self._last_check_result = result
        
        return result
    
    def _check_database(self) -> Dict[str, Any]:
        """Check MongoDB connection"""
        start = time.perf_counter()
        try:
            from database.utils.session import get_mongodb_client
            client = get_mongodb_client()
            if client:
                client.admin.command('ping')
                elapsed = (time.perf_counter() - start) * 1000
                return {
                    "status": HealthStatus.HEALTHY,
                    "latency_ms": round(elapsed, 2),
                    "message": "MongoDB connected"
                }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "latency_ms": 0,
                    "message": "No MongoDB client"
                }
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return {
                "status": HealthStatus.UNHEALTHY,
                "latency_ms": round(elapsed, 2),
                "message": f"MongoDB error: {str(e)}"
            }
    
    def _check_cache(self) -> Dict[str, Any]:
        """Check cache (Redis/Memory) status"""
        start = time.perf_counter()
        try:
            from database.cache.chatbot_cache import ChatbotCache
            
            # Test write/read
            test_key = "_health_check_"
            ChatbotCache.set_conversation(test_key, {"test": True})
            result = ChatbotCache.get_conversation(test_key)
            ChatbotCache.invalidate_conversation(test_key)
            
            elapsed = (time.perf_counter() - start) * 1000
            
            if result:
                stats = ChatbotCache.get_stats()
                backend = stats.get("backend", "unknown")
                return {
                    "status": HealthStatus.HEALTHY,
                    "latency_ms": round(elapsed, 2),
                    "message": f"Cache OK ({backend})",
                    "backend": backend
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED,
                    "latency_ms": round(elapsed, 2),
                    "message": "Cache test failed"
                }
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return {
                "status": HealthStatus.DEGRADED,
                "latency_ms": round(elapsed, 2),
                "message": f"Cache error: {str(e)}"
            }
    
    def _get_version(self) -> str:
        """Get application version"""
        try:
            import os
            version_file = os.path.join(os.path.dirname(__file__), '..', 'VERSION')
            if os.path.exists(version_file):
                with open(version_file) as f:
                    return f.read().strip()
        except:
            pass
        return "2.2.0"  # Default version
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        import platform
        import os
        
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "pid": os.getpid(),
            "hostname": platform.node()
        }


# Singleton instance
health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """Get the health checker singleton"""
    return health_checker


# Flask Blueprint for health endpoints
def create_health_blueprint():
    """Create Flask blueprint with health endpoints"""
    try:
        from flask import Blueprint, jsonify
        
        health_bp = Blueprint('health', __name__)
        checker = get_health_checker()
        
        @health_bp.route('/health', methods=['GET'])
        @health_bp.route('/health/live', methods=['GET'])
        def liveness():
            """Liveness probe"""
            result = checker.liveness()
            return jsonify(result), 200
        
        @health_bp.route('/health/ready', methods=['GET'])
        def readiness():
            """Readiness probe"""
            result = checker.readiness()
            status_code = 200 if result["status"] == HealthStatus.HEALTHY else 503
            return jsonify(result), status_code
        
        @health_bp.route('/health/detailed', methods=['GET'])
        def detailed():
            """Detailed health check"""
            result = checker.detailed()
            status_code = 200 if result["status"] == HealthStatus.HEALTHY else 503
            return jsonify(result), status_code
        
        return health_bp
    except ImportError:
        logger.warning("Flask not available, health blueprint not created")
        return None


# Decorator for health-aware operations
def require_healthy(check_name: str = "database"):
    """Decorator to check health before operation"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            checker = get_health_checker()
            if check_name == "database":
                result = checker._check_database()
            elif check_name == "cache":
                result = checker._check_cache()
            else:
                result = {"status": HealthStatus.HEALTHY}
            
            if result["status"] == HealthStatus.UNHEALTHY:
                raise ConnectionError(f"{check_name} is unhealthy: {result.get('message')}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
