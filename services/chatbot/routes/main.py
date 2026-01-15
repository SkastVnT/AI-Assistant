"""
Main routes: /, /new, /chat, /clear, /history
"""
import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, session, render_template
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import MEMORY_DIR
from core.extensions import MONGODB_ENABLED, logger
from core.chatbot import get_chatbot
from core.tools import google_search_tool, github_search_tool

# Check MCP availability
MCP_AVAILABLE = False
try:
    from src.handlers.mcp_handler import inject_code_context, get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    pass

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page - Original beautiful UI with full SDXL support"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')


@main_bp.route('/new')
def index_new():
    """New Tailwind version (experimental)"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index_tailwind.html')


@main_bp.route('/chat', methods=['POST'])
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
            language = data.get('language', 'vi')
            custom_prompt = data.get('custom_prompt', '')
            
            # Safe JSON parsing
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
        else:
            # JSON request
            data = request.json
            message = data.get('message', '')
            model = data.get('model', 'grok')
            context = data.get('context', 'casual')
            deep_thinking = data.get('deep_thinking', False)
            language = data.get('language', 'vi')
            custom_prompt = data.get('custom_prompt', '')
            tools = data.get('tools', [])
            history = data.get('history', None)
            memory_ids = data.get('memory_ids', [])
            mcp_selected_files = data.get('mcp_selected_files', [])
        
        if not message:
            return jsonify({'error': 'Tin nhắn trống'}), 400
        
        # MCP Integration: Inject code context
        if MCP_AVAILABLE:
            try:
                mcp_client = get_mcp_client()
                if mcp_client and mcp_client.enabled:
                    logger.info(f"[MCP] Injecting code context")
                    message = inject_code_context(message, mcp_client, mcp_selected_files)
            except Exception as e:
                logger.warning(f"[MCP] Error injecting context: {e}")
        
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        
        # Handle tools
        tool_results = []
        if tools and len(tools) > 0:
            logger.info(f"[TOOLS] Active tools: {tools}")
            
            if 'google-search' in tools:
                search_result = google_search_tool(message)
                tool_results.append(f"## 🔍 Google Search Results\n\n{search_result}")
            
            if 'github' in tools:
                github_result = github_search_tool(message)
                tool_results.append(f"## 🐙 GitHub Search Results\n\n{github_result}")
            
            if 'image-generation' in tools:
                # Handle AI image generation via tools
                tool_results.append(_handle_image_generation_tool(chatbot, message, model))
        
        # Return tool results if any
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
                            memories.append(json.load(f))
                    except Exception as e:
                        logger.error(f"Error loading memory {mem_id}: {e}")
        
        # Process chat
        if history:
            original_history = chatbot.conversation_history.copy()
            result = chatbot.chat(message, model, context, deep_thinking, history, memories, language, custom_prompt)
            chatbot.conversation_history = original_history
        else:
            result = chatbot.chat(message, model, context, deep_thinking, None, memories, language, custom_prompt)
        
        # Extract response
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


@main_bp.route('/clear', methods=['POST'])
def clear():
    """Clear chat history"""
    try:
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        chatbot.clear_history()
        
        return jsonify({'message': 'Đã xóa lịch sử chat'})
        
    except Exception as e:
        logger.error(f"[Clear History] Error: {str(e)}")
        return jsonify({'error': 'Failed to clear chat history'}), 500


@main_bp.route('/history', methods=['GET'])
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


def _handle_image_generation_tool(chatbot, message, model):
    """Handle AI-powered image generation tool"""
    import json
    import re
    
    prompt_request = f"""Bạn là chuyên gia tạo prompt cho Stable Diffusion.

NHIỆM VỤ: Chuyển đổi mô tả của người dùng thành prompt CHÍNH XÁC.

⚠️ QUY TẮC:
1. CHỈ mô tả ĐÚNG những gì user yêu cầu
2. NSFW Protection: TẤT CẢ ảnh phải SFW
3. Negative PHẢI CÓ: nsfw, nude, naked, explicit, sexual

MÔ TẢ: "{message}"

Trả về JSON:
{{
    "prompt": "prompt mô tả",
    "negative_prompt": "bad quality, blurry, nsfw, nude, naked, explicit",
    "explanation": "giải thích ngắn",
    "has_people": false
}}

CHỈ trả JSON."""
    
    try:
        from src.utils.sd_client import get_sd_client
        import os
        
        ai_response = chatbot.chat(prompt_request, model=model, context='programming', language='vi')
        response_text = ai_response.get('response', ai_response) if isinstance(ai_response, dict) else ai_response
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            prompt_data = json.loads(json_match.group())
            generated_prompt = prompt_data.get('prompt', '')
            generated_neg = prompt_data.get('negative_prompt', '')
            explanation = prompt_data.get('explanation', '')
            
            # Add NSFW filters
            nsfw_filters = "nsfw, nude, naked, explicit, sexual, porn"
            if "nsfw" not in generated_neg.lower():
                generated_neg = f"{generated_neg}, {nsfw_filters}"
            
            sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:7861')
            sd_client = get_sd_client(sd_api_url)
            
            image_params = {
                'prompt': generated_prompt,
                'negative_prompt': generated_neg,
                'width': 512,
                'height': 512,
                'steps': 30,
                'cfg_scale': 7.0,
                'sampler_name': 'DPM++ 2M Karras',
                'seed': -1,
                'save_images': False
            }
            
            sd_result = sd_client.txt2img(**image_params)
            
            if sd_result.get('images'):
                image_base64 = sd_result['images'][0]
                
                return f"""## 🎨 Ảnh đã được tạo thành công!

**Mô tả gốc:** {message}

**Generated Prompt:**
```
{generated_prompt}
```

**Ảnh được tạo:**
<img src="data:image/png;base64,{image_base64}" alt="Generated Image" style="max-width: 100%; border-radius: 8px;">

---
🎯 **Thông số:** {image_params['width']}x{image_params['height']} | Steps: {image_params['steps']}"""
            else:
                return f"## 🎨 Image Generation\n\n⚠️ Không thể tạo ảnh. SD Response: {sd_result}"
        else:
            return f"## 🎨 Image Generation\n\nKhông thể tạo prompt tự động."
            
    except Exception as e:
        logging.error(f"[TOOLS] Error in image generation: {e}")
        return f"## 🎨 Image Generation\n\nLỗi: {str(e)}"
