"""Configuration package for AI Assistant Hub.

Provides centralized access to project configuration:
- model_config: Service definitions and HubConfig
- logging_config: Logging setup
- public_urls: Public URL management for Cloudflare tunnels
- rate_limiter: API rate limiting
- response_cache: LLM response caching
"""

from pathlib import Path

CONFIG_DIR = Path(__file__).parent
PROJECT_ROOT = CONFIG_DIR.parent


def load_config_yml() -> dict:
    """Load config.yml as a dict. Returns empty dict on failure."""
    import yaml
    config_file = CONFIG_DIR / "config.yml"
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_service_port(service_name: str, default: int = 0) -> int:
    """Get port for a service from config.yml or model_config."""
    cfg = load_config_yml()
    services = cfg.get("services", {})
    if service_name in services:
        return services[service_name].get("port", default)
    # Fallback to model_config
    from config.model_config import HubConfig
    svc = HubConfig.get_service_config(service_name)
    return svc.port if svc else default
