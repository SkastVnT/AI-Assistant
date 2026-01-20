"""
Public URL Manager for AI-Assistant Services
Manages dynamic public URLs from Cloudflared tunnels
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"


class PublicURLManager:
    """Manages public URLs for services exposed via Cloudflared."""
    
    # Default local URLs for each service
    LOCAL_SERVICES = {
        "hub-gateway": {"port": 3000, "url": "http://localhost:3000"},
        "chatbot": {"port": 5000, "url": "http://localhost:5000"},
        "speech2text": {"port": 5001, "url": "http://localhost:5001"},
        "text2sql": {"port": 5002, "url": "http://localhost:5002"},
        "document-intelligence": {"port": 5003, "url": "http://localhost:5003"},
        "stable-diffusion": {"port": 7860, "url": "http://localhost:7860"},
        "lora-training": {"port": 7862, "url": "http://localhost:7862"},
        "image-upscale": {"port": 7863, "url": "http://localhost:7863"},
        "mcp-server": {"port": 8000, "url": "http://localhost:8000"},
        "edit-image": {"port": 7861, "url": "http://localhost:7861"},
    }
    
    _cache: Dict[str, str] = {}
    _urls_file = LOGS_DIR / "public_urls.json"
    
    @classmethod
    def get_public_url(cls, service_name: str) -> Optional[str]:
        """Get public URL for a service if available."""
        # First check cache
        if service_name in cls._cache:
            return cls._cache[service_name]
        
        # Then check individual URL file
        url_file = LOGS_DIR / f"{service_name}_public_url.txt"
        if url_file.exists():
            try:
                url = url_file.read_text().strip()
                if url.startswith("https://"):
                    cls._cache[service_name] = url
                    return url
            except Exception:
                pass
        
        # Check JSON file
        if cls._urls_file.exists():
            try:
                with open(cls._urls_file) as f:
                    urls = json.load(f)
                    if service_name in urls:
                        cls._cache[service_name] = urls[service_name]
                        return urls[service_name]
            except Exception:
                pass
        
        return None
    
    @classmethod
    def get_url(cls, service_name: str, prefer_public: bool = True) -> str:
        """
        Get URL for a service.
        
        Args:
            service_name: Name of the service
            prefer_public: If True, return public URL if available, otherwise local
        
        Returns:
            The URL (public or local)
        """
        if prefer_public:
            public_url = cls.get_public_url(service_name)
            if public_url:
                return public_url
        
        # Return local URL
        if service_name in cls.LOCAL_SERVICES:
            return cls.LOCAL_SERVICES[service_name]["url"]
        
        return f"http://localhost:{cls.get_port(service_name)}"
    
    @classmethod
    def get_port(cls, service_name: str) -> int:
        """Get the port number for a service."""
        return cls.LOCAL_SERVICES.get(service_name, {}).get("port", 0)
    
    @classmethod
    def save_public_url(cls, service_name: str, url: str) -> None:
        """Save a public URL for a service."""
        # Save to individual file
        url_file = LOGS_DIR / f"{service_name}_public_url.txt"
        url_file.write_text(url)
        
        # Also update JSON file
        urls = {}
        if cls._urls_file.exists():
            try:
                with open(cls._urls_file) as f:
                    urls = json.load(f)
            except Exception:
                pass
        
        urls[service_name] = url
        
        with open(cls._urls_file, 'w') as f:
            json.dump(urls, f, indent=2)
        
        # Update cache
        cls._cache[service_name] = url
    
    @classmethod
    def get_all_urls(cls, prefer_public: bool = True) -> Dict[str, str]:
        """Get all service URLs."""
        urls = {}
        for service_name in cls.LOCAL_SERVICES:
            urls[service_name] = cls.get_url(service_name, prefer_public)
        return urls
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear the URL cache."""
        cls._cache = {}
    
    @classmethod
    def is_public_available(cls, service_name: str) -> bool:
        """Check if a public URL is available for a service."""
        return cls.get_public_url(service_name) is not None


# Singleton instance for easy access
url_manager = PublicURLManager()
