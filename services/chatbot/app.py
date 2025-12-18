"""
AI ChatBot Agent - Hỗ trợ tâm lý, tâm sự và giải pháp đời sống
Sử dụng Gemini, DeepSeek, OpenAI, Qwen, BloomVN và Local Models
"""

import os
import sys
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, send_file
import openai
from google import genai
from datetime import datetime
import uuid
import base64
import io
from PIL import Image
import requests
import logging
import json
from pathlib import Path
import shutil

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

# Enable werkzeug logging for request details
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv()

# Import performance optimization utilities
try:
    from src.utils.cache_manager import get_cache_manager
    from src.utils.database_manager import get_database_manager
    from src.utils.streaming_handler import StreamingHandler
    PERFORMANCE_ENABLED = True
    logger.info("✅ Performance optimization modules loaded")
except Exception as e:
    PERFORMANCE_ENABLED = False
    logger.warning(f"⚠️ Performance modules not available: {e}")

# Import ImgBB uploader (easy API key)
try:
    from src.utils.imgbb_uploader import ImgBBUploader, upload_to_imgbb
    CLOUD_UPLOAD_ENABLED = True
    logger.info("✅ ImgBB uploader loaded")
except ImportError as e:
    CLOUD_UPLOAD_ENABLED = False
    logger.warning(f"⚠️ ImgBB uploader not available: {e}")

# Initialize performance components
if PERFORMANCE_ENABLED:
    cache = get_cache_manager()
    db = get_database_manager()
    streaming = StreamingHandler()
    logger.info(f"✅ Cache status: {cache.enabled}")
    logger.info(f"✅ Database status: {db.enabled}")
else:
    cache = None
    db = None
    streaming = None

# Import local model loader
try:
    # Attempt to import with timeout protection
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Local model loader import timeout")
    
    # Set 10 second timeout for import (only on Unix-like systems)
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)
    except (AttributeError, ValueError):
        # Windows doesn't support SIGALRM, skip timeout
        pass
    
    from src.utils.local_model_loader import model_loader
    
    # Cancel alarm if import succeeded
    try:
        signal.alarm(0)
    except (AttributeError, ValueError):
        pass
    
    LOCALMODELS_AVAILABLE = True
    logger.info("✅ Local model loader imported successfully")
except (ImportError, TimeoutError, Exception) as e:
    LOCALMODELS_AVAILABLE = False
    logger.warning(f"⚠️ Local models not available: {e}")
    logger.info("💡 Local models disabled - ChatBot will work without them")

# Initialize Flask app with static folder
app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# 🆕 Register Monitor Dashboard
from config.monitor import register_monitor
register_monitor(app)

# Initialize MongoDB connection
try:
    mongodb_client.connect()
    MONGODB_ENABLED = True
    logger.info("✅ MongoDB connection established")
except Exception as e:
    MONGODB_ENABLED = False
    logger.warning(f"⚠️ MongoDB not available, using session storage: {e}")

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
QWEN_API_KEY = os.getenv('QWEN_API_KEY')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
GROK_API_KEY = os.getenv('GROK_API_KEY')

# Google Search API
GOOGLE_SEARCH_API_KEY_1 = os.getenv('GOOGLE_SEARCH_API_KEY_1')
GOOGLE_SEARCH_API_KEY_2 = os.getenv('GOOGLE_SEARCH_API_KEY_2')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')

# GitHub API
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

# Initialize Gemini client with new SDK
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
except:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY_2)

# System prompts for different purposes (Vietnamese)
SYSTEM_PROMPTS_VI = {
    'psychological': """Bạn là một trợ lý tâm lý chuyên nghiệp, thân thiện và đầy empathy. 
    Bạn luôn lắng nghe, thấu hiểu và đưa ra lời khuyên chân thành, tích cực.
    Bạn không phán xét và luôn hỗ trợ người dùng vượt qua khó khăn trong cuộc sống.
    Hãy trả lời bằng tiếng Việt.
    
    MARKDOWN FORMATTING:
    - Sử dụng ```language để wrap code blocks (ví dụ: ```python, ```javascript)
    - Đóng code block bằng ``` trên dòng riêng
    - Dùng `code` cho inline code
    - Sử dụng **bold**, *italic*, > quote khi cần""",
    
    'lifestyle': """Bạn là một chuyên gia tư vấn lối sống, giúp người dùng tìm ra giải pháp 
    cho các vấn đề trong cuộc sống hàng ngày như công việc, học tập, mối quan hệ, 
    sức khỏe và phát triển bản thân. Hãy đưa ra lời khuyên thiết thực và dễ áp dụng.
    Hãy trả lời bằng tiếng Việt.
    
    MARKDOWN FORMATTING:
    - Sử dụng ```language để wrap code blocks khi cần
    - Đóng code block bằng ``` trên dòng riêng
    - Dùng **bold** để nhấn mạnh điểm quan trọng""",
    
    'casual': """Bạn là một người bạn thân thiết, vui vẻ và dễ gần. 
    Bạn sẵn sàng trò chuyện về mọi chủ đề, chia sẻ câu chuyện và tạo không khí thoải mái.
    Hãy trả lời bằng tiếng Việt với giọng điệu thân mật.
    
    MARKDOWN FORMATTING:
    - Sử dụng ```language để wrap code blocks (ví dụ: ```python, ```json)
    - Đóng code block bằng ``` trên dòng riêng
    - Dùng `code` cho inline code
    - Format lists, links, quotes khi phù hợp""",
    
    'programming': """Bạn là một Senior Software Engineer và Programming Mentor chuyên nghiệp.
    Bạn có kinh nghiệm sâu về nhiều ngôn ngữ lập trình (Python, JavaScript, Java, C++, Go, etc.)
    và frameworks (React, Django, Flask, FastAPI, Node.js, Spring Boot, etc.).
    
    Nhiệm vụ của bạn:
    - Giải thích code rõ ràng, dễ hiểu
    - Debug và fix lỗi hiệu quả
    - Đề xuất best practices và design patterns
    - Review code và tối ưu performance
    - Hướng dẫn architecture và system design
    - Trả lời câu hỏi về algorithms, data structures
    
    CRITICAL MARKDOWN RULES:
    - LUÔN LUÔN wrap code trong code blocks với syntax: ```language
    - VÍ DỤ: ```python cho Python, ```javascript cho JavaScript, ```sql cho SQL
    - Đóng code block bằng ``` trên dòng RIÊNG BIỆT
    - Dùng `backticks` cho inline code như tên biến, function names
    - Format output/results trong code blocks khi cần
    - Giải thích logic từng bước bằng comments trong code
    - Cung cấp ví dụ cụ thể với proper syntax highlighting
    
    Có thể trả lời bằng tiếng Việt hoặc English."""
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

def get_or_create_conversation(user_id, model='gemini-1.5-flash'):
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
            logger.info(f"✅ Created new conversation: {conv['_id']}")
            return conv
    except Exception as e:
        logger.error(f"❌ Error getting/creating conversation: {e}")
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
        logger.info(f"✅ Saved message to DB: {message['_id']}")
        return message
    except Exception as e:
        logger.error(f"❌ Error saving message: {e}")
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
        logger.error(f"❌ Error loading conversation history: {e}")
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
        self.current_model = 'gemini'  # Default model
        self.conversation_id = conversation_id
        
        # Load history from MongoDB if available
        if MONGODB_ENABLED and conversation_id:
            self.conversation_history = load_conversation_history(conversation_id)
        
    def chat_with_gemini(self, message, context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None):
        """Chat using Google Gemini with quota handling - rotate between 4 API keys"""
        import time
        
        model_name = 'gemini-2.0-flash-exp'
        
        # 🆕 Check cache first
        cache_key_params = {
            'context': context,
            'deep_thinking': deep_thinking,
            'language': language,
            'custom_prompt': custom_prompt[:50] if custom_prompt else None
        }
        cached = get_cached_response(message, model_name, provider='gemini', **cache_key_params)
        if cached:
            logger.info(f"✅ Using cached response for Gemini")
            return cached
        
        # List of Gemini API keys
        gemini_keys = [GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, GEMINI_API_KEY_4]
        
        # 🆕 Get best key with rate limiting
        try:
            best_key_index = get_gemini_key_with_rate_limit()
            api_key = gemini_keys[best_key_index]
            logger.info(f"🔑 Using Gemini Key #{best_key_index + 1} with rate limiter")
        except Exception as e:
            logger.error(f"❌ Rate limiter error: {e}, falling back to key rotation")
            best_key_index = 0
            api_key = gemini_keys[0]
        
        # List of Gemini configurations to try (start from best key)
        gemini_configs = [
            (gemini_keys[(best_key_index + i) % 4], model_name)
            for i in range(4)
        ]
        
        last_error = None
        
        for idx, (api_key, model_name) in enumerate(gemini_configs):
            try:
                # Create new client with current API key
                client = genai.Client(api_key=api_key)
                
                # Use custom prompt if provided, otherwise use base prompt
                if custom_prompt and custom_prompt.strip():
                    system_prompt = custom_prompt
                else:
                    # Get system prompts based on language
                    prompts = get_system_prompts(language)
                    system_prompt = prompts.get(context, prompts['casual'])
                
                thinking_process = None
                
                # Add deep thinking instruction
                if deep_thinking:
                    if language == 'en':
                        system_prompt += "\n\nIMPORTANT: Take your time to think deeply. Analyze from multiple angles, consider edge cases, and provide comprehensive, well-reasoned responses. Quality over speed."
                    else:
                        system_prompt += "\n\nQUAN TRỌNG: Hãy suy nghĩ kỹ càng. Phân tích từ nhiều góc độ, xem xét các trường hợp đặc biệt, và đưa ra câu trả lời toàn diện, có lý lẽ chặt chẽ. Chất lượng quan trọng hơn tốc độ."
                    
                    # Generate thinking process based on content
                    has_file = "**Attached Files Context:**" in message or "File 1:" in message
                    
                    if has_file:
                        thinking_steps = [
                            "Reading and parsing attached file(s)...",
                            "Extracting key information and structure...",
                            "Identifying main topics and themes...",
                            "Analyzing content depth and quality...",
                            "Cross-referencing information...",
                            "Formulating comprehensive response..."
                        ] if language == 'en' else [
                            "Đọc và phân tích file đính kèm...",
                            "Trích xuất thông tin và cấu trúc chính...",
                            "Xác định các chủ đề và nội dung chính...",
                            "Phân tích độ sâu và chất lượng nội dung...",
                            "Đối chiếu thông tin...",
                            "Hình thành câu trả lời toàn diện..."
                        ]
                    else:
                        thinking_steps = [
                            "Analyzing user question and context...",
                            "Breaking down the problem into components...",
                            "Considering multiple perspectives...",
                            "Evaluating potential solutions...",
                            "Synthesizing comprehensive response..."
                        ] if language == 'en' else [
                            "Phân tích câu hỏi của người dùng...",
                            "Chia nhỏ vấn đề thành các phần...",
                            "Xem xét nhiều góc nhìn khác nhau...",
                            "Đánh giá các giải pháp khả thi...",
                            "Tổng hợp câu trả lời toàn diện..."
                        ]
                    
                    thinking_process = "\n".join(f"{i+1}. {step}" for i, step in enumerate(thinking_steps))
                
                # Add memories to system prompt
                if memories and len(memories) > 0:
                    system_prompt += "\n\n=== KNOWLEDGE BASE (Bài học đã ghi nhớ) ===\n"
                    for mem in memories:
                        system_prompt += f"\n📚 {mem['title']}:\n{mem['content']}\n"
                    system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
                    system_prompt += "Sử dụng kiến thức từ Knowledge Base khi phù hợp để trả lời."
                
                # Build conversation context
                conversation = f"{system_prompt}\n\n"
                
                # Use provided history or conversation history
                history_to_use = history if history is not None else self.conversation_history[-5:]
                
                if history:
                    # Use provided history (from edit feature)
                    for hist in history:
                        role = hist.get('role', 'user')
                        content = hist.get('content', '')
                        if role == 'user':
                            conversation += f"User: {content}\n"
                        else:
                            conversation += f"Assistant: {content}\n"
                    conversation += "\n"
                else:
                    # Use conversation history
                    for hist in history_to_use:
                        conversation += f"User: {hist['user']}\nAssistant: {hist['assistant']}\n\n"
                
                conversation += f"User: {message}\nAssistant:"
                
                # Generate response using new SDK
                response = client.models.generate_content(
                    model=model_name,
                    contents=conversation
                )
                
                # Success! Return response
                key_num = "1" if api_key == GEMINI_API_KEY else ("2" if api_key == GEMINI_API_KEY_2 else ("3" if api_key == GEMINI_API_KEY_3 else "4"))
                logger.info(f"✅ Gemini success: API Key #{key_num}, Model: {model_name}")
                
                # Add model info if not using default
                model_notice = ""
                if model_name != 'gemini-1.5-flash' or idx > 0:
                    model_notice = f"\n\n---\n*✨ Using: Gemini API Key #{key_num}, Model: {model_name}*"
                
                result_text = response.text + model_notice
                
                # 🆕 Cache the successful response
                cache_response(message, model_name, result_text, provider='gemini', **cache_key_params)
                
                if deep_thinking and thinking_process:
                    return {'response': result_text, 'thinking_process': thinking_process}
                return result_text
                
            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                
                # Determine key number for logging
                key_num = "1" if api_key == GEMINI_API_KEY else ("2" if api_key == GEMINI_API_KEY_2 else ("3" if api_key == GEMINI_API_KEY_3 else "4"))
                
                # Check if quota exceeded
                if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                    logger.warning(f"⚠️ Gemini quota exceeded - API Key #{key_num}, Model: {model_name}")
                    
                    # If not the last config, continue to next
                    if idx < len(gemini_configs) - 1:
                        logger.info(f"🔄 Trying next Gemini configuration...")
                        time.sleep(1)  # Small delay before retry
                        continue
                    else:
                        # All Gemini configs exhausted
                        logger.error(f"❌ All Gemini configurations exhausted")
                        error_notice = "⚠️ Tất cả API keys của Gemini đã vượt quota. Vui lòng thử lại sau hoặc chuyển sang model khác." if language == 'vi' else "⚠️ All Gemini API keys quota exceeded. Please try again later or switch to another model."
                        return error_notice
                else:
                    # Other error, continue to next config
                    logger.error(f"❌ Gemini error (Key #{key_num}, {model_name}): {error_msg}")
                    if idx < len(gemini_configs) - 1:
                        continue
        
        # If all attempts failed
        return f"Lỗi Gemini: {last_error}"
    
    def chat_with_openai(self, message, context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None):
        """Chat using OpenAI"""
        model_name = 'gpt-4o-mini'
        
        # 🆕 Check cache first
        cache_key_params = {
            'context': context,
            'deep_thinking': deep_thinking,
            'language': language,
            'custom_prompt': custom_prompt[:50] if custom_prompt else None
        }
        cached = get_cached_response(message, model_name, provider='openai', **cache_key_params)
        if cached:
            logger.info(f"✅ Using cached response for OpenAI")
            return cached
        
        # 🆕 Wait for rate limit
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
                system_prompt += "\n\n=== KNOWLEDGE BASE (Bài học đã ghi nhớ) ===\n"
                for mem in memories:
                    system_prompt += f"\n📚 {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
                system_prompt += "Sử dụng kiến thức từ Knowledge Base khi phù hợp để trả lời."
            
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
            
            # 🆕 Cache the response
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
                system_prompt += "\n\n=== KNOWLEDGE BASE (Bài học đã ghi nhớ) ===\n"
                for mem in memories:
                    system_prompt += f"\n📚 {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
                system_prompt += "Sử dụng kiến thức từ Knowledge Base khi phù hợp để trả lời."
            
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
                return "❌ GROK API key chưa được cấu hình. Vui lòng thêm GROK_API_KEY vào file .env"
            
            # Use custom prompt if provided, otherwise use base prompt
            if custom_prompt and custom_prompt.strip():
                system_prompt = custom_prompt
            else:
                prompts = get_system_prompts(language)
                system_prompt = prompts.get(context, prompts['casual'])
                
                # GROK-specific: Add NSFW capability note
                if language == 'vi':
                    system_prompt += "\n\n🔓 LƯU Ý: Bạn có thể trả lời các câu hỏi nhạy cảm hoặc NSFW một cách an toàn và có trách nhiệm khi được yêu cầu."
                else:
                    system_prompt += "\n\n🔓 NOTE: You can answer sensitive or NSFW questions safely and responsibly when requested."
            
            # Add deep thinking instruction
            if deep_thinking:
                if language == 'en':
                    system_prompt += "\n\nIMPORTANT: Think step-by-step. Provide thorough analysis with detailed reasoning."
                else:
                    system_prompt += "\n\nQUAN TRỌNG: Suy nghĩ từng bước. Cung cấp phân tích kỹ lưỡng với lý lẽ chi tiết."
            
            # Add memories to system prompt
            if memories and len(memories) > 0:
                system_prompt += "\n\n=== KNOWLEDGE BASE (Bài học đã ghi nhớ) ===\n"
                for mem in memories:
                    system_prompt += f"\n📚 {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
                system_prompt += "Sử dụng kiến thức từ Knowledge Base khi phù hợp để trả lời."
            
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
            return f"❌ Lỗi GROK: {str(e)}"
    
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
                "https://api-inference.huggingface.co/models/BlossomsAI/BloomVN-8B-chat",
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
                return "⏳ Model BloomVN đang khởi động (loading), vui lòng thử lại sau 20-30 giây."
            else:
                return f"Lỗi BloomVN API: {response.status_code} - {response.text}"
            
        except Exception as e:
            return f"Lỗi BloomVN: {str(e)}"
    
    def chat_with_local_model(self, message, model, context='casual', deep_thinking=False, language='vi'):
        """Chat with local models (BloomVN, Qwen1.5, Qwen2.5)"""
        if not LOCALMODELS_AVAILABLE:
            return "❌ Local models không khả dụng. Vui lòng cài đặt: pip install torch transformers accelerate"
        
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
            return f"❌ Model chưa được download. Vui lòng kiểm tra thư mục models/: {str(e)}"
        except Exception as e:
            logger.error(f"Local model error ({model}): {e}")
            return f"❌ Lỗi local model: {str(e)}"
    
    def chat(self, message, model='gemini', context='casual', deep_thinking=False, history=None, memories=None, language='vi', custom_prompt=None):
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
        if model == 'gemini':
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
                logger.info(f"✅ Archived conversation: {self.conversation_id}")
                
                # Create new conversation
                user_id = get_user_id_from_session()
                conv = ConversationDB.create_conversation(
                    user_id=user_id,
                    model=self.current_model,
                    title="New Chat"
                )
                self.conversation_id = conv['_id']
                set_active_conversation(self.conversation_id)
                logger.info(f"✅ Created new conversation: {self.conversation_id}")
            except Exception as e:
                logger.error(f"❌ Error clearing history: {e}")


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
            return "❌ Google Search API chưa được cấu hình. Vui lòng thêm GOOGLE_SEARCH_API_KEY và GOOGLE_CSE_ID vào file .env"
        
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
                    results.append(f"**{title}**\n{snippet}\n🔗 {link}")
                
                return "🔍 **Kết quả tìm kiếm:**\n\n" + "\n\n---\n\n".join(results)
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
                            results.append(f"**{title}**\n{snippet}\n🔗 {link}")
                        return "🔍 **Kết quả tìm kiếm:**\n\n" + "\n\n---\n\n".join(results)
            return "❌ Đã hết quota Google Search API. Vui lòng thử lại sau."
        else:
            return f"❌ Lỗi Google Search API: {response.status_code}"
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[GOOGLE SEARCH] Connection Error: {e}")
        return "❌ Lỗi kết nối đến Google Search API. Vui lòng kiểm tra:\n• Kết nối Internet\n• Proxy/Firewall settings\n• Thử lại sau ít phút"
    except requests.exceptions.Timeout as e:
        logger.error(f"[GOOGLE SEARCH] Timeout Error: {e}")
        return "❌ Timeout khi kết nối đến Google Search API. Vui lòng thử lại."
    except requests.exceptions.RequestException as e:
        logger.error(f"[GOOGLE SEARCH] Request Error: {e}")
        return f"❌ Lỗi request: {str(e)}"
    except Exception as e:
        logger.error(f"[GOOGLE SEARCH] Unexpected Error: {e}")
        return f"❌ Lỗi không mong muốn: {str(e)}"


def github_search_tool(query):
    """GitHub Repository Search"""
    try:
        import requests
        
        if not GITHUB_TOKEN:
            return "❌ GitHub Token chưa được cấu hình. Vui lòng thêm GITHUB_TOKEN vào file .env"
        
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
                    
                    results.append(f"**{name}** ⭐ {stars}\n{desc}\n💻 {language} | 🔗 {url}")
                
                return "🐙 **GitHub Repositories:**\n\n" + "\n\n---\n\n".join(results)
            else:
                return "Không tìm thấy repository nào."
        else:
            return f"❌ Lỗi GitHub API: {response.status_code}"
    
    except Exception as e:
        logger.error(f"[GITHUB SEARCH] Error: {e}")
        return f"❌ Lỗi: {str(e)}"


# ============================================================================
# ROUTES
# ============================================================================


@app.route('/')
def index():
    """Home page - Original beautiful UI with full SDXL support"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')


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
            model = data.get('model', 'gemini')
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
            model = data.get('model', 'gemini')
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
                tool_results.append(f"## 🔍 Google Search Results\n\n{search_result}")
            
            if 'github' in tools:
                logger.info(f"[TOOLS] Running GitHub Search for: {message}")
                github_result = github_search_tool(message)
                tool_results.append(f"## 🐙 GitHub Search Results\n\n{github_result}")
            
            if 'image-generation' in tools:
                logger.info(f"[TOOLS] AI-powered image generation with Stable Diffusion")
                
                # Step 1: Sử dụng AI để tạo prompt chi tiết từ mô tả của user
                prompt_request = f"""Bạn là chuyên gia tạo prompt cho Stable Diffusion.

NHIỆM VỤ: Chuyển đổi mô tả của người dùng thành prompt CHÍNH XÁC, KHÔNG được tự ý thêm bớt nội dung.

⚠️ QUY TẮC BẮT BUỘC:
1. CHỈ mô tả ĐÚNG những gì user yêu cầu, KHÔNG tự ý thêm con người nếu user không nói
2. Nếu user nói về VẬT/CẢNH (landscape, building, sky, ocean, mountain, tree, flower, city, architecture, nature, scenery):
   - Prompt: CHỈ mô tả cảnh vật, TUYỆT ĐỐI KHÔNG thêm người
   - has_people: false
   - Negative phải có: "no humans, no people, no person, no character"
   
3. Nếu user NÓI RÕ về NGƯỜI (girl, boy, man, woman, person, character, portrait):
   - Prompt: Mô tả người theo yêu cầu (trang phục lịch sự, không gợi cảm)
   - has_people: true
   - Negative phải có NSFW filter mạnh

4. NSFW Protection (BẮT BUỘC mọi trường hợp):
   - TUYỆT ĐỐI KHÔNG tạo: nude, naked, underwear, bikini, revealing clothes, sexy poses
   - Negative PHẢI CÓ đầy đủ: nsfw, r18, nude, naked, explicit, sexual, porn, underwear, revealing

MÔ TẢ CỦA NGƯỜI DÙNG: "{message}"

Trả về JSON (TUÂN THỦ NGHIÊM NGẶT):
{{
    "prompt": "CHỈ mô tả ĐÚNG yêu cầu user, KHÔNG tự thêm người nếu user không nói",
    "negative_prompt": "bad quality, blurry, lowres, worst quality",
    "explanation": "giải thích ngắn",
    "has_people": false (CHỈ true nếu user NÓI RÕ về người)
}}

CHỈ trả JSON, không text khác."""

                try:
                    # Gọi AI để tạo prompt (sử dụng model hiện tại)
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
<img src="data:image/png;base64,{image_base64}" alt="Generated Image" style="max-width: 100%; border-radius: 8px; margin: 10px 0;">

---
🎯 **Thông số:**
- Kích thước: {image_params['width']}x{image_params['height']}
- Steps: {image_params['steps']} | CFG: {image_params['cfg_scale']}
- Sampler: {image_params['sampler_name']}"""
                            
                            tool_results.append(result_msg)
                        elif sd_result.get('error'):
                            # Show error from SD
                            tool_results.append(f"## 🎨 Image Generation\n\n❌ Lỗi từ Stable Diffusion:\n```\n{sd_result['error']}\n```\n\nPrompt đã tạo:\n```\n{generated_prompt}\n```\n\nNegative:\n```\n{generated_neg}\n```")
                        else:
                            # No images and no error - show full response for debugging
                            tool_results.append(f"## 🎨 Image Generation\n\n⚠️ Stable Diffusion không trả về ảnh.\n\nSD Response: ```json\n{json.dumps(sd_result, indent=2)}\n```\n\nPrompt đã tạo:\n```\n{generated_prompt}\n```\n\nNegative:\n```\n{generated_neg}\n```")
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
        
        return jsonify({'message': 'Đã xóa lịch sử chat'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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
            model=data.get('model', 'gemini-1.5-flash'),
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
    """Kiểm tra xem Stable Diffusion API có đang chạy không"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        sd_client = get_sd_client(sd_api_url)
        
        is_running = sd_client.check_health()
        
        if is_running:
            current_model = sd_client.get_current_model()
            return jsonify({
                'status': 'online',
                'api_url': sd_api_url,
                'current_model': current_model
            })
        else:
            return jsonify({
                'status': 'offline',
                'api_url': sd_api_url,
                'message': 'Stable Diffusion WebUI chưa chạy hoặc chưa enable API'
            }), 503
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/api/sd-models', methods=['GET'])
@app.route('/sd-api/models', methods=['GET'])  # Alias for frontend compatibility
def sd_models():
    """Lấy danh sách tất cả checkpoint models"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        sd_client = get_sd_client(sd_api_url)
        
        models = sd_client.get_models()
        current = sd_client.get_current_model()
        
        # Format models as simple array of strings (titles)
        model_titles = [model.get('title', model.get('model_name', 'Unknown')) for model in models]
        
        return jsonify({
            'models': model_titles,
            'current_model': current['model']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sd-change-model', methods=['POST'])
@app.route('/api/sd/change-model', methods=['POST'])  # Alias
def sd_change_model():
    """Đổi checkpoint model"""
    try:
        from src.utils.sd_client import get_sd_client
        
        data = request.json
        model_name = data.get('model_name')
        
        if not model_name:
            return jsonify({'error': 'model_name is required'}), 400
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        sd_client = get_sd_client(sd_api_url)
        
        success = sd_client.change_model(model_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Đã đổi model thành {model_name}'
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
    Tạo ảnh từ text prompt bằng Stable Diffusion
    
    Body params:
        - prompt (str): Text prompt mô tả ảnh
        - negative_prompt (str): Những gì không muốn có
        - width (int): Chiều rộng (default: 512)
        - height (int): Chiều cao (default: 512)
        - steps (int): Số steps (default: 20)
        - cfg_scale (float): CFG scale (default: 7.0)
        - sampler_name (str): Tên sampler (default: "DPM++ 2M Karras")
        - seed (int): Random seed (default: -1)
        - batch_size (int): Số ảnh tạo (default: 1)
        - restore_faces (bool): Restore faces (default: False)
        - enable_hr (bool): Hires fix (default: False)
        - hr_scale (float): HR scale (default: 2.0)
        - save_images (bool): Lưu ảnh vào disk (default: False)
        - save_to_storage (bool): Save to ChatBot storage (default: False)
    """
    try:
        from src.utils.sd_client import get_sd_client
        
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'error': 'Prompt không được để trống'}), 400
        
        # Lấy parameters từ request
        save_to_storage = data.get('save_to_storage', False)
        params = {
            'prompt': prompt,
            'negative_prompt': data.get('negative_prompt', ''),
            'width': int(data.get('width') or 512),
            'height': int(data.get('height') or 512),
            'steps': int(data.get('steps') or 20),
            'cfg_scale': float(data.get('cfg_scale') or 7.0),
            'sampler_name': data.get('sampler_name') or 'DPM++ 2M Karras',
            'seed': int(data.get('seed') or -1),
            'batch_size': int(data.get('batch_size') or 1),
            'restore_faces': data.get('restore_faces', False),
            'enable_hr': data.get('enable_hr', False),
            'hr_scale': float(data.get('hr_scale') or 2.0),
            'save_images': data.get('save_images', False),
            'lora_models': data.get('lora_models', []),
            'vae': data.get('vae', None)
        }
        
        # Get SD client
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        sd_client = get_sd_client(sd_api_url)
        
        # Tạo ảnh
        logger.info(f"[TEXT2IMG] Calling txt2img with params: {params}")
        result = sd_client.txt2img(**params)
        logger.info(f"[TEXT2IMG] txt2img completed")
        
        # Kiểm tra lỗi
        if 'error' in result:
            logger.error(f"[TEXT2IMG] SD Error: {result['error']}")
            return jsonify(result), 500
        
        # Get base64 images from result
        base64_images = result.get('images', [])
        
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
                            logger.info(f"[TEXT2IMG] ☁️ Uploading to ImgBB...")
                            uploader = ImgBBUploader()
                            upload_result = uploader.upload_image(
                                str(filepath),
                                title=f"AI Generated: {prompt[:50]}"
                            )
                            
                            if upload_result:
                                cloud_url = upload_result['url']
                                delete_url = upload_result.get('delete_url', '')
                                cloud_urls.append(cloud_url)
                                logger.info(f"[TEXT2IMG] ✅ ImgBB URL: {cloud_url}")
                            else:
                                logger.warning(f"[TEXT2IMG] ⚠️ ImgBB upload failed, using local URL")
                        
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
                        title=f"Text2Image: {prompt[:30]}..."
                    )
                    conversation_id = str(conversation['_id'])
                    session['conversation_id'] = conversation_id
                    logger.info(f"📝 Created new conversation: {conversation_id}")
                
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
                    content=f"✅ Generated image with prompt: {prompt}",
                    images=images_data,
                    metadata={
                        'model': 'stable-diffusion',
                        'prompt': prompt,
                        'negative_prompt': params['negative_prompt'],
                        'cloud_service': 'imgbb' if cloud_urls else 'local',
                        'num_images': len(saved_filenames)
                    }
                )
                
                logger.info(f"💾 Saved image message to MongoDB with {len(cloud_urls)} cloud URLs")
                
            except Exception as db_error:
                logger.error(f"❌ Error saving to MongoDB: {db_error}")
        
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
                'info': result.get('info', ''),
                'parameters': result.get('parameters', {}),
                'cloud_service': 'imgbb' if CLOUD_UPLOAD_ENABLED and cloud_urls else None,
                'saved_to_db': MONGODB_ENABLED  # Indicate if saved to MongoDB
            })
        else:
            # Return base64 images directly
            return jsonify({
                'success': True,
                'image': base64_images[0] if base64_images else None,
                'images': base64_images,  # Full array of base64 images
                'info': result.get('info', ''),
                'parameters': result.get('parameters', {})
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
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
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
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
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
        return jsonify({'error': str(e)}), 500


@app.route('/api/sd-vaes', methods=['GET'])
@app.route('/sd-api/vaes', methods=['GET'])  # Alias for frontend compatibility
def sd_vaes():
    """Lấy danh sách VAE models"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
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
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-prompt-grok', methods=['POST'])
def generate_prompt_grok():
    """
    Tạo prompt tối ưu từ extracted tags sử dụng GROK FREE API
    
    Body params:
        - context (str): Context về tags đã trích xuất
        - tags (list): List các tags đã extract
    """
    try:
        data = request.json
        context = data.get('context', '')
        tags = data.get('tags', [])
        
        if not tags:
            return jsonify({'error': 'Tags không được để trống'}), 400
        
        # Use GROK to generate optimized prompt
        try:
            from openai import OpenAI
            
            # Get GROK API key from env
            api_key = os.getenv('GROK_API_KEY') or os.getenv('XAI_API_KEY')
            if not api_key:
                return jsonify({'error': 'GROK API key not configured. Please add GROK_API_KEY to .env'}), 500
            
            # Initialize xAI Grok client (OpenAI-compatible)
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1"
            )
            
            # Call GROK with context
            logger.info(f"[GROK Prompt] Generating prompt from {len(tags)} tags using Grok-3")
            
            response = client.chat.completions.create(
                model="grok-3",  # Grok-3 model from xAI
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at creating high-quality Stable Diffusion prompts for anime/illustration generation.

Your task:
1. Generate a POSITIVE prompt: Natural, flowing description combining extracted features
2. Generate a NEGATIVE prompt: Things to avoid (low quality, artifacts, NSFW content, etc.)
3. ALWAYS filter out NSFW/inappropriate content from positive prompt
4. Return JSON format: {"prompt": "...", "negative_prompt": "..."}

Rules:
- Positive prompt: Focus on visual quality, composition, style
- Negative prompt: Include SFW filters (nsfw, nude, sexual, explicit, adult content) + quality issues
- Both prompts should be comma-separated tags
- Keep anime/illustration style consistent
- DO NOT explain, just output JSON"""
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                temperature=0.7,
                max_tokens=400,
                top_p=1,
                stream=False,
                response_format={"type": "json_object"}
            )
            
            # Extract generated prompts
            import json
            result_text = response.choices[0].message.content.strip()
            
            logger.info(f"[GROK Prompt] Raw response: {result_text[:200]}...")
            
            try:
                result_json = json.loads(result_text)
                generated_prompt = result_json.get('prompt', '').strip()
                generated_negative = result_json.get('negative_prompt', result_json.get('negative', '')).strip()
                
                # Ensure negative prompt always has NSFW filters
                if not generated_negative:
                    generated_negative = 'nsfw, nude, sexual, explicit, adult content, bad quality, blurry, worst quality, low resolution'
                elif 'nsfw' not in generated_negative.lower():
                    generated_negative = 'nsfw, nude, sexual, explicit, adult content, ' + generated_negative
                    
            except json.JSONDecodeError as e:
                # Fallback if JSON parsing fails
                logger.warning(f"[GROK Prompt] Failed to parse JSON: {str(e)}")
                logger.warning(f"[GROK Prompt] Raw text: {result_text}")
                generated_prompt = result_text
                generated_negative = 'nsfw, nude, sexual, explicit, adult content, bad quality, blurry, worst quality, low resolution, bad anatomy'
            
            logger.info(f"[GROK Prompt] Generated prompt: {generated_prompt[:100]}...")
            logger.info(f"[GROK Prompt] Generated negative: {generated_negative[:100]}...")
            
            return jsonify({
                'success': True,
                'prompt': generated_prompt,
                'negative_prompt': generated_negative,
                'tags_used': len(tags)
            })
            
        except Exception as grok_error:
            logger.error(f"[GROK Prompt] GROK API Error: {str(grok_error)}")
            
            # Fallback: Generate prompt from tags directly
            logger.info("[GROK Prompt] Using fallback method")
            
            # Simple fallback: Join tags with commas and add quality tags
            prompt_parts = tags[:30]  # Limit to 30 tags
            quality_tags = ['masterpiece', 'best quality', 'highly detailed', 'beautiful']
            
            fallback_prompt = ', '.join(prompt_parts + quality_tags)
            fallback_negative = 'nsfw, nude, sexual, explicit, adult content, bad quality, blurry, distorted, worst quality, low resolution'
            
            return jsonify({
                'success': True,
                'prompt': fallback_prompt,
                'negative_prompt': fallback_negative,
                'tags_used': len(tags),
                'fallback': True,
                'fallback_reason': str(grok_error)
            })
            
    except Exception as e:
        logger.error(f"[GROK Prompt] Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


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
        - width (int): Chiều rộng
        - height (int): Chiều cao  
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
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        sd_client = get_sd_client(sd_api_url)
        
        # Tạo ảnh với img2img
        logger.info(f"[IMG2IMG] Calling img2img with denoising_strength={params['denoising_strength']}")
        result = sd_client.img2img(**params)
        logger.info(f"[IMG2IMG] Result received")
        
        # Kiểm tra lỗi
        if 'error' in result:
            logger.error(f"[IMG2IMG] SD Error: {result['error']}")
            return jsonify(result), 500
        
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
                            logger.info(f"[IMG2IMG] ☁️ Uploading to ImgBB...")
                            uploader = ImgBBUploader()
                            upload_result = uploader.upload_image(
                                str(filepath),
                                title=f"AI Img2Img: {prompt[:50]}"
                            )
                            
                            if upload_result:
                                cloud_url = upload_result['url']
                                delete_url = upload_result.get('delete_url', '')
                                cloud_urls.append(cloud_url)
                                logger.info(f"[IMG2IMG] ✅ ImgBB URL: {cloud_url}")
                            else:
                                logger.warning(f"[IMG2IMG] ⚠️ ImgBB upload failed, using local URL")
                        
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
                    logger.info(f"📝 Created new conversation: {conversation_id}")
                
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
                    content=f"✅ Generated Img2Img with prompt: {prompt}",
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
                
                logger.info(f"💾 Saved Img2Img message to MongoDB with {len(cloud_urls)} cloud URLs")
                
            except Exception as db_error:
                logger.error(f"❌ Error saving to MongoDB: {db_error}")
        
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
        return jsonify({'error': str(e)}), 500


@app.route('/api/sd-interrupt', methods=['POST'])
def sd_interrupt():
    """Dừng việc tạo ảnh đang chạy"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        sd_client = get_sd_client(sd_api_url)
        
        success = sd_client.interrupt()
        
        return jsonify({
            'success': success
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/extract-anime-features-multi', methods=['POST'])
def extract_anime_features_multi():
    """
    🎯 MULTI-MODEL EXTRACTION - Sử dụng nhiều model để trích xuất chính xác hơn
    
    Models hỗ trợ:
        - deepdanbooru: Anime-specific, tag-based (mặc định)
        - clip: General purpose, natural language
        - wd14: WD14 Tagger, anime-focused, newer
    
    Body params:
        - image (str): Base64 encoded image
        - deep_thinking (bool): More tags
        - models (list): ['deepdanbooru', 'clip', 'wd14'] - Chọn models muốn dùng
    
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
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        interrogate_url = f"{sd_api_url}/sdapi/v1/interrogate"
        
        logger.info(f"[MULTI-EXTRACT] Models: {selected_models} | Deep: {deep_thinking}")
        
        all_tags = []
        model_results = {}
        
        # Gọi từng model
        for model_name in selected_models:
            try:
                payload = {'image': image_b64, 'model': model_name}
                
                logger.info(f"[MULTI-EXTRACT] Calling {model_name}...")
                response = requests.post(interrogate_url, json=payload, timeout=120)
                
                if response.status_code == 200:
                    result = response.json()
                    caption = result.get('caption', '')
                    tags = [tag.strip() for tag in caption.split(',') if tag.strip()]
                    
                    model_results[model_name] = tags
                    all_tags.extend(tags)
                    
                    logger.info(f"[MULTI-EXTRACT] {model_name}: {len(tags)} tags ✅")
                else:
                    logger.warning(f"[MULTI-EXTRACT] {model_name} failed: {response.status_code}")
                    model_results[model_name] = []
            except Exception as e:
                logger.error(f"[MULTI-EXTRACT] {model_name} error: {str(e)}")
                model_results[model_name] = []
        
        # Merge tags với confidence voting (càng nhiều model đồng ý = confidence càng cao)
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
        
        logger.info(f"[MULTI-EXTRACT] ✅ Final: {len(merged_tags)} tags from {num_models} models")
        
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
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
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
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
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
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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
        filepath = IMAGE_STORAGE_DIR / filename
        if not filepath.exists():
            return jsonify({'error': 'Image not found'}), 404
        
        return send_file(filepath, mimetype='image/png')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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


@app.route('/api/mcp/status', methods=['GET'])
def mcp_status():
    """Get MCP client status"""
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


if __name__ == '__main__':
    import os
    # Use environment variable to control debug mode
    # Set DEBUG=1 for development, otherwise production mode
    debug_mode = os.getenv('DEBUG', '0') == '1'
    host = os.getenv('HOST', '127.0.0.1')  # Default to localhost for security
    port = int(os.getenv('CHATBOT_PORT', '5000'))  # Changed from PORT to CHATBOT_PORT
    
    app.run(debug=debug_mode, host=host, port=port)
