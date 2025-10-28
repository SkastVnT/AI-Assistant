"""
AI Assistant Hub - Main Gateway
Kết nối 3 services: ChatBot, Speech2Text, Text2SQL
"""

from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Service configurations
SERVICES = {
    'chatbot': {
        'name': 'AI ChatBot',
        'description': 'Trợ lý AI hỗ trợ tâm lý, tâm sự và giải pháp đời sống',
        'icon': '🤖',
        'port': 5000,
        'url': 'http://localhost:5000',
        'color': 'from-purple-500 to-pink-500',
        'features': [
            'Hỗ trợ 3 mô hình AI: Gemini, GPT-3.5, DeepSeek',
            'Chat về tâm lý, tâm sự',
            'Tư vấn giải pháp đời sống',
            'Trò chuyện vui vẻ, thân thiện'
        ],
        'status': 'available'
    },
    'speech2text': {
        'name': 'Speech to Text',
        'description': 'Chuyển đổi giọng nói thành văn bản với AI',
        'icon': '🎤',
        'port': 5001,
        'url': 'http://localhost:5001',
        'color': 'from-blue-500 to-cyan-500',
        'features': [
            'Nhận dạng giọng nói tiếng Việt',
            'Hỗ trợ nhiều định dạng audio',
            'Phân tách người nói (Diarization)',
            'Xuất kết quả văn bản'
        ],
        'status': 'available'
    },
    'text2sql': {
        'name': 'Text to SQL',
        'description': 'Chuyển đổi ngôn ngữ tự nhiên thành câu truy vấn SQL',
        'icon': '💾',
        'port': 5002,
        'url': 'http://localhost:5002',
        'color': 'from-green-500 to-emerald-500',
        'features': [
            'Tạo câu SQL từ ngôn ngữ tự nhiên',
            'Hỗ trợ nhiều loại database',
            'Tích hợp Gemini AI',
            'Lưu trữ và học từ lịch sử'
        ],
        'status': 'available'
    }
}

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html', services=SERVICES)

@app.route('/api/services')
def get_services():
    """Get all services information"""
    return jsonify(SERVICES)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'services': len(SERVICES),
        'message': 'AI Assistant Hub is running'
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AI Assistant Hub - Main Gateway")
    print("=" * 60)
    print(f"📍 Hub URL: http://localhost:8080")
    print(f"")
    print(f"📦 Available Services:")
    for key, service in SERVICES.items():
        print(f"   • {service['icon']} {service['name']}: {service['url']}")
    print(f"")
    print(f"💡 Lưu ý: Các services cần chạy riêng trên các port của chúng")
    print(f"   - ChatBot: cd ChatBot && python app.py")
    print(f"   - Speech2Text: cd 'Speech2Text Services'/app && python web_ui.py")
    print(f"   - Text2SQL: cd 'Text2SQL Services' && python app.py")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=8080)
