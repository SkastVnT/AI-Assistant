"""
Tests for Health Check Module
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock


class TestHealthStatus:
    """Test HealthStatus enum."""
    
    def test_health_status_values(self):
        """Test health status values."""
        from src.health import HealthStatus
        
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestCheckResult:
    """Test CheckResult dataclass."""
    
    def test_check_result_creation(self):
        """Test creating check result."""
        from src.health import CheckResult, HealthStatus
        
        result = CheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            message="OK",
            duration_ms=10.5
        )
        
        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "OK"
        assert result.duration_ms == 10.5
        assert result.details == {}  # default
    
    def test_check_result_with_details(self):
        """Test check result with details."""
        from src.health import CheckResult, HealthStatus
        
        result = CheckResult(
            name="db_check",
            status=HealthStatus.UNHEALTHY,
            message="Connection failed",
            details={"error": "timeout"}
        )
        
        assert result.details == {"error": "timeout"}


class TestHealthChecker:
    """Test HealthChecker class."""
    
    def test_initialization(self):
        """Test health checker initialization."""
        from src.health import HealthChecker
        
        checker = HealthChecker("test-service", "1.0.0")
        
        assert checker.service_name == "test-service"
        assert checker.version == "1.0.0"
        assert checker.start_time is not None
    
    def test_register_check(self):
        """Test registering a check."""
        from src.health import HealthChecker
        
        checker = HealthChecker("test-service")
        
        def simple_check():
            return True, "OK", {}
        
        checker.register_check("simple", simple_check)
        
        assert "simple" in checker._checks
    
    def test_check_health_healthy(self):
        """Test health check with all healthy."""
        from src.health import HealthChecker
        
        checker = HealthChecker("test-service", "1.0.0")
        checker.register_check("check1", lambda: (True, "OK", {}))
        checker.register_check("check2", lambda: (True, "OK", {}))
        
        result = checker.check_health()
        
        assert result["status"] == "healthy"
        assert result["service"] == "test-service"
        assert result["version"] == "1.0.0"
        assert len(result["checks"]) == 2
    
    def test_check_health_unhealthy(self):
        """Test health check with critical failure."""
        from src.health import HealthChecker
        
        checker = HealthChecker("test-service")
        checker.register_check("healthy", lambda: (True, "OK", {}))
        checker.register_check("failing", lambda: (False, "Error", {}), is_critical=True)
        
        result = checker.check_health()
        
        assert result["status"] == "unhealthy"
    
    def test_check_health_degraded(self):
        """Test health check with non-critical failure."""
        from src.health import HealthChecker
        
        checker = HealthChecker("test-service")
        checker.register_check("healthy", lambda: (True, "OK", {}))
        checker.register_check("optional", lambda: (False, "Error", {}), is_critical=False)
        
        result = checker.check_health()
        
        assert result["status"] == "degraded"
    
    def test_check_handles_exception(self):
        """Test that check handles exceptions."""
        from src.health import HealthChecker
        
        checker = HealthChecker("test-service")
        checker.register_check("failing", lambda: 1/0)  # Will raise ZeroDivisionError
        
        result = checker.check_health()
        
        assert result["status"] == "unhealthy"
        assert "division" in result["checks"][0]["message"].lower() or "zero" in result["checks"][0]["message"].lower()
    
    def test_check_liveness(self):
        """Test liveness check."""
        from src.health import HealthChecker
        
        checker = HealthChecker("test-service")
        result = checker.check_liveness()
        
        assert result["alive"] is True
        assert result["service"] == "test-service"
    
    def test_check_readiness(self):
        """Test readiness check."""
        from src.health import HealthChecker
        
        checker = HealthChecker("test-service")
        checker.register_check("ready_check", lambda: (True, "OK", {}), is_readiness=True)
        
        result = checker.check_readiness()
        
        assert result["ready"] is True
        assert len(result["checks"]) == 1


class TestCommonChecks:
    """Test common check functions."""
    
    def test_check_disk_space(self):
        """Test disk space check."""
        from src.health import check_disk_space
        
        healthy, message, details = check_disk_space(min_free_gb=0.001)
        
        assert healthy is True
        assert "free" in message.lower()
        assert "free_gb" in details
    
    def test_check_mongodb(self):
        """Test MongoDB check with mock."""
        from src.health import check_mongodb
        
        mock_client = Mock()
        mock_client.admin.command.return_value = {"ok": 1}
        mock_client.server_info.return_value = {"version": "4.4.0"}
        
        healthy, message, details = check_mongodb(mock_client)
        
        assert healthy is True
        assert message == "Connected"
        assert details["version"] == "4.4.0"
    
    def test_check_mongodb_failure(self):
        """Test MongoDB check failure."""
        from src.health import check_mongodb
        
        mock_client = Mock()
        mock_client.admin.command.side_effect = Exception("Connection refused")
        
        healthy, message, details = check_mongodb(mock_client)
        
        assert healthy is False
        assert "refused" in message.lower()
    
    def test_check_redis(self):
        """Test Redis check with mock."""
        from src.health import check_redis
        
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.info.return_value = {"used_memory_human": "1.5M"}
        
        healthy, message, details = check_redis(mock_client)
        
        assert healthy is True
        assert message == "Connected"


class TestFlaskIntegration:
    """Test Flask integration."""
    
    @pytest.fixture
    def app(self):
        """Create Flask test app."""
        from flask import Flask
        from src.health import HealthChecker, create_health_blueprint
        
        app = Flask(__name__)
        
        checker = HealthChecker("test-api", "1.0.0")
        checker.register_check("always_ok", lambda: (True, "OK", {}))
        
        app.register_blueprint(create_health_blueprint(checker))
        
        return app
    
    def test_health_endpoint(self, app):
        """Test /health endpoint."""
        with app.test_client() as client:
            response = client.get('/health')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "healthy"
    
    def test_live_endpoint(self, app):
        """Test /live endpoint."""
        with app.test_client() as client:
            response = client.get('/live')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["alive"] is True
    
    def test_version_endpoint(self, app):
        """Test /version endpoint."""
        with app.test_client() as client:
            response = client.get('/version')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["version"] == "1.0.0"
