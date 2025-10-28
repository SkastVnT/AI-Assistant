"""
AI ChatBot Agent - Hỗ trợ tâm lý, tâm sự và giải pháp đời sống
Sử dụng Gemini, DeepSeek, và OpenAI
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

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Configure API keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY_1')
GEMINI_API_KEY_2 = os.getenv('GEMINI_API_KEY_2')

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
        
    def chat_with_gemini(self, message, context='casual', deep_thinking=False):
        """Chat using Google Gemini"""
        try:
            # Use gemini-2.0-flash (newest stable model)
            model = genai.GenerativeModel('gemini-2.0-flash')
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            # Add deep thinking instruction
            if deep_thinking:
                system_prompt += "\n\nIMPORTANT: Take your time to think deeply. Analyze from multiple angles, consider edge cases, and provide comprehensive, well-reasoned responses. Quality over speed."
            
            # Build conversation context
            conversation = f"{system_prompt}\n\n"
            for hist in self.conversation_history[-5:]:  # Last 5 messages
                conversation += f"User: {hist['user']}\nAssistant: {hist['assistant']}\n\n"
            conversation += f"User: {message}\nAssistant:"
            
            response = model.generate_content(conversation)
            return response.text
            
        except Exception as e:
            return f"Lỗi Gemini: {str(e)}"
    
    def chat_with_openai(self, message, context='casual', deep_thinking=False):
        """Chat using OpenAI"""
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            # Add deep thinking instruction
            if deep_thinking:
                system_prompt += "\n\nIMPORTANT: Think step-by-step. Provide thorough analysis with detailed reasoning."
            
            messages = [{"role": "system", "content": system_prompt}]
            
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
    
    def chat_with_deepseek(self, message, context='casual', deep_thinking=False):
        """Chat using DeepSeek (via OpenAI compatible API)"""
        try:
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            # Add deep thinking instruction
            if deep_thinking:
                system_prompt += "\n\nIMPORTANT: Analyze deeply with comprehensive reasoning."
            
            # DeepSeek uses OpenAI compatible API
            client = openai.OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com/v1"
            )
            
            messages = [{"role": "system", "content": system_prompt}]
            
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
    
    def chat(self, message, model='gemini', context='casual', deep_thinking=False):
        """Main chat method"""
        if model == 'gemini':
            response = self.chat_with_gemini(message, context, deep_thinking)
        elif model == 'openai':
            response = self.chat_with_openai(message, context, deep_thinking)
        elif model == 'deepseek':
            response = self.chat_with_deepseek(message, context, deep_thinking)
        else:
            response = "Model không được hỗ trợ."
        
        # Save to conversation history
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


@app.route('/')
def index():
    """Home page"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint"""
    try:
        data = request.json
        message = data.get('message', '')
        model = data.get('model', 'gemini')
        context = data.get('context', 'casual')
        deep_thinking = data.get('deep_thinking', False)
        tools = data.get('tools', [])
        
        if not message:
            return jsonify({'error': 'Tin nhắn trống'}), 400
        
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        
        response = chatbot.chat(message, model, context, deep_thinking)
        
        return jsonify({
            'response': response,
            'model': model,
            'context': context,
            'deep_thinking': deep_thinking,
            'tools': tools,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
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
            'width': int(data.get('width', 512)),
            'height': int(data.get('height', 512)),
            'steps': int(data.get('steps', 20)),
            'cfg_scale': float(data.get('cfg_scale', 7.0)),
            'sampler_name': data.get('sampler_name', 'DPM++ 2M Karras'),
            'seed': int(data.get('seed', -1)),
            'batch_size': int(data.get('batch_size', 1)),
            'restore_faces': data.get('restore_faces', False),
            'enable_hr': data.get('enable_hr', False),
            'hr_scale': float(data.get('hr_scale', 2.0)),
            'save_images': data.get('save_images', False)
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
