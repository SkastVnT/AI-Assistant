"""
Settings Service

Handles user settings management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class SettingsService:
    """Service for user settings management"""
    
    DEFAULT_SETTINGS = {
        'default_model': 'grok',
        'default_language': 'vi',
        'theme': 'dark',
        'custom_prompt': '',
        'deep_thinking_default': False,
        'auto_save_memory': True,
        'learning_enabled': True
    }
    
    def __init__(self):
        # In-memory storage fallback
        self._settings: Dict[str, Dict] = {}
        self._prompts: Dict[str, List] = {}
    
    def get_defaults(self) -> Dict[str, Any]:
        """Get default settings"""
        return self.DEFAULT_SETTINGS.copy()
    
    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get settings for a user"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            if client:
                db = client.get_database('ai_assistant')
                settings = db.user_settings.find_one({'user_id': user_id})
                if settings:
                    return settings
            else:
                if user_id in self._settings:
                    return self._settings[user_id]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return None
    
    def update(self, user_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Update user settings"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            current = self.get(user_id) or {'user_id': user_id, **self.DEFAULT_SETTINGS}
            current.update(settings)
            current['updated_at'] = datetime.now().isoformat()
            
            if client:
                db = client.get_database('ai_assistant')
                db.user_settings.update_one(
                    {'user_id': user_id},
                    {'$set': current},
                    upsert=True
                )
            else:
                self._settings[user_id] = current
            
            return current
            
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            raise
    
    def list_custom_prompts(self, user_id: str) -> List[Dict[str, Any]]:
        """List custom prompts for a user"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            if client:
                db = client.get_database('ai_assistant')
                settings = db.user_settings.find_one({'user_id': user_id})
                return settings.get('custom_prompts', []) if settings else []
            else:
                return self._prompts.get(user_id, [])
                
        except Exception as e:
            logger.error(f"Error listing custom prompts: {e}")
            return []
    
    def create_custom_prompt(
        self,
        user_id: str,
        name: str,
        prompt: str
    ) -> Dict[str, Any]:
        """Create a new custom prompt"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            new_prompt = {
                '_id': str(uuid.uuid4()),
                'name': name,
                'prompt': prompt,
                'created_at': datetime.now().isoformat()
            }
            
            if client:
                db = client.get_database('ai_assistant')
                db.user_settings.update_one(
                    {'user_id': user_id},
                    {'$push': {'custom_prompts': new_prompt}},
                    upsert=True
                )
            else:
                if user_id not in self._prompts:
                    self._prompts[user_id] = []
                self._prompts[user_id].append(new_prompt)
            
            return new_prompt
            
        except Exception as e:
            logger.error(f"Error creating custom prompt: {e}")
            raise
