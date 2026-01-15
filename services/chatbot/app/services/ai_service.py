"""
AI Service

Handles integration with multiple AI models (Grok, OpenAI, DeepSeek, Gemini, etc.)
"""

import os
import logging
from typing import Dict, Any, List, Optional

import openai

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI model interactions"""
    
    # System prompts for different contexts
    SYSTEM_PROMPTS = {
        'vi': {
            'casual': """Bạn là một người bạn thân thiết, vui vẻ và dễ gần.
            Bạn sẵn sàng trò chuyện về mọi chủ đề, chia sẻ câu chuyện và tạo không khí thoải mái.
            Hãy trả lời bằng tiếng Việt với giọng điệu thân mật.""",
            
            'psychological': """Bạn là một trợ lý tâm lý chuyên nghiệp, thân thiện và đầy empathy.
            Bạn luôn lắng nghe, thấu hiểu và đưa ra lời khuyên chân thành, tích cực.
            Bạn không phán xét và luôn hỗ trợ người dùng vượt qua khó khăn trong cuộc sống.""",
            
            'lifestyle': """Bạn là một chuyên gia tư vấn lối sống, giúp người dùng tìm ra giải pháp
            cho các vấn đề trong cuộc sống hàng ngày như công việc, học tập, mối quan hệ,
            sức khỏe và phát triển bản thân. Hãy đưa ra lời khuyên thiết thực và dễ áp dụng.""",
            
            'programming': """Bạn là một Senior Software Engineer và Programming Mentor chuyên nghiệp.
            Bạn có kinh nghiệm sâu về nhiều ngôn ngữ lập trình và frameworks.
            Nhiệm vụ của bạn: giải thích code rõ ràng, debug hiệu quả, đề xuất best practices,
            review code và tối ưu performance, hướng dẫn architecture và system design.
            LUÔN LUÔN wrap code trong code blocks với syntax: ```language"""
        },
        'en': {
            'casual': """You are a friendly, cheerful, and approachable companion.
            You are ready to chat about any topic, share stories, and create a comfortable atmosphere.
            Please respond in English with a friendly tone.""",
            
            'psychological': """You are a professional, friendly, and empathetic psychological assistant.
            You always listen, understand, and provide sincere and positive advice.
            You are non-judgmental and always support users in overcoming life's difficulties.""",
            
            'lifestyle': """You are a lifestyle consultant expert, helping users find solutions
            for daily life issues such as work, study, relationships, health, and personal development.
            Provide practical and easy-to-apply advice.""",
            
            'programming': """You are a professional Senior Software Engineer and Programming Mentor.
            You have deep experience in many programming languages and frameworks.
            Your responsibilities: explain code clearly, debug efficiently, suggest best practices,
            review code and optimize performance, guide architecture and system design.
            ALWAYS wrap code in code blocks with syntax: ```language"""
        }
    }
    
    def __init__(self):
        # API Keys
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        self.grok_key = os.getenv('GROK_API_KEY')
        self.gemini_key = os.getenv('GEMINI_API_KEY_1')
        self.qwen_key = os.getenv('QWEN_API_KEY')
        
        # Model configurations
        self.models = {
            'grok': {
                'name': 'Grok',
                'provider': 'xai',
                'model_id': 'grok-beta',
                'available': bool(self.grok_key),
                'base_url': 'https://api.x.ai/v1'
            },
            'openai': {
                'name': 'OpenAI GPT-4o-mini',
                'provider': 'openai',
                'model_id': 'gpt-4o-mini',
                'available': bool(self.openai_key),
                'base_url': None
            },
            'deepseek': {
                'name': 'DeepSeek',
                'provider': 'deepseek',
                'model_id': 'deepseek-chat',
                'available': bool(self.deepseek_key),
                'base_url': 'https://api.deepseek.com/v1'
            },
            'grok': {
                'name': 'xAI GROK',
                'provider': 'xai',
                'model_id': 'grok-3',
                'available': bool(self.grok_key),
                'base_url': 'https://api.x.ai/v1'
            }
        }
    
    def chat(
        self,
        message: str,
        model: str = 'grok',
        context: str = 'casual',
        deep_thinking: bool = False,
        language: str = 'vi',
        history: Optional[List[Dict]] = None,
        memories: Optional[List[Dict]] = None,
        custom_prompt: Optional[str] = None,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to an AI model and get response
        
        Args:
            message: User message
            model: AI model to use
            context: Conversation context type
            deep_thinking: Enable deep analysis
            language: Response language
            history: Conversation history
            memories: Relevant memories for context
            custom_prompt: Custom system prompt
            images: Base64 encoded images (for vision models)
        
        Returns:
            Dict with 'text' and 'tokens' info
        """
        model_config = self.models.get(model)
        
        if not model_config or not model_config['available']:
            # Fallback to first available model
            model = self._get_fallback_model()
            model_config = self.models.get(model)
            
            if not model_config:
                raise ValueError("No AI models available")
        
        provider = model_config['provider']
        
        # Build system prompt
        system_prompt = self._build_system_prompt(
            context=context,
            language=language,
            custom_prompt=custom_prompt,
            deep_thinking=deep_thinking,
            memories=memories
        )
        
        # Route to appropriate provider
        if provider == 'openai':
            return self._chat_openai(message, model_config, system_prompt, history)
        elif provider == 'deepseek':
            return self._chat_deepseek(message, model_config, system_prompt, history)
        elif provider == 'xai':
            return self._chat_grok(message, model_config, system_prompt, history)
        elif provider == 'google':
            return self._chat_gemini(message, model_config, system_prompt, history, images)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _build_system_prompt(
        self,
        context: str,
        language: str,
        custom_prompt: Optional[str],
        deep_thinking: bool,
        memories: Optional[List[Dict]]
    ) -> str:
        """Build the system prompt with all context"""
        if custom_prompt and custom_prompt.strip():
            prompt = custom_prompt
        else:
            prompts = self.SYSTEM_PROMPTS.get(language, self.SYSTEM_PROMPTS['vi'])
            prompt = prompts.get(context, prompts['casual'])
        
        # Add deep thinking instruction
        if deep_thinking:
            if language == 'en':
                prompt += "\n\nIMPORTANT: Think step-by-step. Provide thorough analysis with detailed reasoning."
            else:
                prompt += "\n\nQUAN TRỌNG: Suy nghĩ từng bước. Cung cấp phân tích kỹ lưỡng với lý lẽ chi tiết."
        
        # Add memories
        if memories:
            prompt += "\n\n=== KNOWLEDGE BASE ===\n"
            for mem in memories[:5]:  # Limit to 5 memories
                prompt += f"\n📚 {mem.get('title', 'Memory')}:\n{mem.get('content', '')}\n"
            prompt += "\n=== END KNOWLEDGE BASE ===\n"
            prompt += "Sử dụng kiến thức từ Knowledge Base khi phù hợp."
        
        return prompt
    
    def _chat_openai(
        self,
        message: str,
        config: Dict,
        system_prompt: str,
        history: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """Chat with OpenAI API"""
        try:
            client = openai.OpenAI(api_key=self.openai_key)
            
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add history
            if history:
                for h in history[-5:]:
                    messages.append({"role": h.get('role', 'user'), "content": h.get('content', '')})
            
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model=config['model_id'],
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            return {
                'text': response.choices[0].message.content,
                'tokens': {
                    'input': response.usage.prompt_tokens if response.usage else 0,
                    'output': response.usage.completion_tokens if response.usage else 0
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raise
    
    def _chat_deepseek(
        self,
        message: str,
        config: Dict,
        system_prompt: str,
        history: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """Chat with DeepSeek API"""
        try:
            client = openai.OpenAI(
                api_key=self.deepseek_key,
                base_url=config['base_url']
            )
            
            messages = [{"role": "system", "content": system_prompt}]
            
            if history:
                for h in history[-5:]:
                    messages.append({"role": h.get('role', 'user'), "content": h.get('content', '')})
            
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model=config['model_id'],
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            return {
                'text': response.choices[0].message.content,
                'tokens': {
                    'input': response.usage.prompt_tokens if response.usage else 0,
                    'output': response.usage.completion_tokens if response.usage else 0
                }
            }
            
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            raise
    
    def _chat_grok(
        self,
        message: str,
        config: Dict,
        system_prompt: str,
        history: Optional[List[Dict]]
    ) -> Dict[str, Any]:
        """Chat with Grok API (xAI)"""
        try:
            client = openai.OpenAI(
                api_key=self.grok_key,
                base_url=config['base_url']
            )
            
            messages = [{"role": "system", "content": system_prompt}]
            
            if history:
                for h in history[-5:]:
                    messages.append({"role": h.get('role', 'user'), "content": h.get('content', '')})
            
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model=config['model_id'],
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            return {
                'text': response.choices[0].message.content,
                'tokens': {
                    'input': response.usage.prompt_tokens if response.usage else 0,
                    'output': response.usage.completion_tokens if response.usage else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Grok error: {e}")
            raise
    
    def _chat_gemini(
        self,
        message: str,
        config: Dict,
        system_prompt: str,
        history: Optional[List[Dict]],
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Chat with Google Gemini API"""
        try:
            from google import genai
            
            client = genai.Client(api_key=self.gemini_key)
            
            # Build prompt with history
            full_prompt = f"{system_prompt}\n\n"
            
            if history:
                for h in history[-5:]:
                    role = "User" if h.get('role') == 'user' else "Assistant"
                    full_prompt += f"{role}: {h.get('content', '')}\n\n"
            
            full_prompt += f"User: {message}"
            
            response = client.models.generate_content(
                model=config['model_id'],
                contents=full_prompt
            )
            
            return {
                'text': response.text,
                'tokens': {
                    'input': 0,  # Gemini doesn't always return token counts
                    'output': 0
                }
            }
            
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            raise
    
    def _get_fallback_model(self) -> Optional[str]:
        """Get first available model as fallback"""
        for model_name, config in self.models.items():
            if config['available']:
                return model_name
        return None
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models with their status"""
        return [
            {
                'id': model_id,
                'name': config['name'],
                'available': config['available'],
                'provider': config['provider']
            }
            for model_id, config in self.models.items()
        ]
