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
from dotenv import load_dotenv
from flask import Flask, send_from_directory, session, render_template, request, jsonify

# Load environment variables
load_dotenv()

# Import rate limiter and cache from root config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.rate_limiter import get_gemini_key_with_rate_limit, wait_for_openai_rate_limit, get_rate_limit_stats
from config.response_cache import get_cached_response, cache_response, get_all_cache_stats

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
sys.path.insert(0, str(CHATBOT_DIR))
sys.path.insert(0, str(ROOT_DIR))

# Create Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure static folder for Storage
app.static_folder = str(CHATBOT_DIR / 'static')

# Import and register extensions
from core.extensions import logger, register_monitor, LOCALMODELS_AVAILABLE, model_loader

# Register monitor for health checks
register_monitor(app)

# Initialize MongoDB connection
try:
    mongodb_client.connect()
    MONGODB_ENABLED = True
    logger.info("âœ… MongoDB connection established")
except Exception as e:
    MONGODB_ENABLED = False
    logger.warning(f"âš ï¸ MongoDB not available, using session storage: {e}")

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

# Google Search API
GOOGLE_SEARCH_API_KEY_1 = os.getenv('GOOGLE_SEARCH_API_KEY_1')
GOOGLE_SEARCH_API_KEY_2 = os.getenv('GOOGLE_SEARCH_API_KEY_2')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')

# GitHub API
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

# ⛔ GEMINI DISABLED - Quota exhausted, use GROK/DeepSeek/OpenAI instead
# Initialize Gemini client with new SDK (optional - fallback to None if no key)
gemini_client = None
# try:
#     if GEMINI_API_KEY:
#         gemini_client = genai.Client(api_key=GEMINI_API_KEY)
#         logger.info("✅ Gemini API initialized with primary key")
# except Exception as e:
#     logger.warning(f"⚠️ Primary Gemini key failed: {e}")
#     try:
#         if GEMINI_API_KEY_2:
#             gemini_client = genai.Client(api_key=GEMINI_API_KEY_2)
#             logger.info("✅ Gemini API initialized with backup key")
#     except Exception as e2:
#         logger.warning(f"⚠️ Backup Gemini key failed: {e2}")
#         logger.warning("⚠️ Gemini API not available - Chat functionality will be limited")
logger.warning("⚠️ Gemini API DISABLED to avoid quota errors")

# System prompts for different purposes (Vietnamese)
SYSTEM_PROMPTS_VI = {
    'psychological': """Bạn là một trợ lý tâm lý chuyên nghiệp, thân thiện và đầy empathy. 
    Báº¡n luÃ´n láº¯ng nghe, tháº¥u hiá»ƒu vÃ  Ä‘Æ°a ra lá»i khuyÃªn chÃ¢n thÃ nh, tÃ­ch cá»±c.
    Báº¡n khÃ´ng phÃ¡n xÃ©t vÃ  luÃ´n há»— trá»£ ngÆ°á»i dÃ¹ng vÆ°á»£t qua khÃ³ khÄƒn trong cuá»™c sá»‘ng.
    HÃ£y tráº£ lá»i báº±ng tiáº¿ng Viá»‡t.
    
    MARKDOWN FORMATTING:
    - Sử dụng ```language để wrap code blocks (ví dụ: ```python, ```javascript)
    - ÄÃ³ng code block báº±ng ``` trÃªn dÃ²ng riÃªng
    - Dùng `code` cho inline code
    - Sử dụng **bold**, *italic*, > quote khi cần""",
    
    'lifestyle': """Báº¡n lÃ  má»™t chuyÃªn gia tÆ° váº¥n lá»‘i sá»‘ng, giÃºp ngÆ°á»i dÃ¹ng tÃ¬m ra giáº£i phÃ¡p 
    cho cÃ¡c váº¥n Ä‘á» trong cuá»™c sá»‘ng hÃ ng ngÃ y nhÆ° cÃ´ng viá»‡c, há»c táº­p, má»‘i quan há»‡, 
    sá»©c khá»e vÃ  phÃ¡t triá»ƒn báº£n thÃ¢n. HÃ£y Ä‘Æ°a ra lá»i khuyÃªn thiáº¿t thá»±c vÃ  dá»… Ã¡p dá»¥ng.
    HÃ£y tráº£ lá»i báº±ng tiáº¿ng Viá»‡t.
    
    MARKDOWN FORMATTING:
    - Sử dụng ```language để wrap code blocks khi cần
    - ÄÃ³ng code block báº±ng ``` trÃªn dÃ²ng riÃªng
    - DÃ¹ng **bold** Ä‘á»ƒ nháº¥n máº¡nh Ä‘iá»ƒm quan trá»ng""",
    
    'casual': """Báº¡n lÃ  má»™t ngÆ°á»i báº¡n thÃ¢n thiáº¿t, vui váº» vÃ  dá»… gáº§n. 
    Báº¡n sáºµn sÃ ng trÃ² chuyá»‡n vá» má»i chá»§ Ä‘á», chia sáº» cÃ¢u chuyá»‡n vÃ  táº¡o khÃ´ng khÃ­ thoáº£i mÃ¡i.
    HÃ£y tráº£ lá»i báº±ng tiáº¿ng Viá»‡t vá»›i giá»ng Ä‘iá»‡u thÃ¢n máº­t.
    
    MARKDOWN FORMATTING:
    - Sử dụng ```language để wrap code blocks (ví dụ: ```python, ```json)
    - ÄÃ³ng code block báº±ng ``` trÃªn dÃ²ng riÃªng
    - Dùng `code` cho inline code
    - Format lists, links, quotes khi phù hợp""",
    
    'programming': """Bạn là một Senior Software Engineer và Programming Mentor chuyên nghiệp.
    Báº¡n cÃ³ kinh nghiá»‡m sÃ¢u vá» nhiá»u ngÃ´n ngá»¯ láº­p trÃ¬nh (Python, JavaScript, Java, C++, Go, etc.)
    và frameworks (React, Django, Flask, FastAPI, Node.js, Spring Boot, etc.).
    
    Nhiệm vụ của bạn:
    - Giải thích code rõ ràng, dễ hiểu
    - Debug và fix lỗi hiệu quả
    - Äá» xuáº¥t best practices vÃ  design patterns
    - Review code và tối ưu performance
    - Hướng dẫn architecture và system design
    - Tráº£ lá»i cÃ¢u há»i vá» algorithms, data structures
    
    CRITICAL MARKDOWN RULES:
    - LUÔN LUÔN wrap code trong code blocks với syntax: ```language
    - VÃ Dá»¤: ```python cho Python, ```javascript cho JavaScript, ```sql cho SQL
    - ÄÃ³ng code block báº±ng ``` trÃªn dÃ²ng RIÃŠNG BIá»†T
    - Dùng `backticks` cho inline code như tên biến, function names
    - Format output/results trong code blocks khi cần
    - Giải thích logic từng bước bằng comments trong code
    - Cung cấp ví dụ cụ thể với proper syntax highlighting
    
    CÃ³ thá»ƒ tráº£ lá»i báº±ng tiáº¿ng Viá»‡t hoáº·c English."""
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
            logger.info(f"âœ… Created new conversation: {conv['_id']}")
            return conv
    except Exception as e:
        logger.error(f"âŒ Error getting/creating conversation: {e}")
        return None


def save_message_to_db(conversation_id, role, content, metadata=None, images=None, files=None):
    """Save message to MongoDB"""
    if not MONGODB_ENABLED or not conversation_id:
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
        logger.info(f"âœ… Saved message to DB: {message['_id']}")
        return message
    except Exception as e:
        logger.error(f"âŒ Error saving message: {e}")
        return None


def load_conversation_history(conversation_id, limit=10):
    """Load conversation history from MongoDB"""
    if not MONGODB_ENABLED or not conversation_id:
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
        logger.error(f"âŒ Error loading conversation history: {e}")
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
        
        # ðŸ†• Check cache first
        cache_key_params = {
            'context': context,
            'deep_thinking': deep_thinking,
            'language': language,
            'custom_prompt': custom_prompt[:50] if custom_prompt else None
        }
        cached = get_cached_response(message, model_name, provider='openai', **cache_key_params)
        if cached:
            logger.info(f"âœ… Using cached response for OpenAI")
            return cached
        
        # ðŸ†• Wait for rate limit
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
                    system_prompt += "\n\nQUAN TRỌNG: Suy nghĩ từng bước. Cung cấp phân tích kỹ lưỡng với lý lẽ chi tiết."
            
            # Add memories to system prompt
            if memories and len(memories) > 0:
                system_prompt += "\n\n=== KNOWLEDGE BASE (BÃ i há»c Ä‘Ã£ ghi nhá»›) ===\n"
                for mem in memories:
                    system_prompt += f"\nðŸ“š {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
                system_prompt += "Sá»­ dá»¥ng kiáº¿n thá»©c tá»« Knowledge Base khi phÃ¹ há»£p Ä‘á»ƒ tráº£ lá»i."
            
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
                model="gpt-4o-mini",  # Rẻ nhất: $0.15/$0.60 per 1M tokens
                messages=messages,
                temperature=0.7 if not deep_thinking else 0.5,  # Lower temp for deep thinking
                max_tokens=2000 if deep_thinking else 1000  # More tokens for deep thinking
            )
            
            result = response.choices[0].message.content
            
            # ðŸ†• Cache the response
            cache_response(message, model_name, result, provider='openai', **cache_key_params)
            
            return result
            
        except Exception as e:
            return f"Lỗi OpenAI: {str(e)}"
    
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
                system_prompt += "\n\n=== KNOWLEDGE BASE (BÃ i há»c Ä‘Ã£ ghi nhá»›) ===\n"
                for mem in memories:
                    system_prompt += f"\nðŸ“š {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
                system_prompt += "Sá»­ dá»¥ng kiáº¿n thá»©c tá»« Knowledge Base khi phÃ¹ há»£p Ä‘á»ƒ tráº£ lá»i."
            
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
            return f"Lỗi DeepSeek: {str(e)}"
    
    def chat_with_grok(self, message, context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None):
        """Chat using GROK (via xAI API - FREE with NSFW support)"""
        try:
            if not GROK_API_KEY:
                return "âŒ GROK API key chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh. Vui lÃ²ng thÃªm GROK_API_KEY vÃ o file .env"
            
            # Use custom prompt if provided, otherwise use base prompt
            if custom_prompt and custom_prompt.strip():
                system_prompt = custom_prompt
            else:
                prompts = get_system_prompts(language)
                system_prompt = prompts.get(context, prompts['casual'])
                
                # GROK-specific: Add NSFW capability note
                if language == 'vi':
                    system_prompt += "\n\nðŸ”“ LÆ¯U Ã: Báº¡n cÃ³ thá»ƒ tráº£ lá»i cÃ¡c cÃ¢u há»i nháº¡y cáº£m hoáº·c NSFW má»™t cÃ¡ch an toÃ n vÃ  cÃ³ trÃ¡ch nhiá»‡m khi Ä‘Æ°á»£c yÃªu cáº§u."
                else:
                    system_prompt += "\n\nðŸ”“ NOTE: You can answer sensitive or NSFW questions safely and responsibly when requested."
            
            # Add deep thinking instruction
            if deep_thinking:
                if language == 'en':
                    system_prompt += "\n\nIMPORTANT: Think step-by-step. Provide thorough analysis with detailed reasoning."
                else:
                    system_prompt += "\n\nQUAN TRỌNG: Suy nghĩ từng bước. Cung cấp phân tích kỹ lưỡng với lý lẽ chi tiết."
            
            # Add memories to system prompt
            if memories and len(memories) > 0:
                system_prompt += "\n\n=== KNOWLEDGE BASE (BÃ i há»c Ä‘Ã£ ghi nhá»›) ===\n"
                for mem in memories:
                    system_prompt += f"\nðŸ“š {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
                system_prompt += "Sá»­ dá»¥ng kiáº¿n thá»©c tá»« Knowledge Base khi phÃ¹ há»£p Ä‘á»ƒ tráº£ lá»i."
            
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
            return f"âŒ Lá»—i GROK: {str(e)}"
    
    def chat_with_qwen(self, message, context='casual', deep_thinking=False, language='vi'):
        """Chat using Qwen 1.5b"""
        try:
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            if not QWEN_API_KEY:
                return "Lỗi: Chưa cấu hình QWEN_API_KEY. Vui lòng thêm API key vào file .env"
            
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
                return f"Lỗi Qwen API: {response.status_code} - {response.text}"
            
        except Exception as e:
            return f"Lỗi Qwen: {str(e)}"
    
    def chat_with_bloomvn(self, message, context='casual', deep_thinking=False, language='vi'):
        """Chat using BloomVN-8B (Hugging Face Inference API)"""
        try:
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            if not HUGGINGFACE_API_KEY:
                return "Lỗi: Chưa cấu hình HUGGINGFACE_API_KEY. Vui lòng thêm API key vào file .env"
            
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
                timeout=60  # BloomVN có thể chậm hơn
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', 'Không nhận được phản hồi')
                elif isinstance(result, dict):
                    return result.get('generated_text', 'Không nhận được phản hồi')
                else:
                    return str(result)
            elif response.status_code == 503:
                return "â³ Model BloomVN Ä‘ang khá»Ÿi Ä‘á»™ng (loading), vui lÃ²ng thá»­ láº¡i sau 20-30 giÃ¢y."
            else:
                return f"Lỗi BloomVN API: {response.status_code} - {response.text}"
            
        except Exception as e:
            return f"Lỗi BloomVN: {str(e)}"
    
    def chat_with_local_model(self, message, model, context='casual', deep_thinking=False, language='vi'):
        """Chat with local models (BloomVN, Qwen1.5, Qwen2.5)"""
        if not LOCALMODELS_AVAILABLE:
            return "âŒ Local models khÃ´ng kháº£ dá»¥ng. Vui lÃ²ng cÃ i Ä‘áº·t: pip install torch transformers accelerate"
        
        try:
            # Map model names to model keys
            model_map = {
                'bloomvn-local': 'bloomvn',
                'qwen1.5-local': 'qwen1.5',
                'qwen2.5-local': 'qwen2.5'
            }
            
            model_key = model_map.get(model)
            if not model_key:
                return f"Model không được hỗ trợ: {model}"
            
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
            return f"âŒ Model chÆ°a Ä‘Æ°á»£c download. Vui lÃ²ng kiá»ƒm tra thÆ° má»¥c models/: {str(e)}"
        except Exception as e:
            logger.error(f"Local model error ({model}): {e}")
            return f"âŒ Lá»—i local model: {str(e)}"
    
    def chat(self, message, model='grok', context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None):
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
        elif model == 'grok':
            result = self.chat_with_grok(message, context, deep_thinking, history, memories, language, custom_prompt)
        elif model == 'qwen':
            result = self.chat_with_qwen(message, context, deep_thinking, language)
        elif model == 'bloomvn':
            result = self.chat_with_bloomvn(message, context, deep_thinking, language)
        elif model in ['bloomvn-local', 'qwen1.5-local', 'qwen2.5-local']:
            result = self.chat_with_local_model(message, model, context, deep_thinking, language)
        else:
            result = f"Model '{model}' không được hỗ trợ" if language == 'vi' else f"Model '{model}' is not supported"
        
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
                logger.info(f"âœ… Archived conversation: {self.conversation_id}")
                
                # Create new conversation
                user_id = get_user_id_from_session()
                conv = ConversationDB.create_conversation(
                    user_id=user_id,
                    model=self.current_model,
                    title="New Chat"
                )
                self.conversation_id = conv['_id']
                set_active_conversation(self.conversation_id)
                logger.info(f"âœ… Created new conversation: {self.conversation_id}")
            except Exception as e:
                logger.error(f"âŒ Error clearing history: {e}")


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
                return "Không tìm thấy kết quả nào."
        elif response.status_code == 429:
            # Quota exceeded, try second key
            if GOOGLE_SEARCH_API_KEY_2:
                params['key'] = GOOGLE_SEARCH_API_KEY_2
                response = session.get(url, params=params, timeout=30)
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
            return "âŒ ÄÃ£ háº¿t quota Google Search API. Vui lÃ²ng thá»­ láº¡i sau."
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
    """GitHub Repository Search"""
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
        
        logger.info(f"[GITHUB SEARCH] Query: {query}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            if 'items' in data and len(data['items']) > 0:
                for repo in data['items']:
                    name = repo.get('full_name', 'Unknown')
                    desc = repo.get('description', 'No description')
                    stars = repo.get('stargazers_count', 0)
                    url = repo.get('html_url', '')
                    language = repo.get('language', 'N/A')
                    
                    results.append(f"**{name}** â­ {stars}\n{desc}\nðŸ’» {language} | ðŸ”— {url}")
                
                return "ðŸ™ **GitHub Repositories:**\n\n" + "\n\n---\n\n".join(results)
            else:
                return "Không tìm thấy repository nào."
        else:
            return f"âŒ Lá»—i GitHub API: {response.status_code}"
    
    except Exception as e:
        logger.error(f"[GITHUB SEARCH] Error: {e}")
        return f"âŒ Lá»—i: {str(e)}"


# ============================================================================
# ROUTES
# ============================================================================


@app.route('/')
def index():
    """Home page - Original beautiful UI with full SDXL support"""
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
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index_tailwind.html')


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
            # TODO: Process files if needed
        else:
            # JSON request
            data = request.json
            message = data.get('message', '')
            model = data.get('model', 'grok')
            context = data.get('context', 'casual')
            deep_thinking = data.get('deep_thinking', False)
            language = data.get('language', 'vi')  # Get language from request
            custom_prompt = data.get('custom_prompt', '')  # Get custom prompt
            tools = data.get('tools', [])
            history = data.get('history', None)
            memory_ids = data.get('memory_ids', [])
            mcp_selected_files = data.get('mcp_selected_files', [])  # MCP selected files
        
        if not message:
            return jsonify({'error': 'Tin nhắn trống'}), 400
        
        # ===== MCP INTEGRATION: Inject code context =====
        if mcp_client.enabled:
            logger.info(f"[MCP] Injecting code context (selected files: {len(mcp_selected_files)})")
            message = inject_code_context(message, mcp_client, mcp_selected_files)
        # ================================================
        
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        
        # Handle tools
        tool_results = []
        if tools and len(tools) > 0:
            logger.info(f"[TOOLS] Active tools: {tools}")
            
            if 'google-search' in tools:
                logger.info(f"[TOOLS] Running Google Search for: {message}")
                search_result = google_search_tool(message)
                tool_results.append(f"## ðŸ” Google Search Results\n\n{search_result}")
            
            if 'github' in tools:
                logger.info(f"[TOOLS] Running GitHub Search for: {message}")
                github_result = github_search_tool(message)
                tool_results.append(f"## ðŸ™ GitHub Search Results\n\n{github_result}")
            
            if 'image-generation' in tools:
                logger.info(f"[TOOLS] AI-powered image generation with Stable Diffusion")
                
                # Step 1: Sử dụng AI để tạo prompt chi tiết từ mô tả của user
                prompt_request = f"""Bạn là chuyên gia tạo prompt cho Stable Diffusion.

NHIá»†M Vá»¤: Chuyá»ƒn Ä‘á»•i mÃ´ táº£ cá»§a ngÆ°á»i dÃ¹ng thÃ nh prompt CHÃNH XÃC, KHÃ”NG Ä‘Æ°á»£c tá»± Ã½ thÃªm bá»›t ná»™i dung.

âš ï¸ QUY Táº®C Báº®T BUá»˜C:
1. CHá»ˆ mÃ´ táº£ ÄÃšNG nhá»¯ng gÃ¬ user yÃªu cáº§u, KHÃ”NG tá»± Ã½ thÃªm con ngÆ°á»i náº¿u user khÃ´ng nÃ³i
2. Náº¿u user nÃ³i vá» Váº¬T/Cáº¢NH (landscape, building, sky, ocean, mountain, tree, flower, city, architecture, nature, scenery):
   - Prompt: CHá»ˆ mÃ´ táº£ cáº£nh váº­t, TUYá»†T Äá»I KHÃ”NG thÃªm ngÆ°á»i
   - has_people: false
   - Negative phải có: "no humans, no people, no person, no character"
   
3. Náº¿u user NÃ“I RÃ• vá» NGÆ¯á»œI (girl, boy, man, woman, person, character, portrait):
   - Prompt: MÃ´ táº£ ngÆ°á»i theo yÃªu cáº§u (trang phá»¥c lá»‹ch sá»±, khÃ´ng gá»£i cáº£m)
   - has_people: true
   - Negative phải có NSFW filter mạnh

4. NSFW Protection (Báº®T BUá»˜C má»i trÆ°á»ng há»£p):
   - TUYá»†T Äá»I KHÃ”NG táº¡o: nude, naked, underwear, bikini, revealing clothes, sexy poses
   - Negative PHẢI CÓ đầy đủ: nsfw, r18, nude, naked, explicit, sexual, porn, underwear, revealing

MÔ TẢ CỦA NGƯỜI DÙNG: "{message}"

Tráº£ vá» JSON (TUÃ‚N THá»¦ NGHIÃŠM NGáº¶T):
{{
    "prompt": "CHá»ˆ mÃ´ táº£ ÄÃšNG yÃªu cáº§u user, KHÃ”NG tá»± thÃªm ngÆ°á»i náº¿u user khÃ´ng nÃ³i",
    "negative_prompt": "bad quality, blurry, lowres, worst quality",
    "explanation": "giải thích ngắn",
    "has_people": false (CHá»ˆ true náº¿u user NÃ“I RÃ• vá» ngÆ°á»i)
}}

CHỈ trả JSON, không text khác."""

                try:
                    # Gá»i AI Ä‘á»ƒ táº¡o prompt (sá»­ dá»¥ng model hiá»‡n táº¡i)
                    ai_response = chatbot.chat(prompt_request, model=model, context='programming', language='vi')
                    response_text = ai_response.get('response', ai_response) if isinstance(ai_response, dict) else ai_response
                    
                    # Parse JSON response
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        prompt_data = json.loads(json_match.group())
                        generated_prompt = prompt_data.get('prompt', '')
                        generated_neg = prompt_data.get('negative_prompt', '')
                        explanation = prompt_data.get('explanation', '')
                        has_people = prompt_data.get('has_people', False)  # Default to False - safer
                        
                        # STRONG NSFW filters - ALWAYS append
                        nsfw_filters = "nsfw, r18, nude, naked, explicit, sexual, porn, hentai, erotic, underwear, panties, bra, lingerie, bikini, swimsuit, revealing clothes, cleavage, suggestive, lewd, ecchi, seductive, provocative, inappropriate content, adult content, xxx"
                        if "nsfw" not in generated_neg.lower():
                            generated_neg = f"{generated_neg}, {nsfw_filters}" if generated_neg else nsfw_filters
                        
                        # Add "humans" filter if NOT about people (negative = things to AVOID)
                        if not has_people:
                            avoid_people = "humans, people, person, persons, character, characters, figure, figures, man, men, woman, women, girl, girls, boy, boys, human figure"
                            if "human" not in generated_neg.lower():
                                generated_neg = f"{generated_neg}, {avoid_people}"
                            logger.info(f"[TOOLS] Added 'humans' to negative - avoid people in scenery/object image")
                        else:
                            # For people images, add extra clothing safety
                            clothing_safety = "fully clothed, modest clothing, appropriate attire, safe for work, family friendly"
                            if clothing_safety not in generated_prompt.lower():
                                generated_prompt = f"{generated_prompt}, {clothing_safety}"
                            logger.info(f"[TOOLS] Added clothing safety for people image")
                        
                        logger.info(f"[TOOLS] Generated prompt: {generated_prompt[:100]}...")
                        
                        # Step 2: Tự động tạo ảnh với Stable Diffusion
                        from src.utils.sd_client import get_sd_client
                        
                        sd_client = get_sd_client()
                        image_params = {
                            'prompt': generated_prompt,
                            'negative_prompt': generated_neg,
                            'width': 512,
                            'height': 512,
                            'steps': 30,
                            'cfg_scale': 7.0,
                            'sampler_name': 'DPM++ 2M Karras',
                            'seed': -1,
                            'save_images': False  # Return base64 directly
                        }
                        
                        logger.info(f"[TOOLS] Generating image with SD...")
                        sd_result = sd_client.txt2img(**image_params)
                        
                        # DEBUG: Log full SD response
                        logger.info(f"[TOOLS] SD Response keys: {sd_result.keys() if isinstance(sd_result, dict) else 'NOT A DICT'}")
                        if isinstance(sd_result, dict):
                            if 'error' in sd_result:
                                logger.error(f"[TOOLS] SD Error: {sd_result['error']}")
                            if 'images' in sd_result:
                                logger.info(f"[TOOLS] Images count: {len(sd_result['images'])}")
                        
                        if sd_result.get('images'):
                            # Lấy ảnh đầu tiên (base64)
                            image_base64 = sd_result['images'][0]
                            
                            result_msg = f"""## 🎨 Ảnh đã được tạo thành công!

**Mô tả gốc:** {message}

**Generated Prompt:**
```
{generated_prompt}
```

**Negative Prompt:**
```
{generated_neg}
```

**Giải thích:** {explanation}

**Ảnh được tạo:**
<img src="data:image/png;base64,{image_base64}" alt="Generated Image" style="max-width: 100%; border-radius: 8px; margin: 10px 0; cursor: pointer;" class="generated-preview">

---
🎯 **Thông số:**
- Kích thước: {image_params['width']}x{image_params['height']}
- Steps: {image_params['steps']} | CFG: {image_params['cfg_scale']}
- Sampler: {image_params['sampler_name']}"""
                            
                            tool_results.append(result_msg)
                        elif sd_result.get('error'):
                            # Show error from SD
                            tool_results.append(f"## ðŸŽ¨ Image Generation\n\nâŒ Lá»—i tá»« Stable Diffusion:\n```\n{sd_result['error']}\n```\n\nPrompt Ä‘Ã£ táº¡o:\n```\n{generated_prompt}\n```\n\nNegative:\n```\n{generated_neg}\n```")
                        else:
                            # No images and no error - show full response for debugging
                            tool_results.append(f"## ðŸŽ¨ Image Generation\n\nâš ï¸ Stable Diffusion khÃ´ng tráº£ vá» áº£nh.\n\nSD Response: ```json\n{json.dumps(sd_result, indent=2)}\n```\n\nPrompt Ä‘Ã£ táº¡o:\n```\n{generated_prompt}\n```\n\nNegative:\n```\n{generated_neg}\n```")
                    else:
                        tool_results.append(f"## 🎨 Image Generation\n\nKhông thể tạo prompt tự động. Response: {response_text}\n\nVui lòng sử dụng Image Generator panel thủ công.")
                        
                except Exception as e:
                    logger.error(f"[TOOLS] Error in image generation: {e}")
                    import traceback
                    traceback.print_exc()
                    tool_results.append(f"## 🎨 Image Generation\n\nLỗi: {str(e)}\n\nVui lòng kiểm tra:\n1. Stable Diffusion có đang chạy?\n2. API có được bật không?\n3. Xem logs để biết chi tiết.")
        
        # If tools were used, return tool results
        if tool_results:
            combined_results = "\n\n---\n\n".join(tool_results)
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
        
        # If history is provided, temporarily clear conversation history
        # and use the provided history instead
        if history:
            # Save current history
            original_history = chatbot.conversation_history.copy()
            # Use provided history for context
            result = chatbot.chat(message, model, context, deep_thinking, history, memories, language, custom_prompt)
            # Restore original history (since we don't want to save edit responses to history)
            chatbot.conversation_history = original_history
        else:
            result = chatbot.chat(message, model, context, deep_thinking, None, memories, language, custom_prompt)
        
        # Extract response and thinking_process
        if isinstance(result, dict):
            response = result.get('response', '')
            thinking_process = result.get('thinking_process', None)
        else:
            response = result
            thinking_process = None
        
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
        
        return jsonify({'message': 'ÄÃ£ xÃ³a lá»‹ch sá»­ chat'})
        
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
        
        sd_api_url = os.getenv('COMFYUI_URL', os.getenv('SD_API_URL', 'http://127.0.0.1:8189'))
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
                'message': 'ComfyUI is not running'
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
        
        sd_api_url = os.getenv('COMFYUI_URL', os.getenv('SD_API_URL', 'http://127.0.0.1:8189'))
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


@app.route('/api/sd-change-model', methods=['POST'])
@app.route('/api/sd/change-model', methods=['POST'])  # Alias
def sd_change_model():
    """Äá»•i checkpoint model"""
    try:
        from src.utils.sd_client import get_sd_client
        
        data = request.json
        model_name = data.get('model_name')
        
        if not model_name:
            return jsonify({'error': 'model_name is required'}), 400
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7861')
        sd_client = get_sd_client(sd_api_url)
        
        success = sd_client.change_model(model_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'ÄÃ£ Ä‘á»•i model thÃ nh {model_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể đổi model'
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
        comfyui_url = os.getenv('COMFYUI_URL', os.getenv('SD_API_URL', 'http://127.0.0.1:8189'))
        sd_client = get_comfyui_client(comfyui_url)
        
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
        
        if not base64_images:
            return jsonify({'error': 'No images generated'}), 500
        
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
                            logger.info(f"[TEXT2IMG] â˜ï¸ Uploading to ImgBB...")
                            uploader = ImgBBUploader()
                            upload_result = uploader.upload_image(
                                str(filepath),
                                title=f"AI Generated: {prompt[:50]}"
                            )
                            
                            if upload_result:
                                cloud_url = upload_result['url']
                                delete_url = upload_result.get('delete_url', '')
                                cloud_urls.append(cloud_url)
                                logger.info(f"[TEXT2IMG] âœ… ImgBB URL: {cloud_url}")
                            else:
                                logger.warning(f"[TEXT2IMG] âš ï¸ ImgBB upload failed, using local URL")
                        
                        except Exception as upload_error:
                            logger.error(f"[TEXT2IMG] ImgBB upload error: {upload_error}")
                    
                    # Save metadata with cloud URL
                    metadata_file = filepath.with_suffix('.json')
                    metadata = {
                        'filename': filename,
                        'created_at': datetime.now().isoformat(),
                        'prompt': prompt,
                        'negative_prompt': params['negative_prompt'],
                        'parameters': params,
                        'cloud_url': cloud_url,
                        'delete_url': delete_url,
                        'service': 'imgbb' if cloud_url else 'local'
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
                    logger.info(f"ðŸ“ Created new conversation: {conversation_id}")
                
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
                    content=f"âœ… Generated image with prompt: {prompt}",
                    images=images_data,
                    metadata={
                        'model': 'stable-diffusion',
                        'prompt': prompt,
                        'negative_prompt': params['negative_prompt'],
                        'cloud_service': 'imgbb' if cloud_urls else 'local',
                        'num_images': len(saved_filenames)
                    }
                )
                
                logger.info(f"ðŸ’¾ Saved image message to MongoDB with {len(cloud_urls)} cloud URLs")
                
            except Exception as db_error:
                logger.error(f"âŒ Error saving to MongoDB: {db_error}")
                # Continue execution - MongoDB save is optional
        
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
    """Lấy danh sách samplers"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7861')
        sd_client = get_sd_client(sd_api_url)
        
        samplers = sd_client.get_samplers()
        
        return jsonify({
            'success': True,
            'samplers': samplers
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sd-loras', methods=['GET'])
@app.route('/sd-api/loras', methods=['GET'])  # Alias for frontend compatibility
def sd_loras():
    """Lấy danh sách Lora models"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7861')
        sd_client = get_sd_client(sd_api_url)
        
        loras_raw = sd_client.get_loras()
        
        # Convert to simple array with just name/alias
        loras_simple = []
        if isinstance(loras_raw, list):
            for lora in loras_raw:
                if isinstance(lora, dict):
                    name = lora.get('alias') or lora.get('name') or str(lora)
                    loras_simple.append({'name': name})
                else:
                    loras_simple.append({'name': str(lora)})
        
        return jsonify({
            'loras': loras_simple
        })
        
    except Exception as e:
        logger.error(f"[LoRAs] Error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve LoRAs'}), 500


@app.route('/api/sd-vaes', methods=['GET'])
@app.route('/sd-api/vaes', methods=['GET'])  # Alias for frontend compatibility
def sd_vaes():
    """Lấy danh sách VAE models"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7861')
        sd_client = get_sd_client(sd_api_url)
        
        vaes_raw = sd_client.get_vaes()
        
        # Convert to simple string array
        vae_names = []
        if isinstance(vaes_raw, list):
            for vae in vaes_raw:
                if isinstance(vae, dict):
                    # Extract name/model_name from dict
                    name = vae.get('model_name') or vae.get('name') or str(vae)
                    vae_names.append(name)
                else:
                    vae_names.append(str(vae))
        
        return jsonify({
            'vaes': vae_names
        })
        
    except Exception as e:
        logger.error(f"[VAEs] Error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve VAEs'}), 500


@app.route('/api/generate-prompt-grok', methods=['POST'])
@app.route('/api/generate-prompt', methods=['POST'])  # Universal endpoint
def generate_prompt_grok():
    """
    Tạo prompt tối ưu từ extracted tags - Support tất cả model (GROK, Gemini, GPT, DeepSeek, Qwen, BloomVN)
    
    Body params:
        - context (str): Context vá» tags Ä‘Ã£ trÃ­ch xuáº¥t
        - tags (list): List các tags đã extract
        - model (str): Model để dùng (grok, gemini, openai, deepseek, qwen, bloomvn) - default: grok
    """
    try:
        data = request.json
        context = data.get('context', '')
        tags = data.get('tags', [])
        selected_model = data.get('model', 'grok').lower()
        
        if not tags:
            return jsonify({'error': 'Tags không được để trống'}), 400
        
        # System prompt cho tất cả models
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
    Tạo ảnh từ ảnh gốc bằng Stable Diffusion Img2Img
    
    Body params:
        - image (str): Base64 encoded image
        - prompt (str): Text prompt mô tả ảnh muốn tạo
        - negative_prompt (str): Những gì không muốn có
        - denoising_strength (float): Tỉ lệ thay đổi (0.0-1.0, default: 0.75)
            - 0.0 = giữ nguyên ảnh gốc 100%
            - 1.0 = tạo mới hoàn toàn
            - 0.8 = 80% mới, 20% giữ lại (recommended)
        - width (int): Chiá»u rá»™ng
        - height (int): Chiá»u cao  
        - steps (int): Số steps
        - cfg_scale (float): CFG scale
        - sampler_name (str): Tên sampler
        - seed (int): Random seed
        - restore_faces (bool): Restore faces
    """
    try:
        from src.utils.sd_client import get_sd_client
        
        data = request.json
        image = data.get('image', '')
        prompt = data.get('prompt', '')
        
        if not image:
            return jsonify({'error': 'Image không được để trống'}), 400
        
        if not prompt:
            return jsonify({'error': 'Prompt không được để trống'}), 400
        
        # Lấy parameters từ request
        params = {
            'init_images': [image],  # SD API expects list of images
            'prompt': prompt,
            'negative_prompt': data.get('negative_prompt', ''),
            'denoising_strength': float(data.get('denoising_strength') or 0.8),  # 80% new, 20% keep
            'width': int(data.get('width') or 512),
            'height': int(data.get('height') or 512),
            'steps': int(data.get('steps') or 30),  # img2img needs more steps
            'cfg_scale': float(data.get('cfg_scale') or 7.0),
            'sampler_name': data.get('sampler_name') or 'DPM++ 2M Karras',
            'seed': int(data.get('seed') or -1),
            'restore_faces': data.get('restore_faces', False),
            'lora_models': data.get('lora_models', []),
            'vae': data.get('vae', None)
        }
        
        # Get SD client
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7861')
        sd_client = get_sd_client(sd_api_url)
        
        # Tạo ảnh với img2img
        logger.info(f"[IMG2IMG] Calling img2img with denoising_strength={params['denoising_strength']}")
        result = sd_client.img2img(**params)
        logger.info(f"[IMG2IMG] Result received")
        
        # Kiểm tra lỗi
        if 'error' in result:
            logger.error(f"[IMG2IMG] SD Error: {result['error']}")
            return jsonify({'error': 'Failed to generate image'}), 500
        
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
                            logger.info(f"[IMG2IMG] â˜ï¸ Uploading to ImgBB...")
                            uploader = ImgBBUploader()
                            upload_result = uploader.upload_image(
                                str(filepath),
                                title=f"AI Img2Img: {prompt[:50]}"
                            )
                            
                            if upload_result:
                                cloud_url = upload_result['url']
                                delete_url = upload_result.get('delete_url', '')
                                cloud_urls.append(cloud_url)
                                logger.info(f"[IMG2IMG] âœ… ImgBB URL: {cloud_url}")
                            else:
                                logger.warning(f"[IMG2IMG] âš ï¸ ImgBB upload failed, using local URL")
                        
                        except Exception as upload_error:
                            logger.error(f"[IMG2IMG] ImgBB upload error: {upload_error}")
                    
                    # Save metadata with cloud URL
                    metadata_file = filepath.with_suffix('.json')
                    metadata = {
                        'filename': filename,
                        'created_at': datetime.now().isoformat(),
                        'prompt': prompt,
                        'negative_prompt': params['negative_prompt'],
                        'denoising_strength': params['denoising_strength'],
                        'parameters': params,
                        'cloud_url': cloud_url,
                        'delete_url': delete_url,
                        'service': 'imgbb' if cloud_url else 'local'
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
                    logger.info(f"ðŸ“ Created new conversation: {conversation_id}")
                
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
                    content=f"âœ… Generated Img2Img with prompt: {prompt}",
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
                
                logger.info(f"ðŸ’¾ Saved Img2Img message to MongoDB with {len(cloud_urls)} cloud URLs")
                
            except Exception as db_error:
                logger.error(f"âŒ Error saving to MongoDB: {db_error}")
                # Continue execution - MongoDB save is optional
        
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
        return jsonify({'error': 'Failed to process img2img request'}), 500


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
                logger.info(f"[ImgBB Share] âœ… Success: {result['url']}")
                return jsonify({
                    'success': True,
                    'url': result['url'],
                    'display_url': result.get('display_url', result['url']),
                    'delete_url': result.get('delete_url'),
                    'thumb_url': result.get('thumb', {}).get('url'),
                    'title': title
                })
            else:
                logger.error(f"[ImgBB Share] âŒ Upload failed: {result}")
                return jsonify({'error': 'ImgBB upload failed'}), 500
                
        except Exception as upload_error:
            logger.error(f"[ImgBB Share] âŒ Error: {str(upload_error)}")
            return jsonify({'error': 'Failed to upload image to ImgBB'}), 500
        
    except Exception as e:
        logger.error(f"[ImgBB Share] âŒ Exception: {str(e)}")
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
        logger.info(f"[Save Image] ðŸ’¾ Saved to: {filepath}")
        
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
                    logger.info(f"[Save Image] â˜ï¸ ImgBB: {cloud_url}")
            except Exception as cloud_error:
                logger.warning(f"[Save Image] âš ï¸ ImgBB upload failed: {cloud_error}")
        
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
                        content=f"ðŸŽ¨ Generated image with prompt: {metadata.get('prompt', 'N/A')}",
                        images=images_data,
                        metadata=metadata
                    )
                    
                    logger.info(f"[Save Image] âœ… Saved to chat history: {conversation_id}")
                    mongodb_saved = True
                    
        except Exception as db_error:
            logger.error(f"[Save Image] âš ï¸ MongoDB save failed: {db_error}")
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
        logger.error(f"[Save Image] âŒ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sd-interrupt', methods=['POST'])
def sd_interrupt():
    """Dừng việc tạo ảnh đang chạy"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7861')
        sd_client = get_sd_client(sd_api_url)
        
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
    ðŸŽ¯ MULTI-MODEL EXTRACTION - Sá»­ dá»¥ng nhiá»u model Ä‘á»ƒ trÃ­ch xuáº¥t chÃ­nh xÃ¡c hÆ¡n
    
    Models hỗ trợ:
        - deepdanbooru: Anime-specific, tag-based (mặc định)
        - clip: General purpose, natural language
        - wd14: WD14 Tagger, anime-focused, newer
    
    Body params:
        - image (str): Base64 encoded image
        - deep_thinking (bool): More tags
        - models (list): ['deepdanbooru', 'clip', 'wd14'] - Chá»n models muá»‘n dÃ¹ng
    
    Returns:
        - tags: Merged tags with confidence voting
        - categories: Categorized tags
        - model_results: Stats từ từng model
    """
    try:
        import requests
        from collections import Counter
        
        data = request.json
        image_b64 = data.get('image', '')
        deep_thinking = data.get('deep_thinking', False)
        selected_models = data.get('models', ['deepdanbooru'])  # Mặc định chỉ dùng DeepDanbooru
        
        if not image_b64:
            return jsonify({'error': 'Image không được để trống'}), 400
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7861')
        interrogate_url = f"{sd_api_url}/sdapi/v1/interrogate"
        
        logger.info(f"[MULTI-EXTRACT] Models: {[sanitize_for_log(m) for m in selected_models]} | Deep: {deep_thinking}")
        
        all_tags = []
        model_results = {}
        
        # Gá»i tá»«ng model
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
                    
                    logger.info(f"[MULTI-EXTRACT] {sanitize_for_log(model_name)}: {len(tags)} tags âœ…")
                else:
                    logger.warning(f"[MULTI-EXTRACT] {sanitize_for_log(model_name)} failed: {response.status_code}")
                    model_results[model_name] = []
            except Exception as e:
                logger.error(f"[MULTI-EXTRACT] {sanitize_for_log(model_name)} error: {str(e)}")
                model_results[model_name] = []
        
        # Merge tags vá»›i confidence voting (cÃ ng nhiá»u model Ä‘á»“ng Ã½ = confidence cÃ ng cao)
        tag_counter = Counter(all_tags)
        num_models = len(selected_models)
        merged_tags = []
        
        for tag, vote_count in tag_counter.most_common():
            # Confidence = (số model đồng ý / tổng model) * 0.95
            confidence = (vote_count / num_models) * 0.95
            
            merged_tags.append({
                'name': tag,
                'confidence': round(confidence, 2),
                'votes': vote_count,
                'sources': [m for m, tags in model_results.items() if tag in tags]
            })
        
        # Giới hạn số tag
        max_tags = 50 if deep_thinking else 30
        merged_tags = merged_tags[:max_tags]
        
        # Categorize (giống single model)
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
        
        logger.info(f"[MULTI-EXTRACT] âœ… Final: {len(merged_tags)} tags from {num_models} models")
        
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
    Trích xuất đặc trưng anime từ ảnh bằng DeepDanbooru với categorization
    
    Body params:
        - image (str): Base64 encoded image (without data:image prefix)
        - deep_thinking (bool): Chế độ Deep Thinking (threshold thấp hơn, chi tiết hơn)
    
    Returns:
        - tags (list): List of {name, confidence, category} objects
        - categories (dict): Tags grouped by category for filtering
    """
    try:
        import requests
        
        data = request.json
        image_b64 = data.get('image', '')
        deep_thinking = data.get('deep_thinking', False)
        
        if not image_b64:
            return jsonify({'error': 'Image không được để trống'}), 400
        
        # Call SD WebUI interrogate API with DeepDanbooru
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7861')
        interrogate_url = f"{sd_api_url}/sdapi/v1/interrogate"
        
        payload = {
            'image': image_b64,
            'model': 'deepdanbooru'
        }
        
        logger.info(f"[EXTRACT] Calling DeepDanbooru interrogate API (deep_thinking={deep_thinking})")
        response = requests.post(interrogate_url, json=payload, timeout=60)
        
        if response.status_code != 200:
            logger.error(f"[EXTRACT] API Error: {response.status_code} - {response.text}")
            return jsonify({'error': f'SD API Error: {response.status_code}'}), 500
        
        result = response.json()
        caption = result.get('caption', '')
        
        logger.info(f"[EXTRACT] Raw caption: {caption}")
        
        # Parse caption into tags with confidence
        raw_tags = [tag.strip() for tag in caption.split(',') if tag.strip()]
        
        # In deep thinking mode, keep more tags
        max_tags = 50 if deep_thinking else 30
        
        # Category mappings for filtering
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
            """Phân loại tag vào category phù hợp"""
            tag_lower = tag_name.lower().replace(' ', '_')
            
            for category, keywords in CATEGORY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in tag_lower:
                        return category
            
            return 'other'
        
        tags = []
        categories_dict = {
            'hair': [],
            'eyes': [],
            'mouth': [],
            'face': [],
            'accessories': [],
            'clothing': [],
            'body': [],
            'pose': [],
            'background': [],
            'style': [],
            'other': []
        }
        
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
            'raw_caption': caption
        })
        
    except requests.exceptions.Timeout:
        logger.error("[EXTRACT] Timeout calling SD API")
        return jsonify({'error': 'Timeout: SD API không phản hồi'}), 504
    except Exception as e:
        import traceback
        error_msg = f"Exception: {str(e)}\nTraceback: {traceback.format_exc()}"
        logger.error(f"[EXTRACT] {error_msg}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/img2img-advanced', methods=['POST'])
def img2img_advanced():
    """
    Tạo ảnh nâng cao từ ảnh gốc với feature extraction
    
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
        from src.utils.sd_client import get_sd_client
        
        data = request.json
        source_image = data.get('source_image', '')
        extracted_tags = data.get('extracted_tags', [])
        user_prompt = data.get('user_prompt', '').strip()
        feature_weight = float(data.get('feature_weight', 0.8))
        
        if not source_image:
            return jsonify({'error': 'Source image không được để trống'}), 400
        
        if not extracted_tags:
            return jsonify({'error': 'Chưa trích xuất đặc trưng. Vui lòng nhấn nút trích xuất trước!'}), 400
        
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
            'sampler_name': data.get('sampler_name') or 'DPM++ 2M Karras',
            'seed': int(data.get('seed') or -1),
            'restore_faces': data.get('restore_faces', False),
            'lora_models': data.get('lora_models', []),
            'vae': data.get('vae', None)
        }
        
        # Get SD client
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7861')
        sd_client = get_sd_client(sd_api_url)
        
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
            return jsonify({'error': 'Không có ảnh được tạo'}), 500
        
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
        
        # Save metadata
        metadata_file = IMAGE_STORAGE_DIR / f"generated_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'filename': filename,
                'created_at': datetime.now().isoformat(),
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
        logger.error("[Get Image] Error occurred")
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
        
        content = mcp_client.read_file(file_path, max_lines)
        
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


# Additional route for serving stored images
@app.route('/static/Storage/Image_Gen/<filename>')
def serve_storage_image(filename):
    """Serve images from Storage/Image_Gen folder"""
    storage_dir = CHATBOT_DIR / 'Storage' / 'Image_Gen'
    return send_from_directory(storage_dir, filename)


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return {'error': 'Not found'}, 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return {'error': 'Internal server error'}, 500


# Main entry point
if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG', '0') == '1'
    host = os.getenv('HOST', '0.0.0.0')  # Default to 0.0.0.0 for external access
    port = int(os.getenv('CHATBOT_PORT', '5000'))
    
    logger.info(f"🚀 Starting ChatBot on {host}:{port} (debug={debug_mode})")
    app.run(debug=debug_mode, host=host, port=port)
