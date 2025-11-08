"""
Model Configuration for AI Assistant Hub
Centralized configuration for all AI services
"""

import os
from dataclasses import dataclass
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ServiceConfig:
    """Configuration for a single service."""
    name: str
    description: str
    icon: str
    port: int
    url: str
    color: str
    features: List[str]


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
            description="Trợ lý AI thông minh với Gemini, GPT-3.5, DeepSeek & Local LLMs",
            icon="🤖",
            port=5000,
            url="http://localhost:5000",
            color="from-blue-500 to-purple-600",
            features=[
                "Nhiều mô hình AI (Gemini, GPT, DeepSeek)",
                "Local LLMs (Qwen, BloomVN)",
                "Tư vấn tâm lý chuyên sâu",
                "Trò chuyện tự nhiên"
            ]
        ),
        "stable_diffusion": ServiceConfig(
            name="Stable Diffusion",
            description="Tạo hình ảnh từ mô tả văn bản với AI",
            icon="🎨",
            port=7860,
            url="http://localhost:7860",
            color="from-pink-500 to-rose-600",
            features=[
                "Text-to-Image generation",
                "Nhiều models & checkpoints",
                "ControlNet & LoRA support",
                "Inpainting & Outpainting"
            ]
        ),
        "speech2text": ServiceConfig(
            name="Speech to Text",
            description="Chuyển đổi giọng nói thành văn bản tiếng Việt",
            icon="🎤",
            port=5002,
            url="http://localhost:5002",
            color="from-green-500 to-teal-600",
            features=[
                "Whisper + PhoWhisper fusion",
                "Nhận dạng tiếng Việt chuẩn",
                "Phân tách người nói (Diarization)",
                "Hỗ trợ nhiều định dạng audio"
            ]
        ),
        "text2sql": ServiceConfig(
            name="Text to SQL",
            description="Tạo câu truy vấn SQL từ ngôn ngữ tự nhiên",
            icon="💾",
            port=5001,
            url="http://localhost:5001",
            color="from-orange-500 to-red-600",
            features=[
                "Gemini AI powered",
                "Học từ lịch sử truy vấn",
                "Hỗ trợ ClickHouse & MongoDB",
                "SQL validation & optimization"
            ]
        ),
        "document_intelligence": ServiceConfig(
            name="Document Intelligence",
            description="OCR và phân tích tài liệu thông minh với AI",
            icon="📄",
            port=5003,
            url="http://localhost:5003",
            color="from-indigo-500 to-blue-600",
            features=[
                "PaddleOCR - Vietnamese support",
                "Gemini 2.0 Flash AI enhancement",
                "PDF & Image processing",
                "Structured data extraction"
            ]
        ),
        "rag_services": ServiceConfig(
            name="RAG Services",
            description="Retrieval-Augmented Generation cho Q&A thông minh",
            icon="📚",
            port=5004,
            url="http://localhost:5004",
            color="from-cyan-500 to-blue-600",
            features=[
                "Document retrieval & embedding",
                "LangChain integration",
                "ChromaDB vector store",
                "Context-aware answering"
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
    def get_all_services(cls) -> Dict[str, ServiceConfig]:
        """Get all service configurations."""
        return cls.SERVICES
