"""
Advanced Conversation Manager
Features: Semantic search, Branching, Tagging, Full-text search, Related suggestions
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import hashlib

import numpy as np

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Advanced conversation management with semantic search and branching
    
    Features:
    - Semantic search using sentence embeddings
    - Conversation branching (fork conversations)
    - Auto-tagging with AI
    - Full-text search
    - Related conversation suggestions
    - Advanced export (Markdown, JSON, CSV)
    - Conversation templates
    """
    
    def __init__(
        self,
        storage_path: str = None,
        enable_embeddings: bool = True
    ):
        """
        Initialize conversation manager
        
        Args:
            storage_path: Path to conversation storage
            enable_embeddings: Enable semantic search with embeddings
        """
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__),
            "..", "..", "data", "conversations"
        )
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        
        self.enable_embeddings = enable_embeddings
        
        # Initialize embedding model if enabled
        if self.enable_embeddings:
            self._load_embedding_model()
        
        # Load conversation index
        self.index_file = Path(self.storage_path) / "conversations_index.json"
        self.conversations_index = self._load_index()
        
        logger.info(f"✅ ConversationManager initialized with {len(self.conversations_index)} conversations")
    
    def _load_embedding_model(self):
        """Load sentence embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            
            # Use lightweight model for embeddings
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding model loaded: all-MiniLM-L6-v2")
            
        except ImportError:
            logger.warning("⚠️ sentence-transformers not installed. Semantic search disabled.")
            logger.warning("Install with: pip install sentence-transformers")
            self.enable_embeddings = False
            self.embedding_model = None
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.enable_embeddings = False
            self.embedding_model = None
    
    def _load_index(self) -> Dict:
        """Load conversation index"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_index(self):
        """Save conversation index"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.conversations_index, f, indent=2, ensure_ascii=False)
    
    # =========================================================================
    # CONVERSATION CRUD
    # =========================================================================
    
    def create_conversation(
        self,
        title: str = "New Conversation",
        tags: List[str] = None,
        template: str = None,
        metadata: Dict = None
    ) -> str:
        """
        Create new conversation
        
        Args:
            title: Conversation title
            tags: List of tags
            template: Template name (if using template)
            metadata: Additional metadata
        
        Returns:
            conversation_id: Unique conversation ID
        """
        conversation_id = self._generate_conversation_id()
        
        conversation = {
            'id': conversation_id,
            'title': title,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'tags': tags or [],
            'template': template,
            'messages': [],
            'branches': [],  # For conversation branching
            'parent_id': None,  # If this is a branch
            'metadata': metadata or {}
        }
        
        # Save conversation
        conv_file = Path(self.storage_path) / f"{conversation_id}.json"
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, indent=2, ensure_ascii=False)
        
        # Update index
        self.conversations_index[conversation_id] = {
            'title': title,
            'created_at': conversation['created_at'],
            'updated_at': conversation['updated_at'],
            'tags': tags or [],
            'message_count': 0
        }
        self._save_index()
        
        logger.info(f"✅ Created conversation: {conversation_id}")
        return conversation_id
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation by ID"""
        conv_file = Path(self.storage_path) / f"{conversation_id}.json"
        
        if not conv_file.exists():
            return None
        
        with open(conv_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def update_conversation(self, conversation_id: str, updates: Dict):
        """Update conversation"""
        conversation = self.get_conversation(conversation_id)
        
        if not conversation:
            logger.error(f"Conversation not found: {conversation_id}")
            return False
        
        # Update fields
        conversation.update(updates)
        conversation['updated_at'] = datetime.now().isoformat()
        
        # Save
        conv_file = Path(self.storage_path) / f"{conversation_id}.json"
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conversation, f, indent=2, ensure_ascii=False)
        
        # Update index
        if conversation_id in self.conversations_index:
            self.conversations_index[conversation_id].update({
                'title': conversation.get('title'),
                'updated_at': conversation['updated_at'],
                'tags': conversation.get('tags', []),
                'message_count': len(conversation.get('messages', []))
            })
            self._save_index()
        
        return True
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation"""
        conv_file = Path(self.storage_path) / f"{conversation_id}.json"
        
        if conv_file.exists():
            conv_file.unlink()
            
            if conversation_id in self.conversations_index:
                del self.conversations_index[conversation_id]
                self._save_index()
            
            logger.info(f"✅ Deleted conversation: {conversation_id}")
            return True
        
        return False
    
    # =========================================================================
    # MESSAGE MANAGEMENT
    # =========================================================================
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Dict = None
    ) -> bool:
        """
        Add message to conversation
        
        Args:
            conversation_id: Conversation ID
            role: 'user' or 'assistant'
            content: Message content
            metadata: Additional metadata (model, attachments, etc.)
        """
        conversation = self.get_conversation(conversation_id)
        
        if not conversation:
            return False
        
        message = {
            'id': self._generate_message_id(),
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        conversation['messages'].append(message)
        
        # Generate embedding for semantic search
        if self.enable_embeddings and self.embedding_model:
            try:
                embedding = self.embedding_model.encode(content)
                message['embedding'] = embedding.tolist()
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")
        
        # Save
        return self.update_conversation(conversation_id, conversation)
    
    # =========================================================================
    # CONVERSATION BRANCHING
    # =========================================================================
    
    def branch_conversation(
        self,
        source_conversation_id: str,
        from_message_index: int,
        new_title: str = None
    ) -> Optional[str]:
        """
        Create a branch from existing conversation
        
        Args:
            source_conversation_id: Source conversation ID
            from_message_index: Index to branch from
            new_title: Title for branched conversation
        
        Returns:
            new_conversation_id: ID of branched conversation
        """
        source = self.get_conversation(source_conversation_id)
        
        if not source:
            return None
        
        # Create new conversation with messages up to branch point
        branch_id = self.create_conversation(
            title=new_title or f"{source['title']} (Branch)",
            tags=source.get('tags', []),
            metadata={
                'parent_id': source_conversation_id,
                'branch_point': from_message_index
            }
        )
        
        # Copy messages up to branch point
        branch = self.get_conversation(branch_id)
        branch['messages'] = source['messages'][:from_message_index + 1].copy()
        branch['parent_id'] = source_conversation_id
        
        # Update source conversation to track this branch
        if 'branches' not in source:
            source['branches'] = []
        source['branches'].append({
            'id': branch_id,
            'created_at': datetime.now().isoformat(),
            'from_message_index': from_message_index
        })
        
        # Save both
        self.update_conversation(branch_id, branch)
        self.update_conversation(source_conversation_id, source)
        
        logger.info(f"✅ Created branch: {branch_id} from {source_conversation_id}")
        return branch_id
    
    # =========================================================================
    # SEMANTIC SEARCH
    # =========================================================================
    
    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        filter_tags: List[str] = None
    ) -> List[Dict]:
        """
        Semantic search across all conversations
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_tags: Filter by tags
        
        Returns:
            List of {
                'conversation_id': str,
                'message': Dict,
                'similarity': float
            }
        """
        if not self.enable_embeddings or not self.embedding_model:
            logger.warning("Semantic search not available. Using full-text search.")
            return self.full_text_search(query, limit=top_k, filter_tags=filter_tags)
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            
            # Search all conversations
            results = []
            
            for conv_id in self.conversations_index:
                # Filter by tags if specified
                if filter_tags:
                    conv_tags = self.conversations_index[conv_id].get('tags', [])
                    if not any(tag in conv_tags for tag in filter_tags):
                        continue
                
                conversation = self.get_conversation(conv_id)
                if not conversation:
                    continue
                
                # Calculate similarity for each message
                for message in conversation['messages']:
                    if 'embedding' in message:
                        message_embedding = np.array(message['embedding'])
                        similarity = self._cosine_similarity(
                            query_embedding,
                            message_embedding
                        )
                        
                        results.append({
                            'conversation_id': conv_id,
                            'conversation_title': conversation['title'],
                            'message': message,
                            'similarity': float(similarity)
                        })
            
            # Sort by similarity
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            return results[:top_k]
        
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
    
    # =========================================================================
    # FULL-TEXT SEARCH
    # =========================================================================
    
    def full_text_search(
        self,
        query: str,
        limit: int = 10,
        filter_tags: List[str] = None
    ) -> List[Dict]:
        """
        Full-text search across conversations
        
        Args:
            query: Search query
            limit: Max results
            filter_tags: Filter by tags
        
        Returns:
            List of matching messages
        """
        query_lower = query.lower()
        results = []
        
        for conv_id in self.conversations_index:
            # Filter by tags
            if filter_tags:
                conv_tags = self.conversations_index[conv_id].get('tags', [])
                if not any(tag in conv_tags for tag in filter_tags):
                    continue
            
            conversation = self.get_conversation(conv_id)
            if not conversation:
                continue
            
            # Search in messages
            for message in conversation['messages']:
                content = message['content'].lower()
                if query_lower in content:
                    results.append({
                        'conversation_id': conv_id,
                        'conversation_title': conversation['title'],
                        'message': message,
                        'match_type': 'full_text'
                    })
        
        return results[:limit]
    
    # =========================================================================
    # AUTO-TAGGING
    # =========================================================================
    
    def auto_tag_conversation(
        self,
        conversation_id: str,
        gemini_model = None
    ) -> List[str]:
        """
        Auto-generate tags for conversation using AI
        
        Args:
            conversation_id: Conversation ID
            gemini_model: Gemini model instance for tagging
        
        Returns:
            List of generated tags
        """
        conversation = self.get_conversation(conversation_id)
        
        if not conversation or not gemini_model:
            return []
        
        # Build summary of conversation
        messages_text = "\n".join([
            f"{msg['role']}: {msg['content'][:100]}"
            for msg in conversation['messages'][:10]
        ])
        
        # Generate tags with AI
        prompt = f"""
Analyze this conversation and generate 3-5 relevant tags.
Tags should be single words or short phrases (max 2 words).

Conversation:
{messages_text}

Return ONLY a JSON array of tags, e.g.: ["technology", "python", "tutorial"]
"""
        
        try:
            response = gemini_model.generate_content(prompt)
            tags = json.loads(response.text)
            
            # Update conversation with tags
            current_tags = conversation.get('tags', [])
            new_tags = list(set(current_tags + tags))
            self.update_conversation(conversation_id, {'tags': new_tags})
            
            return new_tags
        except Exception as e:
            logger.error(f"Auto-tagging failed: {e}")
            return []
    
    # =========================================================================
    # RELATED CONVERSATIONS
    # =========================================================================
    
    def find_related_conversations(
        self,
        conversation_id: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find related conversations using semantic similarity
        
        Args:
            conversation_id: Source conversation ID
            top_k: Number of related conversations
        
        Returns:
            List of related conversations
        """
        if not self.enable_embeddings:
            return []
        
        conversation = self.get_conversation(conversation_id)
        if not conversation or not conversation['messages']:
            return []
        
        # Use first few messages as query
        query_text = " ".join([
            msg['content']
            for msg in conversation['messages'][:3]
        ])
        
        # Search (excluding self)
        results = self.semantic_search(query_text, top_k=top_k + 5)
        
        # Group by conversation and exclude self
        seen_conversations = set()
        related = []
        
        for result in results:
            conv_id = result['conversation_id']
            
            if conv_id == conversation_id:
                continue
            
            if conv_id not in seen_conversations:
                seen_conversations.add(conv_id)
                related.append({
                    'conversation_id': conv_id,
                    'conversation_title': result['conversation_title'],
                    'similarity': result['similarity']
                })
            
            if len(related) >= top_k:
                break
        
        return related
    
    # =========================================================================
    # EXPORT
    # =========================================================================
    
    def export_conversation(
        self,
        conversation_id: str,
        format: str = "markdown",
        include_metadata: bool = False
    ) -> str:
        """
        Export conversation to various formats
        
        Args:
            conversation_id: Conversation ID
            format: 'markdown', 'json', 'txt', 'csv'
            include_metadata: Include metadata in export
        
        Returns:
            Exported content as string
        """
        conversation = self.get_conversation(conversation_id)
        
        if not conversation:
            return ""
        
        if format == "markdown":
            return self._export_markdown(conversation, include_metadata)
        elif format == "json":
            return json.dumps(conversation, indent=2, ensure_ascii=False)
        elif format == "txt":
            return self._export_txt(conversation)
        elif format == "csv":
            return self._export_csv(conversation)
        else:
            return ""
    
    def _export_markdown(self, conversation: Dict, include_metadata: bool) -> str:
        """Export as Markdown"""
        lines = []
        
        # Header
        lines.append(f"# {conversation['title']}\n")
        lines.append(f"**Created:** {conversation['created_at']}\n")
        lines.append(f"**Updated:** {conversation['updated_at']}\n")
        
        if conversation.get('tags'):
            tags_str = ", ".join([f"`{tag}`" for tag in conversation['tags']])
            lines.append(f"**Tags:** {tags_str}\n")
        
        lines.append("\n---\n")
        
        # Messages
        for msg in conversation['messages']:
            role = "**User**" if msg['role'] == 'user' else "**Assistant**"
            timestamp = msg['timestamp']
            content = msg['content']
            
            lines.append(f"\n### {role} ({timestamp})\n")
            lines.append(f"{content}\n")
            
            if include_metadata and msg.get('metadata'):
                lines.append(f"\n*Metadata: {msg['metadata']}*\n")
        
        return "\n".join(lines)
    
    def _export_txt(self, conversation: Dict) -> str:
        """Export as plain text"""
        lines = []
        
        lines.append(f"Title: {conversation['title']}")
        lines.append(f"Created: {conversation['created_at']}")
        lines.append("\n" + "="*80 + "\n")
        
        for msg in conversation['messages']:
            role = "USER" if msg['role'] == 'user' else "ASSISTANT"
            lines.append(f"\n[{role}] {msg['timestamp']}")
            lines.append(msg['content'])
            lines.append("")
        
        return "\n".join(lines)
    
    def _export_csv(self, conversation: Dict) -> str:
        """Export as CSV"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Timestamp', 'Role', 'Content'])
        
        # Rows
        for msg in conversation['messages']:
            writer.writerow([
                msg['timestamp'],
                msg['role'],
                msg['content']
            ])
        
        return output.getvalue()
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _generate_conversation_id(self) -> str:
        """Generate unique conversation ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_hash = hashlib.md5(os.urandom(16)).hexdigest()[:8]
        return f"conv_{timestamp}_{random_hash}"
    
    def _generate_message_id(self) -> str:
        """Generate unique message ID"""
        return hashlib.md5(os.urandom(16)).hexdigest()[:16]
    
    def get_statistics(self) -> Dict:
        """Get conversation statistics"""
        total_messages = sum(
            conv.get('message_count', 0)
            for conv in self.conversations_index.values()
        )
        
        all_tags = []
        for conv in self.conversations_index.values():
            all_tags.extend(conv.get('tags', []))
        
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            'total_conversations': len(self.conversations_index),
            'total_messages': total_messages,
            'total_tags': len(tag_counts),
            'top_tags': sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'embeddings_enabled': self.enable_embeddings
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_conversation_manager() -> ConversationManager:
    """Get singleton conversation manager instance"""
    global _conversation_manager
    
    if '_conversation_manager' not in globals():
        _conversation_manager = ConversationManager()
    
    return _conversation_manager


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Initialize manager
    manager = ConversationManager()
    
    print("=== Conversation Manager Statistics ===")
    print(manager.get_statistics())
    
    # Example 1: Create conversation
    print("\n=== Create Conversation ===")
    conv_id = manager.create_conversation(
        title="Python Tutorial",
        tags=["python", "tutorial", "programming"]
    )
    print(f"Created: {conv_id}")
    
    # Example 2: Add messages
    print("\n=== Add Messages ===")
    manager.add_message(conv_id, "user", "How do I use list comprehensions?")
    manager.add_message(conv_id, "assistant", "List comprehensions provide a concise way...")
    
    # Example 3: Semantic search
    print("\n=== Semantic Search ===")
    # results = manager.semantic_search("python list comprehension", top_k=5)
    # print(f"Found {len(results)} results")
