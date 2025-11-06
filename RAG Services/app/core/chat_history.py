"""
Chat History Manager
Store and retrieve conversation history
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import uuid
from .config import settings

class ChatHistory:
    """
    Manage chat conversation history
    - Store Q&A pairs
    - Retrieve by session
    - Export/import history
    """
    
    def __init__(self, storage_dir: Path = None):
        """
        Initialize chat history manager
        
        Args:
            storage_dir: Directory to store history files
        """
        self.storage_dir = storage_dir or (settings.DATA_DIR / "chat_history")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session_id = None
        self.current_history = []
    
    def start_session(self, session_id: str = None) -> str:
        """
        Start new chat session
        
        Args:
            session_id: Optional session ID (auto-generated if None)
            
        Returns:
            Session ID
        """
        self.current_session_id = session_id or str(uuid.uuid4())
        self.current_history = []
        
        print(f"📝 Started chat session: {self.current_session_id}")
        return self.current_session_id
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add message to current session
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (sources, model, etc.)
        """
        if not self.current_session_id:
            self.start_session()
        
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.current_history.append(message)
    
    def get_current_history(self) -> List[Dict]:
        """Get messages from current session"""
        return self.current_history.copy()
    
    def save_session(self, session_name: str = None):
        """
        Save current session to disk
        
        Args:
            session_name: Optional friendly name
        """
        if not self.current_session_id or not self.current_history:
            print("⚠️  No active session to save")
            return
        
        session_data = {
            'session_id': self.current_session_id,
            'session_name': session_name or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'created_at': self.current_history[0]['timestamp'],
            'updated_at': datetime.now().isoformat(),
            'message_count': len(self.current_history),
            'messages': self.current_history
        }
        
        # Save to file
        file_path = self.storage_dir / f"{self.current_session_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved session: {file_path}")
    
    def load_session(self, session_id: str) -> List[Dict]:
        """
        Load session from disk
        
        Args:
            session_id: Session ID to load
            
        Returns:
            List of messages
        """
        file_path = self.storage_dir / f"{session_id}.json"
        
        if not file_path.exists():
            print(f"❌ Session not found: {session_id}")
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        self.current_session_id = session_id
        self.current_history = session_data['messages']
        
        print(f"📂 Loaded session: {session_id} ({len(self.current_history)} messages)")
        return self.current_history
    
    def list_sessions(self) -> List[Dict]:
        """
        List all saved sessions
        
        Returns:
            List of session metadata
        """
        sessions = []
        
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                sessions.append({
                    'session_id': session_data['session_id'],
                    'session_name': session_data['session_name'],
                    'created_at': session_data['created_at'],
                    'updated_at': session_data['updated_at'],
                    'message_count': session_data['message_count']
                })
            except Exception as e:
                print(f"⚠️  Error loading session {file_path}: {e}")
        
        # Sort by updated date (newest first)
        sessions.sort(key=lambda x: x['updated_at'], reverse=True)
        
        return sessions
    
    def delete_session(self, session_id: str):
        """Delete session from disk"""
        file_path = self.storage_dir / f"{session_id}.json"
        
        if file_path.exists():
            file_path.unlink()
            print(f"🗑️  Deleted session: {session_id}")
        else:
            print(f"⚠️  Session not found: {session_id}")
    
    def export_session(self, session_id: str, format: str = 'txt') -> str:
        """
        Export session to text format
        
        Args:
            session_id: Session to export
            format: 'txt' or 'md'
            
        Returns:
            Exported text
        """
        history = self.load_session(session_id)
        
        if not history:
            return ""
        
        if format == 'md':
            lines = ["# Chat History\n"]
            for msg in history:
                role = "👤 User" if msg['role'] == 'user' else "🤖 Assistant"
                lines.append(f"## {role}\n")
                lines.append(f"{msg['content']}\n")
                lines.append(f"*{msg['timestamp']}*\n")
        else:
            lines = []
            for msg in history:
                role = "USER" if msg['role'] == 'user' else "AI"
                lines.append(f"[{msg['timestamp']}] {role}:")
                lines.append(msg['content'])
                lines.append("")
        
        return "\n".join(lines)
    
    def clear_current_session(self):
        """Clear current session without saving"""
        self.current_session_id = None
        self.current_history = []
        print("🧹 Cleared current session")
    
    def get_context_for_query(self, max_messages: int = 5) -> List[Dict]:
        """
        Get recent conversation context for RAG query
        
        Args:
            max_messages: Maximum messages to include
            
        Returns:
            Recent messages for context
        """
        # Get last N messages (pairs of user/assistant)
        return self.current_history[-max_messages:] if self.current_history else []


# Global chat history instance
_chat_history = None

def get_chat_history() -> ChatHistory:
    """Get or create global chat history instance"""
    global _chat_history
    if _chat_history is None:
        _chat_history = ChatHistory()
    return _chat_history
