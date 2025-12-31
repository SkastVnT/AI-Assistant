"""
Tests for Environment Validator Module
"""

import pytest
import os
from unittest.mock import patch


class TestEnvVarType:
    """Test EnvVarType enum."""
    
    def test_env_var_types(self):
        """Test environment variable types."""
        from src.config.env_validator import EnvVarType
        
        assert EnvVarType.STRING.value == "string"
        assert EnvVarType.INTEGER.value == "integer"
        assert EnvVarType.BOOLEAN.value == "boolean"
        assert EnvVarType.URL.value == "url"


class TestEnvVar:
    """Test EnvVar dataclass."""
    
    def test_env_var_creation(self):
        """Test creating env var definition."""
        from src.config.env_validator import EnvVar, EnvVarType
        
        env_var = EnvVar(
            name="DATABASE_URL",
            required=True,
            var_type=EnvVarType.URL,
            description="Database connection string"
        )
        
        assert env_var.name == "DATABASE_URL"
        assert env_var.required is True
        assert env_var.var_type == EnvVarType.URL
    
    def test_env_var_defaults(self):
        """Test env var default values."""
        from src.config.env_validator import EnvVar, EnvVarType
        
        env_var = EnvVar(name="TEST_VAR")
        
        assert env_var.required is True
        assert env_var.var_type == EnvVarType.STRING
        assert env_var.default is None
        assert env_var.sensitive is False


class TestEnvironmentValidator:
    """Test EnvironmentValidator class."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        from src.config.env_validator import EnvironmentValidator
        
        validator = EnvironmentValidator("test-service")
        
        assert validator.service_name == "test-service"
    
    def test_add_var(self):
        """Test adding a variable."""
        from src.config.env_validator import EnvironmentValidator, EnvVar
        
        validator = EnvironmentValidator("test")
        env_var = EnvVar(name="TEST_VAR")
        
        result = validator.add_var(env_var)
        
        assert result is validator  # Returns self for chaining
        assert len(validator._vars) == 1
    
    def test_add_vars(self):
        """Test adding multiple variables."""
        from src.config.env_validator import EnvironmentValidator, EnvVar
        
        validator = EnvironmentValidator("test")
        vars_list = [
            EnvVar(name="VAR1"),
            EnvVar(name="VAR2")
        ]
        
        validator.add_vars(vars_list)
        
        assert len(validator._vars) == 2
    
    def test_validate_required_missing(self):
        """Test validation fails for missing required var."""
        from src.config.env_validator import EnvironmentValidator, EnvVar
        
        validator = EnvironmentValidator("test")
        validator.add_var(EnvVar(name="MISSING_VAR", required=True))
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises((EnvironmentError, SystemExit)):
                validator.validate(exit_on_error=False)
    
    def test_validate_optional_with_default(self):
        """Test optional var uses default."""
        from src.config.env_validator import EnvironmentValidator, EnvVar
        
        validator = EnvironmentValidator("test")
        validator.add_var(EnvVar(
            name="OPTIONAL_VAR",
            required=False,
            default="default_value"
        ))
        
        with patch.dict(os.environ, {}, clear=True):
            result = validator.validate(exit_on_error=False)
        
        assert result.get("OPTIONAL_VAR") == "default_value"
    
    def test_validate_integer_type(self):
        """Test integer type parsing."""
        from src.config.env_validator import EnvironmentValidator, EnvVar, EnvVarType
        
        validator = EnvironmentValidator("test")
        validator.add_var(EnvVar(
            name="PORT",
            var_type=EnvVarType.INTEGER
        ))
        
        with patch.dict(os.environ, {"PORT": "8080"}, clear=True):
            result = validator.validate(exit_on_error=False)
        
        assert result["PORT"] == 8080
        assert isinstance(result["PORT"], int)
    
    def test_validate_integer_invalid(self):
        """Test invalid integer raises error."""
        from src.config.env_validator import EnvironmentValidator, EnvVar, EnvVarType
        
        validator = EnvironmentValidator("test")
        validator.add_var(EnvVar(
            name="PORT",
            var_type=EnvVarType.INTEGER
        ))
        
        with patch.dict(os.environ, {"PORT": "not_a_number"}, clear=True):
            with pytest.raises((EnvironmentError, SystemExit)):
                validator.validate(exit_on_error=False)
    
    def test_validate_boolean_type(self):
        """Test boolean type parsing."""
        from src.config.env_validator import EnvironmentValidator, EnvVar, EnvVarType
        
        validator = EnvironmentValidator("test")
        validator.add_var(EnvVar(
            name="DEBUG",
            var_type=EnvVarType.BOOLEAN
        ))
        
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=True):
            result = validator.validate(exit_on_error=False)
        
        assert result["DEBUG"] is True
    
    def test_validate_allowed_values(self):
        """Test allowed values validation."""
        from src.config.env_validator import EnvironmentValidator, EnvVar
        
        validator = EnvironmentValidator("test")
        validator.add_var(EnvVar(
            name="ENVIRONMENT",
            allowed_values=["development", "production"]
        ))
        
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            result = validator.validate(exit_on_error=False)
        
        assert result["ENVIRONMENT"] == "development"
    
    def test_validate_allowed_values_invalid(self):
        """Test invalid allowed value raises error."""
        from src.config.env_validator import EnvironmentValidator, EnvVar
        
        validator = EnvironmentValidator("test")
        validator.add_var(EnvVar(
            name="ENVIRONMENT",
            allowed_values=["development", "production"]
        ))
        
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}, clear=True):
            with pytest.raises((EnvironmentError, SystemExit)):
                validator.validate(exit_on_error=False)
    
    def test_validate_min_max_range(self):
        """Test min/max range validation."""
        from src.config.env_validator import EnvironmentValidator, EnvVar, EnvVarType
        
        validator = EnvironmentValidator("test")
        validator.add_var(EnvVar(
            name="TIMEOUT",
            var_type=EnvVarType.INTEGER,
            min_value=1,
            max_value=300
        ))
        
        with patch.dict(os.environ, {"TIMEOUT": "60"}, clear=True):
            result = validator.validate(exit_on_error=False)
        
        assert result["TIMEOUT"] == 60
    
    def test_validate_below_min(self):
        """Test value below minimum raises error."""
        from src.config.env_validator import EnvironmentValidator, EnvVar, EnvVarType
        
        validator = EnvironmentValidator("test")
        validator.add_var(EnvVar(
            name="TIMEOUT",
            var_type=EnvVarType.INTEGER,
            min_value=10
        ))
        
        with patch.dict(os.environ, {"TIMEOUT": "5"}, clear=True):
            with pytest.raises((EnvironmentError, SystemExit)):
                validator.validate(exit_on_error=False)
    
    def test_validate_url_type(self):
        """Test URL type validation."""
        from src.config.env_validator import EnvironmentValidator, EnvVar, EnvVarType
        
        validator = EnvironmentValidator("test")
        validator.add_var(EnvVar(
            name="API_URL",
            var_type=EnvVarType.URL
        ))
        
        with patch.dict(os.environ, {"API_URL": "https://api.example.com"}, clear=True):
            result = validator.validate(exit_on_error=False)
        
        assert result["API_URL"] == "https://api.example.com"
    
    def test_validate_invalid_url(self):
        """Test invalid URL raises error."""
        from src.config.env_validator import EnvironmentValidator, EnvVar, EnvVarType
        
        validator = EnvironmentValidator("test")
        validator.add_var(EnvVar(
            name="API_URL",
            var_type=EnvVarType.URL
        ))
        
        with patch.dict(os.environ, {"API_URL": "not-a-url"}, clear=True):
            with pytest.raises((EnvironmentError, SystemExit)):
                validator.validate(exit_on_error=False)


class TestCreateValidator:
    """Test create_validator helper function."""
    
    def test_create_basic_validator(self):
        """Test creating basic validator."""
        from src.config.env_validator import create_validator
        
        validator = create_validator(
            "test-service",
            include_mongodb=False,
            include_flask=False
        )
        
        assert validator.service_name == "test-service"
        assert len(validator._vars) > 0  # Has SERVICE_VARS
    
    def test_create_validator_with_mongodb(self):
        """Test validator includes MongoDB vars."""
        from src.config.env_validator import create_validator
        
        validator = create_validator(
            "test-service",
            include_mongodb=True,
            include_flask=False
        )
        
        var_names = [v.name for v in validator._vars]
        assert "MONGODB_URI" in var_names
    
    def test_create_validator_with_redis(self):
        """Test validator includes Redis vars."""
        from src.config.env_validator import create_validator
        
        validator = create_validator(
            "test-service",
            include_mongodb=False,
            include_redis=True,
            include_flask=False
        )
        
        var_names = [v.name for v in validator._vars]
        assert "REDIS_URL" in var_names


class TestValidationError:
    """Test ValidationError class."""
    
    def test_validation_error_str(self):
        """Test validation error string representation."""
        from src.config.env_validator import ValidationError
        
        error = ValidationError("MY_VAR", "is required", "error")
        
        assert "[ERROR]" in str(error)
        assert "MY_VAR" in str(error)
        assert "is required" in str(error)
    
    def test_validation_warning_str(self):
        """Test validation warning string."""
        from src.config.env_validator import ValidationError
        
        warning = ValidationError("MY_VAR", "using default", "warning")
        
        assert "[WARNING]" in str(warning)
