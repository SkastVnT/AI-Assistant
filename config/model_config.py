"""
Model Configuration for AI Assistant Hub
Centralized configuration for all AI services
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ServiceConfig:
    """Configuration for a single service."""
    name: str
    description: str
    icon: str
    port: int
    url: str  # Local URL
    color: str
    features: List[str]
    public_url: Optional[str] = None  # Public URL if exposed
    
    def get_effective_url(self, prefer_public: bool = True) -> str:
        """Get the URL to use - public if available and preferred."""
        if prefer_public and self.public_url:
            return self.public_url
        return self.url


class HubConfig:
    """Main configuration for Hub Gateway."""
    
    # Flask Configuration
    DEBUG = os.getenv("DEBUG", "True") == "True"
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")
    HOST = os.getenv("HUB_HOST", "0.0.0.0")
    PORT = int(os.getenv("HUB_PORT", "3000"))
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    
    # Services Configuration
    SERVICES: Dict[str, ServiceConfig] = {
        "chatbot": ServiceConfig(
            name="AI ChatBot",
            description="Trợ lý AI thông minh với Gemini, GPT-3.5, DeepSeek",
            icon="🤖",
            port=5000,
            url="http://localhost:5000",
            color="from-blue-500 to-purple-600",
            features=[
                "3 mô hình AI mạnh mẽ",
                "Tư vấn tâm lý chuyên sâu",
                "Giải pháp đời sống thực tế",
                "Trò chuyện tự nhiên"
            ]
        ),
        "speech2text": ServiceConfig(
            name="Speech to Text",
            description="Chuyển đổi giọng nói thành văn bản tiếng Việt",
            icon="🎤",
            port=5001,
            url="http://localhost:5001",
            color="from-green-500 to-teal-600",
            features=[
                "Nhận dạng tiếng Việt chuẩn",
                "Phân tách người nói (Diarization)",
                "Hỗ trợ nhiều định dạng audio",
                "Real-time transcription"
            ]
        ),
        "text2sql": ServiceConfig(
            name="Text to SQL",
            description="Tạo câu truy vấn SQL từ ngôn ngữ tự nhiên",
            icon="💾",
            port=5002,
            url="http://localhost:5002",
            color="from-orange-500 to-red-600",
            features=[
                "Gemini AI powered",
                "Học từ lịch sử truy vấn",
                "Hỗ trợ nhiều loại database",
                "SQL validation"
            ]
        )
    }
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/hub.log")
    
    # Cache Configuration
    CACHE_DIR = "data/cache"
    ENABLE_CACHE = os.getenv("ENABLE_CACHE", "True") == "True"
    
    @classmethod
    def get_service_config(cls, service_name: str) -> ServiceConfig:
        """Get configuration for a specific service."""
        return cls.SERVICES.get(service_name)
    
    @classmethod
    def get_all_services(cls, update_public_urls: bool = True) -> Dict[str, ServiceConfig]:
        """
        Get all service configurations.
        
        Args:
            update_public_urls: If True, update services with public URLs from files
        """
        if update_public_urls:
            cls._update_public_urls()
        return cls.SERVICES
    
    @classmethod
    def _update_public_urls(cls) -> None:
        """Update services with public URLs from URL manager."""
        try:
            from config.public_urls import url_manager
            
            for service_name, service in cls.SERVICES.items():
                public_url = url_manager.get_public_url(service_name)
                if public_url:
                    service.public_url = public_url
        except ImportError:
            pass  # URL manager not available

