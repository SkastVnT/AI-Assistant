"""
Configuration module for VistralS2T
Handles environment variables and model configurations
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
config_dir = Path(__file__).parent
load_dotenv(config_dir / ".env")

# API Keys
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HF_API_TOKEN") or "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"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# Audio Settings
AUDIO_PATH = os.getenv("AUDIO_PATH", "")
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "32000"))

# Model Settings
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
PHOWHISPER_MODEL = os.getenv("PHOWHISPER_MODEL", "vinai/PhoWhisper-large")
QWEN_MODEL = os.getenv("QWEN_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")

# Output Paths
OUTPUT_RAW = os.getenv("OUTPUT_RAW", "app/output/raw")
OUTPUT_VISTRAL = os.getenv("OUTPUT_VISTRAL", "app/output/vistral")
OUTPUT_DUAL = os.getenv("OUTPUT_DUAL", "app/output/dual")

__all__ = [
    "HF_TOKEN",
    "OPENAI_API_KEY", 
    "DEEPSEEK_API_KEY",
    "AUDIO_PATH",
    "SAMPLE_RATE",
    "WHISPER_MODEL",
    "PHOWHISPER_MODEL",
    "QWEN_MODEL",
    "OUTPUT_RAW",
    "OUTPUT_VISTRAL",
    "OUTPUT_DUAL",
]
