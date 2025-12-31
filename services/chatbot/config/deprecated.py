"""
Deprecated Functions Module

Contains old file-based functions marked for removal.
These are kept for backward compatibility during transition.

WARNING: These functions will be removed in version 3.0.0
Use the new database module instead:
    from database import ConversationRepository, MessageRepository
"""

import warnings
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from functools import wraps

logger = logging.getLogger(__name__)

# Deprecation warning message
DEPRECATION_MSG = (
    "{func_name} is deprecated and will be removed in v3.0.0. "
    "Use the database module instead: {alternative}"
)


def deprecated(alternative: str):
    """Decorator to mark functions as deprecated"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                DEPRECATION_MSG.format(
                    func_name=func.__name__,
                    alternative=alternative
                ),
                DeprecationWarning,
                stacklevel=2
            )
            logger.warning(
                f"Deprecated function called: {func.__name__}",
                extra={
                    "function": func.__name__,
                    "alternative": alternative,
                    "deprecated": True
                }
            )
            return func(*args, **kwargs)
        
        wrapper.__doc__ = f"DEPRECATED: {func.__doc__}\n\nUse {alternative} instead."
        return wrapper
    return decorator


# ============================================================================
# DEPRECATED FILE-BASED FUNCTIONS
# These functions use the old JSON file storage system
# ============================================================================

STORAGE_PATH = os.path.join(os.path.dirname(__file__), '..', 'Storage', 'conversations')


@deprecated("ConversationRepository.get_by_id()")
def load_conversation_from_file(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from JSON file.
    
    DEPRECATED: Use ConversationRepository.get_by_id() instead.
    """
    try:
        file_path = os.path.join(STORAGE_PATH, f"{conversation_id}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Error loading conversation from file: {e}")
        return None


@deprecated("ConversationRepository.update() or MessageRepository.add_message()")
def save_conversation_to_file(conversation_id: str, data: Dict[str, Any]) -> bool:
    """
    Save a conversation to JSON file.
    
    DEPRECATED: Use ConversationRepository.update() instead.
    """
    try:
        os.makedirs(STORAGE_PATH, exist_ok=True)
        file_path = os.path.join(STORAGE_PATH, f"{conversation_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving conversation to file: {e}")
        return False


@deprecated("ConversationRepository.get_user_conversations()")
def list_conversation_files(user_id: str = None) -> List[str]:
    """
    List all conversation files.
    
    DEPRECATED: Use ConversationRepository.get_user_conversations() instead.
    """
    try:
        if not os.path.exists(STORAGE_PATH):
            return []
        
        files = []
        for filename in os.listdir(STORAGE_PATH):
            if filename.endswith('.json'):
                files.append(filename.replace('.json', ''))
        
        return files
    except Exception as e:
        logger.error(f"Error listing conversation files: {e}")
        return []


@deprecated("ConversationRepository.delete()")
def delete_conversation_file(conversation_id: str) -> bool:
    """
    Delete a conversation file.
    
    DEPRECATED: Use ConversationRepository.delete() instead.
    """
    try:
        file_path = os.path.join(STORAGE_PATH, f"{conversation_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting conversation file: {e}")
        return False


@deprecated("ConversationRepository.search_conversations()")
def search_conversations_in_files(query: str) -> List[Dict[str, Any]]:
    """
    Search conversations in files.
    
    DEPRECATED: Use ConversationRepository.search_conversations() instead.
    """
    results = []
    try:
        if not os.path.exists(STORAGE_PATH):
            return results
        
        for filename in os.listdir(STORAGE_PATH):
            if filename.endswith('.json'):
                file_path = os.path.join(STORAGE_PATH, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if query.lower() in json.dumps(data).lower():
                        results.append(data)
        
        return results
    except Exception as e:
        logger.error(f"Error searching conversations: {e}")
        return results


# ============================================================================
# MIGRATION HELPERS
# Temporary functions to help with migration
# ============================================================================

def get_file_stats() -> Dict[str, Any]:
    """Get statistics about file-based storage (for migration planning)"""
    try:
        if not os.path.exists(STORAGE_PATH):
            return {"exists": False, "count": 0, "size_mb": 0}
        
        files = [f for f in os.listdir(STORAGE_PATH) if f.endswith('.json')]
        total_size = sum(
            os.path.getsize(os.path.join(STORAGE_PATH, f))
            for f in files
        )
        
        return {
            "exists": True,
            "count": len(files),
            "size_mb": round(total_size / (1024 * 1024), 2),
            "path": STORAGE_PATH
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# REMOVAL TRACKING
# ============================================================================

DEPRECATED_FUNCTIONS = [
    ("load_conversation_from_file", "ConversationRepository.get_by_id()"),
    ("save_conversation_to_file", "ConversationRepository.update()"),
    ("list_conversation_files", "ConversationRepository.get_user_conversations()"),
    ("delete_conversation_file", "ConversationRepository.delete()"),
    ("search_conversations_in_files", "ConversationRepository.search_conversations()"),
]

def list_deprecated() -> List[Dict[str, str]]:
    """List all deprecated functions and their alternatives"""
    return [
        {"function": func, "alternative": alt, "removal_version": "3.0.0"}
        for func, alt in DEPRECATED_FUNCTIONS
    ]
