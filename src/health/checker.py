"""
Health Check Module
Unified health and readiness checks for all services
"""

import os
import time
import logging
import platform
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0
    details: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """
    Unified health checker for services.
    """
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        """
        Initialize health checker.
        
        Args:
            service_name: Name of the service
            version: Service version
        """
        self.service_name = service_name
        self.version = version
        self.start_time = time.time()
        self._checks: Dict[str, Callable] = {}
        self._readiness_checks: Dict[str, Callable] = {}
    
    def register_check(self, name: str, check_func: Callable, 
                       is_critical: bool = True,
                       is_readiness: bool = False) -> None:
        """
        Register a health check function.
        
        Args:
            name: Check name
            check_func: Function that returns (healthy: bool, message: str, details: dict)
            is_critical: If True, failure marks service as unhealthy
            is_readiness: If True, include in readiness checks
        """
        self._checks[name] = {
            "func": check_func,
            "critical": is_critical
        }
        
        if is_readiness:
            self._readiness_checks[name] = self._checks[name]
    
    def _run_check(self, name: str, check_info: Dict) -> CheckResult:
        """Run a single health check."""
        start = time.perf_counter()
        
        try:
            result = check_info["func"]()
            duration_ms = (time.perf_counter() - start) * 1000
            
            if isinstance(result, tuple):
                healthy, message, details = result[0], result[1], result[2] if len(result) > 2 else {}
            elif isinstance(result, dict):
                healthy = result.get("healthy", result.get("status") == "ok")
                message = result.get("message", "")
                details = result.get("details", result)
            elif isinstance(result, bool):
                healthy, message, details = result, "", {}
            else:
                healthy, message, details = False, "Invalid check result", {}
            
            return CheckResult(
                name=name,
                status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
                message=message,
                duration_ms=round(duration_ms, 2),
                details=details
            )
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error(f"Health check '{name}' failed: {e}")
            
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=round(duration_ms, 2),
                details={"error": str(e)}
            )
    
    def check_health(self) -> Dict[str, Any]:
        """
        Run all health checks.
        
        Returns:
            Health status dictionary
        """
        results = []
        overall_status = HealthStatus.HEALTHY
        
        for name, check_info in self._checks.items():
            result = self._run_check(name, check_info)
            results.append(result)
            
            if result.status == HealthStatus.UNHEALTHY:
                if check_info["critical"]:
                    overall_status = HealthStatus.UNHEALTHY
                elif overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        uptime = time.time() - self.start_time
        
        return {
            "status": overall_status.value,
            "service": self.service_name,
            "version": self.version,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "uptime_seconds": round(uptime, 2),
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                    "details": r.details
                }
                for r in results
            ],
            "system": {
                "python_version": platform.python_version(),
                "platform": platform.system(),
                "hostname": platform.node()
            }
        }
    
    def check_readiness(self) -> Dict[str, Any]:
        """
        Run readiness checks (subset of health checks).
        
        Returns:
            Readiness status dictionary
        """
        results = []
        ready = True
        
        for name, check_info in self._readiness_checks.items():
            result = self._run_check(name, check_info)
            results.append(result)
            
            if result.status == HealthStatus.UNHEALTHY:
                ready = False
        
        return {
            "ready": ready,
            "service": self.service_name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "duration_ms": r.duration_ms
                }
                for r in results
            ]
        }
    
    def check_liveness(self) -> Dict[str, Any]:
        """
        Simple liveness check (service is running).
        
        Returns:
            Liveness status dictionary
        """
        return {
            "alive": True,
            "service": self.service_name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }


# ============================================================================
# COMMON CHECK FUNCTIONS
# ============================================================================

def check_mongodb(client, db_name: str = "ai_assistant") -> tuple:
    """
    Check MongoDB connection.
    
    Args:
        client: MongoClient instance
        db_name: Database name
    
    Returns:
        (healthy, message, details)
    """
    try:
        # Ping server
        client.admin.command("ping")
        
        # Get server info
        info = client.server_info()
        
        return True, "Connected", {
            "version": info.get("version"),
            "database": db_name
        }
    except Exception as e:
        return False, str(e), {}


def check_redis(redis_client) -> tuple:
    """
    Check Redis connection.
    
    Args:
        redis_client: Redis client instance
    
    Returns:
        (healthy, message, details)
    """
    try:
        redis_client.ping()
        info = redis_client.info("memory")
        
        return True, "Connected", {
            "used_memory": info.get("used_memory_human")
        }
    except Exception as e:
        return False, str(e), {}


def check_disk_space(min_free_gb: float = 1.0) -> tuple:
    """
    Check available disk space.
    
    Args:
        min_free_gb: Minimum free space in GB
    
    Returns:
        (healthy, message, details)
    """
    import shutil
    
    try:
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024 ** 3)
        
        healthy = free_gb >= min_free_gb
        
        return healthy, f"{free_gb:.1f} GB free", {
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "free_gb": round(free_gb, 2)
        }
    except Exception as e:
        return False, str(e), {}


def check_memory(max_percent: float = 90.0) -> tuple:
    """
    Check memory usage.
    
    Args:
        max_percent: Maximum memory usage percentage
    
    Returns:
        (healthy, message, details)
    """
    try:
        import psutil
        memory = psutil.virtual_memory()
        
        healthy = memory.percent < max_percent
        
        return healthy, f"{memory.percent}% used", {
            "total_gb": round(memory.total / (1024 ** 3), 2),
            "available_gb": round(memory.available / (1024 ** 3), 2),
            "percent": memory.percent
        }
    except ImportError:
        return True, "psutil not installed", {}
    except Exception as e:
        return False, str(e), {}


def check_api_endpoint(url: str, timeout: float = 5.0) -> tuple:
    """
    Check external API endpoint.
    
    Args:
        url: URL to check
        timeout: Request timeout
    
    Returns:
        (healthy, message, details)
    """
    try:
        import requests
        response = requests.get(url, timeout=timeout)
        
        healthy = response.status_code < 400
        
        return healthy, f"Status {response.status_code}", {
            "status_code": response.status_code,
            "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2)
        }
    except Exception as e:
        return False, str(e), {}


# ============================================================================
# FLASK INTEGRATION
# ============================================================================

def create_health_blueprint(health_checker: HealthChecker, url_prefix: str = ""):
    """
    Create Flask blueprint for health endpoints.
    
    Args:
        health_checker: HealthChecker instance
        url_prefix: URL prefix for endpoints
    
    Returns:
        Flask Blueprint
    """
    from flask import Blueprint, jsonify
    
    bp = Blueprint('health', __name__, url_prefix=url_prefix)
    
    @bp.route('/health')
    def health():
        """Full health check."""
        result = health_checker.check_health()
        status_code = 200 if result["status"] == "healthy" else 503
        return jsonify(result), status_code
    
    @bp.route('/ready')
    def ready():
        """Readiness check."""
        result = health_checker.check_readiness()
        status_code = 200 if result["ready"] else 503
        return jsonify(result), status_code
    
    @bp.route('/live')
    def live():
        """Liveness check."""
        return jsonify(health_checker.check_liveness()), 200
    
    @bp.route('/version')
    def version():
        """Version info."""
        return jsonify({
            "service": health_checker.service_name,
            "version": health_checker.version
        }), 200
    
    return bp
