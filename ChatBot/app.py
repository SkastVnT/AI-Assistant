"""
AI ChatBot Agent - Hỗ trợ tâm lý, tâm sự và giải pháp đời sống
Sử dụng Gemini, DeepSeek, OpenAI, Qwen, BloomVN và Local Models
"""

import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, send_file
import openai
import google.generativeai as genai
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

# Import local model loader
try:
    from src.utils.local_model_loader import model_loader
    LOCALMODELS_AVAILABLE = True
    logger.info("✅ Local model loader imported successfully")
except Exception as e:
    LOCALMODELS_AVAILABLE = False
    logger.warning(f"⚠️ Local models not available: {e}")

# Initialize Flask app with static folder
app = Flask(__name__, 
            static_folder='static',
            static_url_path='/static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

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
QWEN_API_KEY = os.getenv('QWEN_API_KEY')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')

# Google Search API
GOOGLE_SEARCH_API_KEY_1 = os.getenv('GOOGLE_SEARCH_API_KEY_1')
GOOGLE_SEARCH_API_KEY_2 = os.getenv('GOOGLE_SEARCH_API_KEY_2')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')

# GitHub API
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

# Configure Gemini - try both keys
try:
    genai.configure(api_key=GEMINI_API_KEY)
except:
    genai.configure(api_key=GEMINI_API_KEY_2)

# System prompts for different purposes
SYSTEM_PROMPTS = {
    'psychological': """Bạn là một trợ lý tâm lý chuyên nghiệp, thân thiện và đầy empathy. 
    Bạn luôn lắng nghe, thấu hiểu và đưa ra lời khuyên chân thành, tích cực.
    Bạn không phán xét và luôn hỗ trợ người dùng vượt qua khó khăn trong cuộc sống.
    Hãy trả lời bằng tiếng Việt.""",
    
    'lifestyle': """Bạn là một chuyên gia tư vấn lối sống, giúp người dùng tìm ra giải pháp 
    cho các vấn đề trong cuộc sống hàng ngày như công việc, học tập, mối quan hệ, 
    sức khỏe và phát triển bản thân. Hãy đưa ra lời khuyên thiết thực và dễ áp dụng.
    Hãy trả lời bằng tiếng Việt.""",
    
    'casual': """Bạn là một người bạn thân thiết, vui vẻ và dễ gần. 
    Bạn sẵn sàng trò chuyện về mọi chủ đề, chia sẻ câu chuyện và tạo không khí thoải mái.
    Hãy trả lời bằng tiếng Việt với giọng điệu thân mật.""",
    
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
    
    Luôn format code với markdown (```language), giải thích từng bước logic, 
    và đưa ra ví dụ cụ thể. Có thể trả lời bằng tiếng Việt hoặc English."""
}


class ChatbotAgent:
    """Multi-model chatbot agent"""
    
    def __init__(self):
        self.conversation_history = []
        self.current_model = 'gemini'  # Default model
        
    def chat_with_gemini(self, message, context='casual', deep_thinking=False, history=None, memories=None):
        """Chat using Google Gemini"""
        try:
            # Use gemini-2.0-flash (newest stable model)
            model = genai.GenerativeModel('gemini-2.0-flash')
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            # Add deep thinking instruction
            if deep_thinking:
                system_prompt += "\n\nIMPORTANT: Take your time to think deeply. Analyze from multiple angles, consider edge cases, and provide comprehensive, well-reasoned responses. Quality over speed."
            
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
            
            response = model.generate_content(conversation)
            return response.text
            
        except Exception as e:
            return f"Lỗi Gemini: {str(e)}"
    
    def chat_with_openai(self, message, context='casual', deep_thinking=False, history=None, memories=None):
        """Chat using OpenAI"""
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            # Add deep thinking instruction
            if deep_thinking:
                system_prompt += "\n\nIMPORTANT: Think step-by-step. Provide thorough analysis with detailed reasoning."
            
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
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Lỗi OpenAI: {str(e)}"
    
    def chat_with_deepseek(self, message, context='casual', deep_thinking=False, history=None, memories=None):
        """Chat using DeepSeek (via OpenAI compatible API)"""
        try:
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
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
    
    def chat_with_qwen(self, message, context='casual', deep_thinking=False):
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
    
    def chat_with_bloomvn(self, message, context='casual', deep_thinking=False):
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
    
    def chat_with_local_model(self, message, model, context='casual', deep_thinking=False):
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
    
    def chat(self, message, model='gemini', context='casual', deep_thinking=False, history=None, memories=None):
        """Main chat method"""
        if model == 'gemini':
            response = self.chat_with_gemini(message, context, deep_thinking, history, memories)
        elif model == 'openai':
            response = self.chat_with_openai(message, context, deep_thinking, history, memories)
        elif model == 'deepseek':
            response = self.chat_with_deepseek(message, context, deep_thinking, history, memories)
        elif model == 'qwen':
            response = self.chat_with_qwen(message, context, deep_thinking)
        elif model == 'bloomvn':
            response = self.chat_with_bloomvn(message, context, deep_thinking)
        elif model in ['bloomvn-local', 'qwen1.5-local', 'qwen2.5-local']:
            response = self.chat_with_local_model(message, model, context, deep_thinking)
        else:
            response = "Model không được hỗ trợ."
        
        # Only save to conversation history if no custom history provided
        if history is None:
            self.conversation_history.append({
                'user': message,
                'assistant': response,
                'timestamp': datetime.now().isoformat(),
                'model': model,
                'context': context,
                'deep_thinking': deep_thinking
            })
        
        return response
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []


# Store chatbot instances per session
chatbots = {}


def get_chatbot(session_id):
    """Get or create chatbot for session"""
    if session_id not in chatbots:
        chatbots[session_id] = ChatbotAgent()
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
    """Home page - Original beautiful UI"""
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
            tools = data.get('tools', [])
            history = data.get('history', None)
            memory_ids = data.get('memory_ids', [])
        
        if not message:
            return jsonify({'error': 'Tin nhắn trống'}), 400
        
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
            response = chatbot.chat(message, model, context, deep_thinking, history, memories)
            # Restore original history (since we don't want to save edit responses to history)
            chatbot.conversation_history = original_history
        else:
            response = chatbot.chat(message, model, context, deep_thinking, None, memories)
        
        return jsonify({
            'response': response,
            'model': model,
            'context': context,
            'deep_thinking': deep_thinking,
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
# STABLE DIFFUSION IMAGE GENERATION ROUTES
# ============================================================================

@app.route('/api/sd-health', methods=['GET'])
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
def sd_models():
    """Lấy danh sách tất cả checkpoint models"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        sd_client = get_sd_client(sd_api_url)
        
        models = sd_client.get_models()
        current = sd_client.get_current_model()
        
        return jsonify({
            'models': models,
            'current_model': current['model']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sd-change-model', methods=['POST'])
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
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-image', methods=['POST'])
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
    """
    try:
        from src.utils.sd_client import get_sd_client
        
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'error': 'Prompt không được để trống'}), 400
        
        # Lấy parameters từ request
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
        print(f"[DEBUG] Calling txt2img with params: {params}")
        result = sd_client.txt2img(**params)
        print(f"[DEBUG] txt2img result: {result}")
        
        # Kiểm tra lỗi
        if 'error' in result:
            print(f"[ERROR] SD Error: {result['error']}")
            return jsonify(result), 500
        
        # Trả về kết quả
        return jsonify({
            'success': True,
            'images': result.get('images', []),
            'info': result.get('info', ''),
            'parameters': result.get('parameters', {})
        })
        
    except Exception as e:
        import traceback
        error_msg = f"Exception: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sd-samplers', methods=['GET'])
def sd_samplers():
    """Lấy danh sách samplers"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        sd_client = get_sd_client(sd_api_url)
        
        samplers = sd_client.get_samplers()
        
        return jsonify({
            'samplers': samplers
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sd-loras', methods=['GET'])
def sd_loras():
    """Lấy danh sách Lora models"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        sd_client = get_sd_client(sd_api_url)
        
        loras = sd_client.get_loras()
        
        return jsonify({
            'loras': loras
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sd-vaes', methods=['GET'])
def sd_vaes():
    """Lấy danh sách VAE models"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
        sd_client = get_sd_client(sd_api_url)
        
        vaes = sd_client.get_vaes()
        
        return jsonify({
            'vaes': vaes
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/img2img', methods=['POST'])
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
        
        # Trả về kết quả
        return jsonify({
            'success': True,
            'images': result.get('images', []),
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


if __name__ == '__main__':
    # debug=False: Tắt auto-reload và debugger (dùng cho production)
    # debug=True: Bật auto-reload khi sửa code (dùng khi develop)
    app.run(debug=True, host='0.0.0.0', port=5000)
