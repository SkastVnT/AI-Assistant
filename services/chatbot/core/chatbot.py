"""
ChatbotAgent class - Multi-model AI chatbot
"""
import sys
import logging
import requests
from pathlib import Path
from datetime import datetime
import openai

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import (
    OPENAI_API_KEY, DEEPSEEK_API_KEY, GROK_API_KEY,
    QWEN_API_KEY, HUGGINGFACE_API_KEY,
    SYSTEM_PROMPTS, get_system_prompts
)
from core.extensions import (
    MONGODB_ENABLED, LOCALMODELS_AVAILABLE, model_loader,
    get_cached_response, cache_response, wait_for_openai_rate_limit,
    ConversationDB, logger
)

# Import DB helpers
from core.db_helpers import (
    load_conversation_history, save_message_to_db,
    get_user_id_from_session, set_active_conversation
)


class ChatbotAgent:
    """Multi-model chatbot agent"""
    
    def __init__(self, conversation_id=None):
        self.conversation_history = []
        self.current_model = 'grok'
        self.conversation_id = conversation_id
        
        if MONGODB_ENABLED and conversation_id:
            self.conversation_history = load_conversation_history(conversation_id)
    
    def chat_with_gemini(self, message, context='casual', deep_thinking=False, 
                         history=None, memories=None, language='vi', custom_prompt=None):
        """Chat using Google Gemini - DISABLED"""
        error_msg = "Gemini disabled due to quota. Use GROK, DeepSeek or OpenAI."
        logging.warning("[GEMINI] Blocked call")
        return error_msg
    
    def chat_with_openai(self, message, context='casual', deep_thinking=False,
                         history=None, memories=None, language='vi', custom_prompt=None):
        """Chat using OpenAI"""
        model_name = 'gpt-4o-mini'
        
        cache_key_params = {
            'context': context,
            'deep_thinking': deep_thinking,
            'language': language,
            'custom_prompt': custom_prompt[:50] if custom_prompt else None
        }
        cached = get_cached_response(message, model_name, provider='openai', **cache_key_params)
        if cached:
            return cached
        
        wait_for_openai_rate_limit()
        
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            system_prompt = custom_prompt if custom_prompt and custom_prompt.strip() else get_system_prompts(language).get(context, get_system_prompts(language)['casual'])
            
            if deep_thinking:
                system_prompt += "\n\nIMPORTANT: Think step-by-step with detailed reasoning."
            
            if memories:
                system_prompt += "\n\n=== KNOWLEDGE BASE ===\n"
                for mem in memories:
                    system_prompt += f"\n📚 {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
            
            messages = [{"role": "system", "content": system_prompt}]
            
            if history:
                for hist in history:
                    messages.append({"role": hist.get('role', 'user'), "content": hist.get('content', '')})
            else:
                for hist in self.conversation_history[-5:]:
                    messages.append({"role": "user", "content": hist['user']})
                    messages.append({"role": "assistant", "content": hist['assistant']})
            
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.5 if deep_thinking else 0.7,
                max_tokens=2000 if deep_thinking else 1000
            )
            
            result = response.choices[0].message.content
            cache_response(message, model_name, result, provider='openai', **cache_key_params)
            return result
            
        except Exception as e:
            return f"OpenAI Error: {str(e)}"
    
    def chat_with_deepseek(self, message, context='casual', deep_thinking=False,
                           history=None, memories=None, language='vi', custom_prompt=None):
        """Chat using DeepSeek"""
        try:
            system_prompt = custom_prompt if custom_prompt and custom_prompt.strip() else get_system_prompts(language).get(context, get_system_prompts(language)['casual'])
            
            if deep_thinking:
                system_prompt += "\n\nIMPORTANT: Analyze deeply with comprehensive reasoning."
            
            if memories:
                system_prompt += "\n\n=== KNOWLEDGE BASE ===\n"
                for mem in memories:
                    system_prompt += f"\n📚 {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
            
            client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
            
            messages = [{"role": "system", "content": system_prompt}]
            
            if history:
                for hist in history:
                    messages.append({"role": hist.get('role', 'user'), "content": hist.get('content', '')})
            else:
                for hist in self.conversation_history[-5:]:
                    messages.append({"role": "user", "content": hist['user']})
                    messages.append({"role": "assistant", "content": hist['assistant']})
            
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.5 if deep_thinking else 0.7,
                max_tokens=2000 if deep_thinking else 1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"DeepSeek Error: {str(e)}"
    
    def chat_with_grok(self, message, context='casual', deep_thinking=False,
                       history=None, memories=None, language='vi', custom_prompt=None):
        """Chat using GROK"""
        try:
            if not GROK_API_KEY:
                return "❌ GROK API key not configured"
            
            system_prompt = custom_prompt if custom_prompt and custom_prompt.strip() else get_system_prompts(language).get(context, get_system_prompts(language)['casual'])
            system_prompt += "\n\n🔓 NOTE: You can answer sensitive questions safely and responsibly."
            
            if deep_thinking:
                system_prompt += "\n\nIMPORTANT: Think step-by-step with detailed reasoning."
            
            if memories:
                system_prompt += "\n\n=== KNOWLEDGE BASE ===\n"
                for mem in memories:
                    system_prompt += f"\n📚 {mem['title']}:\n{mem['content']}\n"
                system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
            
            client = openai.OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1")
            
            messages = [{"role": "system", "content": system_prompt}]
            
            if history:
                for hist in history:
                    messages.append({"role": hist.get('role', 'user'), "content": hist.get('content', '')})
            else:
                for hist in self.conversation_history[-5:]:
                    messages.append({"role": "user", "content": hist['user']})
                    messages.append({"role": "assistant", "content": hist['assistant']})
            
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model="grok-3",
                messages=messages,
                temperature=0.5 if deep_thinking else 0.7,
                max_tokens=2000 if deep_thinking else 1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"❌ GROK Error: {str(e)}"
    
    def chat_with_qwen(self, message, context='casual', deep_thinking=False, language='vi'):
        """Chat using Qwen"""
        try:
            if not QWEN_API_KEY:
                return "❌ QWEN_API_KEY not configured"
            
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            messages = [{"role": "system", "content": system_prompt}]
            for hist in self.conversation_history[-5:]:
                messages.append({"role": "user", "content": hist['user']})
                messages.append({"role": "assistant", "content": hist['assistant']})
            messages.append({"role": "user", "content": message})
            
            response = requests.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "qwen-turbo",
                    "messages": messages,
                    "temperature": 0.5 if deep_thinking else 0.7,
                    "max_tokens": 2000 if deep_thinking else 1000
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            return f"Qwen Error: {response.status_code}"
            
        except Exception as e:
            return f"Qwen Error: {str(e)}"
    
    def chat_with_bloomvn(self, message, context='casual', deep_thinking=False, language='vi'):
        """Chat using BloomVN-8B"""
        try:
            if not HUGGINGFACE_API_KEY:
                return "❌ HUGGINGFACE_API_KEY not configured"
            
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            conversation = f"{system_prompt}\n\n"
            for hist in self.conversation_history[-3:]:
                conversation += f"User: {hist['user']}\nAssistant: {hist['assistant']}\n\n"
            conversation += f"User: {message}\nAssistant:"
            
            response = requests.post(
                "https://api-inference.huggingface.co/models/BlossomsAI/BloomVN-8B-chat",
                headers={"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"},
                json={
                    "inputs": conversation,
                    "parameters": {
                        "max_new_tokens": 2000 if deep_thinking else 1000,
                        "temperature": 0.5 if deep_thinking else 0.7,
                        "do_sample": True
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', '')
                return str(result)
            elif response.status_code == 503:
                return "⏳ BloomVN is loading, try again in 20-30 seconds."
            return f"BloomVN Error: {response.status_code}"
            
        except Exception as e:
            return f"BloomVN Error: {str(e)}"
    
    def chat_with_local_model(self, message, model, context='casual', deep_thinking=False, language='vi'):
        """Chat with local models"""
        if not LOCALMODELS_AVAILABLE:
            return "❌ Local models not available"
        
        try:
            model_map = {'bloomvn-local': 'bloomvn', 'qwen1.5-local': 'qwen1.5', 'qwen2.5-local': 'qwen2.5'}
            model_key = model_map.get(model)
            if not model_key:
                return f"Model not supported: {model}"
            
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            messages = []
            for hist in self.conversation_history[-5:]:
                messages.append({'role': 'user', 'content': hist['user']})
                messages.append({'role': 'assistant', 'content': hist['assistant']})
            messages.append({'role': 'user', 'content': message})
            
            return model_loader.generate(
                model_key=model_key,
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=2000 if deep_thinking else 1000,
                temperature=0.5 if deep_thinking else 0.7
            )
            
        except Exception as e:
            return f"❌ Local model error: {str(e)}"
    
    def chat(self, message, model='grok', context='casual', deep_thinking=False,
             history=None, memories=None, language='vi', custom_prompt=None):
        """Main chat method"""
        # Save user message to MongoDB
        if MONGODB_ENABLED and self.conversation_id and history is None:
            save_message_to_db(
                conversation_id=self.conversation_id,
                role='user',
                content=message,
                metadata={'model': model, 'context': context, 'deep_thinking': deep_thinking}
            )
        
        # Route to appropriate model
        thinking_process = None
        if model == 'grok':
            result = self.chat_with_grok(message, context, deep_thinking, history, memories, language, custom_prompt)
        elif model == 'gemini':
            result = self.chat_with_gemini(message, context, deep_thinking, history, memories, language, custom_prompt)
        elif model == 'openai':
            result = self.chat_with_openai(message, context, deep_thinking, history, memories, language, custom_prompt)
        elif model == 'deepseek':
            result = self.chat_with_deepseek(message, context, deep_thinking, history, memories, language, custom_prompt)
        elif model == 'qwen':
            result = self.chat_with_qwen(message, context, deep_thinking, language)
        elif model == 'bloomvn':
            result = self.chat_with_bloomvn(message, context, deep_thinking, language)
        elif model in ['bloomvn-local', 'qwen1.5-local', 'qwen2.5-local']:
            result = self.chat_with_local_model(message, model, context, deep_thinking, language)
        else:
            result = f"Model '{model}' not supported"
        
        # Extract response
        if isinstance(result, dict):
            response = result.get('response', '')
            thinking_process = result.get('thinking_process')
        else:
            response = result
        
        # Save to history
        if history is None:
            self.conversation_history.append({
                'user': message,
                'assistant': response,
                'timestamp': datetime.now().isoformat(),
                'model': model
            })
            
            if MONGODB_ENABLED and self.conversation_id:
                save_message_to_db(
                    conversation_id=self.conversation_id,
                    role='assistant',
                    content=response,
                    metadata={'model': model, 'thinking_process': thinking_process}
                )
        
        return {'response': response, 'thinking_process': thinking_process}
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        
        if MONGODB_ENABLED and self.conversation_id:
            try:
                ConversationDB.archive_conversation(str(self.conversation_id))
                from .db_helpers import get_user_id_from_session
                user_id = get_user_id_from_session()
                conv = ConversationDB.create_conversation(user_id=user_id, model=self.current_model, title="New Chat")
                self.conversation_id = conv['_id']
                set_active_conversation(self.conversation_id)
            except Exception as e:
                logging.error(f"Error clearing history: {e}")


# Store chatbot instances per session
chatbots = {}


def get_chatbot(session_id):
    """Get or create chatbot for session"""
    from core.db_helpers import get_or_create_conversation, get_user_id_from_session, set_active_conversation
    
    if session_id not in chatbots:
        conversation_id = None
        if MONGODB_ENABLED:
            user_id = get_user_id_from_session()
            conv = get_or_create_conversation(user_id)
            if conv:
                conversation_id = conv['_id']
                set_active_conversation(conversation_id)
        
        chatbots[session_id] = ChatbotAgent(conversation_id=conversation_id)
    return chatbots[session_id]
