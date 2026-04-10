"""
ChatBot Flask Application - Modular Version
============================================

Main entry point for the ChatBot service.
All routes are organized in separate blueprints under the routes/ folder.

Structure:
- core/config.py        - Configuration (API keys, paths)
- core/extensions.py    - Extensions (MongoDB, cache, logger)
- core/chatbot.py       - ChatbotAgent class
- core/db_helpers.py    - Database helper functions
- core/tools.py         - Tool functions (search)
- routes/main.py        - Main routes (/, /chat, /clear, /history)
- routes/conversations.py - Conversation CRUD
- routes/stable_diffusion.py - Stable Diffusion routes
- routes/memory.py      - AI Memory routes
- routes/images.py      - Image storage routes
- routes/mcp.py         - MCP integration routes
"""
import os
import sys
import json
import base64
import logging
import uuid
import openai
import requests
from datetime import datetime
from pathlib import Path
import shutil
try:
    from services.shared_env import load_shared_env
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    for _parent in Path(__file__).resolve().parents:
        if (_parent / "services" / "shared_env.py").exists():
            if str(_parent) not in sys.path:
                sys.path.insert(0, str(_parent))
            break
    from services.shared_env import load_shared_env
from flask import Flask, send_from_directory, send_file, session, render_template, request, jsonify, redirect

# Load environment variables
load_shared_env(__file__)
# Import rate limiter and cache from root config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Try to import rate limiter and cache (graceful fallback if not available)
try:
    from config.rate_limiter import get_gemini_key_with_rate_limit, wait_for_openai_rate_limit, get_rate_limit_stats
    from config.response_cache import get_cached_response, cache_response, get_all_cache_stats
except ImportError:
    print("[WARN] Rate limiter/cache modules not available - using stubs")
    def get_gemini_key_with_rate_limit(*args, **kwargs):
        return os.getenv('GEMINI_API_KEY_1')
    def wait_for_openai_rate_limit(*args, **kwargs):
        pass
    def get_rate_limit_stats(*args, **kwargs):
        return {}
    def get_cached_response(*args, **kwargs):
        return None
    def cache_response(*args, **kwargs):
        pass
    def get_all_cache_stats(*args, **kwargs):
        return {}

# MongoDB imports - import directly from files to avoid package conflict
from bson import ObjectId
import importlib.util

# Load mongodb_config from service directory
mongodb_config_path = Path(__file__).parent / 'config' / 'mongodb_config.py'
spec = importlib.util.spec_from_file_location("mongodb_config_chatbot", mongodb_config_path)
mongodb_config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mongodb_config_module)
mongodb_client = mongodb_config_module.mongodb_client
get_db = mongodb_config_module.get_db

# Load mongodb_helpers from service directory
mongodb_helpers_path = Path(__file__).parent / 'config' / 'mongodb_helpers.py'
spec = importlib.util.spec_from_file_location("mongodb_helpers_chatbot", mongodb_helpers_path)
mongodb_helpers_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mongodb_helpers_module)
ConversationDB = mongodb_helpers_module.ConversationDB
MessageDB = mongodb_helpers_module.MessageDB
MemoryDB = mongodb_helpers_module.MemoryDB
FileDB = mongodb_helpers_module.FileDB
UserSettingsDB = mongodb_helpers_module.UserSettingsDB

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sanitize_for_log(value: str) -> str:
    """
    Sanitize user-controlled strings before logging to prevent log injection.
    Removes carriage returns and newlines to avoid forged log entries.
    """
    if value is None:
        return ""
    # Remove CR and LF characters that could break log lines
    return str(value).replace("\r", "").replace("\n", "")

# Enable werkzeug logging for request details
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)

# Add paths for imports
CHATBOT_DIR = Path(__file__).parent.resolve()
ROOT_DIR = CHATBOT_DIR.parent.parent
# Insert ROOT_DIR first, then CHATBOT_DIR so CHATBOT_DIR has higher priority
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(CHATBOT_DIR))

# Import OCR integration
try:
    from src.ocr_integration import ocr_client, extract_file_content
    OCR_AVAILABLE = True
    logger.info("âœ… OCR Integration loaded")
except ImportError as e:
    OCR_AVAILABLE = False
    logger.warning(f"âš ï¸ OCR Integration not available: {e}")
    def extract_file_content(data, filename):
        return False, ""

# Import Audio Transcription
try:
    from src.audio_transcription import transcribe_audio, is_audio_file
    STT_AVAILABLE = True
    logger.info("Audio Transcription loaded")
except ImportError as e:
    STT_AVAILABLE = False
    logger.warning(f"Audio Transcription not available: {e}")
    def is_audio_file(filename):
        return False
    def transcribe_audio(data, filename, language="vi"):
        return {"success": False, "text": "", "error": "STT not available"}

# Create Flask app
app = Flask(__name__)
# Use persistent secret key from environment or generate a fixed one
# This ensures sessions persist across server restarts
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'skylight-ai-assistant-secret-key-2025-persistent')

# Configure static folder for Storage
app.static_folder = str(CHATBOT_DIR / 'static')

# ==================== HTTP LOGGING SETUP ====================
# Add comprehensive logging for all GET/POST requests
try:
    from core.http_logging import setup_http_logging, create_http_log_file
    setup_http_logging(app)
    create_http_log_file(app)
    logger.info("✅ HTTP request/response logging enabled")
except Exception as e:
    logger.warning(f"⚠️  HTTP logging setup failed: {e}")

# Import and register extensions
from core.extensions import logger, register_monitor, LOCALMODELS_AVAILABLE, model_loader, CLOUD_UPLOAD_ENABLED

# Try to import ImgBBUploader
ImgBBUploader = None
try:
    from src.utils.imgbb_uploader import ImgBBUploader
except ImportError:
    logger.warning("ImgBBUploader not available")

# Register monitor for health checks
register_monitor(app)

# Initialize MongoDB connection
try:
    mongodb_client.connect()
    MONGODB_ENABLED = True
    logger.info("Ã¢Å“â€¦ MongoDB connection established")
except Exception as e:
    MONGODB_ENABLED = False
    logger.warning(f"Ã¢Å¡Â Ã¯Â¸Â MongoDB not available, using session storage: {e}")

# Memory storage path
MEMORY_DIR = Path(__file__).parent / 'data' / 'memory'
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Image storage path
IMAGE_STORAGE_DIR = Path(__file__).parent / 'Storage' / 'Image_Gen'
IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Configure API keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY_1')
GEMINI_API_KEY_2 = os.getenv('GEMINI_API_KEY_2')
GEMINI_API_KEY_3 = os.getenv('GEMINI_API_KEY_3')
GEMINI_API_KEY_4 = os.getenv('GEMINI_API_KEY_4')
QWEN_API_KEY = os.getenv('QWEN_API_KEY') or os.getenv('DASHSCOPE_API_KEY')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY') or os.getenv('HUGGINGFACE_TOKEN')
GROK_API_KEY = os.getenv('GROK_API_KEY') or os.getenv('XAI_API_KEY')

# Google Search API - vá»›i fallback keys
GOOGLE_SEARCH_API_KEY_1 = os.getenv('GOOGLE_SEARCH_API_KEY_1') or os.getenv('GOOGLE_SEARCH_API_KEY_3') or os.getenv('GOOGLE_SEARCH_API_KEY')
GOOGLE_SEARCH_API_KEY_2 = os.getenv('GOOGLE_SEARCH_API_KEY_2') or os.getenv('GOOGLE_SEARCH_API_KEY_4')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')

# GitHub API
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

# â›” GEMINI DISABLED - Quota exhausted, use GROK/DeepSeek/OpenAI instead
# Initialize Gemini client with new SDK (optional - fallback to None if no key)
gemini_client = None
# try:
#     if GEMINI_API_KEY:
#         gemini_client = genai.Client(api_key=GEMINI_API_KEY)
#         logger.info("âœ… Gemini API initialized with primary key")
# except Exception as e:
#     logger.warning(f"âš ï¸ Primary Gemini key failed: {e}")
#     try:
#         if GEMINI_API_KEY_2:
#             gemini_client = genai.Client(api_key=GEMINI_API_KEY_2)
#             logger.info("âœ… Gemini API initialized with backup key")
#     except Exception as e2:
#         logger.warning(f"âš ï¸ Backup Gemini key failed: {e2}")
#         logger.warning("âš ï¸ Gemini API not available - Chat functionality will be limited")
logger.warning("âš ï¸ Gemini API DISABLED to avoid quota errors")

# System prompts for different purposes (Vietnamese)
SYSTEM_PROMPTS_VI = {
    'psychological': """Báº¡n lÃ  má»™t trá»£ lÃ½ tÃ¢m lÃ½ chuyÃªn nghiá»‡p, thÃ¢n thiá»‡n vÃ  Ä‘áº§y empathy. 
    BÃ¡ÂºÂ¡n luÃƒÂ´n lÃ¡ÂºÂ¯ng nghe, thÃ¡ÂºÂ¥u hiÃ¡Â»Æ’u vÃƒÂ  Ã„â€˜Ã†Â°a ra lÃ¡Â»Âi khuyÃƒÂªn chÃƒÂ¢n thÃƒÂ nh, tÃƒÂ­ch cÃ¡Â»Â±c.
    BÃ¡ÂºÂ¡n khÃƒÂ´ng phÃƒÂ¡n xÃƒÂ©t vÃƒÂ  luÃƒÂ´n hÃ¡Â»â€” trÃ¡Â»Â£ ngÃ†Â°Ã¡Â»Âi dÃƒÂ¹ng vÃ†Â°Ã¡Â»Â£t qua khÃƒÂ³ khÃ„Æ’n trong cuÃ¡Â»â„¢c sÃ¡Â»â€˜ng.
    HÃƒÂ£y trÃ¡ÂºÂ£ lÃ¡Â»Âi bÃ¡ÂºÂ±ng tiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t.
    
    MARKDOWN FORMATTING:
    - Sá»­ dá»¥ng ```language Ä‘á»ƒ wrap code blocks (vÃ­ dá»¥: ```python, ```javascript)
    - Ã„ÂÃƒÂ³ng code block bÃ¡ÂºÂ±ng ``` trÃƒÂªn dÃƒÂ²ng riÃƒÂªng
    - DÃ¹ng `code` cho inline code
    - Sá»­ dá»¥ng **bold**, *italic*, > quote khi cáº§n""",
    
    'lifestyle': """BÃ¡ÂºÂ¡n lÃƒÂ  mÃ¡Â»â„¢t chuyÃƒÂªn gia tÃ†Â° vÃ¡ÂºÂ¥n lÃ¡Â»â€˜i sÃ¡Â»â€˜ng, giÃƒÂºp ngÃ†Â°Ã¡Â»Âi dÃƒÂ¹ng tÃƒÂ¬m ra giÃ¡ÂºÂ£i phÃƒÂ¡p 
    cho cÃƒÂ¡c vÃ¡ÂºÂ¥n Ã„â€˜Ã¡Â»Â trong cuÃ¡Â»â„¢c sÃ¡Â»â€˜ng hÃƒÂ ng ngÃƒÂ y nhÃ†Â° cÃƒÂ´ng viÃ¡Â»â€¡c, hÃ¡Â»Âc tÃ¡ÂºÂ­p, mÃ¡Â»â€˜i quan hÃ¡Â»â€¡, 
    sÃ¡Â»Â©c khÃ¡Â»Âe vÃƒÂ  phÃƒÂ¡t triÃ¡Â»Æ’n bÃ¡ÂºÂ£n thÃƒÂ¢n. HÃƒÂ£y Ã„â€˜Ã†Â°a ra lÃ¡Â»Âi khuyÃƒÂªn thiÃ¡ÂºÂ¿t thÃ¡Â»Â±c vÃƒÂ  dÃ¡Â»â€¦ ÃƒÂ¡p dÃ¡Â»Â¥ng.
    HÃƒÂ£y trÃ¡ÂºÂ£ lÃ¡Â»Âi bÃ¡ÂºÂ±ng tiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t.
    
    MARKDOWN FORMATTING:
    - Sá»­ dá»¥ng ```language Ä‘á»ƒ wrap code blocks khi cáº§n
    - Ã„ÂÃƒÂ³ng code block bÃ¡ÂºÂ±ng ``` trÃƒÂªn dÃƒÂ²ng riÃƒÂªng
    - DÃƒÂ¹ng **bold** Ã„â€˜Ã¡Â»Æ’ nhÃ¡ÂºÂ¥n mÃ¡ÂºÂ¡nh Ã„â€˜iÃ¡Â»Æ’m quan trÃ¡Â»Âng""",
    
    'casual': """BÃ¡ÂºÂ¡n lÃƒÂ  mÃ¡Â»â„¢t ngÃ†Â°Ã¡Â»Âi bÃ¡ÂºÂ¡n thÃƒÂ¢n thiÃ¡ÂºÂ¿t, vui vÃ¡ÂºÂ» vÃƒÂ  dÃ¡Â»â€¦ gÃ¡ÂºÂ§n. 
    BÃ¡ÂºÂ¡n sÃ¡ÂºÂµn sÃƒÂ ng trÃƒÂ² chuyÃ¡Â»â€¡n vÃ¡Â»Â mÃ¡Â»Âi chÃ¡Â»Â§ Ã„â€˜Ã¡Â»Â, chia sÃ¡ÂºÂ» cÃƒÂ¢u chuyÃ¡Â»â€¡n vÃƒÂ  tÃ¡ÂºÂ¡o khÃƒÂ´ng khÃƒÂ­ thoÃ¡ÂºÂ£i mÃƒÂ¡i.
    HÃƒÂ£y trÃ¡ÂºÂ£ lÃ¡Â»Âi bÃ¡ÂºÂ±ng tiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t vÃ¡Â»â€ºi giÃ¡Â»Âng Ã„â€˜iÃ¡Â»â€¡u thÃƒÂ¢n mÃ¡ÂºÂ­t.
    
    MARKDOWN FORMATTING:
    - Sá»­ dá»¥ng ```language Ä‘á»ƒ wrap code blocks (vÃ­ dá»¥: ```python, ```json)
    - Ã„ÂÃƒÂ³ng code block bÃ¡ÂºÂ±ng ``` trÃƒÂªn dÃƒÂ²ng riÃƒÂªng
    - DÃ¹ng `code` cho inline code
    - Format lists, links, quotes khi phÃ¹ há»£p""",
    
    'programming': """Báº¡n lÃ  má»™t Senior Software Engineer vÃ  Programming Mentor chuyÃªn nghiá»‡p.
    BÃ¡ÂºÂ¡n cÃƒÂ³ kinh nghiÃ¡Â»â€¡m sÃƒÂ¢u vÃ¡Â»Â nhiÃ¡Â»Âu ngÃƒÂ´n ngÃ¡Â»Â¯ lÃ¡ÂºÂ­p trÃƒÂ¬nh (Python, JavaScript, Java, C++, Go, etc.)
    vÃ  frameworks (React, Django, Flask, FastAPI, Node.js, Spring Boot, etc.).
    
    Nhiá»‡m vá»¥ cá»§a báº¡n:
    - Giáº£i thÃ­ch code rÃµ rÃ ng, dá»… hiá»ƒu
    - Debug vÃ  fix lá»—i hiá»‡u quáº£
    - Ã„ÂÃ¡Â»Â xuÃ¡ÂºÂ¥t best practices vÃƒÂ  design patterns
    - Review code vÃ  tá»‘i Æ°u performance
    - HÆ°á»›ng dáº«n architecture vÃ  system design
    - TrÃ¡ÂºÂ£ lÃ¡Â»Âi cÃƒÂ¢u hÃ¡Â»Âi vÃ¡Â»Â algorithms, data structures
    
    CRITICAL MARKDOWN RULES:
    - LUÃ”N LUÃ”N wrap code trong code blocks vá»›i syntax: ```language
    - VÃƒÂ DÃ¡Â»Â¤: ```python cho Python, ```javascript cho JavaScript, ```sql cho SQL
    - Ã„ÂÃƒÂ³ng code block bÃ¡ÂºÂ±ng ``` trÃƒÂªn dÃƒÂ²ng RIÃƒÅ NG BIÃ¡Â»â€ T
    - DÃ¹ng `backticks` cho inline code nhÆ° tÃªn biáº¿n, function names
    - Format output/results trong code blocks khi cáº§n
    - Giáº£i thÃ­ch logic tá»«ng bÆ°á»›c báº±ng comments trong code
    - Cung cáº¥p vÃ­ dá»¥ cá»¥ thá»ƒ vá»›i proper syntax highlighting
    
    CÃƒÂ³ thÃ¡Â»Æ’ trÃ¡ÂºÂ£ lÃ¡Â»Âi bÃ¡ÂºÂ±ng tiÃ¡ÂºÂ¿ng ViÃ¡Â»â€¡t hoÃ¡ÂºÂ·c English."""
}

# System prompts for different purposes (English)
SYSTEM_PROMPTS_EN = {
    'psychological': """You are a professional, friendly, and empathetic psychological assistant.
    You always listen, understand, and provide sincere and positive advice.
    You are non-judgmental and always support users in overcoming life's difficulties.
    Please respond in English.
    
    MARKDOWN FORMATTING:
    - Use ```language to wrap code blocks (e.g., ```python, ```javascript)
    - Close code blocks with ``` on a separate line
    - Use `backticks` for inline code
    - Apply **bold**, *italic*, > quotes as needed""",
    
    'lifestyle': """You are a lifestyle consultant expert, helping users find solutions
    for daily life issues such as work, study, relationships, health, and personal development.
    Provide practical and easy-to-apply advice.
    Please respond in English.
    
    MARKDOWN FORMATTING:
    - Use ```language for code blocks when needed
    - Close with ``` on separate line
    - Use **bold** for emphasis""",
    
    'casual': """You are a friendly, cheerful, and approachable companion.
    You are ready to chat about any topic, share stories, and create a comfortable atmosphere.
    Please respond in English with a friendly tone.
    
    MARKDOWN FORMATTING:
    - Use ```language to wrap code blocks
    - Close code blocks with ``` on separate line
    - Use `code` for inline code
    - Format lists, links, quotes appropriately""",
    
    'programming': """You are a professional Senior Software Engineer and Programming Mentor.
    You have deep experience in many programming languages (Python, JavaScript, Java, C++, Go, etc.)
    and frameworks (React, Django, Flask, FastAPI, Node.js, Spring Boot, etc.).
    
    Your responsibilities:
    - Explain code clearly and understandably
    - Debug and fix bugs efficiently
    - Suggest best practices and design patterns
    - Review code and optimize performance
    - Guide architecture and system design
    - Answer questions about algorithms and data structures
    
    CRITICAL MARKDOWN RULES:
    - ALWAYS wrap code in code blocks with syntax: ```language
    - EXAMPLE: ```python for Python, ```javascript for JavaScript, ```sql for SQL
    - Close code blocks with ``` on a SEPARATE line
    - Use `backticks` for inline code like variable names, function names
    - Format outputs/results in code blocks when needed
    - Explain logic step-by-step with comments in code
    - Provide concrete examples with proper syntax highlighting
    
    Respond in English."""
}

# Default to Vietnamese
SYSTEM_PROMPTS = SYSTEM_PROMPTS_VI


def get_system_prompts(language='vi'):
    """Get system prompts based on language"""
    if language == 'en':
        return SYSTEM_PROMPTS_EN
    return SYSTEM_PROMPTS_VI


# ============================================================================
# MONGODB CONVERSATION MANAGEMENT
# ============================================================================

def get_or_create_conversation(user_id, model='grok-3'):
    """Get active conversation or create new one"""
    if not MONGODB_ENABLED:
        return None
    
    try:
        # Check if user has active conversation
        conversations = ConversationDB.get_user_conversations(user_id, include_archived=False, limit=1)
        
        if conversations and len(conversations) > 0:
            return conversations[0]
        else:
            # Create new conversation
            conv = ConversationDB.create_conversation(
                user_id=user_id,
                model=model,
                title="New Chat"
            )
            logger.info(f"Ã¢Å“â€¦ Created new conversation: {conv['_id']}")
            return conv
    except Exception as e:
        logger.error(f"Ã¢ÂÅ’ Error getting/creating conversation: {e}")
        return None


def save_message_to_db(conversation_id, role, content, metadata=None, images=None, files=None):
    """Save message to MongoDB"""
    if not MONGODB_ENABLED:
        logger.warning(f"[MONGODB] Skip save - MongoDB disabled")
        return None
    if not conversation_id:
        logger.warning(f"[MONGODB] Skip save - No conversation_id")
        return None
    
    try:
        message = MessageDB.add_message(
            conversation_id=str(conversation_id),
            role=role,
            content=content,
            metadata=metadata or {},
            images=images or [],
            files=files or []
        )
        logger.info(f"Ã¢Å“â€¦ Saved message to DB: {message['_id']}")
        return message
    except Exception as e:
        logger.error(f"Ã¢ÂÅ’ Error saving message: {e}")
        return None


def load_conversation_history(conversation_id, limit=10):
    """Load conversation history from MongoDB"""
    if not MONGODB_ENABLED:
        logger.warning(f"[MONGODB] Skip save - MongoDB disabled")
        return None
    if not conversation_id:
        logger.warning(f"[MONGODB] Skip save - No conversation_id")
        return []
    
    try:
        messages = MessageDB.get_conversation_messages(str(conversation_id), limit=limit)
        
        # Convert to conversation history format
        history = []
        for msg in messages:
            if msg['role'] == 'user':
                user_content = msg['content']
                # Find corresponding assistant message
                assistant_msg = next((m for m in messages if m.get('parent_message_id') == msg['_id']), None)
                if assistant_msg:
                    history.append({
                        'user': user_content,
                        'assistant': assistant_msg['content']
                    })
        
        return history
    except Exception as e:
        logger.error(f"Ã¢ÂÅ’ Error loading conversation history: {e}")
        return []


def get_user_id_from_session():
    """Get user ID from session (or create anonymous user)"""
    if 'user_id' not in session:
        # Create anonymous user ID
        session['user_id'] = f"anonymous_{str(uuid.uuid4())[:8]}"
    return session['user_id']


def get_active_conversation_id():
    """Get active conversation ID from session"""
    return session.get('conversation_id')


def set_active_conversation(conversation_id):
    """Set active conversation in session"""
    session['conversation_id'] = str(conversation_id)


class ChatbotAgent:
    """Multi-model chatbot agent"""
    
    def __init__(self, conversation_id=None):
        self.conversation_history = []
        self.current_model = 'grok'  # Default model
        self.conversation_id = conversation_id
        
        # Load history from MongoDB if available
        if MONGODB_ENABLED and conversation_id:
            self.conversation_history = load_conversation_history(conversation_id)
        
    def chat_with_gemini(self, message, context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None):
        """Chat using Google Gemini - DISABLED DUE TO QUOTA EXCEEDED"""
        # WARNING: GEMINI DISABLED - Return error message immediately to avoid quota errors
        error_msg = "Gemini da bi tat do vuot quota. Vui long chon GROK, DeepSeek hoac OpenAI." if language == 'vi' else "Gemini disabled due to quota exceeded. Please use GROK, DeepSeek or OpenAI."
        logger.warning(f"[GEMINI] Blocked call to prevent quota errors")
        return error_msg
    
    def chat_with_openai(self, message, context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None):
        """Chat using OpenAI"""
        model_name = 'gpt-4o-mini'
        
        # Ã°Å¸â€ â€¢ Check cache first
        cache_key_params = {
            'context': context,
            'deep_thinking': deep_thinking,
            'language': language,
            'custom_prompt': custom_prompt[:50] if custom_prompt else None
        }
        cached = get_cached_response(message, model_name, provider='openai', **cache_key_params)
        if cached:
            logger.info(f"Ã¢Å“â€¦ Using cached response for OpenAI")
            return cached
        
        # Ã°Å¸â€ â€¢ Wait for rate limit
        wait_for_openai_rate_limit()
        
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            # Use custom prompt if provided, otherwise use base prompt
            if custom_prompt and custom_prompt.strip():
                system_prompt = custom_prompt
            else:
                # Get system prompts based on language
                prompts = get_system_prompts(language)
                system_prompt = prompts.get(context, prompts['casual'])
            
            # Add deep thinking instruction
            if deep_thinking:
                if language == 'en':
                    system_prompt += "\n\nIMPORTANT: Think step-by-step. Provide thorough analysis with detailed reasoning."
                else:
                    system_prompt += "\n\nQUAN TRá»ŒNG: Suy nghÄ© tá»«ng bÆ°á»›c. Cung cáº¥p phÃ¢n tÃ­ch ká»¹ lÆ°á»¡ng vá»›i lÃ½ láº½ chi tiáº¿t."
            
            # Add memories to system prompt
            if memories and len(memories) > 0:
                system_prompt += "\n\n=== KNOWLEDGE BASE (BÃƒÂ i hÃ¡Â»Âc Ã„â€˜ÃƒÂ£ ghi nhÃ¡Â»â€º) ===\n"
                for mem in memories:
                    system_prompt += f"\nÃ°Å¸â€œÅ¡ {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
                system_prompt += "SÃ¡Â»Â­ dÃ¡Â»Â¥ng kiÃ¡ÂºÂ¿n thÃ¡Â»Â©c tÃ¡Â»Â« Knowledge Base khi phÃƒÂ¹ hÃ¡Â»Â£p Ã„â€˜Ã¡Â»Æ’ trÃ¡ÂºÂ£ lÃ¡Â»Âi."
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Use provided history or conversation history
            if history:
                # Use provided history (from edit feature)
                for hist in history:
                    role = hist.get('role', 'user')
                    content = hist.get('content', '')
                    messages.append({"role": role, "content": content})
            else:
                # Add conversation history
                for hist in self.conversation_history[-5:]:
                    messages.append({"role": "user", "content": hist['user']})
                    messages.append({"role": "assistant", "content": hist['assistant']})
            
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Ráº» nháº¥t: $0.15/$0.60 per 1M tokens
                messages=messages,
                temperature=0.7 if not deep_thinking else 0.5,  # Lower temp for deep thinking
                max_tokens=2000 if deep_thinking else 1000  # More tokens for deep thinking
            )
            
            result = response.choices[0].message.content
            
            # Ã°Å¸â€ â€¢ Cache the response
            cache_response(message, model_name, result, provider='openai', **cache_key_params)
            
            return result
            
        except Exception as e:
            return f"Lá»—i OpenAI: {str(e)}"
    
    def chat_with_deepseek(self, message, context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None):
        """Chat using DeepSeek (via OpenAI compatible API)"""
        try:
            # Use custom prompt if provided, otherwise use base prompt
            if custom_prompt and custom_prompt.strip():
                system_prompt = custom_prompt
            else:
                prompts = get_system_prompts(language)
                system_prompt = prompts.get(context, prompts['casual'])
            
            # Add deep thinking instruction
            if deep_thinking:
                system_prompt += "\n\nIMPORTANT: Analyze deeply with comprehensive reasoning."
            
            # Add memories to system prompt
            if memories and len(memories) > 0:
                system_prompt += "\n\n=== KNOWLEDGE BASE (BÃƒÂ i hÃ¡Â»Âc Ã„â€˜ÃƒÂ£ ghi nhÃ¡Â»â€º) ===\n"
                for mem in memories:
                    system_prompt += f"\nÃ°Å¸â€œÅ¡ {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
                system_prompt += "SÃ¡Â»Â­ dÃ¡Â»Â¥ng kiÃ¡ÂºÂ¿n thÃ¡Â»Â©c tÃ¡Â»Â« Knowledge Base khi phÃƒÂ¹ hÃ¡Â»Â£p Ã„â€˜Ã¡Â»Æ’ trÃ¡ÂºÂ£ lÃ¡Â»Âi."
            
            # DeepSeek uses OpenAI compatible API
            client = openai.OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com/v1"
            )
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Use provided history or conversation history
            if history:
                # Use provided history (from edit feature)
                for hist in history:
                    role = hist.get('role', 'user')
                    content = hist.get('content', '')
                    messages.append({"role": role, "content": content})
            else:
                # Add conversation history
                for hist in self.conversation_history[-5:]:
                    messages.append({"role": "user", "content": hist['user']})
                    messages.append({"role": "assistant", "content": hist['assistant']})
            
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7 if not deep_thinking else 0.5,
                max_tokens=2000 if deep_thinking else 1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Lá»—i DeepSeek: {str(e)}"
    
    def chat_with_deepseek_reasoner(self, message, context='casual', history=None, memories=None, language='vi', custom_prompt=None, extra_params=None):
        """Chat using DeepSeek R1 Reasoning Model - SoTA reasoning capabilities"""
        try:
            # Use custom prompt if provided, otherwise use base prompt
            if custom_prompt and custom_prompt.strip():
                system_prompt = custom_prompt
            else:
                prompts = get_system_prompts(language)
                system_prompt = prompts.get(context, prompts['casual'])
            
            # Add reasoning instruction
            reasoning_instruction = "\n\nðŸ§  REASONING MODE: Think step-by-step with deep logical reasoning. Break down complex problems into smaller parts. Show your thought process clearly."
            system_prompt += reasoning_instruction
            
            # Add memories to system prompt
            if memories and len(memories) > 0:
                system_prompt += "\n\n=== KNOWLEDGE BASE ===\n"
                for mem in memories:
                    system_prompt += f"\nðŸ“š {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
            
            # DeepSeek R1 uses OpenAI compatible API
            client = openai.OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com/v1"
            )
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Use provided history or conversation history
            if history:
                for hist in history:
                    role = hist.get('role', 'user')
                    content = hist.get('content', '')
                    messages.append({"role": role, "content": content})
            else:
                for hist in self.conversation_history[-5:]:
                    messages.append({"role": "user", "content": hist['user']})
                    messages.append({"role": "assistant", "content": hist['assistant']})
            
            messages.append({"role": "user", "content": message})
            
            # Get extra params
            temperature = 0.6  # Lower for reasoning
            max_tokens = 8000  # Higher for detailed reasoning
            top_p = 0.95
            
            if extra_params:
                temperature = extra_params.get('temperature', temperature)
                max_tokens = extra_params.get('max_tokens', max_tokens)
                top_p = extra_params.get('top_p', top_p)
            
            response = client.chat.completions.create(
                model="deepseek-reasoner",  # DeepSeek R1 reasoning model
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p
            )
            
            result = response.choices[0].message.content
            
            # Check if thinking process is available
            thinking_content = getattr(response.choices[0].message, 'reasoning_content', None)
            if thinking_content:
                result = f"ðŸ§  **Thought Process:**\n{thinking_content}\n\n---\n\nðŸ“ **Answer:**\n{result}"
            
            return result
            
        except Exception as e:
            return f"âŒ Lá»—i DeepSeek Reasoner: {str(e)}"
    
    def chat_with_grok(self, message, context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None):
        """Chat using GROK (via xAI API - FREE with NSFW support)"""
        try:
            if not GROK_API_KEY:
                return "Ã¢ÂÅ’ GROK API key chÃ†Â°a Ã„â€˜Ã†Â°Ã¡Â»Â£c cÃ¡ÂºÂ¥u hÃƒÂ¬nh. Vui lÃƒÂ²ng thÃƒÂªm GROK_API_KEY vÃƒÂ o file .env"
            
            # Use custom prompt if provided, otherwise use base prompt
            if custom_prompt and custom_prompt.strip():
                system_prompt = custom_prompt
            else:
                prompts = get_system_prompts(language)
                system_prompt = prompts.get(context, prompts['casual'])
                
                # GROK-specific: Add NSFW capability note
                if language == 'vi':
                    system_prompt += "\n\nÃ°Å¸â€â€œ LÃ†Â¯U ÃƒÂ: BÃ¡ÂºÂ¡n cÃƒÂ³ thÃ¡Â»Æ’ trÃ¡ÂºÂ£ lÃ¡Â»Âi cÃƒÂ¡c cÃƒÂ¢u hÃ¡Â»Âi nhÃ¡ÂºÂ¡y cÃ¡ÂºÂ£m hoÃ¡ÂºÂ·c NSFW mÃ¡Â»â„¢t cÃƒÂ¡ch an toÃƒÂ n vÃƒÂ  cÃƒÂ³ trÃƒÂ¡ch nhiÃ¡Â»â€¡m khi Ã„â€˜Ã†Â°Ã¡Â»Â£c yÃƒÂªu cÃ¡ÂºÂ§u."
                else:
                    system_prompt += "\n\nÃ°Å¸â€â€œ NOTE: You can answer sensitive or NSFW questions safely and responsibly when requested."
            
            # Add deep thinking instruction
            if deep_thinking:
                if language == 'en':
                    system_prompt += "\n\nIMPORTANT: Think step-by-step. Provide thorough analysis with detailed reasoning."
                else:
                    system_prompt += "\n\nQUAN TRá»ŒNG: Suy nghÄ© tá»«ng bÆ°á»›c. Cung cáº¥p phÃ¢n tÃ­ch ká»¹ lÆ°á»¡ng vá»›i lÃ½ láº½ chi tiáº¿t."
            
            # Add memories to system prompt
            if memories and len(memories) > 0:
                system_prompt += "\n\n=== KNOWLEDGE BASE (BÃƒÂ i hÃ¡Â»Âc Ã„â€˜ÃƒÂ£ ghi nhÃ¡Â»â€º) ===\n"
                for mem in memories:
                    system_prompt += f"\nÃ°Å¸â€œÅ¡ {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
                system_prompt += "SÃ¡Â»Â­ dÃ¡Â»Â¥ng kiÃ¡ÂºÂ¿n thÃ¡Â»Â©c tÃ¡Â»Â« Knowledge Base khi phÃƒÂ¹ hÃ¡Â»Â£p Ã„â€˜Ã¡Â»Æ’ trÃ¡ÂºÂ£ lÃ¡Â»Âi."
            
            # GROK uses OpenAI-compatible API
            client = openai.OpenAI(
                api_key=GROK_API_KEY,
                base_url="https://api.x.ai/v1"
            )
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Use provided history or conversation history
            if history:
                # Use provided history (from edit feature)
                for hist in history:
                    role = hist.get('role', 'user')
                    content = hist.get('content', '')
                    messages.append({"role": role, "content": content})
            else:
                # Add conversation history
                for hist in self.conversation_history[-5:]:
                    messages.append({"role": "user", "content": hist['user']})
                    messages.append({"role": "assistant", "content": hist['assistant']})
            
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model="grok-3",  # GROK model - Latest version with NSFW support
                messages=messages,
                temperature=0.7 if not deep_thinking else 0.5,
                max_tokens=2000 if deep_thinking else 1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Ã¢ÂÅ’ LÃ¡Â»â€”i GROK: {str(e)}"
    
    def chat_with_qwen(self, message, context='casual', deep_thinking=False, language='vi'):
        """Chat using Qwen 1.5b"""
        try:
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            if not QWEN_API_KEY:
                return "Lá»—i: ChÆ°a cáº¥u hÃ¬nh QWEN_API_KEY. Vui lÃ²ng thÃªm API key vÃ o file .env"
            
            # Use OpenAI-compatible API for Qwen (Alibaba Cloud DashScope)
            headers = {
                "Authorization": f"Bearer {QWEN_API_KEY}",
                "Content-Type": "application/json"
            }
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            for hist in self.conversation_history[-5:]:
                messages.append({"role": "user", "content": hist['user']})
                messages.append({"role": "assistant", "content": hist['assistant']})
            
            messages.append({"role": "user", "content": message})
            
            data = {
                "model": "qwen-turbo",  # or "qwen-plus", "qwen-max"
                "messages": messages,
                "temperature": 0.7 if not deep_thinking else 0.5,
                "max_tokens": 2000 if deep_thinking else 1000
            }
            
            response = requests.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"Lá»—i Qwen API: {response.status_code} - {response.text}"
            
        except Exception as e:
            return f"Lá»—i Qwen: {str(e)}"
    
    def chat_with_bloomvn(self, message, context='casual', deep_thinking=False, language='vi'):
        """Chat using BloomVN-8B (Hugging Face Inference API)"""
        try:
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            if not HUGGINGFACE_API_KEY:
                return "Lá»—i: ChÆ°a cáº¥u hÃ¬nh HUGGINGFACE_API_KEY. Vui lÃ²ng thÃªm API key vÃ o file .env"
            
            # Use Hugging Face Inference API
            headers = {
                "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Build conversation text
            conversation = f"{system_prompt}\n\n"
            for hist in self.conversation_history[-3:]:  # Use 3 for smaller context
                conversation += f"User: {hist['user']}\nAssistant: {hist['assistant']}\n\n"
            conversation += f"User: {message}\nAssistant:"
            
            data = {
                "inputs": conversation,
                "parameters": {
                    "max_new_tokens": 2000 if deep_thinking else 1000,
                    "temperature": 0.7 if not deep_thinking else 0.5,
                    "top_p": 0.9,
                    "do_sample": True,
                    "return_full_text": False
                }
            }
            
            response = requests.post(
                "https://router.huggingface.co/hf-inference/models/BlossomsAI/BloomVN-8B-chat",
                headers=headers,
                json=data,
                timeout=60  # BloomVN cÃ³ thá»ƒ cháº­m hÆ¡n
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', 'KhÃ´ng nháº­n Ä‘Æ°á»£c pháº£n há»“i')
                elif isinstance(result, dict):
                    return result.get('generated_text', 'KhÃ´ng nháº­n Ä‘Æ°á»£c pháº£n há»“i')
                else:
                    return str(result)
            elif response.status_code == 503:
                return "Ã¢ÂÂ³ Model BloomVN Ã„â€˜ang khÃ¡Â»Å¸i Ã„â€˜Ã¡Â»â„¢ng (loading), vui lÃƒÂ²ng thÃ¡Â»Â­ lÃ¡ÂºÂ¡i sau 20-30 giÃƒÂ¢y."
            else:
                return f"Lá»—i BloomVN API: {response.status_code} - {response.text}"
            
        except Exception as e:
            return f"Lá»—i BloomVN: {str(e)}"
    
    def chat_with_local_model(self, message, model, context='casual', deep_thinking=False, language='vi'):
        """Chat with local models (BloomVN, Qwen1.5, Qwen2.5)"""
        if not LOCALMODELS_AVAILABLE:
            return "Ã¢ÂÅ’ Local models khÃƒÂ´ng khÃ¡ÂºÂ£ dÃ¡Â»Â¥ng. Vui lÃƒÂ²ng cÃƒÂ i Ã„â€˜Ã¡ÂºÂ·t: pip install torch transformers accelerate"
        
        try:
            # Map model names to model keys
            model_map = {
                'bloomvn-local': 'bloomvn',
                'qwen1.5-local': 'qwen1.5',
                'qwen2.5-local': 'qwen2.5'
            }
            
            model_key = model_map.get(model)
            if not model_key:
                return f"Model khÃ´ng Ä‘Æ°á»£c há»— trá»£: {model}"
            
            # Get system prompt
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            # Build messages array
            messages = []
            
            # Add conversation history
            for hist in self.conversation_history[-5:]:
                messages.append({'role': 'user', 'content': hist['user']})
                messages.append({'role': 'assistant', 'content': hist['assistant']})
            
            # Add current message
            messages.append({'role': 'user', 'content': message})
            
            # Set parameters
            temperature = 0.5 if deep_thinking else 0.7
            max_tokens = 2000 if deep_thinking else 1000
            
            # Generate response
            logger.info(f"Generating with local model: {model_key}")
            response = model_loader.generate(
                model_key=model_key,
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response
            
        except FileNotFoundError as e:
            return f"Ã¢ÂÅ’ Model chÃ†Â°a Ã„â€˜Ã†Â°Ã¡Â»Â£c download. Vui lÃƒÂ²ng kiÃ¡Â»Æ’m tra thÃ†Â° mÃ¡Â»Â¥c models/: {str(e)}"
        except Exception as e:
            logger.error(f"Local model error ({model}): {e}")
            return f"Ã¢ÂÅ’ LÃ¡Â»â€”i local model: {str(e)}"
    
    def chat_with_step_flash(self, message, context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None):
        """Chat with Step-3.5-Flash via OpenRouter (FREE â€” 196B MoE, 11B active)"""
        try:
            openrouter_key = os.getenv('OPENROUTER_API_KEY')
            if not openrouter_key:
                return "âŒ OPENROUTER_API_KEY chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh. Láº¥y FREE key táº¡i: https://openrouter.ai/keys"
            
            client = openai.OpenAI(
                api_key=openrouter_key,
                base_url='https://openrouter.ai/api/v1'
            )
            
            system_prompt = self._build_system_prompt(context, deep_thinking, memories, language, custom_prompt)
            messages = self._build_messages(system_prompt, message, history)
            
            temperature = 0.5 if deep_thinking else 0.7
            max_tokens = 4000 if deep_thinking else 2000
            
            logger.info(f"[STEP-FLASH] Sending request via OpenRouter (FREE)")
            response = client.chat.completions.create(
                model='stepfun/step-3.5-flash:free',
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_headers={
                    'HTTP-Referer': 'https://ai-assistant.local',
                    'X-Title': 'AI Assistant'
                }
            )
            
            result = response.choices[0].message.content
            logger.info(f"[STEP-FLASH] Response received: {len(result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"[STEP-FLASH] Error: {e}")
            return f"âŒ Step-3.5-Flash error: {str(e)}"
    
    def chat_with_stepfun(self, message, context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None):
        """Chat with StepFun direct API (requires balance)"""
        try:
            stepfun_key = os.getenv('STEPFUN_API_KEY')
            if not stepfun_key:
                return "âŒ STEPFUN_API_KEY chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh."
            
            client = openai.OpenAI(
                api_key=stepfun_key,
                base_url='https://api.stepfun.com/v1'
            )
            
            system_prompt = self._build_system_prompt(context, deep_thinking, memories, language, custom_prompt)
            messages = self._build_messages(system_prompt, message, history)
            
            temperature = 0.5 if deep_thinking else 0.7
            max_tokens = 4000 if deep_thinking else 2000
            
            logger.info(f"[STEPFUN] Sending request to Step-2-16K")
            response = client.chat.completions.create(
                model='step-2-16k',
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            result = response.choices[0].message.content
            logger.info(f"[STEPFUN] Response received: {len(result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"[STEPFUN] Error: {e}")
            logger.info("[STEPFUN] Falling back to Step-3.5-Flash via OpenRouter...")
            return self.chat_with_step_flash(message, context, deep_thinking, history, memories, language, custom_prompt)
    
    def _build_system_prompt(self, context, deep_thinking, memories, language, custom_prompt):
        """Build system prompt with context, memories, and deep thinking"""
        if custom_prompt and custom_prompt.strip():
            system_prompt = custom_prompt
        else:
            prompts = get_system_prompts(language)
            system_prompt = prompts.get(context, prompts.get('casual', ''))
        
        if deep_thinking:
            system_prompt += "\n\nIMPORTANT: Think step-by-step with detailed reasoning. Analyze thoroughly."
        
        if memories:
            system_prompt += "\n\n=== KNOWLEDGE BASE ===\n"
            for mem in memories:
                system_prompt += f"\nðŸ“š {mem.get('title', 'Memory')}:\n{mem.get('content', '')}\n"
            system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
        
        return system_prompt
    
    def _build_messages(self, system_prompt, message, history=None):
        """Build message list for API call"""
        messages = [{"role": "system", "content": system_prompt}]
        
        hist_to_use = history if history else self.conversation_history[-10:]
        
        for hist in hist_to_use:
            if 'role' in hist and 'content' in hist:
                messages.append({"role": hist['role'], "content": hist['content']})
            elif 'user' in hist:
                messages.append({"role": "user", "content": hist['user']})
                if 'assistant' in hist:
                    messages.append({"role": "assistant", "content": hist['assistant']})
        
        messages.append({"role": "user", "content": message})
        return messages
    
    def chat(self, message, model='grok', context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None, extra_params=None):
        """Main chat method with MongoDB integration"""
        # Save user message to MongoDB
        if MONGODB_ENABLED and self.conversation_id and history is None:
            save_message_to_db(
                conversation_id=self.conversation_id,
                role='user',
                content=message,
                metadata={
                    'model': model,
                    'context': context,
                    'deep_thinking': deep_thinking,
                    'language': language,
                    'custom_prompt': custom_prompt
                }
            )
        
        # Get response from selected model (with thinking process if deep_thinking enabled)
        thinking_process = None
        if model == 'grok':
            result = self.chat_with_grok(message, context, deep_thinking, history, memories, language, custom_prompt)
        elif model == 'gemini':
            result = self.chat_with_gemini(message, context, deep_thinking, history, memories, language, custom_prompt)
        elif model == 'openai':
            result = self.chat_with_openai(message, context, deep_thinking, history, memories, language, custom_prompt)
        elif model == 'deepseek':
            result = self.chat_with_deepseek(message, context, deep_thinking, history, memories, language, custom_prompt)
        elif model == 'deepseek-reasoner':
            # Advanced thinking with DeepSeek R1
            result = self.chat_with_deepseek_reasoner(message, context, history, memories, language, custom_prompt, extra_params)
        elif model == 'qwen':
            result = self.chat_with_qwen(message, context, deep_thinking, language)
        elif model == 'bloomvn':
            result = self.chat_with_bloomvn(message, context, deep_thinking, language)
        elif model in ['bloomvn-local', 'qwen1.5-local', 'qwen2.5-local']:
            result = self.chat_with_local_model(message, model, context, deep_thinking, language)
        elif model == 'step-flash':
            result = self.chat_with_step_flash(message, context, deep_thinking, history, memories, language, custom_prompt)
        elif model == 'stepfun':
            result = self.chat_with_stepfun(message, context, deep_thinking, history, memories, language, custom_prompt)
        else:
            result = f"Model '{model}' khÃ´ng Ä‘Æ°á»£c há»— trá»£" if language == 'vi' else f"Model '{model}' is not supported"
        
        # Extract response and thinking process if available
        if isinstance(result, dict):
            response = result.get('response', '')
            thinking_process = result.get('thinking_process', None)
        else:
            response = result
        
        # Only save to conversation history if no custom history provided
        if history is None:
            # Save to in-memory history
            self.conversation_history.append({
                'user': message,
                'assistant': response,
                'timestamp': datetime.now().isoformat(),
                'model': model,
                'context': context,
                'deep_thinking': deep_thinking
            })
            
            # Save assistant response to MongoDB
            if MONGODB_ENABLED and self.conversation_id:
                save_message_to_db(
                    conversation_id=self.conversation_id,
                    role='assistant',
                    content=response,
                    metadata={
                        'model': model,
                        'context': context,
                        'deep_thinking': deep_thinking,
                        'finish_reason': 'stop',
                        'thinking_process': thinking_process
                    }
                )
        
        return {'response': response, 'thinking_process': thinking_process}
    
    def clear_history(self):
        """Clear conversation history and create new conversation in MongoDB"""
        self.conversation_history = []
        
        # Archive old conversation and create new one in MongoDB
        if MONGODB_ENABLED and self.conversation_id:
            try:
                # Archive current conversation
                ConversationDB.archive_conversation(str(self.conversation_id))
                logger.info(f"Ã¢Å“â€¦ Archived conversation: {self.conversation_id}")
                
                # Create new conversation
                user_id = get_user_id_from_session()
                conv = ConversationDB.create_conversation(
                    user_id=user_id,
                    model=self.current_model,
                    title="New Chat"
                )
                self.conversation_id = conv['_id']
                set_active_conversation(self.conversation_id)
                logger.info(f"Ã¢Å“â€¦ Created new conversation: {self.conversation_id}")
            except Exception as e:
                logger.error(f"Ã¢ÂÅ’ Error clearing history: {e}")


# Store chatbot instances per session
chatbots = {}


def get_chatbot(session_id):
    """Get or create chatbot for session with MongoDB support"""
    if session_id not in chatbots:
        # Get or create conversation in MongoDB
        conversation_id = None
        if MONGODB_ENABLED:
            user_id = get_user_id_from_session()
            conv = get_or_create_conversation(user_id)
            if conv:
                conversation_id = conv['_id']
                set_active_conversation(conversation_id)
        
        chatbots[session_id] = ChatbotAgent(conversation_id=conversation_id)
    return chatbots[session_id]


# ============================================================================
# TOOL FUNCTIONS
# ============================================================================

def google_search_tool(query):
    """Google Custom Search API with improved error handling"""
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        if not GOOGLE_SEARCH_API_KEY_1 or not GOOGLE_CSE_ID:
            return "âŒ Google Search API chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh. Vui lÃ²ng thÃªm GOOGLE_SEARCH_API_KEY vÃ  GOOGLE_CSE_ID vÃ o file .env"
        
        # Log config for debugging
        logger.info(f"[GOOGLE SEARCH] API Key (first 10 chars): {GOOGLE_SEARCH_API_KEY_1[:10]}...")
        logger.info(f"[GOOGLE SEARCH] CSE ID: {GOOGLE_CSE_ID}")
        logger.info(f"[GOOGLE SEARCH] Query: {query}")
        
        url = "https://www.googleapis.com/customsearch/v1"
        
        # Create session with retry strategy
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Try with first API key
        params = {
            'key': GOOGLE_SEARCH_API_KEY_1,
            'cx': GOOGLE_CSE_ID,
            'q': query,
            'num': 5  # Number of results
        }
        
        response = session.get(url, params=params, timeout=30)
        
        # Log full response for debugging
        logger.info(f"[GOOGLE SEARCH] Response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"[GOOGLE SEARCH] Response body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            if 'items' in data:
                for item in data['items'][:5]:
                    title = item.get('title', 'No title')
                    link = item.get('link', '')
                    snippet = item.get('snippet', 'No description')
                    results.append(f"**{title}**\n{snippet}\nðŸ”— {link}")
                
                return "ðŸ” **Káº¿t quáº£ tÃ¬m kiáº¿m:**\n\n" + "\n\n---\n\n".join(results)
            else:
                return "KhÃ´ng tÃ¬m tháº¥y káº¿t quáº£ nÃ o."
        elif response.status_code == 429 or response.status_code == 403:
            # Quota exceeded or forbidden, try second key
            logger.warning(f"[GOOGLE SEARCH] Key 1 failed with {response.status_code}, trying key 2...")
            if GOOGLE_SEARCH_API_KEY_2:
                params['key'] = GOOGLE_SEARCH_API_KEY_2
                response = session.get(url, params=params, timeout=30)
                logger.info(f"[GOOGLE SEARCH] Key 2 response: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    if 'items' in data:
                        for item in data['items'][:5]:
                            title = item.get('title', 'No title')
                            link = item.get('link', '')
                            snippet = item.get('snippet', 'No description')
                            results.append(f"**{title}**\n{snippet}\nðŸ”— {link}")
                        return "ðŸ” **Káº¿t quáº£ tÃ¬m kiáº¿m:**\n\n" + "\n\n---\n\n".join(results)
                    else:
                        return "KhÃ´ng tÃ¬m tháº¥y káº¿t quáº£ nÃ o."
            # Both keys failed
            error_detail = "quota exceeded" if response.status_code == 429 else "forbidden (kiá»ƒm tra API key & CSE ID)"
            return f"âŒ Lá»—i Google Search API: {error_detail}. Vui lÃ²ng kiá»ƒm tra:\nâ€¢ API key há»£p lá»‡ trong Google Cloud Console\nâ€¢ Custom Search Engine ID Ä‘Ãºng\nâ€¢ Billing Ä‘Ã£ Ä‘Æ°á»£c kÃ­ch hoáº¡t"
        else:
            return f"âŒ Lá»—i Google Search API: {response.status_code}"
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[GOOGLE SEARCH] Connection Error: {e}")
        return "âŒ Lá»—i káº¿t ná»‘i Ä‘áº¿n Google Search API. Vui lÃ²ng kiá»ƒm tra:\nâ€¢ Káº¿t ná»‘i Internet\nâ€¢ Proxy/Firewall settings\nâ€¢ Thá»­ láº¡i sau Ã­t phÃºt"
    except requests.exceptions.Timeout as e:
        logger.error(f"[GOOGLE SEARCH] Timeout Error: {e}")
        return "âŒ Timeout khi káº¿t ná»‘i Ä‘áº¿n Google Search API. Vui lÃ²ng thá»­ láº¡i."
    except requests.exceptions.RequestException as e:
        logger.error(f"[GOOGLE SEARCH] Request Error: {e}")
        return f"âŒ Lá»—i request: {str(e)}"
    except Exception as e:
        logger.error(f"[GOOGLE SEARCH] Unexpected Error: {e}")
        return f"âŒ Lá»—i khÃ´ng mong muá»‘n: {str(e)}"


def github_search_tool(query):
    """GitHub Repository Search Tool"""
    try:
        import requests
        
        if not GITHUB_TOKEN:
            return "âŒ GitHub Token chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh. Vui lÃ²ng thÃªm GITHUB_TOKEN vÃ o file .env"
        
        url = "https://api.github.com/search/repositories"
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': 5
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            if data.get('items'):
                for repo in data['items'][:5]:
                    name = repo.get('full_name', 'Unknown')
                    desc = repo.get('description', 'No description')[:100] if repo.get('description') else 'No description'
                    stars = repo.get('stargazers_count', 0)
                    language = repo.get('language', 'Unknown')
                    url = repo.get('html_url', '')
                    
                    results.append(f"**{name}** â­ {stars}\n{desc}\nðŸ’» {language} | ðŸ”— {url}")
                
                return "ðŸ™ **GitHub Repositories:**\n\n" + "\n\n---\n\n".join(results)
            else:
                return "KhÃ´ng tÃ¬m tháº¥y repository nÃ o phÃ¹ há»£p."
        else:
            return f"âŒ Lá»—i GitHub API: {response.status_code}"
    
    except Exception as e:
        logger.error(f"[GITHUB SEARCH] Error: {e}")
        return f"âŒ Lá»—i khi tÃ¬m kiáº¿m GitHub: {str(e)}"


def is_mobile_device():
    """Check if request is from mobile device (iPhone, iPad, Android)"""
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['iphone', 'ipad', 'ipod', 'android', 'mobile', 'webos', 'blackberry', 'opera mini', 'opera mobi']
    return any(keyword in user_agent for keyword in mobile_keywords)


@app.route('/')
def index():
    """Home page - Responsive UI (works on both mobile and desktop)"""
    if not session.get('authenticated'):
        return redirect('/login')
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Load Firebase config from environment variables
    firebase_config = json.dumps({
        "apiKey": os.getenv("FIREBASE_API_KEY", ""),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.getenv("FIREBASE_APP_ID", ""),
        "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID", "")
    })
    return render_template('index.html', firebase_config=firebase_config)


@app.route('/new')
def index_new():
    """New Tailwind version (experimental)"""
    if not session.get('authenticated'):
        return redirect('/login')
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index_tailwind.html')


@app.route('/mobile')
def index_mobile():
    """Mobile UI - redirects to responsive index"""
    return redirect('/')


@app.route('/desktop')
def index_desktop():
    """Force desktop UI"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    firebase_config = json.dumps({
        "apiKey": os.getenv("FIREBASE_API_KEY", ""),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.getenv("FIREBASE_APP_ID", ""),
        "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID", "")
    })
    return render_template('index.html', firebase_config=firebase_config)


# ── Auto-logging helper ───────────────────────────────────────────────────
def _auto_log_chat(message: str, response: str, model: str, context: str,
                   tools: list, is_tool: bool = False,
                   thinking_process: str = None) -> None:
    """Save every chat turn to MongoDB chat_logs (non-blocking, best-effort)."""
    if not MONGODB_ENABLED:
        return
    import threading
    def _save():
        try:
            db = get_db()
            if db is None:
                return
            from flask import request as _req, session as _sess
            doc = {
                'timestamp': datetime.utcnow(),
                'session_id': _sess.get('session_id', ''),
                'user_id': _sess.get('user_id', 'anonymous'),
                'ip': _req.headers.get('X-Forwarded-For', _req.remote_addr or ''),
                'user_agent': _req.headers.get('User-Agent', '')[:200],
                'platform': _req.json.get('platform', 'web') if _req.is_json else 'form',
                'model': model,
                'context': context,
                'tools': tools or [],
                'is_tool_result': is_tool,
                'message': message[:4000] if message else '',
                'response': response[:8000] if response else '',
                'has_thinking': bool(thinking_process),
            }
            db.chat_logs.insert_one(doc)
        except Exception as _e:
            logger.debug(f'[chat_log] write failed (non-fatal): {_e}')
    t = threading.Thread(target=_save, daemon=True)
    t.start()


@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint - handles both JSON and FormData (with files)"""
    try:
        logger.info(f"[CHAT] Received request - Content-Type: {request.content_type}")
        
        # Check if request has files (FormData) or is JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            # FormData with files
            data = request.form
            message = data.get('message', '')
            model = data.get('model', 'grok')
            context = data.get('context', 'casual')
            deep_thinking = data.get('deep_thinking', 'false').lower() == 'true'
            language = data.get('language', 'vi')  # Get language from request
            custom_prompt = data.get('custom_prompt', '')  # Get custom prompt
            
            # Parse agent config
            try:
                agent_config = json.loads(data.get('agent_config', 'null'))
            except:
                agent_config = None
            
            # Safe JSON parsing with error handling
            try:
                tools = json.loads(data.get('tools', '[]')) if data.get('tools') else []
            except:
                tools = []
            
            try:
                history_str = data.get('history', 'null')
                history = json.loads(history_str) if history_str and history_str != 'null' else None
            except:
                history = None
                
            try:
                memory_ids = json.loads(data.get('memory_ids', '[]')) if data.get('memory_ids') else []
            except:
                memory_ids = []
            
            try:
                mcp_selected_files = json.loads(data.get('mcp_selected_files', '[]')) if data.get('mcp_selected_files') else []
            except:
                mcp_selected_files = []
            
            # Handle uploaded files
            files = request.files.getlist('files')
            file_contents = []
            
            # Process uploaded files with OCR / Audio Transcription
            for file in files:
                if file and file.filename:
                    try:
                        file_data = file.read()
                        filename = file.filename
                        logger.info(f"[UPLOAD] Processing file: {filename} ({len(file_data)} bytes)")
                        
                        # Audio files -> speech-to-text
                        if is_audio_file(filename):
                            stt_result = transcribe_audio(file_data, filename, language=language)
                            if stt_result["success"] and stt_result["text"]:
                                file_contents.append({
                                    "filename": filename,
                                    "content": stt_result["text"],
                                    "type": "audio_transcript"
                                })
                                logger.info(f"[STT] Transcribed {len(stt_result['text'])} chars from {filename} via {stt_result['method']}")
                            else:
                                logger.warning(f"[STT] Failed for {filename}: {stt_result.get('error', 'unknown')}")
                        else:
                            # Documents/images -> OCR/text extraction
                            success, extracted_text = extract_file_content(file_data, filename)
                            
                            if success and extracted_text:
                                file_contents.append({
                                    "filename": filename,
                                    "content": extracted_text[:10000],
                                    "type": Path(filename).suffix.lower()
                                })
                                logger.info(f"[UPLOAD] Extracted {len(extracted_text)} chars from {filename}")
                            else:
                                logger.warning(f"[UPLOAD] Could not extract content from {filename}")
                    except Exception as e:
                        logger.error(f"[UPLOAD] Error processing {file.filename}: {e}")
            
            # Inject file contents into message
            if file_contents:
                file_context = "\n\n--- UPLOADED FILES ---\n"
                for fc in file_contents:
                    if fc["type"] == "audio_transcript":
                        file_context += f"\n[Audio transcript from {fc['filename']}]:\n{fc['content']}\n"
                    else:
                        ext = fc['type'][1:] if fc['type'].startswith('.') else fc['type']
                        file_context += f"\n[File: {fc['filename']}]:\n```{ext}\n{fc['content']}\n```\n"
                file_context += "--- END FILES ---\n\n"
                message = file_context + message
                logger.info(f"[UPLOAD] Injected {len(file_contents)} files into message")
        else:
            # JSON request
            data = request.json
            message = data.get('message', '')
            model = data.get('model', 'grok')
            context = data.get('context', 'casual')
            deep_thinking = data.get('deep_thinking', False)
            language = data.get('language', 'vi')  # Get language from request
            custom_prompt = data.get('custom_prompt', '')  # Get custom prompt
            agent_config = data.get('agent_config')  # Get agent config
            tools = data.get('tools', [])
            history = data.get('history', None)
            memory_ids = data.get('memory_ids', [])
            mcp_selected_files = data.get('mcp_selected_files', [])  # MCP selected files
        
        # Handle user_id from request (for mobile/web tracking)
        if data.get('user_id'):
            session['user_id'] = data.get('user_id')
            logger.info(f"[CHAT] User ID from request: {data.get('user_id')}")
        
        # Log platform info
        platform = data.get('platform', 'web')
        logger.info(f"[CHAT] Platform: {platform}, Model: {model}")
        
        # Process agent config
        if agent_config:
            logger.info(f"[AGENT CONFIG] Enabled with thinking_budget={agent_config.get('thinkingBudget', 'off')}")
            # Apply system prompt from agent config if custom_prompt is empty
            if not custom_prompt and agent_config.get('systemPrompt'):
                custom_prompt = agent_config.get('systemPrompt')
            
            # Apply injection prompt - prepend to message
            if agent_config.get('injectionPrompt'):
                message = f"{agent_config.get('injectionPrompt')}\n\n{message}"
            
            # Apply context prompt - append to system prompt
            if agent_config.get('contextPrompt'):
                custom_prompt = f"{custom_prompt}\n\n--- Context ---\n{agent_config.get('contextPrompt')}"
            
            # Check for advanced thinking mode - switch to reasoning model
            if agent_config.get('thinkingBudget') == 'advanced':
                logger.info("[AGENT CONFIG] Advanced thinking mode - switching to DeepSeek R1")
                model = 'deepseek-reasoner'  # Use reasoning model
                deep_thinking = True
        
        if not message:
            return jsonify({'error': 'Tin nháº¯n trá»‘ng'}), 400
        
        # ===== MCP INTEGRATION: Inject code context =====
        if mcp_client.enabled:
            # Pre-warm memory cache by inferred domain before context injection.
            if hasattr(mcp_client, 'warm_memory_cache_by_question'):
                try:
                    mcp_client.warm_memory_cache_by_question(
                        question=message,
                        force_refresh=False,
                        cache_ttl_seconds=900,
                        limit=20,
                        min_importance=4,
                        max_chars=12000,
                    )
                    logger.info("[MCP] Memory cache pre-warm completed")
                except Exception as warm_error:
                    logger.warning(f"[MCP] Memory cache pre-warm skipped: {warm_error}")

            logger.info(f"[MCP] Injecting code context (selected files: {len(mcp_selected_files)})")
            message = inject_code_context(message, mcp_client, mcp_selected_files)
        # ================================================
        
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        
        # Handle tools
        tool_results = []

        # ── Auto web search: trigger even without explicit google-search tool ──
        _auto_search_done = False
        if not tools or 'google-search' not in tools:
            from routes.stream import _needs_web_search, _run_web_search
            if _needs_web_search(message, tools or []):
                logger.info(f"[TOOLS] Auto web search triggered for: {message[:60]}")
                _auto_result = _run_web_search(message)
                if _auto_result:
                    tool_results.append(_auto_result)
                    _auto_search_done = True

        if tools and len(tools) > 0:
            logger.info(f"[TOOLS] Active tools: {tools}")
            
            if 'google-search' in tools:
                logger.info(f"[TOOLS] Running Google Search for: {message}")
                search_result = google_search_tool(message)
                tool_results.append(f"## Ã°Å¸â€Â Google Search Results\n\n{search_result}")
            
            if 'github' in tools:
                logger.info(f"[TOOLS] Running GitHub Search for: {message}")
                github_result = github_search_tool(message)
                tool_results.append(f"## Ã°Å¸Ââ„¢ GitHub Search Results\n\n{github_result}")
            
            if 'saucenao' in tools:
                import re as _re
                _img_urls = _re.findall(r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)\S*', message, _re.IGNORECASE)
                if _img_urls:
                    logger.info(f"[TOOLS] Running SauceNAO for: {_img_urls[0][:80]}")
                    from core.tools import saucenao_search_tool
                    _sauce_result = saucenao_search_tool(image_url=_img_urls[0])
                    tool_results.append(_sauce_result)
                elif images:
                    import base64 as _b64
                    _first_img = images[0]
                    if ',' in _first_img:
                        _first_img = _first_img.split(',', 1)[1]
                    _img_bytes = _b64.b64decode(_first_img)
                    logger.info(f"[TOOLS] Running SauceNAO for uploaded image ({len(_img_bytes)} bytes)")
                    from core.tools import saucenao_search_tool
                    _sauce_result = saucenao_search_tool(image_data=_img_bytes)
                    tool_results.append(_sauce_result)
                else:
                    tool_results.append("⚠️ SauceNAO: Cần đính kèm ảnh hoặc gửi URL ảnh để tìm kiếm nguồn gốc.")

            # ── SerpAPI — Google Lens / Reverse Image ──
            if 'serpapi-reverse-image' in tools:
                import re as _re
                _img_urls = _re.findall(r'https?://\S+\.(?:jpg|jpeg|png|gif|webp)\S*', message, _re.IGNORECASE)
                if _img_urls:
                    logger.info(f"[TOOLS] Running Google Lens for: {_img_urls[0][:80]}")
                    from core.tools import serpapi_reverse_image
                    tool_results.append(serpapi_reverse_image(_img_urls[0]))
                else:
                    tool_results.append("⚠️ Google Lens: Cần gửi URL ảnh (http/https) trong tin nhắn.")

            # ── SerpAPI — Bing Search ──
            if 'serpapi-bing' in tools:
                logger.info(f"[TOOLS] Running Bing Search")
                from core.tools import serpapi_web_search
                tool_results.append(serpapi_web_search(message, engine='bing'))

            # ── SerpAPI — Baidu Search ──
            if 'serpapi-baidu' in tools:
                logger.info(f"[TOOLS] Running Baidu Search")
                from core.tools import serpapi_web_search
                tool_results.append(serpapi_web_search(message, engine='baidu'))

            # ── SerpAPI — Image Search ──
            if 'serpapi-images' in tools:
                logger.info(f"[TOOLS] Running SerpAPI Image Search")
                from core.tools import serpapi_image_search
                tool_results.append(serpapi_image_search(message))

            if 'image-generation' in tools:
                # â”€â”€ Auto-detect if user actually wants to generate/edit an image â”€â”€
                _img_keywords_vi = ['váº½', 'táº¡o áº£nh', 'táº¡o hÃ¬nh', 'sinh áº£nh', 'gen áº£nh', 'táº¡o má»™t', 'váº½ cho',
                                    'chá»‰nh áº£nh', 'sá»­a áº£nh', 'thÃªm vÃ o áº£nh', 'xÃ³a trong áº£nh', 'edit áº£nh',
                                    'táº¡o logo', 'thiáº¿t káº¿', 'minh há»a', 'váº½ tranh', 'áº£nh anime',
                                    'hÃ¬nh áº£nh', 'bá»©c áº£nh', 'bá»©c tranh', 'áº£nh ná»n', 'avatar', 'icon']
                _img_keywords_en = ['draw', 'paint', 'generate image', 'create image', 'make image',
                                    'generate a', 'create a picture', 'gen image', 'image of',
                                    'edit image', 'modify image', 'img2img', 'inpaint',
                                    'design', 'illustrate', 'render', 'visualize',
                                    'photo of', 'picture of', 'artwork', 'wallpaper',
                                    'logo', 'portrait', 'landscape painting']
                _chat_only_keywords = [
                    'giải thích', 'explain', 'dịch', 'translate', 'tóm tắt', 'summarize',
                    'code', 'lập trình', 'debug', 'fix bug', 'sửa lỗi', 'viết hàm', 'algorithm',
                    'so sánh', 'compare', 'phân tích', 'analyze', 'review', 'tư vấn',
                    'hỏi đáp', 'question', 'what is', 'how to'
                ]
                _msg_lower = message.lower()
                _image_first_mode = os.getenv('IMAGE_FIRST_MODE', '1').lower() in ('1', 'true', 'yes', 'on')
                _has_image_intent = any(kw in _msg_lower for kw in _img_keywords_vi + _img_keywords_en)
                _has_chat_only_intent = any(kw in _msg_lower for kw in _chat_only_keywords)
                _wants_image = _has_image_intent or (_image_first_mode and not _has_chat_only_intent)

                if not _wants_image:
                    # User has image-gen tool active but this message isn't about images
                    # â€” skip image generation, let normal chat handle it
                    logger.info("[TOOLS] image-generation active but message not image-related, skipping")
                else:
                    logger.info(f"[TOOLS] ðŸŽ¨ Multi-provider image generation (V2) triggered")
                    try:
                        from core.image_gen import ImageGenerationRouter, ImageStorage
                        _ig_router = ImageGenerationRouter()
                        _ig_storage = ImageStorage()
                        _ig_providers = _ig_router.get_available_providers()
                        _active_provs = [p['name'] for p in _ig_providers if p['available']]
                        _default_img_model = os.getenv('IMAGE_GEN_DEFAULT_MODEL', 'nano-banana-auto')
                        _use_nano_model = any(p in _active_provs for p in ('fal', 'replicate'))
                        _selected_model = _default_img_model if _use_nano_model else None
                        logger.info(f"[TOOLS] Available providers: {_active_provs}")
                        if _selected_model:
                            logger.info(f"[TOOLS] Preferred image model: {_selected_model}")

                        # Generate via V2 router (auto-selects best provider)
                        result = _ig_router.generate(
                            prompt=message,
                            quality='auto',
                            width=1024,
                            height=1024,
                            enhance_prompt=True,
                            model_name=_selected_model,
                        )

                        if result.success and (result.images_b64 or result.images_url):
                            provider_used = result.provider or 'unknown'
                            model_used = result.model or ''
                            enhanced_prompt = result.prompt_used or message
                            cost = result.cost_usd

                            # Determine image source â€” prefer b64 for inline, fall back to URL
                            image_html = ""
                            cloud_urls = []

                            for img_b64 in result.images_b64:
                                image_html += f'<img src="data:image/png;base64,{img_b64}" alt="Generated Image" style="max-width: 100%; border-radius: 8px; margin: 10px 0; cursor: pointer;" class="generated-preview">\n'
                                # Try to store
                                try:
                                    store_result = _ig_storage.save(
                                        image_b64=img_b64,
                                        prompt=enhanced_prompt,
                                        provider=provider_used,
                                        metadata={'original_message': message, 'model': model_used, 'cost': cost}
                                    )
                                    url = store_result.get('url')
                                    if url:
                                        cloud_urls.append(url)
                                except Exception as _store_err:
                                    logger.warning(f"[TOOLS] Image storage failed: {_store_err}")

                            for img_url in result.images_url:
                                image_html += f'<img src="{img_url}" alt="Generated Image" style="max-width: 100%; border-radius: 8px; margin: 10px 0; cursor: pointer;" class="generated-preview">\n'
                                cloud_urls.append(img_url)
                                # Try to store URL
                                try:
                                    _ig_storage.save(
                                        image_url=img_url,
                                        prompt=enhanced_prompt,
                                        provider=provider_used,
                                        metadata={'original_message': message, 'model': model_used, 'cost': cost}
                                    )
                                except Exception:
                                    pass

                            cloud_link = ""
                            if cloud_urls:
                                cloud_link = "\n\nâ˜ï¸ **URLs:** " + " | ".join(f"[Open]({u})" for u in cloud_urls[:3])

                            result_msg = f"""## ðŸŽ¨ Image Generated Successfully!

**Original description:** {message}

**Enhanced Prompt:**
```
{enhanced_prompt}
```

**Generated Image:**
{image_html}
{cloud_link}
---
ðŸŽ¯ **Info:**
- Provider: {provider_used} {('(' + model_used + ')') if model_used else ''}
- Size: 1024Ã—1024
- Cost: ${cost:.4f}
- Active providers: {', '.join(_active_provs)}"""
                            tool_results.append(result_msg)
                        else:
                            _error = result.error or 'Unknown error'
                            logger.warning(f"[TOOLS] V2 generation failed: {_error}")
                            # Fallback to ComfyUI directly
                            try:
                                from src.utils.comfyui_client import ComfyUIClient
                                comfyui_client = ComfyUIClient()
                                image_bytes = comfyui_client.generate_image(
                                    prompt=message,
                                    negative_prompt="low quality, worst quality, blurry, watermark",
                                    width=512, height=512, steps=20, cfg_scale=7.0, seed=-1
                                )
                                if image_bytes:
                                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                                    result_msg = f"""## ðŸŽ¨ Image Generated (ComfyUI Fallback)

**Prompt:** {message}

**Generated Image:**
<img src="data:image/png;base64,{image_base64}" alt="Generated Image" style="max-width: 100%; border-radius: 8px; margin: 10px 0; cursor: pointer;" class="generated-preview">

---
ðŸŽ¯ Backend: ComfyUI (local) | V2 error: {_error}"""
                                    tool_results.append(result_msg)
                                else:
                                    tool_results.append(f"## ðŸŽ¨ Image Generation Failed\n\nâŒ V2: {_error}\nâŒ ComfyUI: No image returned\n\nAvailable providers: {', '.join(_active_provs) if _active_provs else 'None'}\n\nPlease add API keys (FAL_API_KEY, REPLICATE_API_TOKEN, BFL_API_KEY, TOGETHER_API_KEY, OPENAI_API_KEY, STEPFUN_API_KEY) to .env")
                            except Exception as _comfy_err:
                                tool_results.append(f"## ðŸŽ¨ Image Generation Failed\n\nâŒ V2: {_error}\nâŒ ComfyUI: {str(_comfy_err)}\n\nPlease check your API keys or start ComfyUI.")

                    except Exception as e:
                        logger.error(f"[TOOLS] Error in image generation: {e}")
                        import traceback
                        traceback.print_exc()
                        tool_results.append(f"## ðŸŽ¨ Image Generation\n\nError: {str(e)}\n\nPlease check your image generation API keys in .env")
        
            # â”€â”€ Deep Research Tool â”€â”€
            if 'deep-research' in tools:
                logger.info(f"[TOOLS] ðŸ”¬ Deep Research triggered for: {message[:80]}")
                try:
                    # Step 1: Web search for latest information
                    search_result = google_search_tool(message)
                    
                    # Step 2: Multi-model analysis
                    research_analyses = []
                    research_models = [
                        ('grok', 'Grok-3'),
                        ('deepseek-reasoner', 'DeepSeek R1'),
                        ('openai', 'GPT-4o-mini'),
                    ]
                    
                    research_prompt = f"""Based on the following web search results, provide a comprehensive analysis of the topic.

SEARCH RESULTS:
{search_result[:8000]}

USER QUESTION: {message}

Provide:
1. Key findings & facts
2. Multiple perspectives
3. Critical analysis
4. Conclusion with confidence level"""

                    for _model_id, _model_name in research_models:
                        try:
                            _research_bot = get_chatbot(session.get('session_id'))
                            _analysis = _research_bot.ask(
                                research_prompt,
                                context=context,
                                model=_model_id,
                                history=[],
                                deep_thinking=True,
                            )
                            _resp_text = _analysis.get('response', '') if isinstance(_analysis, dict) else str(_analysis)
                            if _resp_text:
                                research_analyses.append(f"### ðŸ¤– {_model_name} Analysis\n\n{_resp_text[:3000]}")
                        except Exception as _model_err:
                            logger.warning(f"[DEEP RESEARCH] {_model_name} failed: {_model_err}")
                            research_analyses.append(f"### âš ï¸ {_model_name}\n\nAnalysis unavailable: {str(_model_err)[:100]}")

                    # Step 3: Synthesize
                    analyses_text = "\n\n---\n\n".join(research_analyses) if research_analyses else "No analyses available"
                    
                    result_msg = f"""## ðŸ”¬ Deep Research Report

**Query:** {message}

---

### ðŸ“¡ Web Search Results
{search_result[:4000]}

---

### ðŸ§  Multi-Model Analysis

{analyses_text}

---

### ðŸ“Š Research Summary
- Sources consulted: Web search + {len(research_analyses)} AI models
- Models: {', '.join(m[1] for m in research_models)}
- Approach: Search â†’ Analyze â†’ Cross-reference â†’ Synthesize"""

                    tool_results.append(result_msg)
                except Exception as e:
                    logger.error(f"[TOOLS] Deep Research error: {e}")
                    tool_results.append(f"## ðŸ”¬ Deep Research\n\nError: {str(e)}")

            # â”€â”€ Code Interpreter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if 'code-interpreter' in tools:
                logger.info(f"[TOOLS] Code Interpreter for: {message[:80]}")
                try:
                    import subprocess, tempfile, re as _re
                    # Extract code blocks from message
                    code_blocks = _re.findall(r'```(?:python|py|javascript|js)?\s*\n(.*?)```', message, _re.DOTALL)
                    if not code_blocks:
                        # Try to detect inline code or treat entire message as instruction
                        code_blocks = _re.findall(r'`([^`]+)`', message)
                    
                    if code_blocks:
                        results_parts = []
                        for i, code in enumerate(code_blocks):
                            code = code.strip()
                            # Detect language
                            is_js = any(kw in code for kw in ['console.log', 'const ', 'let ', 'var ', 'function ', '=>', 'document.'])
                            
                            if is_js:
                                # Run JavaScript with Node.js
                                with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
                                    f.write(code)
                                    f.flush()
                                    try:
                                        proc = subprocess.run(['node', f.name], capture_output=True, text=True, timeout=30, cwd=tempfile.gettempdir())
                                        stdout = proc.stdout[:3000] if proc.stdout else ''
                                        stderr = proc.stderr[:1000] if proc.stderr else ''
                                        results_parts.append(f"**Block {i+1} (JavaScript):**\n```\n{stdout}\n```" + (f"\nâš ï¸ Stderr:\n```\n{stderr}\n```" if stderr else ''))
                                    finally:
                                        os.unlink(f.name)
                            else:
                                # Run Python
                                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                                    f.write(code)
                                    f.flush()
                                    try:
                                        proc = subprocess.run([sys.executable, f.name], capture_output=True, text=True, timeout=30, cwd=tempfile.gettempdir())
                                        stdout = proc.stdout[:3000] if proc.stdout else ''
                                        stderr = proc.stderr[:1000] if proc.stderr else ''
                                        results_parts.append(f"**Block {i+1} (Python):**\n```\n{stdout}\n```" + (f"\nâš ï¸ Stderr:\n```\n{stderr}\n```" if stderr else ''))
                                    finally:
                                        os.unlink(f.name)
                        
                        tool_results.append(f"## ðŸ’» Code Interpreter\n\n" + "\n\n".join(results_parts))
                    else:
                        # No code detected â€” ask AI to write & run code for the task
                        _code_prompt = f"Write a Python script to accomplish this task. Output ONLY the Python code, no explanations:\n\n{message}"
                        _code_resp = chatbot.chat(_code_prompt, model, context='', deep_thinking=False, history=[], language=language)
                        _code_text = _code_resp.get('response', '') if isinstance(_code_resp, dict) else str(_code_resp)
                        _extracted = _re.findall(r'```(?:python|py)?\s*\n(.*?)```', _code_text, _re.DOTALL)
                        if _extracted:
                            _script = _extracted[0].strip()
                            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                                f.write(_script)
                                f.flush()
                                try:
                                    proc = subprocess.run([sys.executable, f.name], capture_output=True, text=True, timeout=30, cwd=tempfile.gettempdir())
                                    stdout = proc.stdout[:3000] if proc.stdout else ''
                                    stderr = proc.stderr[:1000] if proc.stderr else ''
                                    tool_results.append(f"## ðŸ’» Code Interpreter\n\n**Generated Code:**\n```python\n{_script[:2000]}\n```\n\n**Output:**\n```\n{stdout}\n```" + (f"\nâš ï¸ Stderr:\n```\n{stderr}\n```" if stderr else ''))
                                finally:
                                    os.unlink(f.name)
                        else:
                            tool_results.append(f"## ðŸ’» Code Interpreter\n\n{_code_text}")
                except Exception as e:
                    logger.error(f"[TOOLS] Code Interpreter error: {e}")
                    tool_results.append(f"## ðŸ’» Code Interpreter\n\nâŒ Error: {str(e)}")

            # â”€â”€ PDF Analyzer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if 'pdf-analyzer' in tools:
                logger.info(f"[TOOLS] PDF Analyzer for: {message[:80]}")
                try:
                    import re as _re
                    # Check if user attached a PDF (base64 or URL) in history, or search for local PDFs
                    pdf_text = ""
                    pdf_source = ""
                    
                    # Try to find PDF URL in message
                    url_match = _re.search(r'https?://\S+\.pdf', message, _re.IGNORECASE)
                    if url_match:
                        pdf_url = url_match.group(0)
                        pdf_source = pdf_url
                        import httpx
                        resp = httpx.get(pdf_url, timeout=30, follow_redirects=True)
                        if resp.status_code == 200:
                            import io
                            try:
                                import PyPDF2
                                reader = PyPDF2.PdfReader(io.BytesIO(resp.content))
                                pages = []
                                for i, page in enumerate(reader.pages):
                                    text = page.extract_text() or ''
                                    if text.strip():
                                        pages.append(f"**Page {i+1}:**\n{text[:2000]}")
                                pdf_text = "\n\n---\n\n".join(pages[:50])
                            except ImportError:
                                try:
                                    import pdfplumber
                                    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
                                        pages = []
                                        for i, page in enumerate(pdf.pages):
                                            text = page.extract_text() or ''
                                            if text.strip():
                                                pages.append(f"**Page {i+1}:**\n{text[:2000]}")
                                        pdf_text = "\n\n---\n\n".join(pages[:50])
                                except ImportError:
                                    pdf_text = "âš ï¸ No PDF parser available. Install: `pip install PyPDF2` or `pip install pdfplumber`"
                    
                    # Check for local PDF in uploads
                    if not pdf_text:
                        upload_dir = Path(__file__).parent / 'uploads'
                        if upload_dir.exists():
                            pdf_files = list(upload_dir.glob('**/*.pdf'))
                            if pdf_files:
                                latest_pdf = max(pdf_files, key=lambda f: f.stat().st_mtime)
                                pdf_source = latest_pdf.name
                                try:
                                    import PyPDF2
                                    with open(latest_pdf, 'rb') as f:
                                        reader = PyPDF2.PdfReader(f)
                                        pages = []
                                        for i, page in enumerate(reader.pages):
                                            text = page.extract_text() or ''
                                            if text.strip():
                                                pages.append(f"**Page {i+1}:**\n{text[:2000]}")
                                        pdf_text = "\n\n---\n\n".join(pages[:50])
                                except ImportError:
                                    try:
                                        import pdfplumber
                                        with pdfplumber.open(str(latest_pdf)) as pdf:
                                            pages = []
                                            for i, page in enumerate(pdf.pages):
                                                text = page.extract_text() or ''
                                                if text.strip():
                                                    pages.append(f"**Page {i+1}:**\n{text[:2000]}")
                                            pdf_text = "\n\n---\n\n".join(pages[:50])
                                    except ImportError:
                                        pdf_text = "âš ï¸ No PDF parser available. Install: `pip install PyPDF2` or `pip install pdfplumber`"
                    
                    if pdf_text and 'âš ï¸' not in pdf_text:
                        # Ask AI to analyze the extracted text
                        _analysis_prompt = f"Analyze this PDF document and answer the user's question.\n\nUser question: {message}\n\nPDF Source: {pdf_source}\n\nExtracted text:\n{pdf_text[:8000]}"
                        _analysis = chatbot.chat(_analysis_prompt, model, context='', deep_thinking=True, history=[], language=language)
                        _analysis_text = _analysis.get('response', '') if isinstance(_analysis, dict) else str(_analysis)
                        tool_results.append(f"## ðŸ“„ PDF Analysis\n\n**Source:** {pdf_source}\n\n{_analysis_text}")
                    elif pdf_text:
                        tool_results.append(f"## ðŸ“„ PDF Analyzer\n\n{pdf_text}")
                    else:
                        tool_results.append(f"## ðŸ“„ PDF Analyzer\n\nKhÃ´ng tÃ¬m tháº¥y file PDF. HÃ£y:\n- Gá»­i URL file PDF trong tin nháº¯n\n- Hoáº·c upload file PDF trÆ°á»›c khi sá»­ dá»¥ng tool nÃ y")
                except Exception as e:
                    logger.error(f"[TOOLS] PDF Analyzer error: {e}")
                    tool_results.append(f"## ðŸ“„ PDF Analyzer\n\nâŒ Error: {str(e)}")

            # â”€â”€ Real-time Translation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if 'translator' in tools:
                logger.info(f"[TOOLS] Translation for: {message[:80]}")
                try:
                    _trans_prompt = f"""You are a professional translator. Analyze the following text and:
1. Auto-detect the source language
2. Translate it to the most appropriate target language (if Vietnamese â†’ English, if English â†’ Vietnamese, if other â†’ both Vietnamese and English)
3. Provide pronunciation guide if applicable
4. Note any idioms, cultural context, or nuances

Text to translate:
{message}

Respond in this format:
**Detected Language:** [language]
**Translation(s):**
[translations with target language labels]
**Pronunciation:** [if applicable]
**Notes:** [cultural context, idioms, nuances]"""
                    
                    _trans_resp = chatbot.chat(_trans_prompt, model, context='', deep_thinking=False, history=[], language=language)
                    _trans_text = _trans_resp.get('response', '') if isinstance(_trans_resp, dict) else str(_trans_resp)
                    tool_results.append(f"## ðŸŒ Translation\n\n{_trans_text}")
                except Exception as e:
                    logger.error(f"[TOOLS] Translation error: {e}")
                    tool_results.append(f"## ðŸŒ Translation\n\nâŒ Error: {str(e)}")

            # â”€â”€ Web Scraper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if 'web-scraper' in tools:
                logger.info(f"[TOOLS] Web Scraper for: {message[:80]}")
                try:
                    import re as _re
                    url_match = _re.search(r'https?://[^\s<>"\']+', message)
                    if url_match:
                        target_url = url_match.group(0).rstrip('.,;:!?)')
                        import httpx
                        from bs4 import BeautifulSoup
                        
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        }
                        resp = httpx.get(target_url, timeout=30, follow_redirects=True, headers=headers)
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        
                        # Remove scripts, styles
                        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                            tag.decompose()
                        
                        # Extract title
                        title = soup.title.string.strip() if soup.title and soup.title.string else 'No title'
                        
                        # Extract meta description
                        meta_desc = ''
                        meta_tag = soup.find('meta', attrs={'name': 'description'})
                        if meta_tag and meta_tag.get('content'):
                            meta_desc = meta_tag['content']
                        
                        # Extract main text
                        main_text = soup.get_text(separator='\n', strip=True)[:6000]
                        
                        # Extract links
                        links = []
                        for a in soup.find_all('a', href=True)[:20]:
                            href = a['href']
                            text = a.get_text(strip=True)[:80]
                            if text and href.startswith('http'):
                                links.append(f"- [{text}]({href})")
                        
                        # Extract images
                        images = []
                        for img in soup.find_all('img', src=True)[:10]:
                            src = img['src']
                            alt = img.get('alt', '')[:60]
                            if src.startswith('http'):
                                images.append(f"- ![{alt}]({src})")
                        
                        # Extract tables
                        tables_text = ""
                        for table in soup.find_all('table')[:3]:
                            rows = table.find_all('tr')
                            if rows:
                                table_data = []
                                for row in rows[:20]:
                                    cells = [c.get_text(strip=True)[:50] for c in row.find_all(['td', 'th'])]
                                    table_data.append(' | '.join(cells))
                                tables_text += "\n".join(table_data) + "\n\n"
                        
                        result = f"""## ðŸŒ Web Scraper

**URL:** {target_url}
**Title:** {title}
**Description:** {meta_desc[:200]}

### ðŸ“ Content
{main_text[:5000]}
"""
                        if tables_text:
                            result += f"\n### ðŸ“Š Tables\n{tables_text[:2000]}"
                        if links:
                            result += f"\n### ðŸ”— Links ({len(links)})\n" + "\n".join(links[:15])
                        if images:
                            result += f"\n### ðŸ–¼ï¸ Images ({len(images)})\n" + "\n".join(images[:8])
                        
                        tool_results.append(result)
                    else:
                        tool_results.append("## ðŸŒ Web Scraper\n\nKhÃ´ng tÃ¬m tháº¥y URL trong tin nháº¯n. HÃ£y gá»­i URL cáº§n scrape, vÃ­ dá»¥: `https://example.com`")
                except Exception as e:
                    logger.error(f"[TOOLS] Web Scraper error: {e}")
                    tool_results.append(f"## ðŸŒ Web Scraper\n\nâŒ Error: {str(e)}")

            # â”€â”€ Memory Manager â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if 'memory-manager' in tools:
                logger.info(f"[TOOLS] Memory Manager for: {message[:80]}")
                try:
                    user_prefs_file = MEMORY_DIR / '_user_preferences.json'
                    
                    # Load existing preferences
                    prefs = {}
                    if user_prefs_file.exists():
                        with open(user_prefs_file, 'r', encoding='utf-8') as f:
                            prefs = json.load(f)
                    
                    # Ask AI to extract preferences/facts from message
                    _mem_prompt = f"""Analyze this message and extract any user preferences, facts, or important information to remember.
Current stored preferences: {json.dumps(prefs, ensure_ascii=False)[:2000]}

User message: {message}

Respond in JSON format:
{{
    "new_facts": ["fact1", "fact2"],
    "preferences": {{"key": "value"}},
    "summary": "Brief summary of what was learned",
    "relevant_memories": ["any relevant stored info for this context"]
}}"""
                    
                    _mem_resp = chatbot.chat(_mem_prompt, model, context='', deep_thinking=False, history=[], language=language)
                    _mem_text = _mem_resp.get('response', '') if isinstance(_mem_resp, dict) else str(_mem_resp)
                    
                    # Try to parse AI response as JSON
                    import re as _re
                    _json_match = _re.search(r'\{.*\}', _mem_text, _re.DOTALL)
                    if _json_match:
                        try:
                            mem_data = json.loads(_json_match.group(0))
                            # Update preferences
                            if mem_data.get('preferences'):
                                prefs.update(mem_data['preferences'])
                            if mem_data.get('new_facts'):
                                if 'facts' not in prefs:
                                    prefs['facts'] = []
                                prefs['facts'].extend(mem_data['new_facts'])
                                prefs['facts'] = prefs['facts'][-100:]  # Keep last 100 facts
                            prefs['last_updated'] = datetime.now().isoformat()
                            
                            # Save updated preferences
                            with open(user_prefs_file, 'w', encoding='utf-8') as f:
                                json.dump(prefs, f, ensure_ascii=False, indent=2)
                            
                            summary = mem_data.get('summary', 'Preferences updated')
                            relevant = mem_data.get('relevant_memories', [])
                            facts_count = len(prefs.get('facts', []))
                            
                            result = f"## ðŸ§  Memory Manager\n\n**Status:** Updated successfully\n**Summary:** {summary}\n**Total facts stored:** {facts_count}"
                            if relevant:
                                result += f"\n\n**Relevant memories:**\n" + "\n".join(f"- {r}" for r in relevant[:5])
                            tool_results.append(result)
                        except json.JSONDecodeError:
                            tool_results.append(f"## ðŸ§  Memory Manager\n\n{_mem_text}")
                    else:
                        tool_results.append(f"## ðŸ§  Memory Manager\n\n{_mem_text}")
                except Exception as e:
                    logger.error(f"[TOOLS] Memory Manager error: {e}")
                    tool_results.append(f"## ðŸ§  Memory Manager\n\nâŒ Error: {str(e)}")
        
        # If tools were used, return tool results
        if tool_results:
            combined_results = "\n\n---\n\n".join(tool_results)
            _auto_log_chat(message, combined_results, 'tools', context, tools, is_tool=True)
            return jsonify({
                'response': combined_results,
                'model': 'tools',
                'context': context,
                'deep_thinking': False,
                'tools': tools,
                'timestamp': datetime.now().isoformat()
            })
        
        # Load selected memories
        memories = []
        if memory_ids:
            for mem_id in memory_ids:
                memory_file = MEMORY_DIR / f"{mem_id}.json"
                if memory_file.exists():
                    try:
                        with open(memory_file, 'r', encoding='utf-8') as f:
                            memory = json.load(f)
                            memories.append(memory)
                    except Exception as e:
                        logger.error(f"Error loading memory {mem_id}: {e}")
        
        # Prepare extra params from agent config
        extra_params = {}
        if agent_config:
            if agent_config.get('temperature') is not None:
                extra_params['temperature'] = agent_config.get('temperature')
            if agent_config.get('topP') is not None:
                extra_params['top_p'] = agent_config.get('topP')
            if agent_config.get('tokenLimit') is not None:
                extra_params['max_tokens'] = agent_config.get('tokenLimit')
            if agent_config.get('thinkingBudget') == 'on':
                deep_thinking = True
        
        # If history is provided, temporarily clear conversation history
        # and use the provided history instead
        if history:
            # Save current history
            original_history = chatbot.conversation_history.copy()
            # Use provided history for context
            result = chatbot.chat(message, model, context, deep_thinking, history, memories, language, custom_prompt, extra_params)
            # Restore original history (since we don't want to save edit responses to history)
            chatbot.conversation_history = original_history
        else:
            result = chatbot.chat(message, model, context, deep_thinking, None, memories, language, custom_prompt, extra_params)
        
        # Extract response and thinking_process
        if isinstance(result, dict):
            response = result.get('response', '')
            thinking_process = result.get('thinking_process', None)
        else:
            response = result
            thinking_process = None
        
        _auto_log_chat(message, response, model, context, tools,
                       thinking_process=thinking_process)
        return jsonify({
            'response': response,
            'model': model,
            'context': context,
            'deep_thinking': deep_thinking,
            'thinking_process': thinking_process,
            'tools': tools,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"[CHAT] Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/clear', methods=['POST'])
def clear():
    """Clear chat history"""
    try:
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        chatbot.clear_history()
        
        return jsonify({'message': 'Ã„ÂÃƒÂ£ xÃƒÂ³a lÃ¡Â»â€¹ch sÃ¡Â»Â­ chat'})
        
    except Exception as e:
        logger.error(f"[Clear History] Error: {str(e)}")
        return jsonify({'error': 'Failed to clear chat history'}), 500


@app.route('/history', methods=['GET'])
def history():
    """Get chat history"""
    try:
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        
        return jsonify({
            'history': chatbot.conversation_history
        })
        
    except Exception as e:
        logger.error(f"[History] Error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve chat history'}), 500


# ============================================================================
# MONGODB CONVERSATION ROUTES
# ============================================================================

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations for current user"""
    try:
        if not MONGODB_ENABLED:
            return jsonify({'error': 'MongoDB not enabled'}), 503
        
        user_id = get_user_id_from_session()
        conversations = ConversationDB.get_user_conversations(user_id, include_archived=False, limit=50)
        
        # Convert ObjectId to string
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
        
        return jsonify({
            'conversations': conversations,
            'count': len(conversations)
        })
        
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get specific conversation with messages"""
    try:
        if not MONGODB_ENABLED:
            return jsonify({'error': 'MongoDB not enabled'}), 503
        
        # Get conversation with messages
        conv = ConversationDB.get_conversation_with_messages(conversation_id)
        
        if not conv:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Convert ObjectId to string
        conv['_id'] = str(conv['_id'])
        for msg in conv.get('messages', []):
            msg['_id'] = str(msg['_id'])
            msg['conversation_id'] = str(msg['conversation_id'])
        
        return jsonify(conv)
        
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        if not MONGODB_ENABLED:
            return jsonify({'error': 'MongoDB not enabled'}), 503
        
        success = ConversationDB.delete_conversation(conversation_id)
        
        if success:
            # Clear from session if it's the active conversation
            if session.get('conversation_id') == conversation_id:
                session.pop('conversation_id', None)
            
            return jsonify({'message': 'Conversation deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete conversation'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<conversation_id>/archive', methods=['POST'])
def archive_conversation(conversation_id):
    """Archive a conversation"""
    try:
        if not MONGODB_ENABLED:
            return jsonify({'error': 'MongoDB not enabled'}), 503
        
        success = ConversationDB.archive_conversation(conversation_id)
        
        if success:
            return jsonify({'message': 'Conversation archived successfully'})
        else:
            return jsonify({'error': 'Failed to archive conversation'}), 500
        
    except Exception as e:
        logger.error(f"Error archiving conversation: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/new', methods=['POST'])
def create_new_conversation():
    """Create a new conversation"""
    try:
        if not MONGODB_ENABLED:
            return jsonify({'error': 'MongoDB not enabled'}), 503
        
        data = request.json or {}
        user_id = get_user_id_from_session()
        
        conv = ConversationDB.create_conversation(
            user_id=user_id,
            model=data.get('model', 'gemini-2.0-flash'),
            title=data.get('title', 'New Chat')
        )
        
        # Set as active conversation
        set_active_conversation(conv['_id'])
        
        # Update chatbot instance
        session_id = session.get('session_id')
        if session_id in chatbots:
            chatbots[session_id].conversation_id = conv['_id']
            chatbots[session_id].conversation_history = []
        
        conv['_id'] = str(conv['_id'])
        
        return jsonify(conv)
        
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# STABLE DIFFUSION IMAGE GENERATION ROUTES
# ============================================================================

@app.route('/api/sd-health', methods=['GET'])
@app.route('/sd-api/status', methods=['GET'])  # Alias for frontend compatibility
def sd_health():
    """Check Stable Diffusion API status (ComfyUI)"""
    try:
        from src.utils.comfyui_client import get_comfyui_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:8188')
        sd_client = get_comfyui_client(sd_api_url)
        
        is_running = sd_client.check_health()
        
        if is_running:
            current_model = sd_client.get_current_model()
            response = jsonify({
                'status': 'online',
                'api_url': sd_api_url,
                'current_model': current_model,
                'backend': 'comfyui'
            })
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            return response
        else:
            response = jsonify({
                'status': 'offline',
                'api_url': sd_api_url,
                'message': 'ComfyUI is not running. Please start it with: cd /workspace/AI-Assistant/ComfyUI && python main.py --listen 0.0.0.0 --port 8188'
            })
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            return response, 503
            
    except Exception as e:
        logger.error(f"[SD Health Check] Error: {e}")
        response = jsonify({
            'status': 'error',
            'message': str(e)
        })
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response, 500


@app.route('/api/sd-models', methods=['GET'])
@app.route('/sd-api/models', methods=['GET'])  # Alias for frontend compatibility
def sd_models():
    """Get list of checkpoint models from ComfyUI"""
    try:
        from src.utils.comfyui_client import get_comfyui_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:8188')
        sd_client = get_comfyui_client(sd_api_url)
        
        models = sd_client.get_models()
        current = sd_client.get_current_model()
        
        return jsonify({
            'models': models,
            'current_model': current
        })
        
    except Exception as e:
        logger.error(f"[SD Models] Error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve SD models'}), 500


@app.route('/api/sd-loras', methods=['GET'])
@app.route('/sd-api/loras', methods=['GET'])  # Alias for frontend compatibility
def sd_loras():
    """Get list of LoRA models from ComfyUI"""
    try:
        import requests
        from pathlib import Path
        
        # Try ComfyUI API first
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:8188')
        
        try:
            response = requests.get(f"{sd_api_url}/object_info/LoraLoader", timeout=5)
            if response.status_code == 200:
                data = response.json()
                lora_names = data.get('LoraLoader', {}).get('input', {}).get('required', {}).get('lora_name', [[]])[0]
                loras = [{'name': name, 'alias': name.replace('.safetensors', '')} for name in lora_names if name != 'None']
                return jsonify({'loras': loras})
        except:
            pass
        
        # Fallback: scan local directory
        lora_dir = Path('/workspace/AI-Assistant/ComfyUI/models/loras')
        loras = []
        
        if lora_dir.exists():
            for lora_file in lora_dir.rglob('*.safetensors'):
                rel_path = lora_file.relative_to(lora_dir)
                loras.append({
                    'name': str(rel_path),
                    'alias': lora_file.stem,
                    'path': str(lora_file)
                })
        
        return jsonify({'loras': loras})
        
    except Exception as e:
        logger.error(f"[SD LoRAs] Error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve LoRAs', 'loras': []}), 500


@app.route('/api/sd-vaes', methods=['GET'])
@app.route('/sd-api/vaes', methods=['GET'])  # Alias for frontend compatibility  
def sd_vaes():
    """Get list of VAE models from ComfyUI"""
    try:
        import requests
        from pathlib import Path
        
        # Try ComfyUI API first
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:8188')
        
        try:
            response = requests.get(f"{sd_api_url}/object_info/VAELoader", timeout=5)
            if response.status_code == 200:
                data = response.json()
                vae_names = data.get('VAELoader', {}).get('input', {}).get('required', {}).get('vae_name', [[]])[0]
                vaes = [{'name': name, 'alias': name.replace('.safetensors', '').replace('.pt', '')} for name in vae_names if name != 'None']
                return jsonify({'vaes': vaes})
        except:
            pass
        
        # Fallback: scan local directory
        vae_dir = Path('/workspace/AI-Assistant/ComfyUI/models/vae')
        vaes = [{'name': 'Automatic (Default)', 'alias': 'auto'}]
        
        if vae_dir.exists():
            for vae_file in vae_dir.rglob('*.safetensors'):
                vaes.append({
                    'name': vae_file.name,
                    'alias': vae_file.stem,
                    'path': str(vae_file)
                })
            for vae_file in vae_dir.rglob('*.pt'):
                vaes.append({
                    'name': vae_file.name,
                    'alias': vae_file.stem,
                    'path': str(vae_file)
                })
        
        return jsonify({'vaes': vaes})
        
    except Exception as e:
        logger.error(f"[SD VAEs] Error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve VAEs', 'vaes': [{'name': 'Automatic (Default)', 'alias': 'auto'}]}), 500


@app.route('/api/sd-change-model', methods=['POST'])
@app.route('/api/sd/change-model', methods=['POST'])  # Alias
def sd_change_model():
    """Ã„ÂÃ¡Â»â€¢i checkpoint model"""
    try:
        from src.utils.comfyui_client import ComfyUIClient
        
        data = request.json
        model_name = data.get('model_name')
        
        if not model_name:
            return jsonify({'error': 'model_name is required'}), 400
        
        sd_api_url = os.getenv('COMFYUI_URL', 'http://127.0.0.1:8188')
        from src.utils.comfyui_client import get_comfyui_client; sd_client = get_comfyui_client(sd_api_url)
        
        success = sd_client.change_model(model_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Ã„ÂÃƒÂ£ Ã„â€˜Ã¡Â»â€¢i model thÃƒÂ nh {model_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'KhÃ´ng thá»ƒ Ä‘á»•i model'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/generate-image', methods=['POST'])
@app.route('/sd-api/text2img', methods=['POST'])  # Alias for frontend compatibility
def generate_image():
    """
    Generate image from text prompt using ComfyUI
    
    Body params:
        - prompt (str): Text prompt describing the image
        - negative_prompt (str): What NOT to include
        - width (int): Width (default: 1024)
        - height (int): Height (default: 1024)
        - steps (int): Number of steps (default: 20)
        - cfg_scale (float): CFG scale (default: 7.0)
        - seed (int): Random seed (default: -1)
        - model (str): Model checkpoint name (optional)
        - save_to_storage (bool): Save to ChatBot storage (default: False)
    """
    try:
        # Use ComfyUI client
        from src.utils.comfyui_client import get_comfyui_client
        
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Get parameters from request
        save_to_storage = data.get('save_to_storage', False)
        params = {
            'prompt': prompt,
            'negative_prompt': data.get('negative_prompt', 'bad quality, blurry, distorted'),
            'width': int(data.get('width') or 1024),
            'height': int(data.get('height') or 1024),
            'steps': int(data.get('steps') or 20),
            'cfg_scale': float(data.get('cfg_scale') or 7.0),
            'seed': int(data.get('seed') or -1),
            'model': data.get('model', None)
        }
        
        # Get ComfyUI client
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:8188')
        sd_client = get_comfyui_client(sd_api_url)
        
        # Generate image using ComfyUI
        logger.info(f"[TEXT2IMG] Generating with ComfyUI: {params['prompt'][:50]}...")
        image_bytes = sd_client.generate_image(**params)
        logger.info(f"[TEXT2IMG] ComfyUI generation completed")
        
        # Check result
        if not image_bytes:
            logger.error("[TEXT2IMG] ComfyUI returned no image")
            return jsonify({'error': 'Failed to generate image'}), 500
        
        # Convert to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        base64_images = [base64_image]
        
        # Save to storage if requested
        saved_filenames = []
        cloud_urls = []  # PostImages URLs
        
        if save_to_storage:
            for idx, image_base64 in enumerate(base64_images):
                try:
                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"generated_{timestamp}_{idx}.png"
                    filepath = IMAGE_STORAGE_DIR / filename
                    
                    # Decode and save image locally first
                    image_data = base64.b64decode(image_base64)
                    with open(filepath, 'wb') as f:
                        f.write(image_data)
                    
                    saved_filenames.append(filename)
                    logger.info(f"[TEXT2IMG] Saved locally: {filename}")
                    
                    # Upload to PostImages (NO API KEY NEEDED!)
                    cloud_url = None
                    delete_url = None
                    
                    if CLOUD_UPLOAD_ENABLED:
                        try:
                            logger.info(f"[TEXT2IMG] Ã¢ËœÂÃ¯Â¸Â Uploading to ImgBB...")
                            uploader = ImgBBUploader()
                            upload_result = uploader.upload_image(
                                str(filepath),
                                title=f"AI Generated: {prompt[:50]}"
                            )
                            
                            if upload_result:
                                cloud_url = upload_result['url']
                                delete_url = upload_result.get('delete_url', '')
                                cloud_urls.append(cloud_url)
                                logger.info(f"[TEXT2IMG] Ã¢Å“â€¦ ImgBB URL: {cloud_url}")
                            else:
                                logger.warning(f"[TEXT2IMG] Ã¢Å¡Â Ã¯Â¸Â ImgBB upload failed, using local URL")
                        
                        except Exception as upload_error:
                            logger.error(f"[TEXT2IMG] ImgBB upload error: {upload_error}")
                    
                    # Save metadata with cloud URL and session_id for privacy filtering
                    metadata_file = filepath.with_suffix('.json')
                    
                    # Get gallery session ID for privacy
                    gallery_session_id = session.get('gallery_session_id')
                    if not gallery_session_id:
                        import uuid as uuid_module
                        gallery_session_id = str(uuid_module.uuid4())
                        session['gallery_session_id'] = gallery_session_id
                    
                    metadata = {
                        'filename': filename,
                        'created_at': datetime.now().isoformat(),
                        'prompt': prompt,
                        'negative_prompt': params['negative_prompt'],
                        'parameters': params,
                        'cloud_url': cloud_url,
                        'delete_url': delete_url,
                        'service': 'imgbb' if cloud_url else 'local',
                        'session_id': gallery_session_id  # For privacy filtering
                    }
                    
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)
                        
                except Exception as save_error:
                    logger.error(f"[TEXT2IMG] Error saving image {idx}: {save_error}")
        
        # Auto-save message to MongoDB with cloud URLs
        if MONGODB_ENABLED and save_to_storage and saved_filenames:
            try:
                # Get or create conversation
                session_id = session.get('session_id')
                user_id = get_user_id_from_session()
                conversation_id = session.get('conversation_id')
                
                if not conversation_id:
                    # Create new conversation
                    conversation = ConversationDB.create_conversation(
                        user_id=user_id,
                        model='stable-diffusion',
                        title=f"Text2Image: {prompt[:30]}..."
                    )
                    conversation_id = str(conversation['_id'])
                    session['conversation_id'] = conversation_id
                    logger.info(f"Ã°Å¸â€œÂ Created new conversation: {conversation_id}")
                
                # Prepare images array for MongoDB
                images_data = []
                for idx, filename in enumerate(saved_filenames):
                    cloud_url = cloud_urls[idx] if idx < len(cloud_urls) else None
                    
                    images_data.append({
                        'url': f"/static/Storage/Image_Gen/{filename}",
                        'cloud_url': cloud_url,
                        'delete_url': delete_url if cloud_url else None,
                        'caption': f"Generated: {prompt[:50]}",
                        'generated': True,
                        'service': 'imgbb' if cloud_url else 'local',
                        'mime_type': 'image/png'
                    })
                
                # Save assistant message with images
                save_message_to_db(
                    conversation_id=conversation_id,
                    role='assistant',
                    content=f"Ã¢Å“â€¦ Generated image with prompt: {prompt}",
                    images=images_data,
                    metadata={
                        'model': 'stable-diffusion',
                        'prompt': prompt,
                        'negative_prompt': params['negative_prompt'],
                        'cloud_service': 'imgbb' if cloud_urls else 'local',
                        'num_images': len(saved_filenames)
                    }
                )
                
                logger.info(f"Ã°Å¸â€™Â¾ Saved image message to MongoDB with {len(cloud_urls)} cloud URLs")
                
            except Exception as db_error:
                logger.error(f"Ã¢ÂÅ’ Error saving to MongoDB: {db_error}")
                # Continue execution - MongoDB save is optional
        
        # Save to generated_images collection (Gallery)
        if MONGODB_ENABLED and save_to_storage and saved_filenames:
            try:
                from core.image_storage import save_to_mongodb
                gallery_session_id = session.get('gallery_session_id', '')
                for idx, filename in enumerate(saved_filenames):
                    cloud_url = cloud_urls[idx] if idx < len(cloud_urls) else None
                    gallery_doc = {
                        'filename': filename,
                        'local_path': f"/storage/images/{filename}",
                        'cloud_url': cloud_url,
                        'prompt': prompt,
                        'negative_prompt': params.get('negative_prompt', ''),
                        'parameters': params,
                        'session_id': gallery_session_id,
                        'source': 'text2img',
                    }
                    save_to_mongodb(gallery_doc)
                logger.info(f"[TEXT2IMG] Gallery MongoDB saved {len(saved_filenames)} images")
            except Exception as gallery_err:
                logger.warning(f"[TEXT2IMG] Gallery MongoDB save failed: {gallery_err}")
        
        # Return response in format expected by frontend
        if save_to_storage and saved_filenames:
            # Return filenames + cloud URLs
            return jsonify({
                'success': True,
                'images': saved_filenames,  # Local filenames
                'image': saved_filenames[0],  # First filename for backward compatibility
                'cloud_urls': cloud_urls,  # ImgBB URLs
                'cloud_url': cloud_urls[0] if cloud_urls else None,  # First cloud URL
                'base64_images': base64_images,  # Include base64 for direct display
                'info': '',
                'parameters': params,
                'cloud_service': 'imgbb' if CLOUD_UPLOAD_ENABLED and cloud_urls else None,
                'saved_to_db': MONGODB_ENABLED and 'db_error' not in locals()  # Indicate if saved to MongoDB
            })
        else:
            # Return base64 images directly
            return jsonify({
                'success': True,
                'image': base64_images[0] if base64_images else None,
                'images': base64_images,  # Full array of base64 images
                'info': '',
                'parameters': params
            })
        
    except Exception as e:
        import traceback
        error_msg = f"Exception: {str(e)}\nTraceback: {traceback.format_exc()}"
        logger.error(f"[TEXT2IMG] {error_msg}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sd-samplers', methods=['GET'])
@app.route('/sd-api/samplers', methods=['GET'])  # Alias for frontend compatibility
@app.route('/api/sd/samplers', methods=['GET'])  # Another alias
def sd_samplers():
    """Láº¥y danh sÃ¡ch samplers"""
    try:
        from src.utils.comfyui_client import get_comfyui_client
        
        sd_api_url = os.getenv('COMFYUI_URL', 'http://127.0.0.1:8188')
        sd_client = get_comfyui_client(sd_api_url)
        
        samplers = sd_client.get_samplers()
        
        return jsonify({
            'success': True,
            'samplers': samplers
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


        return jsonify({'error': 'Failed to retrieve VAEs'}), 500


@app.route('/api/generate-prompt-grok', methods=['POST'])
@app.route('/api/generate-prompt', methods=['POST'])  # Universal endpoint
def generate_prompt_grok():
    """
    Táº¡o prompt tá»‘i Æ°u tá»« extracted tags - Support táº¥t cáº£ model (GROK, Gemini, GPT, DeepSeek, Qwen, BloomVN)
    
    Body params:
        - context (str): Context vÃ¡Â»Â tags Ã„â€˜ÃƒÂ£ trÃƒÂ­ch xuÃ¡ÂºÂ¥t
        - tags (list): List cÃ¡c tags Ä‘Ã£ extract
        - model (str): Model Ä‘á»ƒ dÃ¹ng (grok, gemini, openai, deepseek, qwen, bloomvn) - default: grok
    """
    try:
        data = request.json
        context = data.get('context', '')
        tags = data.get('tags', [])
        selected_model = data.get('model', 'grok').lower()
        
        if not tags:
            return jsonify({'error': 'Tags khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng'}), 400
        
        # System prompt cho táº¥t cáº£ models
        system_prompt = """You are an expert at creating high-quality Stable Diffusion prompts for anime/illustration generation.

Your task:
1. Generate a POSITIVE prompt: Natural, flowing description combining extracted features with quality boosters
2. Generate a NEGATIVE prompt: Things to avoid (low quality, artifacts, NSFW content, etc.)
3. ALWAYS filter out NSFW/inappropriate content from positive prompt
4. Return JSON format: {"prompt": "...", "negative_prompt": "..."}

Rules for POSITIVE prompt:
- Start with quality tags: masterpiece, best quality, highly detailed
- Add style: anime style, illustration, digital art
- Include visual features from tags
- Add atmosphere/mood if applicable
- Use comma-separated format
- Keep it concise (max 150 words)

Rules for NEGATIVE prompt:
- ALWAYS include: nsfw, nude, sexual, explicit, adult content
- Add quality issues: bad quality, blurry, worst quality, low resolution
- Add anatomy issues: bad anatomy, bad hands, bad proportions
- Add artifacts: watermark, signature, text, jpeg artifacts

Output ONLY valid JSON, no explanations."""

        try:
            # Route to appropriate model
            if selected_model == 'grok':
                result = _generate_with_grok(context, system_prompt, tags)
            elif selected_model == 'gemini':
                result = _generate_with_gemini(context, system_prompt, tags)
            elif selected_model == 'openai':
                result = _generate_with_openai(context, system_prompt, tags)
            elif selected_model == 'deepseek':
                result = _generate_with_deepseek(context, system_prompt, tags)
            elif selected_model in ['qwen', 'bloomvn']:
                # Use fallback for local models (they may not have API)
                result = _generate_fallback(tags)
            else:
                # Default to GROK
                result = _generate_with_grok(context, system_prompt, tags)
            
            return jsonify(result)
            
        except Exception as model_error:
            logger.error(f"[Prompt Gen] Model error: {str(model_error)}")
            
            # Fallback: Generate prompt from tags directly
            logger.info("[Prompt Gen] Using fallback method")
            result = _generate_fallback(tags)
            result['fallback'] = True
            result['fallback_reason'] = str(model_error)
            
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"[Prompt Gen] Error: {str(e)}")
        return jsonify({'error': 'Failed to generate prompt'}), 500


def _generate_with_grok(context, system_prompt, tags):
    """Generate prompt using GROK"""
    from openai import OpenAI
    
    api_key = os.getenv('GROK_API_KEY') or os.getenv('XAI_API_KEY')
    if not api_key:
        raise ValueError('GROK API key not configured')
    
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
    
    logger.info(f"[GROK] Generating prompt from {len(tags)} tags")
    
    response = client.chat.completions.create(
        model="grok-3",  # Updated to grok-3 (grok-beta deprecated)
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ],
        temperature=0.7,
        max_tokens=500,
        response_format={"type": "json_object"}
    )
    
    result_text = response.choices[0].message.content.strip()
    result_json = json.loads(result_text)
    
    return _process_prompt_result(result_json, tags, 'grok')


def _generate_with_gemini(context, system_prompt, tags):
    """Generate prompt using Gemini"""
    from google import genai
    from google.genai import types
    
    api_key = GEMINI_API_KEY
    if not api_key:
        raise ValueError('Gemini API key not configured')
    
    logger.info(f"[Gemini] Generating prompt from {len(tags)} tags")
    
    client = genai.Client(api_key=api_key)
    
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents=f"{system_prompt}\n\n{context}",
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=500,
            response_mime_type="application/json"
        )
    )
    
    result_text = response.text.strip()
    result_json = json.loads(result_text)
    
    return _process_prompt_result(result_json, tags, 'gemini')


def _generate_with_openai(context, system_prompt, tags):
    """Generate prompt using OpenAI GPT-4o-mini"""
    import openai
    
    api_key = OPENAI_API_KEY
    if not api_key:
        raise ValueError('OpenAI API key not configured')
    
    logger.info(f"[OpenAI] Generating prompt from {len(tags)} tags")
    
    openai.api_key = api_key
    
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ],
        temperature=0.7,
        max_tokens=500,
        response_format={"type": "json_object"}
    )
    
    result_text = response.choices[0].message.content.strip()
    result_json = json.loads(result_text)
    
    return _process_prompt_result(result_json, tags, 'openai')


def _generate_with_deepseek(context, system_prompt, tags):
    """Generate prompt using DeepSeek"""
    from openai import OpenAI
    
    api_key = DEEPSEEK_API_KEY
    if not api_key:
        raise ValueError('DeepSeek API key not configured')
    
    logger.info(f"[DeepSeek] Generating prompt from {len(tags)} tags")
    
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ],
        temperature=0.7,
        max_tokens=500,
        response_format={"type": "json_object"}
    )
    
    result_text = response.choices[0].message.content.strip()
    result_json = json.loads(result_text)
    
    return _process_prompt_result(result_json, tags, 'deepseek')


def _process_prompt_result(result_json, tags, model_name):
    """Process and validate prompt generation result"""
    generated_prompt = result_json.get('prompt', '').strip()
    generated_negative = result_json.get('negative_prompt', result_json.get('negative', '')).strip()
    
    # Ensure negative prompt always has NSFW filters
    if not generated_negative:
        generated_negative = 'nsfw, nude, sexual, explicit, adult content, bad quality, blurry, worst quality, low resolution, bad anatomy'
    elif 'nsfw' not in generated_negative.lower():
        generated_negative = 'nsfw, nude, sexual, explicit, adult content, ' + generated_negative
    
    logger.info(f"[{model_name.upper()}] Prompt: {generated_prompt[:100]}...")
    logger.info(f"[{model_name.upper()}] Negative: {generated_negative[:100]}...")
    
    return {
        'success': True,
        'prompt': generated_prompt,
        'negative_prompt': generated_negative,
        'tags_used': len(tags),
        'model': model_name
    }


def _generate_fallback(tags):
    """Fallback method - simple tag joining"""
    prompt_parts = tags[:25]  # Limit to 25 tags
    quality_tags = ['masterpiece', 'best quality', 'highly detailed', 'beautiful', 'professional']
    
    fallback_prompt = ', '.join(quality_tags + prompt_parts)
    fallback_negative = 'nsfw, nude, sexual, explicit, adult content, bad quality, blurry, distorted, worst quality, low resolution, bad anatomy, bad hands'
    
    return {
        'success': True,
        'prompt': fallback_prompt,
        'negative_prompt': fallback_negative,
        'tags_used': len(tags)
    }


@app.route('/api/img2img', methods=['POST'])
@app.route('/sd-api/img2img', methods=['POST'])  # Alias for frontend compatibility
def img2img():
    """
    Táº¡o áº£nh tá»« áº£nh gá»‘c báº±ng Stable Diffusion Img2Img
    
    Body params:
        - image (str): Base64 encoded image
        - prompt (str): Text prompt mÃ´ táº£ áº£nh muá»‘n táº¡o
        - negative_prompt (str): Nhá»¯ng gÃ¬ khÃ´ng muá»‘n cÃ³
        - denoising_strength (float): Tá»‰ lá»‡ thay Ä‘á»•i (0.0-1.0, default: 0.75)
            - 0.0 = giá»¯ nguyÃªn áº£nh gá»‘c 100%
            - 1.0 = táº¡o má»›i hoÃ n toÃ n
            - 0.8 = 80% má»›i, 20% giá»¯ láº¡i (recommended)
        - width (int): ChiÃ¡Â»Âu rÃ¡Â»â„¢ng
        - height (int): ChiÃ¡Â»Âu cao  
        - steps (int): Sá»‘ steps
        - cfg_scale (float): CFG scale
        - sampler_name (str): TÃªn sampler
        - seed (int): Random seed
        - restore_faces (bool): Restore faces
    """
    try:
        from src.utils.comfyui_client import get_comfyui_client
        
        data = request.json
        image = data.get('image', '')
        prompt = data.get('prompt', '')
        
        if not image:
            return jsonify({'error': 'Image khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng'}), 400
        
        if not prompt:
            return jsonify({'error': 'Prompt khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng'}), 400
        
        # Láº¥y parameters tá»« request
        params = {
            'init_images': [image],  # SD API expects list of images
            'prompt': prompt,
            'negative_prompt': data.get('negative_prompt', ''),
            'denoising_strength': float(data.get('denoising_strength') or 0.8),  # 80% new, 20% keep
            'width': int(data.get('width') or 512),
            'height': int(data.get('height') or 512),
            'steps': int(data.get('steps') or 30),  # img2img needs more steps
            'cfg_scale': float(data.get('cfg_scale') or 7.0),
            'sampler_name': data.get('sampler_name') or 'euler',
            'seed': int(data.get('seed') or -1),
            'model': data.get('model') or None,
            'lora_models': data.get('lora_models', []),
            'vae': data.get('vae', None)
        }
        
        # Get SD client
        sd_api_url = os.getenv('COMFYUI_URL', 'http://127.0.0.1:8188')
        sd_client = get_comfyui_client(sd_api_url)
        
        # Táº¡o áº£nh vá»›i img2img
        logger.info(f"[IMG2IMG] Calling img2img with denoising_strength={params['denoising_strength']}")
        result = sd_client.img2img(**params)
        logger.info(f"[IMG2IMG] Result received")
        
        # Kiá»ƒm tra lá»—i
        if 'error' in result:
            logger.error(f"[IMG2IMG] SD Error: {result['error']}")
            return jsonify({'error': result['error']}), 500
        
        # Get base64 images from result
        base64_images = result.get('images', [])
        
        if not base64_images:
            return jsonify({'error': 'No images generated'}), 500
        
        # Save to storage if requested
        save_to_storage = data.get('save_to_storage', False)
        saved_filenames = []
        cloud_urls = []
        
        if save_to_storage:
            for idx, image_base64 in enumerate(base64_images):
                try:
                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"img2img_{timestamp}_{idx}.png"
                    filepath = IMAGE_STORAGE_DIR / filename
                    
                    # Decode and save image locally first
                    image_data = base64.b64decode(image_base64)
                    with open(filepath, 'wb') as f:
                        f.write(image_data)
                    
                    saved_filenames.append(filename)
                    logger.info(f"[IMG2IMG] Saved locally: {filename}")
                    
                    # Upload to ImgBB cloud
                    cloud_url = None
                    delete_url = None
                    
                    if CLOUD_UPLOAD_ENABLED:
                        try:
                            logger.info(f"[IMG2IMG] Ã¢ËœÂÃ¯Â¸Â Uploading to ImgBB...")
                            uploader = ImgBBUploader()
                            upload_result = uploader.upload_image(
                                str(filepath),
                                title=f"AI Img2Img: {prompt[:50]}"
                            )
                            
                            if upload_result:
                                cloud_url = upload_result['url']
                                delete_url = upload_result.get('delete_url', '')
                                cloud_urls.append(cloud_url)
                                logger.info(f"[IMG2IMG] Ã¢Å“â€¦ ImgBB URL: {cloud_url}")
                            else:
                                logger.warning(f"[IMG2IMG] Ã¢Å¡Â Ã¯Â¸Â ImgBB upload failed, using local URL")
                        
                        except Exception as upload_error:
                            logger.error(f"[IMG2IMG] ImgBB upload error: {upload_error}")
                    
                    # Save metadata with cloud URL and session_id for privacy filtering
                    metadata_file = filepath.with_suffix('.json')
                    
                    # Get gallery session ID for privacy
                    gallery_session_id = session.get('gallery_session_id')
                    if not gallery_session_id:
                        import uuid as uuid_module
                        gallery_session_id = str(uuid_module.uuid4())
                        session['gallery_session_id'] = gallery_session_id
                    
                    metadata = {
                        'filename': filename,
                        'created_at': datetime.now().isoformat(),
                        'prompt': prompt,
                        'negative_prompt': params['negative_prompt'],
                        'denoising_strength': params['denoising_strength'],
                        'parameters': params,
                        'cloud_url': cloud_url,
                        'delete_url': delete_url,
                        'service': 'imgbb' if cloud_url else 'local',
                        'session_id': gallery_session_id  # For privacy filtering
                    }
                    
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)
                        
                except Exception as save_error:
                    logger.error(f"[IMG2IMG] Error saving image {idx}: {save_error}")
        
        # Auto-save message to MongoDB with cloud URLs
        if MONGODB_ENABLED and save_to_storage and saved_filenames:
            try:
                # Get or create conversation
                user_id = get_user_id_from_session()
                conversation_id = session.get('conversation_id')
                
                if not conversation_id:
                    # Create new conversation
                    conversation = ConversationDB.create_conversation(
                        user_id=user_id,
                        model='stable-diffusion',
                        title=f"Img2Img: {prompt[:30]}..."
                    )
                    conversation_id = str(conversation['_id'])
                    session['conversation_id'] = conversation_id
                    logger.info(f"Ã°Å¸â€œÂ Created new conversation: {conversation_id}")
                
                # Prepare images array for MongoDB
                images_data = []
                for idx, filename in enumerate(saved_filenames):
                    cloud_url = cloud_urls[idx] if idx < len(cloud_urls) else None
                    
                    images_data.append({
                        'url': f"/static/Storage/Image_Gen/{filename}",
                        'cloud_url': cloud_url,
                        'delete_url': delete_url if cloud_url else None,
                        'caption': f"Img2Img: {prompt[:50]}",
                        'generated': True,
                        'service': 'imgbb' if cloud_url else 'local',
                        'mime_type': 'image/png'
                    })
                
                # Save assistant message with images
                save_message_to_db(
                    conversation_id=conversation_id,
                    role='assistant',
                    content=f"Ã¢Å“â€¦ Generated Img2Img with prompt: {prompt}",
                    images=images_data,
                    metadata={
                        'model': 'stable-diffusion-img2img',
                        'prompt': prompt,
                        'negative_prompt': params['negative_prompt'],
                        'denoising_strength': params['denoising_strength'],
                        'cloud_service': 'imgbb' if cloud_urls else 'local',
                        'num_images': len(saved_filenames)
                    }
                )
                
                logger.info(f"Ã°Å¸â€™Â¾ Saved Img2Img message to MongoDB with {len(cloud_urls)} cloud URLs")
                
            except Exception as db_error:
                logger.error(f"Ã¢ÂÅ’ Error saving to MongoDB: {db_error}")
                # Continue execution - MongoDB save is optional
        
        # Save to generated_images collection (Gallery)
        if MONGODB_ENABLED and save_to_storage and saved_filenames:
            try:
                from core.image_storage import save_to_mongodb
                gallery_session_id = session.get('gallery_session_id', '')
                for idx, filename in enumerate(saved_filenames):
                    cloud_url = cloud_urls[idx] if idx < len(cloud_urls) else None
                    gallery_doc = {
                        'filename': filename,
                        'local_path': f"/storage/images/{filename}",
                        'cloud_url': cloud_url,
                        'prompt': prompt,
                        'negative_prompt': params.get('negative_prompt', ''),
                        'denoising_strength': params.get('denoising_strength', ''),
                        'parameters': params,
                        'session_id': gallery_session_id,
                        'source': 'img2img',
                    }
                    save_to_mongodb(gallery_doc)
                logger.info(f"[IMG2IMG] Gallery MongoDB saved {len(saved_filenames)} images")
            except Exception as gallery_err:
                logger.warning(f"[IMG2IMG] Gallery MongoDB save failed: {gallery_err}")
        
        # Return response in format expected by frontend
        if save_to_storage and saved_filenames:
            return jsonify({
                'success': True,
                'image': base64_images[0] if base64_images else None,
                'images': base64_images,
                'filenames': saved_filenames,
                'cloud_urls': cloud_urls,
                'info': result.get('info', ''),
                'parameters': result.get('parameters', {})
            })
        else:
            return jsonify({
                'success': True,
                'image': base64_images[0] if base64_images else None,
                'images': base64_images,
                'info': result.get('info', ''),
                'parameters': result.get('parameters', {})
            })
        
    except Exception as e:
        import traceback
        error_msg = f"Exception: {str(e)}\nTraceback: {traceback.format_exc()}"
        logger.error(f"[IMG2IMG] {error_msg}")
        return jsonify({'error': f'Img2Img failed: {str(e)}'}), 500


@app.route('/api/share-image-imgbb', methods=['POST'])
def share_image_imgbb():
    """
    Upload generated image to ImgBB and return shareable link
    
    Body params:
        - image (str): Base64 encoded image
        - title (str): Optional title for the image
    """
    try:
        data = request.json
        base64_image = data.get('image', '')
        title = data.get('title', f'AI_Generated_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        
        if not base64_image:
            return jsonify({'error': 'No image provided'}), 400
        
        # Remove data:image/...;base64, prefix if present
        if ',' in base64_image:
            base64_image = base64_image.split(',')[1]
        
        # Sanitize title to prevent log injection
        safe_title = title.replace('\n', '\\n').replace('\r', '\\r') if title else 'Untitled'
        logger.info(f"[ImgBB Share] Uploading image: {safe_title}")
        
        try:
            uploader = ImgBBUploader()
            result = uploader.upload(base64_image, title=title)
            
            if result and result.get('url'):
                logger.info(f"[ImgBB Share] Ã¢Å“â€¦ Success: {result['url']}")
                return jsonify({
                    'success': True,
                    'url': result['url'],
                    'display_url': result.get('display_url', result['url']),
                    'delete_url': result.get('delete_url'),
                    'thumb_url': result.get('thumb', {}).get('url'),
                    'title': title
                })
            else:
                logger.error(f"[ImgBB Share] Ã¢ÂÅ’ Upload failed: {result}")
                return jsonify({'error': 'ImgBB upload failed'}), 500
                
        except Exception as upload_error:
            logger.error(f"[ImgBB Share] Ã¢ÂÅ’ Error: {str(upload_error)}")
            return jsonify({'error': 'Failed to upload image to ImgBB'}), 500
        
    except Exception as e:
        logger.error(f"[ImgBB Share] Ã¢ÂÅ’ Exception: {str(e)}")
        return jsonify({'error': 'Failed to process image share request'}), 500


@app.route('/api/save-generated-image', methods=['POST'])
def save_generated_image():
    """
    Save generated image to storage and chat history
    
    Body params:
        - image (str): Base64 encoded image
        - metadata (dict): Generation parameters (prompt, negative, model, etc.)
    """
    try:
        data = request.json
        base64_image = data.get('image', '')
        metadata = data.get('metadata', {})
        
        if not base64_image:
            return jsonify({'error': 'No image provided'}), 400
        
        # Remove prefix if present
        if ',' in base64_image:
            base64_image = base64_image.split(',')[1]
        
        # Clean and sanitize base64 string
        base64_image = base64_image.strip()
        if not base64_image:
            return jsonify({'error': 'Empty image data after stripping'}), 400
        
        # Remove only newlines and carriage returns (keep valid base64 chars)
        base64_image = base64_image.replace('\n', '').replace('\r', '').replace(' ', '').replace('\t', '')
        
        if not base64_image:
            return jsonify({'error': 'No valid base64 data after cleaning'}), 400
        
        # Decode image with error handling (try without validation first)
        try:
            # First try: decode without strict validation
            try:
                image_bytes = base64.b64decode(base64_image)
            except Exception:
                # Second try: fix padding and validate
                padding = len(base64_image) % 4
                if padding:
                    base64_image += '=' * (4 - padding)
                image_bytes = base64.b64decode(base64_image, validate=True)
            
            if not image_bytes:
                return jsonify({'error': 'Failed to decode base64 image'}), 400
            
            # Try to open and validate the image
            image_buffer = io.BytesIO(image_bytes)
            image = Image.open(image_buffer)
            
            # Get format before verify
            image_format = image.format or 'PNG'
            
            # Verify it's a valid image
            image.verify()
            
            # Re-open after verify (verify closes the file)
            image_buffer.seek(0)
            image = Image.open(image_buffer)
        except base64.binascii.Error as e:
            logger.error(f"[Save Image] Base64 decode error: {e}")
            return jsonify({'error': 'Invalid base64 image data'}), 400
        except Exception as e:
            logger.error(f"[Save Image] Image processing error: {e}")
            return jsonify({'error': f'Cannot process image: {str(e)}'}), 400
        
        # Save to storage
        storage_dir = Path(__file__).parent / 'Storage' / 'Image_Gen'
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
        filepath = storage_dir / filename
        
        image.save(filepath, 'PNG')
        logger.info(f"[Save Image] Ã°Å¸â€™Â¾ Saved to: {filepath}")
        
        # Upload to ImgBB if enabled
        cloud_url = None
        delete_url = None
        
        if CLOUD_UPLOAD_ENABLED:
            try:
                uploader = ImgBBUploader()
                cloud_result = uploader.upload(base64_image, title=filename)
                
                if cloud_result and cloud_result.get('url'):
                    cloud_url = cloud_result['url']
                    delete_url = cloud_result.get('delete_url')
                    logger.info(f"[Save Image] Ã¢ËœÂÃ¯Â¸Â ImgBB: {cloud_url}")
            except Exception as cloud_error:
                logger.warning(f"[Save Image] Ã¢Å¡Â Ã¯Â¸Â ImgBB upload failed: {cloud_error}")
        
                
        # Upload to Google Drive (only if GOOGLE_DRIVE_ENABLED=true in .env)
        drive_file_id = None
        drive_web_link = None
        _gd_enabled = os.getenv('GOOGLE_DRIVE_ENABLED', 'false').lower() == 'true'
        if _gd_enabled:
            try:
                from core.google_drive_service import GoogleDriveService
                
                drive_service = GoogleDriveService()
                if drive_service._service is not None:
                    gd_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
                    if gd_folder_id:
                        drive_service.set_folder_id(gd_folder_id)
                        gd_metadata = {
                            'prompt': metadata.get('prompt', ''),
                            'model': metadata.get('model', ''),
                            'sampler': metadata.get('sampler', ''),
                            'steps': metadata.get('steps', ''),
                            'cfg_scale': metadata.get('cfg_scale', ''),
                            'seed': metadata.get('seed', ''),
                        }
                        drive_result = drive_service.upload_image(
                            image_b64=base64_image,
                            filename=filename,
                            metadata=gd_metadata
                        )
                        if drive_result.get('success'):
                            drive_file_id = drive_result.get('file_id')
                            drive_web_link = drive_result.get('web_view_link')
                            logger.info(f"[Save Image] Google Drive uploaded: {drive_web_link}")
                        else:
                            logger.warning(f"[Save Image] Google Drive upload failed: {drive_result.get('error')}")
            except Exception as drive_error:
                logger.warning(f"[Save Image] Google Drive error: {drive_error}")
        # Save metadata JSON alongside the PNG (for local gallery fallback)
        try:
            metadata_json = {
                'filename': filename,
                'created_at': datetime.now().isoformat(),
                'cloud_url': cloud_url,
                'delete_url': delete_url,
                'session_id': session.get('gallery_session_id', ''),
                'prompt': metadata.get('prompt', ''),
                'negative_prompt': metadata.get('negative_prompt', ''),
                'model': metadata.get('model', ''),
                'sampler': metadata.get('sampler', ''),
                'steps': metadata.get('steps', ''),
                'cfg_scale': metadata.get('cfg_scale', ''),
                'width': metadata.get('width', ''),
                'height': metadata.get('height', ''),
                'seed': metadata.get('seed', ''),
                'vae': metadata.get('vae', ''),
                'lora_models': metadata.get('lora_models', ''),
                'denoising_strength': metadata.get('denoising_strength', ''),
            }
            metadata_filepath = filepath.with_suffix('.json')
            with open(metadata_filepath, 'w', encoding='utf-8') as mf:
                json.dump(metadata_json, mf, ensure_ascii=False, indent=2)
        except Exception as meta_err:
            logger.warning(f"[Save Image] Metadata JSON save failed: {meta_err}")
        
        # Save to generated_images collection in MongoDB (for Gallery)
        try:
            from core.image_storage import save_to_mongodb
            gallery_doc = {
                'filename': filename,
                'local_path': f"/storage/images/{filename}",
                'cloud_url': cloud_url,
                'delete_url': delete_url,
                'prompt': metadata.get('prompt', ''),
                'negative_prompt': metadata.get('negative_prompt', ''),
                'model': metadata.get('model', ''),
                'sampler': metadata.get('sampler', ''),
                'steps': metadata.get('steps', ''),
                'cfg_scale': metadata.get('cfg_scale', ''),
                'width': metadata.get('width', ''),
                'height': metadata.get('height', ''),
                'seed': metadata.get('seed', ''),
                'vae': metadata.get('vae', ''),
                'lora_models': metadata.get('lora_models', ''),
                'denoising_strength': metadata.get('denoising_strength', ''),
                'session_id': session.get('gallery_session_id', ''),
                'source': 'comfyui',
            }
            mongo_gallery_id = save_to_mongodb(gallery_doc)
            if mongo_gallery_id:
                logger.info(f"[Save Image] Gallery MongoDB saved: {mongo_gallery_id}")
        except Exception as gallery_err:
            logger.warning(f"[Save Image] Gallery MongoDB save failed: {gallery_err}")
        
        # Save to chat history
        conversation_id = session.get('conversation_id')
        user_id = session.get('user_id', 'anonymous')
        
        # Try to save to MongoDB (optional - graceful degradation)
        mongodb_saved = False
        try:
            if not MONGODB_ENABLED:
                logger.warning("[Save Image] MongoDB not enabled, skipping DB save")
            else:
                # Create conversation if needed
                if not conversation_id:
                    conversation = get_or_create_conversation(
                        user_id=user_id,
                        model=metadata.get('model', 'stable-diffusion')
                    )
                    if conversation:
                        conversation_id = str(conversation['_id'])
                        session['conversation_id'] = conversation_id
                    else:
                        logger.warning("[Save Image] Could not create conversation")
                
                if conversation_id:
                    # Save message with image
                    images_data = [{
                        'url': f"/static/Storage/Image_Gen/{filename}",
                        'cloud_url': cloud_url,
                        'delete_url': delete_url,
                        'caption': metadata.get('prompt', 'AI Generated Image'),
                        'generated': True,
                        'service': 'imgbb' if cloud_url else 'local',
                        'mime_type': 'image/png'
                    }]
                    
                    save_message_to_db(
                        conversation_id=conversation_id,
                        role='assistant',
                        content=f"Ã°Å¸Å½Â¨ Generated image with prompt: {metadata.get('prompt', 'N/A')}",
                        images=images_data,
                        metadata=metadata
                    )
                    
                    logger.info(f"[Save Image] Ã¢Å“â€¦ Saved to chat history: {conversation_id}")
                    mongodb_saved = True
                    
        except Exception as db_error:
            logger.error(f"[Save Image] Ã¢Å¡Â Ã¯Â¸Â MongoDB save failed: {db_error}")
            # Continue - this is optional
        
        # Always return success (local save completed)
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': f"/static/Storage/Image_Gen/{filename}",
            'cloud_url': cloud_url,
            'delete_url': delete_url,
            'saved_to_db': mongodb_saved
        })
        
    except Exception as e:
        logger.error(f"[Save Image] Ã¢ÂÅ’ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sd-interrupt', methods=['POST'])
def sd_interrupt():
    """Dá»«ng viá»‡c táº¡o áº£nh Ä‘ang cháº¡y"""
    try:
        from src.utils.comfyui_client import get_comfyui_client
        
        sd_api_url = os.getenv('COMFYUI_URL', 'http://127.0.0.1:8188')
        sd_client = get_comfyui_client(sd_api_url)
        
        success = sd_client.interrupt()
        
        return jsonify({
            'success': success
        })
        
    except Exception as e:
        logger.error(f"[Save Image] Error: {str(e)}")
        return jsonify({'error': 'Failed to save generated image'}), 500


@app.route('/api/extract-anime-features-multi', methods=['POST'])
def extract_anime_features_multi():
    """
    Ã°Å¸Å½Â¯ MULTI-MODEL EXTRACTION - SÃ¡Â»Â­ dÃ¡Â»Â¥ng nhiÃ¡Â»Âu model Ã„â€˜Ã¡Â»Æ’ trÃƒÂ­ch xuÃ¡ÂºÂ¥t chÃƒÂ­nh xÃƒÂ¡c hÃ†Â¡n
    
    Models há»— trá»£:
        - deepdanbooru: Anime-specific, tag-based (máº·c Ä‘á»‹nh)
        - clip: General purpose, natural language
        - wd14: WD14 Tagger, anime-focused, newer
    
    Body params:
        - image (str): Base64 encoded image
        - deep_thinking (bool): More tags
        - models (list): ['deepdanbooru', 'clip', 'wd14'] - ChÃ¡Â»Ân models muÃ¡Â»â€˜n dÃƒÂ¹ng
    
    Returns:
        - tags: Merged tags with confidence voting
        - categories: Categorized tags
        - model_results: Stats tá»« tá»«ng model
    """
    try:
        import requests
        from collections import Counter
        
        data = request.json
        image_b64 = data.get('image', '')
        deep_thinking = data.get('deep_thinking', False)
        selected_models = data.get('models', ['deepdanbooru'])  # Máº·c Ä‘á»‹nh chá»‰ dÃ¹ng DeepDanbooru
        
        if not image_b64:
            return jsonify({'error': 'Image khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng'}), 400
        
        sd_api_url = os.getenv('COMFYUI_URL', 'http://127.0.0.1:8188')
        interrogate_url = f"{sd_api_url}/sdapi/v1/interrogate"
        
        logger.info(f"[MULTI-EXTRACT] Models: {[sanitize_for_log(m) for m in selected_models]} | Deep: {deep_thinking}")
        
        all_tags = []
        model_results = {}
        
        # GÃ¡Â»Âi tÃ¡Â»Â«ng model
        for model_name in selected_models:
            try:
                payload = {'image': image_b64, 'model': model_name}
                
                logger.info(f"[MULTI-EXTRACT] Calling {sanitize_for_log(model_name)}...")
                response = requests.post(interrogate_url, json=payload, timeout=120)
                
                if response.status_code == 200:
                    result = response.json()
                    caption = result.get('caption', '')
                    tags = [tag.strip() for tag in caption.split(',') if tag.strip()]
                    
                    model_results[model_name] = tags
                    all_tags.extend(tags)
                    
                    logger.info(f"[MULTI-EXTRACT] {sanitize_for_log(model_name)}: {len(tags)} tags Ã¢Å“â€¦")
                else:
                    logger.warning(f"[MULTI-EXTRACT] {sanitize_for_log(model_name)} failed: {response.status_code}")
                    model_results[model_name] = []
            except Exception as e:
                logger.error(f"[MULTI-EXTRACT] {sanitize_for_log(model_name)} error: {str(e)}")
                model_results[model_name] = []
        
        # Merge tags vÃ¡Â»â€ºi confidence voting (cÃƒÂ ng nhiÃ¡Â»Âu model Ã„â€˜Ã¡Â»â€œng ÃƒÂ½ = confidence cÃƒÂ ng cao)
        tag_counter = Counter(all_tags)
        num_models = len(selected_models)
        merged_tags = []
        
        for tag, vote_count in tag_counter.most_common():
            # Confidence = (sá»‘ model Ä‘á»“ng Ã½ / tá»•ng model) * 0.95
            confidence = (vote_count / num_models) * 0.95
            
            merged_tags.append({
                'name': tag,
                'confidence': round(confidence, 2),
                'votes': vote_count,
                'sources': [m for m, tags in model_results.items() if tag in tags]
            })
        
        # Giá»›i háº¡n sá»‘ tag
        max_tags = 50 if deep_thinking else 30
        merged_tags = merged_tags[:max_tags]
        
        # Categorize (giá»‘ng single model)
        CATEGORY_KEYWORDS = {
            'hair': ['hair', 'ahoge', 'bangs', 'braid', 'ponytail', 'twintails', 'bun', 'hairband', 'hairclip', 'hair_ornament', 'hair_ribbon', 'hair_bow'],
            'eyes': ['eyes', 'eye', 'eyelashes', 'eyebrows', 'eyepatch', 'heterochromia', 'pupils'],
            'mouth': ['mouth', 'lips', 'smile', 'smirk', 'frown', 'teeth', 'tongue', 'open_mouth', 'closed_mouth'],
            'face': ['face', 'facial', 'cheeks', 'nose', 'chin', 'forehead', 'blush', 'freckles', 'mole', 'scar', 'makeup'],
            'accessories': ['glasses', 'earrings', 'necklace', 'choker', 'hat', 'bow', 'ribbon', 'jewelry', 'crown', 'tiara', 'mask', 'piercing'],
            'clothing': ['dress', 'shirt', 'skirt', 'uniform', 'jacket', 'coat', 'tie', 'collar', 'sleeve'],
            'body': ['breasts', 'chest', 'shoulders', 'arms', 'hands', 'fingers', 'legs', 'thighs', 'feet'],
            'pose': ['standing', 'sitting', 'lying', 'looking_at_viewer', 'from_side', 'from_behind', 'arms_up', 'hand_on_hip'],
            'background': ['background', 'outdoors', 'indoors', 'sky', 'clouds', 'tree', 'flower', 'water', 'room'],
            'style': ['anime', 'realistic', 'masterpiece', 'best_quality', 'high_resolution', 'detailed', 'beautiful']
        }
        
        def categorize_tag(tag_name):
            tag_lower = tag_name.lower().replace(' ', '_')
            for category, keywords in CATEGORY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in tag_lower:
                        return category
            return 'other'
        
        categories_dict = {
            'hair': [], 'eyes': [], 'mouth': [], 'face': [], 'accessories': [],
            'clothing': [], 'body': [], 'pose': [], 'background': [], 'style': [], 'other': []
        }
        
        for tag_obj in merged_tags:
            category = categorize_tag(tag_obj['name'])
            tag_obj['category'] = category
            categories_dict[category].append(tag_obj)
        
        logger.info(f"[MULTI-EXTRACT] Ã¢Å“â€¦ Final: {len(merged_tags)} tags from {num_models} models")
        
        return jsonify({
            'success': True,
            'tags': merged_tags,
            'categories': categories_dict,
            'model_results': {k: len(v) for k, v in model_results.items()},
            'models_used': selected_models,
            'extraction_mode': 'multi-model'
        })
        
    except Exception as e:
        import traceback
        error_msg = f"Exception: {str(e)}\nTraceback: {traceback.format_exc()}"
        logger.error(f"[MULTI-EXTRACT] ERROR: {error_msg}")
        return jsonify({'error': error_msg}), 500


@app.route('/api/extract-anime-features', methods=['POST'])
@app.route('/sd-api/interrogate', methods=['POST'])  # Alias for frontend compatibility
def extract_anime_features():
    """
    Extract anime features from image using OpenAI Vision API (GPT-4o)
    Falls back to manual categorization if OpenAI fails
    
    Body params:
        - image (str): Base64 encoded image (without data:image prefix)
        - deep_thinking (bool): Deep thinking mode (more detailed extraction)
    
    Returns:
        - tags (list): List of {name, confidence, category} objects
        - categories (dict): Tags grouped by category for filtering
    """
    try:
        import requests
        import openai
        
        data = request.json
        image_b64 = data.get('image', '')
        deep_thinking = data.get('deep_thinking', False)
        
        if not image_b64:
            return jsonify({'error': 'Image is required'}), 400
        
        # Category mappings for filtering
        CATEGORY_KEYWORDS = {
            'hair': ['hair', 'ahoge', 'bangs', 'braid', 'ponytail', 'twintails', 'bun', 'hairband', 'hairclip', 'hair_ornament', 'hair_ribbon', 'hair_bow', 'blonde', 'brown_hair', 'black_hair', 'white_hair', 'pink_hair', 'blue_hair', 'red_hair', 'silver_hair', 'long_hair', 'short_hair', 'medium_hair'],
            'eyes': ['eyes', 'eye', 'eyelashes', 'eyebrows', 'eyepatch', 'heterochromia', 'pupils', 'blue_eyes', 'red_eyes', 'green_eyes', 'brown_eyes', 'golden_eyes', 'purple_eyes', 'closed_eyes'],
            'mouth': ['mouth', 'lips', 'smile', 'smirk', 'frown', 'teeth', 'tongue', 'open_mouth', 'closed_mouth', 'grin'],
            'face': ['face', 'facial', 'cheeks', 'nose', 'chin', 'forehead', 'blush', 'freckles', 'mole', 'scar', 'makeup', 'expression'],
            'accessories': ['glasses', 'earrings', 'necklace', 'choker', 'hat', 'bow', 'ribbon', 'jewelry', 'crown', 'tiara', 'mask', 'piercing', 'headphones', 'headband'],
            'clothing': ['dress', 'shirt', 'skirt', 'uniform', 'jacket', 'coat', 'tie', 'collar', 'sleeve', 'kimono', 'school_uniform', 'maid', 'armor', 'cape', 'hoodie', 'sweater'],
            'body': ['breasts', 'chest', 'shoulders', 'arms', 'hands', 'fingers', 'legs', 'thighs', 'feet', 'slim', 'petite'],
            'pose': ['standing', 'sitting', 'lying', 'looking_at_viewer', 'from_side', 'from_behind', 'arms_up', 'hand_on_hip', 'walking', 'running', 'dancing'],
            'background': ['background', 'outdoors', 'indoors', 'sky', 'clouds', 'tree', 'flower', 'water', 'room', 'night', 'sunset', 'city', 'forest', 'beach', 'snow'],
            'style': ['anime', 'realistic', 'masterpiece', 'best_quality', 'high_resolution', 'detailed', 'beautiful', 'illustration', 'digital_art', '1girl', '1boy', 'solo']
        }
        
        def categorize_tag(tag_name):
            """Categorize tag into appropriate category"""
            tag_lower = tag_name.lower().replace(' ', '_')
            
            for category, keywords in CATEGORY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in tag_lower:
                        return category
            
            return 'other'
        
        tags = []
        categories_dict = {
            'hair': [], 'eyes': [], 'mouth': [], 'face': [],
            'accessories': [], 'clothing': [], 'body': [],
            'pose': [], 'background': [], 'style': [], 'other': []
        }
        raw_caption = ""
        
        # Try OpenAI Vision API first
        if OPENAI_API_KEY:
            try:
                client = openai.OpenAI(api_key=OPENAI_API_KEY)
                
                detail_level = "high" if deep_thinking else "low"
                max_tags = 50 if deep_thinking else 30
                
                vision_prompt = f'''Analyze this anime/illustration image and extract descriptive tags for image generation.
Return ONLY a comma-separated list of tags in the following format. Include {max_tags} tags covering:
- Character appearance (hair color, eye color, expression)
- Clothing and accessories
- Pose and action
- Background and setting
- Art style descriptors (masterpiece, best quality, etc.)

Example output format:
1girl, long blonde hair, blue eyes, smile, school uniform, standing, looking at viewer, cherry blossoms, outdoors, masterpiece, best quality

Return ONLY the comma-separated tags, nothing else.'''
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": vision_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_b64}", "detail": detail_level}
                            }
                        ]
                    }],
                    max_tokens=500,
                    temperature=0.3
                )
                
                raw_caption = response.choices[0].message.content.strip()
                logger.info(f"[EXTRACT] OpenAI Vision extracted: {raw_caption[:100]}...")
                
            except Exception as e:
                logger.warning(f"[EXTRACT] OpenAI Vision failed: {e}, using fallback")
                raw_caption = "1girl, anime, illustration, beautiful, detailed, masterpiece, best quality"
        else:
            logger.warning("[EXTRACT] No OpenAI API key, using default tags")
            raw_caption = "1girl, anime, illustration, beautiful, detailed, masterpiece, best quality"
        
        # Parse caption into tags with confidence
        raw_tags = [tag.strip() for tag in raw_caption.split(',') if tag.strip()]
        max_tags = 50 if deep_thinking else 30
        
        for i, tag_name in enumerate(raw_tags[:max_tags]):
            # Fake confidence: decreases from 0.95 to 0.30
            confidence = 0.95 - (i / max_tags) * 0.65
            category = categorize_tag(tag_name)
            
            tag_obj = {
                'name': tag_name,
                'confidence': round(confidence, 2),
                'category': category
            }
            
            tags.append(tag_obj)
            categories_dict[category].append(tag_obj)
        
        logger.info(f"[EXTRACT] Extracted {len(tags)} tags across {len([c for c in categories_dict.values() if c])} categories")
        
        return jsonify({
            'success': True,
            'tags': tags,
            'categories': categories_dict,
            'raw_caption': raw_caption
        })
        
    except Exception as e:
        import traceback
        error_msg = f"Exception: {str(e)}\nTraceback: {traceback.format_exc()}"
        logger.error(f"[EXTRACT] {error_msg}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/img2img-advanced', methods=['POST'])
def img2img_advanced():
    """
    Táº¡o áº£nh nÃ¢ng cao tá»« áº£nh gá»‘c vá»›i feature extraction
    
    Body params:
        - source_image (str): Base64 encoded source image
        - extracted_tags (list): List of tag names from DeepDanbooru
        - user_prompt (str): User's additional prompt (20% weight)
        - feature_weight (float): Weight for extracted features (0.0-1.0, default: 0.8)
        - negative_prompt (str): Negative prompt
        - denoising_strength (float): Denoising strength (default: 0.6)
        - steps (int): Steps (default: 30)
        - cfg_scale (float): CFG scale (default: 7.0)
        - model (str): Model checkpoint name
    
    Returns:
        - image (str): Base64 encoded generated image
        - info (str): Generation info
    """
    try:
        from src.utils.comfyui_client import ComfyUIClient
        
        data = request.json
        source_image = data.get('source_image', '')
        extracted_tags = data.get('extracted_tags', [])
        user_prompt = data.get('user_prompt', '').strip()
        feature_weight = float(data.get('feature_weight', 0.8))
        
        if not source_image:
            return jsonify({'error': 'Source image khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng'}), 400
        
        if not extracted_tags:
            return jsonify({'error': 'ChÆ°a trÃ­ch xuáº¥t Ä‘áº·c trÆ°ng. Vui lÃ²ng nháº¥n nÃºt trÃ­ch xuáº¥t trÆ°á»›c!'}), 400
        
        # Mix prompts: features (80%) + user prompt (20%)
        # Convert tags list to comma-separated string
        features_prompt = ', '.join(extracted_tags)
        
        if user_prompt:
            # Boost user prompt with emphasis syntax
            user_weight_boost = int((1 - feature_weight) * 10)  # 0.2 -> boost of 2
            if user_weight_boost > 1:
                boosted_user_prompt = f"({user_prompt}:{1 + user_weight_boost * 0.1})"
            else:
                boosted_user_prompt = user_prompt
            
            final_prompt = f"{features_prompt}, {boosted_user_prompt}"
        else:
            final_prompt = features_prompt
        
        logger.info(f"[IMG2IMG-ADVANCED] Features: {len(extracted_tags)} tags")
        logger.info(f"[IMG2IMG-ADVANCED] User prompt: '{user_prompt}'")
        logger.info(f"[IMG2IMG-ADVANCED] Final prompt (first 200 chars): {final_prompt[:200]}...")
        
        # Prepare img2img parameters
        params = {
            'init_images': [source_image],
            'prompt': final_prompt,
            'negative_prompt': data.get('negative_prompt', 'bad quality, blurry, distorted'),
            'denoising_strength': float(data.get('denoising_strength') or 0.6),
            'width': int(data.get('width') or 768),
            'height': int(data.get('height') or 768),
            'steps': int(data.get('steps') or 30),
            'cfg_scale': float(data.get('cfg_scale') or 7.0),
            'sampler_name': data.get('sampler_name') or 'euler',
            'seed': int(data.get('seed') or -1),
            'restore_faces': data.get('restore_faces', False),
            'lora_models': data.get('lora_models', []),
            'vae': data.get('vae', None)
        }
        
        # Get SD client
        sd_api_url = os.getenv('COMFYUI_URL', 'http://127.0.0.1:8188')
        from src.utils.comfyui_client import get_comfyui_client
        sd_client = get_comfyui_client(sd_api_url)
        
        # Change model if specified
        model_name = data.get('model')
        if model_name:
            logger.info(f"[IMG2IMG-ADVANCED] Switching to model: {model_name}")
            try:
                sd_client.change_model(model_name)
            except Exception as e:
                logger.warning(f"[IMG2IMG-ADVANCED] Failed to change model: {e}")
        
        # Generate image
        logger.info(f"[IMG2IMG-ADVANCED] Calling img2img with denoising_strength={params['denoising_strength']}")
        result = sd_client.img2img(**params)
        logger.info(f"[IMG2IMG-ADVANCED] Generation complete")
        
        # Check for errors
        if 'error' in result:
            logger.error(f"[IMG2IMG-ADVANCED] SD Error: {result['error']}")
            return jsonify(result), 500
        
        # Return result
        images = result.get('images', [])
        if not images:
            return jsonify({'error': 'KhÃ´ng cÃ³ áº£nh Ä‘Æ°á»£c táº¡o'}), 500
        
        return jsonify({
            'success': True,
            'image': images[0],  # Return first image
            'info': result.get('info', ''),
            'parameters': result.get('parameters', {}),
            'final_prompt': final_prompt
        })
        
    except Exception as e:
        import traceback
        error_msg = f"Exception: {str(e)}\nTraceback: {traceback.format_exc()}"
        logger.error(f"[IMG2IMG-ADVANCED] {error_msg}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/local-models-status', methods=['GET'])
def local_models_status():
    """Check which local models are available and loaded"""
    try:
        if not LOCALMODELS_AVAILABLE:
            return jsonify({
                'available': False,
                'error': 'Local models not available. Install: pip install torch transformers accelerate'
            })
        
        status = model_loader.get_available_models()
        
        return jsonify({
            'available': True,
            'models': status
        })
        
    except Exception as e:
        logger.error(f"[Local Model Status] Error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve local model status'}), 500


@app.route('/api/unload-model', methods=['POST'])
def unload_model():
    """Unload a local model to free memory"""
    try:
        if not LOCALMODELS_AVAILABLE:
            return jsonify({'error': 'Local models not available'}), 400
        
        data = request.json
        model_key = data.get('model_key')
        
        if not model_key:
            return jsonify({'error': 'model_key required'}), 400
        
        model_loader.unload_model(model_key)
        
        return jsonify({
            'success': True,
            'message': f'Model {model_key} unloaded'
        })
        
    except Exception as e:
        logger.error(f"[Unload Model] Error: {str(e)}")
        return jsonify({'error': 'Failed to unload model'}), 500


# ============================================================================
# AI MEMORY / LEARNING ROUTES
# ============================================================================

@app.route('/api/memory/save', methods=['POST'])
def save_memory():
    """Save a conversation as a learning memory with images"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Invalid JSON data or missing Content-Type header'}), 400
        
        title = data.get('title', '')
        content = data.get('content', '')
        tags = data.get('tags', [])
        images = data.get('images', [])  # Array of {url: str, base64: str}
        
        if not title or not content:
            return jsonify({'error': 'Title and content are required'}), 400
        
        # Create memory object
        memory_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Sanitize title for folder name
        safe_title = title[:30].replace('/', '-').replace('\\', '-')
        folder_name = f"{safe_title}_{timestamp}"
        
        # Create memory folder structure
        memory_folder = MEMORY_DIR / folder_name
        memory_folder.mkdir(parents=True, exist_ok=True)
        
        image_folder = memory_folder / 'image_gen'
        image_folder.mkdir(parents=True, exist_ok=True)
        
        # Save images
        saved_images = []
        for idx, img_data in enumerate(images):
            try:
                # Get image source (URL or base64)
                img_url = img_data.get('url', '')
                img_base64 = img_data.get('base64', '')
                
                if img_url and img_url.startswith('/storage/images/'):
                    # Copy from existing storage
                    source_filename = img_url.split('/')[-1]
                    source_path = IMAGE_STORAGE_DIR / source_filename
                    
                    if source_path.exists():
                        dest_filename = f"image_{idx + 1}_{source_filename}"
                        dest_path = image_folder / dest_filename
                        
                        import shutil
                        shutil.copy2(source_path, dest_path)
                        saved_images.append(dest_filename)
                        
                        # Copy metadata if exists
                        meta_source = source_path.with_suffix('.json')
                        if meta_source.exists():
                            meta_dest = dest_path.with_suffix('.json')
                            shutil.copy2(meta_source, meta_dest)
                            
                elif img_base64:
                    # Save base64 image
                    if ',' in img_base64:
                        img_base64 = img_base64.split(',')[1]
                    
                    image_bytes = base64.b64decode(img_base64)
                    dest_filename = f"image_{idx + 1}.png"
                    dest_path = image_folder / dest_filename
                    
                    with open(dest_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    saved_images.append(dest_filename)
                    
            except Exception as img_error:
                logger.error(f"Error saving image {idx}: {img_error}")
        
        # Create memory object
        memory = {
            'id': memory_id,
            'folder_name': folder_name,
            'title': title,
            'content': content,
            'tags': tags,
            'images': saved_images,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Save to JSON file
        memory_file = memory_folder / 'memory.json'
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'memory': memory,
            'message': f'Saved with {len(saved_images)} images'
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Error saving memory: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/memory/list', methods=['GET'])
def list_memories():
    """List all saved memories (supports both old and new format)"""
    try:
        memories = []
        
        # Check for old format (direct .json files)
        for memory_file in MEMORY_DIR.glob('*.json'):
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
                    memories.append(memory)
            except Exception as e:
                logger.error(f"Error loading memory {memory_file}: {e}")
        
        # Check for new format (folders with memory.json)
        for memory_folder in MEMORY_DIR.iterdir():
            if memory_folder.is_dir():
                memory_file = memory_folder / 'memory.json'
                if memory_file.exists():
                    try:
                        with open(memory_file, 'r', encoding='utf-8') as f:
                            memory = json.load(f)
                            memories.append(memory)
                    except Exception as e:
                        logger.error(f"Error loading memory {memory_file}: {e}")
        
        # Sort by created_at descending
        memories.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            'memories': memories
        })
        
    except Exception as e:
        logger.error(f"[Memory List] Error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve memories'}), 500


@app.route('/api/memory/get/<memory_id>', methods=['GET'])
def get_memory(memory_id):
    """Get a specific memory by ID"""
    try:
        memory_file = MEMORY_DIR / f"{memory_id}.json"
        
        if not memory_file.exists():
            return jsonify({'error': 'Memory not found'}), 404
        
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)
        
        return jsonify({
            'memory': memory
        })
        
    except Exception as e:
        logger.error(f"[Get Memory] Error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve memory'}), 500


@app.route('/api/memory/delete/<memory_id>', methods=['DELETE'])
def delete_memory(memory_id):
    """Delete a memory (supports both old and new format)"""
    try:
        logger.info(f"[DELETE] Attempting to delete memory ID: {memory_id}")
        
        # List all available memories first for debugging
        all_memories = []
        for mf in MEMORY_DIR.iterdir():
            if mf.is_dir():
                mjson = mf / 'memory.json'
                if mjson.exists():
                    try:
                        with open(mjson, 'r', encoding='utf-8') as f:
                            m = json.load(f)
                            all_memories.append(f"{m.get('id')} ({mf.name})")
                    except:
                        pass
        logger.info(f"[DELETE] Available memory IDs: {all_memories}")
        
        # Try old format first (direct .json file)
        memory_file = MEMORY_DIR / f"{memory_id}.json"
        if memory_file.exists():
            logger.info(f"Found old format memory: {memory_file}")
            memory_file.unlink()
            return jsonify({
                'success': True,
                'message': 'Memory deleted (old format)'
            })
        
        # Try new format (folder with memory.json)
        deleted = False
        for memory_folder in MEMORY_DIR.iterdir():
            if memory_folder.is_dir():
                memory_json = memory_folder / 'memory.json'
                if memory_json.exists():
                    try:
                        with open(memory_json, 'r', encoding='utf-8') as f:
                            memory = json.load(f)
                            logger.info(f"Checking folder {memory_folder.name}, ID: {memory.get('id')}")
                            
                            if memory.get('id') == memory_id:
                                # Delete entire folder
                                logger.info(f"Deleting folder: {memory_folder}")
                                shutil.rmtree(memory_folder)
                                deleted = True
                                return jsonify({
                                    'success': True,
                                    'message': 'Memory deleted (new format)'
                                })
                    except Exception as e:
                        logger.error(f"Error reading memory {memory_json}: {e}")
        
        if not deleted:
            logger.warning(f"Memory not found: {memory_id}")
            logger.info(f"Available folders: {[f.name for f in MEMORY_DIR.iterdir() if f.is_dir()]}")
            return jsonify({'error': f'Memory not found: {memory_id}'}), 404
        
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/memory/update/<memory_id>', methods=['PUT'])
def update_memory(memory_id):
    """Update a memory"""
    try:
        memory_file = MEMORY_DIR / f"{memory_id}.json"
        
        if not memory_file.exists():
            return jsonify({'error': 'Memory not found'}), 404
        
        # Load existing memory
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)
        
        # Update fields
        data = request.json
        if 'title' in data:
            memory['title'] = data['title']
        if 'content' in data:
            memory['content'] = data['content']
        if 'tags' in data:
            memory['tags'] = data['tags']
        
        memory['updated_at'] = datetime.now().isoformat()
        
        # Save
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'memory': memory
        })
        
    except Exception as e:
        logger.error(f"[Add Memory] Error: {str(e)}")
        return jsonify({'error': 'Failed to add memory'}), 500


# ============================================================================
# IMAGE STORAGE ROUTES
# ============================================================================

@app.route('/api/save-image', methods=['POST'])
def save_image():
    """Save generated image to disk and return URL"""
    try:
        data = request.json
        image_base64 = data.get('image')
        metadata = data.get('metadata', {})
        
        if not image_base64:
            return jsonify({'error': 'No image data provided'}), 400
        
        # Remove data URL prefix if present
        if 'base64,' in image_base64:
            image_base64 = image_base64.split('base64,')[1]
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"generated_{timestamp}.png"
        filepath = IMAGE_STORAGE_DIR / filename
        
        # Decode and save image
        image_data = base64.b64decode(image_base64)
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        # Get gallery session ID for privacy filtering
        gallery_session_id = session.get('gallery_session_id')
        if not gallery_session_id:
            import uuid as uuid_module
            gallery_session_id = str(uuid_module.uuid4())
            session['gallery_session_id'] = gallery_session_id
        
        # Save metadata with session_id for privacy
        metadata_file = IMAGE_STORAGE_DIR / f"generated_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'filename': filename,
                'created_at': datetime.now().isoformat(),
                'session_id': gallery_session_id,  # For privacy filtering
                'metadata': metadata
            }, f, ensure_ascii=False, indent=2)
        
        # Return URL path
        image_url = f"/storage/images/{filename}"
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': image_url,
            'path': str(filepath)
        })
        
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/storage/images/<filename>')
def serve_image(filename):
    """Serve saved images"""
    try:
        # Validate filename to prevent path traversal attacks
        # Reject any value containing path separators or traversal patterns
        if '/' in filename or '\\' in filename or '..' in filename or '\0' in filename:
            logger.warning("Path traversal attempt detected")
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Additional validation: only allow alphanumeric, underscore, dash, and dot
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
            logger.warning("Invalid filename format detected")
            return jsonify({'error': 'Invalid filename format'}), 400
        
        # Resolve the allowed directory first (before using user input)
        allowed_dir = IMAGE_STORAGE_DIR.resolve()
        
        # After validation, reconstruct path using only the base directory
        # This breaks the taint flow from user input
        validated_filename = filename  # At this point, filename is validated
        
        # Build path by reconstructing from allowed_dir and validated components
        file_path = Path(str(allowed_dir)) / validated_filename
        
        # Resolve to absolute path
        try:
            resolved_file_path = file_path.resolve()
        except (ValueError, OSError):
            logger.warning("Path resolution failed")
            return jsonify({'error': 'Invalid file path'}), 400
        
        # Verify the resolved path is within the allowed directory
        try:
            resolved_file_path.relative_to(allowed_dir)
        except ValueError:
            logger.warning("Path outside allowed directory detected")
            return jsonify({'error': 'Access denied'}), 403
        
        # Check if file exists
        if not resolved_file_path.exists():
            return jsonify({'error': 'Image not found'}), 404
        
        # Check if it's a file (not a directory)
        if not resolved_file_path.is_file():
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Serve the file
        return send_file(str(resolved_file_path), mimetype='image/png')
        
    except Exception as e:
        logger.error(f"[Get Image] Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to retrieve image'}), 500


@app.route('/api/list-images', methods=['GET'])
def list_images():
    """List all saved images"""
    try:
        images = []
        
        for img_file in IMAGE_STORAGE_DIR.glob('generated_*.png'):
            # Try to load metadata
            metadata_file = img_file.with_suffix('.json')
            metadata = {}
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading metadata for {img_file}: {e}")
            
            images.append({
                'filename': img_file.name,
                'url': f"/storage/images/{img_file.name}",
                'created_at': metadata.get('created_at', ''),
                'metadata': metadata.get('metadata', {})
            })
        
        # Sort by created_at descending
        images.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            'images': images,
            'count': len(images)
        })
        
    except Exception as e:
        logger.error(f"[List Images] Error: {str(e)}")
        return jsonify({'error': 'Failed to list images'}), 500


@app.route('/api/delete-image/<filename>', methods=['DELETE'])
def delete_image(filename):
    """Delete saved image"""
    try:
        filepath = IMAGE_STORAGE_DIR / filename
        metadata_file = filepath.with_suffix('.json')
        
        if not filepath.exists():
            return jsonify({'error': 'Image not found'}), 404
        
        # Delete image and metadata
        filepath.unlink()
        if metadata_file.exists():
            metadata_file.unlink()
        
        return jsonify({
            'success': True,
            'message': 'Image deleted'
        })
        
    except Exception as e:
        logger.error(f"[Delete Image] Error: {str(e)}")
        return jsonify({'error': 'Failed to delete image'}), 500


# ============================================================================
# MCP INTEGRATION ROUTES
# ============================================================================

from src.utils.mcp_integration import get_mcp_client, inject_code_context

# Global MCP client
mcp_client = get_mcp_client()

@app.route('/api/mcp/enable', methods=['POST'])
def mcp_enable():
    """Enable MCP integration"""
    try:
        success = mcp_client.enable()
        return jsonify({
            'success': success,
            'status': mcp_client.get_status()
        })
    except Exception as e:
        logger.error(f"MCP enable error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to enable MCP integration'
        }), 500


@app.route('/api/mcp/disable', methods=['POST'])
def mcp_disable():
    """Disable MCP integration"""
    try:
        mcp_client.disable()
        return jsonify({
            'success': True,
            'status': mcp_client.get_status()
        })
    except Exception as e:
        logger.error(f"MCP disable error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to disable MCP integration'
        }), 500


@app.route('/api/mcp/add-folder', methods=['POST'])
def mcp_add_folder():
    """Add folder to MCP access list"""
    try:
        data = request.get_json()
        folder_path = data.get('folder_path')
        
        if not folder_path:
            return jsonify({
                'success': False,
                'error': 'Folder path is required'
            }), 400
        
        success = mcp_client.add_folder(folder_path)
        
        return jsonify({
            'success': success,
            'status': mcp_client.get_status()
        })
    except Exception as e:
        logger.error(f"MCP add folder error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to add folder'
        }), 500


@app.route('/api/mcp/remove-folder', methods=['POST'])
def mcp_remove_folder():
    """Remove folder from MCP access list"""
    try:
        data = request.get_json()
        folder_path = data.get('folder_path')
        
        if not folder_path:
            return jsonify({
                'success': False,
                'error': 'Folder path is required'
            }), 400
        
        mcp_client.remove_folder(folder_path)
        
        return jsonify({
            'success': True,
            'status': mcp_client.get_status()
        })
    except Exception as e:
        logger.error(f"MCP remove folder error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to remove folder'
        }), 500


@app.route('/api/mcp/list-files', methods=['GET'])
def mcp_list_files():
    """List files in selected folders"""
    try:
        folder_path = request.args.get('folder')

        # Path traversal protection: resolve and validate against cwd
        if folder_path:
            resolved = os.path.realpath(folder_path)
            if not resolved.startswith(os.path.realpath(os.getcwd())):
                return jsonify({
                    'success': False,
                    'error': 'Invalid folder path'
                }), 400
            folder_path = resolved

        files = mcp_client.list_files_in_folder(folder_path)
        
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        logger.error(f"MCP list files error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to list files'
        }), 500


@app.route('/api/mcp/search-files', methods=['GET'])
def mcp_search_files():
    """Search files in selected folders"""
    try:
        query = request.args.get('query', '')
        file_type = request.args.get('type', 'all')
        
        files = mcp_client.search_files(query, file_type)
        
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        logger.error(f"MCP search files error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to search files'
        }), 500


@app.route('/api/mcp/read-file', methods=['GET'])
def mcp_read_file():
    """Read file content"""
    try:
        file_path = request.args.get('path')
        max_lines = int(request.args.get('max_lines', 500))
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'File path is required'
            }), 400

        # Path traversal protection: resolve and validate against cwd
        resolved = os.path.realpath(file_path)
        if not resolved.startswith(os.path.realpath(os.getcwd())):
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            }), 400

        content = mcp_client.read_file(resolved, max_lines)
        
        if content and 'error' in content:
            return jsonify({
                'success': False,
                'error': content['error']
            }), 400
        
        return jsonify({
            'success': True,
            'content': content
        })
    except Exception as e:
        logger.error(f"MCP read file error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to read file'
        }), 500


@app.route('/api/mcp/ocr-extract', methods=['POST'])
def mcp_ocr_extract():
    """Extract text from image/document file via OCR through MCP client."""
    try:
        data = request.get_json() or {}
        file_path = (data.get('path') or '').strip()
        max_chars = int(data.get('max_chars', 6000))

        if not file_path:
            return jsonify({
                'success': False,
                'error': 'File path is required'
            }), 400

        result = mcp_client.extract_file_with_ocr(
            file_path=file_path,
            max_chars=max(500, min(max_chars, 50000))
        )

        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid max_chars'
        }), 400
    except Exception as e:
        logger.error(f"MCP OCR extract error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to extract OCR text'
        }), 500


@app.route('/api/mcp/grep', methods=['GET'])
def mcp_grep():
    """Search file content by pattern (grep)."""
    try:
        pattern = request.args.get('pattern', '')
        file_type = request.args.get('type', 'all')
        max_results = int(request.args.get('max_results', 30))
        case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
        regex = request.args.get('regex', 'false').lower() == 'true'

        if not pattern:
            return jsonify({
                'success': False,
                'error': 'Pattern is required'
            }), 400

        results = mcp_client.grep_content(
            pattern=pattern,
            file_type=file_type,
            max_results=max_results,
            case_sensitive=case_sensitive,
            regex=regex,
        )

        return jsonify({
            'success': True,
            'pattern': pattern,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        logger.error(f"MCP grep error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to grep files'
        }), 500


@app.route('/api/mcp/warm-cache', methods=['POST'])
def mcp_warm_cache():
    """Trigger memory cache warmup based on user question domain before chat."""
    try:
        data = request.get_json() or {}
        question = (data.get('question') or '').strip()
        domain = data.get('domain')
        extra_queries = data.get('extra_queries') if isinstance(data.get('extra_queries'), list) else None
        force_refresh = bool(data.get('force_refresh', False))
        cache_ttl_seconds = int(data.get('cache_ttl_seconds', 900))
        limit = int(data.get('limit', 20))
        min_importance = int(data.get('min_importance', 4))
        max_chars = int(data.get('max_chars', 12000))

        if not question:
            return jsonify({
                'success': False,
                'error': 'question is required'
            }), 400

        result = mcp_client.warm_memory_cache_by_question(
            question=question,
            domain=domain,
            extra_queries=extra_queries,
            force_refresh=force_refresh,
            cache_ttl_seconds=cache_ttl_seconds,
            limit=limit,
            min_importance=min_importance,
            max_chars=max_chars,
        )

        status = 200 if result.get('success') else 503
        return jsonify(result), status
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid numeric parameters'
        }), 400
    except Exception as e:
        logger.error(f"MCP warm cache error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to warm memory cache'
        }), 500


@app.route('/api/mcp/status', methods=['GET'])
def mcp_status():
    """Get MCP client status."""
    try:
        return jsonify({
            'success': True,
            'status': mcp_client.get_status()
        })
    except Exception as e:
        logger.error(f"MCP status error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get MCP status'
        }), 500


@app.route('/api/mcp/fetch-url', methods=['POST'])
def mcp_fetch_url():
    """Fetch and extract content from URL with advanced anti-bot bypass"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        import requests
        from bs4 import BeautifulSoup
        import mimetypes
        import random
        import time
        from urllib.parse import urlparse
        
        # Multiple User-Agent rotation for anti-bot bypass
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        ]
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Advanced headers to bypass bot detection
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Referer': f'https://www.google.com/search?q={domain}',
            'Origin': f'{parsed_url.scheme}://{domain}',
        }
        
        session = requests.Session()
        
        # Try with cookies from initial request
        response = None
        last_error = None
        
        for attempt in range(3):
            try:
                if attempt > 0:
                    time.sleep(1 + attempt)  # Backoff delay
                    headers['User-Agent'] = random.choice(user_agents)
                
                response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
                
                # Check for Cloudflare or bot protection pages
                if response.status_code == 403:
                    # Try with different referer
                    headers['Referer'] = url
                    response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
                
                if response.status_code == 403:
                    # Try without some headers that might trigger protection
                    simple_headers = {
                        'User-Agent': random.choice(user_agents),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                    }
                    response = session.get(url, headers=simple_headers, timeout=30, allow_redirects=True)
                
                if response.status_code == 403:
                    # Try with cloudscraper for Cloudflare bypass
                    try:
                        import cloudscraper
                        scraper = cloudscraper.create_scraper(
                            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
                            delay=5
                        )
                        response = scraper.get(url, timeout=30)
                        logger.info(f"[MCP] Cloudscraper used for {domain}")
                    except Exception as cs_error:
                        logger.warning(f"[MCP] Cloudscraper failed: {cs_error}")
                
                if response.status_code == 200:
                    break
                    
                response.raise_for_status()
                break
                
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt == 2:
                    raise
        
        if response is None:
            raise last_error or Exception("Failed to fetch URL after retries")
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '').lower()
        extracted_content = ""
        content_title = url
        
        # Check if it's an image
        if any(img_type in content_type for img_type in ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp']):
            # Use OCR to extract text from image
            try:
                from src.ocr_integration import ocr_client
                import base64
                image_b64 = base64.b64encode(response.content).decode('utf-8')
                extracted_content = ocr_client.extract_text_from_image(image_b64)
                content_title = f"Image: {url.split('/')[-1]}"
            except Exception as ocr_error:
                logger.warning(f"OCR failed for image URL: {ocr_error}")
                extracted_content = f"[Image content from: {url}]"
        
        # Check if it's a PDF
        elif 'application/pdf' in content_type:
            try:
                from src.ocr_integration import ocr_client
                import base64
                pdf_b64 = base64.b64encode(response.content).decode('utf-8')
                extracted_content = ocr_client.extract_text_from_pdf(pdf_b64)
                content_title = f"PDF: {url.split('/')[-1]}"
            except Exception as pdf_error:
                logger.warning(f"PDF extraction failed: {pdf_error}")
                extracted_content = f"[PDF content from: {url}]"
        
        # HTML content
        elif 'text/html' in content_type:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get title
            title_tag = soup.find('title')
            if title_tag:
                content_title = title_tag.get_text(strip=True)
            
            # Remove script, style, nav, footer elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
                element.decompose()
            
            # Try to find main content
            main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': ['content', 'main', 'post']})
            if main_content:
                extracted_content = main_content.get_text(separator='\n', strip=True)
            else:
                # Get body content
                body = soup.find('body')
                if body:
                    extracted_content = body.get_text(separator='\n', strip=True)
                else:
                    extracted_content = soup.get_text(separator='\n', strip=True)
            
            # Clean up content - remove excessive newlines
            import re
            extracted_content = re.sub(r'\n{3,}', '\n\n', extracted_content)
            extracted_content = extracted_content[:10000]  # Limit content length
        
        # Plain text or JSON
        elif 'text/' in content_type or 'application/json' in content_type:
            extracted_content = response.text[:10000]
            content_title = f"Text: {url.split('/')[-1]}"
        
        else:
            extracted_content = f"[Binary content from: {url}]"
        
        return jsonify({
            'success': True,
            'url': url,
            'title': content_title,
            'content': extracted_content,
            'content_type': content_type
        })
        
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Request timeout - URL took too long to respond'
        }), 408
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 0
        error_msg = str(e)
        
        # Provide helpful messages for common errors
        if status_code == 403:
            error_msg = f"403 Forbidden - Website blocked access. This may be due to bot protection (Cloudflare, etc.). Try a different URL or check if the website requires authentication."
        elif status_code == 401:
            error_msg = "401 Unauthorized - Website requires authentication"
        elif status_code == 404:
            error_msg = "404 Not Found - The page does not exist"
        elif status_code == 429:
            error_msg = "429 Too Many Requests - Rate limited. Please wait and try again."
        elif status_code == 503:
            error_msg = "503 Service Unavailable - Website is temporarily down"
            
        logger.error(f"URL fetch HTTP error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch URL: {error_msg}',
            'status_code': status_code
        }), 400
    except requests.exceptions.RequestException as e:
        logger.error(f"URL fetch error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch URL: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"MCP fetch URL error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to process URL content'
        }), 500


@app.route('/api/mcp/upload-file', methods=['POST'])
def mcp_upload_file():
    """Upload and extract content from file for MCP context"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        filename = file.filename
        content = file.read()
        
        # Determine file type and extract content
        extracted_content = ""
        mime_type = mimetypes.guess_type(filename)[0] or ''
        
        # Image files
        if mime_type.startswith('image/'):
            try:
                from src.ocr_integration import ocr_client
                import base64
                image_b64 = base64.b64encode(content).decode('utf-8')
                extracted_content = ocr_client.extract_text_from_image(image_b64)
            except Exception as e:
                logger.warning(f"OCR failed for uploaded image: {e}")
                extracted_content = f"[Image: {filename}]"
        
        # PDF files
        elif mime_type == 'application/pdf' or filename.lower().endswith('.pdf'):
            try:
                from src.ocr_integration import ocr_client
                import base64
                pdf_b64 = base64.b64encode(content).decode('utf-8')
                extracted_content = ocr_client.extract_text_from_pdf(pdf_b64)
            except Exception as e:
                logger.warning(f"PDF extraction failed: {e}")
                extracted_content = f"[PDF: {filename}]"
        
        # Text-based files
        elif mime_type and (mime_type.startswith('text/') or mime_type in ['application/json', 'application/javascript', 'application/xml']):
            try:
                extracted_content = content.decode('utf-8')[:10000]
            except:
                extracted_content = content.decode('latin-1')[:10000]
        
        # Code files without proper MIME type
        elif any(filename.lower().endswith(ext) for ext in ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.css', '.html', '.md', '.txt', '.json', '.yaml', '.yml', '.xml', '.sh', '.bat', '.sql']):
            try:
                extracted_content = content.decode('utf-8')[:10000]
            except:
                extracted_content = content.decode('latin-1')[:10000]
        
        else:
            extracted_content = f"[Binary file: {filename}]"
        
        return jsonify({
            'success': True,
            'filename': filename,
            'content': extracted_content,
            'mime_type': mime_type
        })
        
    except Exception as e:
        logger.error(f"MCP upload file error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to process uploaded file'
        }), 500


# Additional route for serving stored images
@app.route('/static/Storage/Image_Gen/<filename>')
def serve_storage_image(filename):
    """Serve images from Storage/Image_Gen folder"""
    storage_dir = CHATBOT_DIR / 'Storage' / 'Image_Gen'
    return send_from_directory(storage_dir, filename)



# -- Extract text from uploaded file (base64) via OCR/parsing --
@app.route('/api/extract-file-text', methods=['POST'])
def app_extract_file_text():
    import base64 as _b64
    data = request.get_json(silent=True) or {}
    file_b64 = data.get('file_b64', '')
    filename = str(data.get('filename', 'file')).strip()
    if not file_b64 or not filename:
        return jsonify({'success': False, 'error': 'file_b64 and filename required'}), 400
    if ',' in file_b64:
        file_b64 = file_b64.split(',', 1)[1]
    try:
        file_data = _b64.b64decode(file_b64)
    except Exception as e:
        return jsonify({'success': False, 'error': f'Invalid base64: {e}'}), 400
    success, text = extract_file_content(file_data, filename)
    if success and text and text.strip():
        return jsonify({'success': True, 'text': text.strip(), 'filename': filename})
    return jsonify({'success': False, 'text': '', 'error': 'Could not extract text from file'})


# -- Auto-generate title via Ollama --
@app.route('/api/generate-title', methods=['POST'])
def app_generate_title():
    import requests as _req
    data = request.get_json(silent=True) or {}
    raw_message = data.get('message', '')
    if not isinstance(raw_message, str):
        raw_message = ''
    user_message = raw_message.strip()[:200]
    language = str(data.get('language', 'vi')).strip()
    if not user_message:
        return jsonify({'error': 'message is required'}), 400
    if language == 'en':
        prompt = (
            'Generate a concise 3-5 word English title for this conversation. '
            'Return ONLY the title text, no quotes, no explanation:\n'
            f'"{user_message}"'
        )
    else:
        prompt = (
            'Tao tieu de ngan gon 3-7 tu tieng Viet cho cuoc tro chuyen nay. '
            'Chi tra ve tieu de, khong giai thich, khong ngoac kep:\n'
            f'"{user_message}"'
        )
    try:
        resp = _req.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:0.5b',
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.7, 'num_predict': 20},
            },
            timeout=10,
        )
        resp.raise_for_status()
        title = resp.json().get('response', '').strip().replace('"', '').replace("'", '').strip()
        if title:
            return jsonify({'title': title})
    except Exception as e:
        logger.debug(f'[generate-title] Ollama unavailable: {e}')
    fallback = user_message[:40] + ('...' if len(user_message) > 40 else '')
    return jsonify({'title': fallback})


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return {'error': 'Not found'}, 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return {'error': 'Internal server error'}, 500


# Register blueprints from routes/
# main_bp skipped — routes (/, /chat, /clear, etc.) already on app directly

try:
    from routes.memory import memory_bp
    app.register_blueprint(memory_bp, url_prefix='/memory')
    logger.info("âœ… Registered memory blueprint")
except ImportError as e:
    logger.warning(f"âš ï¸ Could not register memory blueprint: {e}")

try:
    from routes.mcp import mcp_bp
    app.register_blueprint(mcp_bp, url_prefix='/api/mcp')
    logger.info("âœ… Registered MCP blueprint")
except ImportError as e:
    logger.warning(f"âš ï¸ Could not register MCP blueprint: {e}")

try:
    from routes.conversations import conversations_bp
    app.register_blueprint(conversations_bp)
    logger.info("âœ… Registered conversations blueprint")
except ImportError as e:
    logger.warning(f"âš ï¸ Could not register conversations blueprint: {e}")

try:
    from routes.images import images_bp
    app.register_blueprint(images_bp)
    logger.info("âœ… Registered images blueprint")
except ImportError as e:
    logger.warning(f"âš ï¸ Could not register images blueprint: {e}")

try:
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    logger.info("âœ… Registered auth blueprint")
except ImportError as e:
    logger.warning(f"âš ï¸ Could not register auth blueprint: {e}")

try:
    from routes.stable_diffusion import sd_bp
    app.register_blueprint(sd_bp)
    logger.info("âœ… Registered stable_diffusion blueprint")
except ImportError as e:
    logger.warning(f"âš ï¸ Could not register stable_diffusion blueprint: {e}")

try:
    from routes.image_gen import image_gen_bp
    app.register_blueprint(image_gen_bp)
    logger.info("âœ… Registered image_gen blueprint (multi-provider)")
except ImportError as e:
    logger.warning(f"âš ï¸ Could not register image_gen blueprint: {e}")

try:
    from routes.models import models_bp
    app.register_blueprint(models_bp)
    logger.info("âœ… Registered models blueprint (health/status)")
except ImportError as e:
    logger.warning(f"âš ï¸ Could not register models blueprint: {e}")

try:
    from routes.stream import stream_bp
    app.register_blueprint(stream_bp)
    logger.info("âœ… Registered stream blueprint (SSE)")
except ImportError as e:
    logger.warning(f"âš ï¸ Could not register stream blueprint: {e}")

try:
    from routes.async_routes import async_bp
    app.register_blueprint(async_bp)
    logger.info("âœ… Registered async blueprint (async chat)")
except ImportError as e:
    logger.warning(f"âš ï¸ Could not register async blueprint: {e}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# â•â•â• External API v1 â€” Stateless API for extensions/.exe â•â•â•
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

try:
    from routes.user_auth import user_auth_bp
    app.register_blueprint(user_auth_bp)
    logger.info("Registered user_auth blueprint")
except ImportError as e:
    logger.warning(f"Could not register user_auth blueprint: {e}")

try:
    from routes.admin import admin_bp
    app.register_blueprint(admin_bp)
    logger.info("Registered admin blueprint")
except ImportError as e:
    logger.warning(f"Could not register admin blueprint: {e}")

try:
    from routes.qr_payment import qr_bp
    app.register_blueprint(qr_bp)
    logger.info("Registered qr_payment blueprint")
except ImportError as e:
    logger.warning(f"Could not register qr_payment blueprint: {e}")

try:
    from core.user_auth import init_admin_users
    _seed_db = get_db()
    if _seed_db is not None:
        init_admin_users(_seed_db)
        logger.info("Admin users seeded successfully")
except Exception as e:
    logger.warning(f"Could not seed admin users: {e}")

EXTERNAL_API_KEY = os.getenv('EXTERNAL_API_KEY', 'ai-assistant-ext-key-2024')

def require_api_key(f):
    """Decorator to require X-API-Key header for external API"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key', '')
        if not api_key or api_key != EXTERNAL_API_KEY:
            return jsonify({'error': 'Invalid or missing API key', 'code': 'UNAUTHORIZED'}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/api/db-health', methods=['GET'])
def db_health():
    """Check liveness of all storage backends."""
    result = {}

    # ── MongoDB ──────────────────────────────────────────────────────────────
    try:
        db = get_db()
        if db is not None:
            db.client.admin.command('ping')
            n_logs = db.chat_logs.estimated_document_count()
            n_convs = db.conversations.estimated_document_count()
            n_msgs  = db.messages.estimated_document_count()
            result['mongodb'] = {
                'status': 'ok',
                'chat_logs': n_logs,
                'conversations': n_convs,
                'messages': n_msgs,
            }
        else:
            result['mongodb'] = {'status': 'disabled'}
    except Exception as e:
        result['mongodb'] = {'status': 'error', 'detail': 'connection failed'}

    # ── Firebase ─────────────────────────────────────────────────────────────
    try:
        import firebase_admin
        if firebase_admin._apps:
            # Quick Firestore ping
            from firebase_admin import firestore as _fs
            _fs.client().collection('_health').document('ping').set(
                {'ts': datetime.utcnow().isoformat()}, merge=True)
            result['firebase'] = {'status': 'ok', 'apps': list(firebase_admin._apps.keys())}
        else:
            result['firebase'] = {'status': 'not_initialized'}
    except Exception as e:
        result['firebase'] = {'status': 'error', 'detail': 'connection failed'}

    # ── ImgBB ────────────────────────────────────────────────────────────────
    imgbb_key = os.getenv('IMGBB_API_KEY', '')
    result['imgbb'] = {'status': 'key_present' if imgbb_key else 'no_key'}

    # ── Google Drive ─────────────────────────────────────────────────────────
    drive_creds = os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH', '') or os.getenv('GOOGLE_SERVICE_ACCOUNT_PATH', '')
    drive_ok = bool(drive_creds) and Path(drive_creds).exists()
    result['google_drive'] = {'status': 'creds_present' if drive_ok else 'no_creds',
                              'path': drive_creds if drive_ok else ''}

    # ── Local image storage ───────────────────────────────────────────────────
    storage_dir = Path(__file__).parent / 'Storage' / 'Image_Gen'
    total_imgs = sum(1 for _ in storage_dir.rglob('*.png')) if storage_dir.exists() else 0
    result['local_storage'] = {'status': 'ok', 'total_images': total_imgs,
                               'path': str(storage_dir)}

    overall = 'ok' if result.get('mongodb', {}).get('status') == 'ok' else 'degraded'
    return jsonify({'overall': overall, 'backends': result,
                    'checked_at': datetime.utcnow().isoformat() + 'Z'})


@app.route('/api/v1/chat', methods=['POST'])
@require_api_key
def external_chat():
    """
    Stateless chat endpoint for external apps (browser extension, .exe client).
    
    Headers:
        X-API-Key: <your-api-key>
    
    Body (JSON):
        {
            "message": "Hello",
            "model": "grok",              // optional
            "context": "casual",           // optional
            "history": [],                 // optional conversation history
            "page_context": "",            // optional â€” injected page text from extension
            "tools": ["image-generation"], // optional
            "language": "vi"               // optional
        }
    
    Returns: { "response": "...", "model": "...", "tokens": 0 }
    """
    try:
        data = request.get_json(force=True)
        if not data or not data.get('message'):
            return jsonify({'error': 'Missing "message" field'}), 400
        
        message = data['message']
        model = data.get('model', 'grok')
        context_type = data.get('context', 'casual')
        history = data.get('history', [])
        page_context = data.get('page_context', '')
        tools = data.get('tools', [])
        language = data.get('language', 'vi')
        
        # If page_context provided, prepend it to the message
        if page_context:
            message = f"[Page Context]\n{page_context[:8000]}\n\n[User Question]\n{message}"
        
        # Build minimal context for the AI
        conversation_history = []
        for h in history[-20:]:  # Last 20 messages max
            role = h.get('role', 'user')
            content = h.get('content', '')
            conversation_history.append({'role': role, 'content': content})
        
        conversation_history.append({'role': 'user', 'content': message})
        
        # Use the same AI routing logic as the main chat
        # Import the process function dynamically
        from core.ai_router import route_to_model
        
        response_text = route_to_model(
            message=message,
            model=model,
            context=context_type,
            history=conversation_history,
            language=language
        )
        
        return jsonify({
            'response': response_text,
            'model': model,
            'tokens': len(response_text.split()),
            'status': 'success'
        })
        
    except ImportError:
        # Fallback: use the chat endpoint logic directly
        logger.warning("[ExtAPI] ai_router not available, using fallback")
        return jsonify({
            'error': 'AI router not available. Use the main /chat endpoint instead.',
            'fallback_url': '/chat'
        }), 503
    except Exception as e:
        logger.error(f"[ExtAPI] Error: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/v1/context', methods=['POST'])
@require_api_key
def inject_context():
    """
    Inject page context into the AI's memory for the current session.
    Used by browser extension to send page content before asking questions.
    
    Body: { "url": "https://...", "title": "Page Title", "content": "page text...", "selection": "selected text" }
    """
    try:
        data = request.get_json(force=True)
        
        # Store in session for use in subsequent chat calls
        if 'ext_context' not in session:
            session['ext_context'] = []
        
        context_entry = {
            'url': data.get('url', ''),
            'title': data.get('title', ''),
            'content': (data.get('content', '') or data.get('selection', ''))[:10000],
            'timestamp': datetime.now().isoformat()
        }
        
        session['ext_context'].append(context_entry)
        # Keep only last 5 contexts
        session['ext_context'] = session['ext_context'][-5:]
        
        return jsonify({
            'status': 'success',
            'message': f'Context from "{context_entry["title"]}" stored',
            'contexts_count': len(session['ext_context'])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/providers', methods=['GET'])
@require_api_key
def list_providers():
    """List available AI models and image generation providers."""
    try:
        models = [
            {'id': 'grok', 'name': 'Grok-3', 'provider': 'xAI', 'tier': 'premium'},
            {'id': 'deepseek-reasoner', 'name': 'DeepSeek R1', 'provider': 'DeepSeek', 'tier': 'premium'},
            {'id': 'openai', 'name': 'GPT-4o-mini', 'provider': 'OpenAI', 'tier': 'standard'},
            {'id': 'deepseek', 'name': 'DeepSeek Chat', 'provider': 'DeepSeek', 'tier': 'standard'},
            {'id': 'gemini', 'name': 'Gemini 2.0 Flash', 'provider': 'Google', 'tier': 'free'},
            {'id': 'qwen', 'name': 'Qwen Turbo', 'provider': 'Alibaba', 'tier': 'other'},
        ]
        
        # Try to get image gen providers
        image_providers = []
        try:
            from core.image_gen.router import ImageGenerationRouter
            router = ImageGenerationRouter()
            for p in router.providers:
                image_providers.append({
                    'name': p.__class__.__name__,
                    'priority': getattr(p, 'priority', 0),
                    'available': getattr(p, 'available', True)
                })
        except:
            pass
        
        return jsonify({
            'chat_models': models,
            'image_providers': image_providers,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/health', methods=['GET'])
def external_health():
    """Public health check for external clients."""
    return jsonify({
        'status': 'online',
        'version': '2.0',
        'endpoints': ['/api/v1/chat', '/api/v1/context', '/api/v1/providers', '/api/v1/health']
    })


# Main entry point
if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG', '0') == '1'
    host = os.getenv('HOST', '0.0.0.0')  # Default to 0.0.0.0 for external access
    port = int(os.getenv('CHATBOT_PORT', '5000'))
    
    logger.info(f"ðŸš€ Starting ChatBot on {host}:{port} (debug={debug_mode})")
    app.run(debug=debug_mode, host=host, port=port)



