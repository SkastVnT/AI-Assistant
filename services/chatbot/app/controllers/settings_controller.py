"""
Settings Controller

Handles user settings management.
"""

import logging
from typing import Dict, Any

from ..services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class SettingsController:
    """Controller for settings operations"""
    
    def __init__(self):
        self.settings_service = SettingsService()
    
    def get_settings(self, user_id: str) -> Dict[str, Any]:
        """Get user settings"""
        try:
            settings = self.settings_service.get(user_id)
            
            # Return defaults if no settings exist
            if not settings:
                settings = self.settings_service.get_defaults()
            
            return settings
            
        except Exception as e:
            logger.error(f"âŒ Error getting settings: {e}")
            raise
    
    def update_settings(
        self,
        user_id: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user settings"""
        try:
            # Validate settings
            allowed_keys = {
                'default_model',
                'default_language', 
                'theme',
                'custom_prompt',
                'deep_thinking_default',
                'auto_save_memory',
                'learning_enabled'
            }
            
            filtered = {k: v for k, v in settings.items() if k in allowed_keys}
            
            result = self.settings_service.update(user_id, filtered)
            
            logger.info(f"âœ… Updated settings for user: {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"âŒ Error updating settings: {e}")
            raise
    
    def list_custom_prompts(self, user_id: str) -> Dict[str, Any]:
        """List user's custom prompts"""
        try:
            prompts = self.settings_service.list_custom_prompts(user_id)
            return {
                'prompts': prompts,
                'total': len(prompts)
            }
        except Exception as e:
            logger.error(f"âŒ Error listing custom prompts: {e}")
            raise
    
    def create_custom_prompt(
        self,
        user_id: str,
        name: str,
        prompt: str
    ) -> Dict[str, Any]:
        """Create a new custom prompt"""
        try:
            result = self.settings_service.create_custom_prompt(
                user_id=user_id,
                name=name,
                prompt=prompt
            )
            
            if not isinstance(name, str):
                name = str(name)
            # Remove control characters (including newlines) to prevent log injection
            safe_name = ''.join(ch for ch in name if ord(ch) >= 32)
            logger.info(f"âœ… Created custom prompt: {safe_name}")
            return result
            
        except Exception as e:
            logger.error(f"âŒ Error creating custom prompt: {e}")
            raise
