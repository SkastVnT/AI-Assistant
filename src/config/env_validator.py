"""
Environment Validation Module
Validates required environment variables and configurations at startup
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EnvVarType(Enum):
    """Environment variable type."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    URL = "url"
    PATH = "path"
    EMAIL = "email"


@dataclass
class EnvVar:
    """Environment variable definition."""
    name: str
    required: bool = True
    var_type: EnvVarType = EnvVarType.STRING
    default: Any = None
    description: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    sensitive: bool = False


class ValidationError:
    """Validation error details."""
    
    def __init__(self, var_name: str, message: str, severity: str = "error"):
        self.var_name = var_name
        self.message = message
        self.severity = severity  # "error" or "warning"
    
    def __str__(self):
        return f"[{self.severity.upper()}] {self.var_name}: {self.message}"


class EnvironmentValidator:
    """
    Validates environment variables at startup.
    """
    
    def __init__(self, service_name: str):
        """
        Initialize validator.
        
        Args:
            service_name: Name of the service
        """
        self.service_name = service_name
        self._vars: List[EnvVar] = []
        self._errors: List[ValidationError] = []
        self._warnings: List[ValidationError] = []
    
    def add_var(self, env_var: EnvVar) -> 'EnvironmentValidator':
        """Add environment variable to validate."""
        self._vars.append(env_var)
        return self
    
    def add_vars(self, env_vars: List[EnvVar]) -> 'EnvironmentValidator':
        """Add multiple environment variables."""
        self._vars.extend(env_vars)
        return self
    
    def _parse_value(self, value: str, var_type: EnvVarType) -> Any:
        """Parse string value to specified type."""
        if var_type == EnvVarType.STRING:
            return value
        elif var_type == EnvVarType.INTEGER:
            return int(value)
        elif var_type == EnvVarType.FLOAT:
            return float(value)
        elif var_type == EnvVarType.BOOLEAN:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif var_type == EnvVarType.URL:
            # Basic URL validation
            if not value.startswith(('http://', 'https://')):
                raise ValueError("Must start with http:// or https://")
            return value
        elif var_type == EnvVarType.PATH:
            return value
        elif var_type == EnvVarType.EMAIL:
            if '@' not in value:
                raise ValueError("Invalid email format")
            return value
        return value
    
    def _validate_var(self, env_var: EnvVar) -> Optional[Any]:
        """Validate a single environment variable."""
        value = os.environ.get(env_var.name)
        
        # Check if required
        if value is None:
            if env_var.required:
                self._errors.append(ValidationError(
                    env_var.name,
                    f"Required environment variable not set. {env_var.description}"
                ))
                return None
            else:
                if env_var.default is not None:
                    self._warnings.append(ValidationError(
                        env_var.name,
                        f"Using default value: {env_var.default if not env_var.sensitive else '***'}",
                        "warning"
                    ))
                return env_var.default
        
        # Parse value
        try:
            parsed = self._parse_value(value, env_var.var_type)
        except (ValueError, TypeError) as e:
            self._errors.append(ValidationError(
                env_var.name,
                f"Invalid value type. Expected {env_var.var_type.value}: {e}"
            ))
            return None
        
        # Validate range
        if env_var.var_type in (EnvVarType.INTEGER, EnvVarType.FLOAT):
            if env_var.min_value is not None and parsed < env_var.min_value:
                self._errors.append(ValidationError(
                    env_var.name,
                    f"Value {parsed} is below minimum {env_var.min_value}"
                ))
                return None
            if env_var.max_value is not None and parsed > env_var.max_value:
                self._errors.append(ValidationError(
                    env_var.name,
                    f"Value {parsed} exceeds maximum {env_var.max_value}"
                ))
                return None
        
        # Validate allowed values
        if env_var.allowed_values and value not in env_var.allowed_values:
            self._errors.append(ValidationError(
                env_var.name,
                f"Value must be one of: {env_var.allowed_values}"
            ))
            return None
        
        # Validate path exists
        if env_var.var_type == EnvVarType.PATH and not os.path.exists(parsed):
            self._warnings.append(ValidationError(
                env_var.name,
                f"Path does not exist: {parsed}",
                "warning"
            ))
        
        return parsed
    
    def validate(self, exit_on_error: bool = True) -> Dict[str, Any]:
        """
        Validate all environment variables.
        
        Args:
            exit_on_error: Exit process if validation fails
        
        Returns:
            Dictionary of validated environment values
        """
        self._errors.clear()
        self._warnings.clear()
        
        values = {}
        
        logger.info(f"Validating environment for {self.service_name}...")
        
        for env_var in self._vars:
            value = self._validate_var(env_var)
            if value is not None:
                values[env_var.name] = value
        
        # Log warnings
        for warning in self._warnings:
            logger.warning(str(warning))
        
        # Log errors
        for error in self._errors:
            logger.error(str(error))
        
        # Handle errors
        if self._errors:
            error_msg = f"Environment validation failed with {len(self._errors)} error(s)"
            logger.error(error_msg)
            
            if exit_on_error:
                self._print_summary()
                sys.exit(1)
            else:
                raise EnvironmentError(error_msg)
        
        logger.info(f"Environment validation passed ({len(self._vars)} variables checked)")
        return values
    
    def _print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 60)
        print(f"ENVIRONMENT VALIDATION FAILED: {self.service_name}")
        print("=" * 60)
        
        print("\nErrors:")
        for error in self._errors:
            print(f"  ❌ {error}")
        
        if self._warnings:
            print("\nWarnings:")
            for warning in self._warnings:
                print(f"  ⚠️  {warning}")
        
        print("\nPlease set the required environment variables and try again.")
        print("=" * 60 + "\n")
    
    @property
    def errors(self) -> List[ValidationError]:
        """Get validation errors."""
        return self._errors
    
    @property
    def warnings(self) -> List[ValidationError]:
        """Get validation warnings."""
        return self._warnings


# ============================================================================
# COMMON ENVIRONMENT CONFIGURATIONS
# ============================================================================

# MongoDB configuration
MONGODB_VARS = [
    EnvVar(
        name="MONGODB_URI",
        required=True,
        var_type=EnvVarType.URL,
        description="MongoDB connection string",
        sensitive=True
    ),
    EnvVar(
        name="MONGODB_DB_NAME",
        required=False,
        default="ai_assistant",
        description="MongoDB database name"
    ),
]

# Redis configuration
REDIS_VARS = [
    EnvVar(
        name="REDIS_URL",
        required=False,
        var_type=EnvVarType.URL,
        default="redis://localhost:6379",
        description="Redis connection URL"
    ),
]

# Flask configuration
FLASK_VARS = [
    EnvVar(
        name="FLASK_ENV",
        required=False,
        default="production",
        allowed_values=["development", "production", "testing"],
        description="Flask environment"
    ),
    EnvVar(
        name="SECRET_KEY",
        required=True,
        description="Flask secret key for sessions",
        sensitive=True
    ),
]

# API Keys
API_KEY_VARS = [
    EnvVar(
        name="GROK_API_KEY",
        required=False,
        description="GROK API key from X.AI",
        sensitive=True
    ),
    EnvVar(
        name="OPENAI_API_KEY",
        required=False,
        description="OpenAI API key",
        sensitive=True
    ),
]

# Service configuration
SERVICE_VARS = [
    EnvVar(
        name="SERVICE_PORT",
        required=False,
        var_type=EnvVarType.INTEGER,
        default=5000,
        min_value=1000,
        max_value=65535,
        description="Service port"
    ),
    EnvVar(
        name="SERVICE_HOST",
        required=False,
        default="0.0.0.0",
        description="Service host"
    ),
    EnvVar(
        name="LOG_LEVEL",
        required=False,
        default="INFO",
        allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        description="Logging level"
    ),
]


def create_validator(service_name: str, 
                     include_mongodb: bool = True,
                     include_redis: bool = False,
                     include_flask: bool = True,
                     include_api_keys: bool = False,
                     additional_vars: List[EnvVar] = None) -> EnvironmentValidator:
    """
    Create a pre-configured environment validator.
    
    Args:
        service_name: Name of the service
        include_mongodb: Include MongoDB vars
        include_redis: Include Redis vars
        include_flask: Include Flask vars
        include_api_keys: Include API key vars
        additional_vars: Additional custom vars
    
    Returns:
        Configured EnvironmentValidator
    """
    validator = EnvironmentValidator(service_name)
    validator.add_vars(SERVICE_VARS)
    
    if include_mongodb:
        validator.add_vars(MONGODB_VARS)
    
    if include_redis:
        validator.add_vars(REDIS_VARS)
    
    if include_flask:
        validator.add_vars(FLASK_VARS)
    
    if include_api_keys:
        validator.add_vars(API_KEY_VARS)
    
    if additional_vars:
        validator.add_vars(additional_vars)
    
    return validator
