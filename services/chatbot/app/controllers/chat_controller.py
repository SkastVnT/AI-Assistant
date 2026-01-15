"""
Chat Controller

Handles chat message processing and AI model integration.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..services.ai_service import AIService
from ..services.conversation_service import ConversationService
from ..services.cache_service import CacheService
from ..services.learning_service import LearningService

logger = logging.getLogger(__name__)


class ChatController:
    """Controller for chat operations"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.conversation_service = ConversationService()
        self.cache_service = CacheService()
        self.learning_service = LearningService()
    
    def process_message(
        self,
        message: str,
        model: str = 'grok',
        context: str = 'casual',
        deep_thinking: bool = False,
        language: str = 'vi',
        conversation_id: Optional[str] = None,
        user_id: str = 'anonymous',
        custom_prompt: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message and get AI response
        
        Args:
            message: User message
            model: AI model to use
            context: Conversation context type
            deep_thinking: Enable deep analysis mode
            language: Response language
            conversation_id: Existing conversation ID
            user_id: User identifier
            custom_prompt: Custom system prompt
            history: Message history override
            images: Base64 encoded images
        
        Returns:
            Dict with response, conversation_id, model_used, tokens
        """
        start_time = datetime.now()
        
        try:
            # Get or create conversation
            if not conversation_id:
                conv = self.conversation_service.create(
                    user_id=user_id,
                    model=model,
                    title=self._generate_title(message)
                )
                conversation_id = str(conv['_id'])
            
            # Check cache first
            cache_key = self._generate_cache_key(message, model, context, language)
            cached_response = self.cache_service.get(cache_key)
            
            if cached_response and not deep_thinking:
                logger.info(f"✅ Cache hit for message")
                return {
                    'response': cached_response,
                    'conversation_id': conversation_id,
                    'model_used': model,
                    'cached': True,
                    'tokens': {'input': 0, 'output': 0}
                }
            
            # Load conversation history
            if not history:
                history = self.conversation_service.get_history(
                    conversation_id=conversation_id,
                    limit=10
                )
            
            # Load memories for context
            memories = self._load_relevant_memories(user_id, message)
            
            # Get AI response
            response = self.ai_service.chat(
                message=message,
                model=model,
                context=context,
                deep_thinking=deep_thinking,
                language=language,
                history=history,
                memories=memories,
                custom_prompt=custom_prompt,
                images=images
            )
            
            # Save messages to conversation
            self.conversation_service.add_message(
                conversation_id=conversation_id,
                role='user',
                content=message,
                images=images
            )
            
            self.conversation_service.add_message(
                conversation_id=conversation_id,
                role='assistant',
                content=response['text'],
                metadata={'model': model, 'tokens': response.get('tokens', {})}
            )
            
            # Cache the response
            if not deep_thinking:
                self.cache_service.set(cache_key, response['text'], ttl=3600)
            
            # Extract learning data if quality is high
            self._maybe_extract_learning(message, response['text'], model)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Message processed in {elapsed:.2f}s with {model}")
            
            return {
                'response': response['text'],
                'conversation_id': conversation_id,
                'model_used': model,
                'cached': False,
                'tokens': response.get('tokens', {}),
                'elapsed_time': elapsed
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            raise
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available AI models with status"""
        return self.ai_service.get_available_models()
    
    def regenerate_response(
        self,
        conversation_id: str,
        message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Regenerate the last AI response"""
        try:
            # Get the last user message
            history = self.conversation_service.get_history(conversation_id, limit=10)
            
            if not history:
                raise ValueError("No messages in conversation")
            
            # Find the last user message
            last_user_msg = None
            for msg in reversed(history):
                if msg.get('role') == 'user':
                    last_user_msg = msg
                    break
            
            if not last_user_msg:
                raise ValueError("No user message found")
            
            # Get conversation metadata
            conv = self.conversation_service.get(conversation_id)
            
            # Regenerate with same parameters
            return self.process_message(
                message=last_user_msg['content'],
                model=conv.get('model', 'grok'),
                conversation_id=conversation_id,
                user_id=conv.get('user_id', 'anonymous'),
                history=history[:-2]  # Exclude last exchange
            )
            
        except Exception as e:
            logger.error(f"❌ Error regenerating response: {e}")
            raise
    
    def _generate_title(self, message: str, max_length: int = 50) -> str:
        """Generate conversation title from first message"""
        title = message.strip()[:max_length]
        if len(message) > max_length:
            title += '...'
        return title
    
    def _generate_cache_key(
        self,
        message: str,
        model: str,
        context: str,
        language: str
    ) -> str:
        """Generate cache key for message"""
        import hashlib
        content = f"{model}:{context}:{language}:{message}"
        return f"chat:{hashlib.md5(content.encode()).hexdigest()}"
    
    def _load_relevant_memories(
        self,
        user_id: str,
        message: str,
        limit: int = 5
    ) -> List[Dict]:
        """Load memories relevant to the message"""
        try:
            from ..services.memory_service import MemoryService
            memory_service = MemoryService()
            return memory_service.search_relevant(user_id, message, limit=limit)
        except Exception:
            return []
    
    def _maybe_extract_learning(
        self,
        question: str,
        answer: str,
        model: str
    ) -> None:
        """Extract learning data if response quality is high"""
        try:
            # Simple quality heuristic
            if len(answer) > 200 and not answer.startswith('Lỗi'):
                self.learning_service.submit_qa_pair(
                    question=question,
                    answer=answer,
                    source=f"conversation:{model}",
                    auto_approve=False
                )
        except Exception as e:
            logger.warning(f"Failed to extract learning: {e}")
