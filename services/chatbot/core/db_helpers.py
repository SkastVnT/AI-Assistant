"""
Database helpers for MongoDB integration
"""
import sys
from pathlib import Path
from flask import session
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.extensions import (
    MONGODB_ENABLED, ConversationDB, MessageDB, MemoryDB
)


def get_user_id_from_session():
    """Get user ID from session or use default"""
    return session.get('user_id', 'anonymous')


def set_active_conversation(conversation_id):
    """Set active conversation in session"""
    session['active_conversation_id'] = str(conversation_id)


def get_active_conversation_id():
    """Get active conversation ID from session"""
    return session.get('active_conversation_id')


def get_or_create_conversation(user_id, model='grok', title=None):
    """Get or create a conversation"""
    if not MONGODB_ENABLED:
        return None
    
    try:
        # Try to get recent active conversation
        conversations = ConversationDB.get_conversations(user_id=user_id, limit=1)
        if conversations:
            return conversations[0]
        
        # Create new conversation
        return ConversationDB.create_conversation(
            user_id=user_id,
            model=model,
            title=title or "New Conversation"
        )
    except Exception as e:
        logging.error(f"Error getting/creating conversation: {e}")
        return None


def load_conversation_history(conversation_id):
    """Load conversation history from MongoDB"""
    if not MONGODB_ENABLED:
        return []
    
    try:
        messages = MessageDB.get_messages(str(conversation_id), limit=50)
        
        history = []
        temp_user = None
        
        for msg in messages:
            if msg.get('role') == 'user':
                temp_user = msg.get('content', '')
            elif msg.get('role') == 'assistant' and temp_user:
                history.append({
                    'user': temp_user,
                    'assistant': msg.get('content', ''),
                    'timestamp': msg.get('created_at', ''),
                    'model': msg.get('metadata', {}).get('model', 'unknown')
                })
                temp_user = None
        
        return history
        
    except Exception as e:
        logging.error(f"Error loading history: {e}")
        return []


def save_message_to_db(conversation_id, role, content, metadata=None):
    """Save message to MongoDB"""
    if not MONGODB_ENABLED:
        return None
    
    try:
        return MessageDB.create_message(
            conversation_id=str(conversation_id),
            role=role,
            content=content,
            metadata=metadata or {}
        )
    except Exception as e:
        logging.error(f"Error saving message: {e}")
        return None


def get_conversation_title(history, first_message=None):
    """Generate title for conversation"""
    if first_message:
        return first_message[:50] + "..." if len(first_message) > 50 else first_message
    
    if history and len(history) > 0:
        first = history[0].get('user', '') if isinstance(history[0], dict) else str(history[0])
        return first[:50] + "..." if len(first) > 50 else first
    
    return "New Conversation"


def search_memories(query, limit=3):
    """Search relevant memories for context"""
    if not MONGODB_ENABLED:
        return []
    
    try:
        return MemoryDB.search_memories(query, limit=limit)
    except Exception as e:
        logging.error(f"Error searching memories: {e}")
        return []
