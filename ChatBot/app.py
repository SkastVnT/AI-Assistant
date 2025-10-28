"""
AI ChatBot Agent - Hỗ trợ tâm lý, tâm sự và giải pháp đời sống
Sử dụng Gemini, DeepSeek, và OpenAI
"""

import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session
import openai
import google.generativeai as genai
from datetime import datetime
import uuid

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Configure API keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY_1')

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

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
    Hãy trả lời bằng tiếng Việt với giọng điệu thân mật."""
}


class ChatbotAgent:
    """Multi-model chatbot agent"""
    
    def __init__(self):
        self.conversation_history = []
        self.current_model = 'gemini'  # Default model
        
    def chat_with_gemini(self, message, context='casual'):
        """Chat using Google Gemini"""
        try:
            model = genai.GenerativeModel('gemini-pro')
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            # Build conversation context
            conversation = f"{system_prompt}\n\n"
            for hist in self.conversation_history[-5:]:  # Last 5 messages
                conversation += f"User: {hist['user']}\nAssistant: {hist['assistant']}\n\n"
            conversation += f"User: {message}\nAssistant:"
            
            response = model.generate_content(conversation)
            return response.text
            
        except Exception as e:
            return f"Lỗi Gemini: {str(e)}"
    
    def chat_with_openai(self, message, context='casual'):
        """Chat using OpenAI"""
        try:
            openai.api_key = OPENAI_API_KEY
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            for hist in self.conversation_history[-5:]:
                messages.append({"role": "user", "content": hist['user']})
                messages.append({"role": "assistant", "content": hist['assistant']})
            
            messages.append({"role": "user", "content": message})
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Lỗi OpenAI: {str(e)}"
    
    def chat_with_deepseek(self, message, context='casual'):
        """Chat using DeepSeek (via OpenAI compatible API)"""
        try:
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            # DeepSeek uses OpenAI compatible API
            openai.api_key = DEEPSEEK_API_KEY
            openai.api_base = "https://api.deepseek.com/v1"
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            for hist in self.conversation_history[-5:]:
                messages.append({"role": "user", "content": hist['user']})
                messages.append({"role": "assistant", "content": hist['assistant']})
            
            messages.append({"role": "user", "content": message})
            
            response = openai.ChatCompletion.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Lỗi DeepSeek: {str(e)}"
    
    def chat(self, message, model='gemini', context='casual'):
        """Main chat method"""
        if model == 'gemini':
            response = self.chat_with_gemini(message, context)
        elif model == 'openai':
            response = self.chat_with_openai(message, context)
        elif model == 'deepseek':
            response = self.chat_with_deepseek(message, context)
        else:
            response = "Model không được hỗ trợ."
        
        # Save to conversation history
        self.conversation_history.append({
            'user': message,
            'assistant': response,
            'timestamp': datetime.now().isoformat(),
            'model': model,
            'context': context
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
        
        if not message:
            return jsonify({'error': 'Tin nhắn trống'}), 400
        
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        
        response = chatbot.chat(message, model, context)
        
        return jsonify({
            'response': response,
            'model': model,
            'context': context,
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
