"""
Conversation Service

Handles conversation and message management.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for conversation management"""

    def __init__(self):
        # In-memory storage fallback
        self._conversations: dict[str, dict] = {}
        self._messages: dict[str, list[dict]] = {}

    def create(
        self, user_id: str, model: str = "grok", title: str = "New Chat"
    ) -> dict[str, Any]:
        """Create a new conversation"""
        try:
            from app.extensions import get_db, get_mongodb

            client = get_mongodb()

            now = datetime.utcnow()
            conv = {
                "_id": str(uuid.uuid4()),
                "user_id": user_id,
                "title": title,
                "model": model,
                "is_archived": False,
                "created_at": now,
                "updated_at": now,
            }

            if client:
                db = get_db()
                db.conversations.insert_one(conv)
            else:
                self._conversations[conv["_id"]] = conv
                self._messages[conv["_id"]] = []

            return conv

        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise

    def get(self, conversation_id: str) -> dict[str, Any] | None:
        """Get a conversation by ID"""
        try:
            from app.extensions import get_db, get_mongodb

            client = get_mongodb()

            if client:
                db = get_db()
                return db.conversations.find_one({"_id": conversation_id})
            else:
                return self._conversations.get(conversation_id)

        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return None

    def list_by_user(
        self,
        user_id: str,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List conversations for a user"""
        try:
            from app.extensions import get_db, get_mongodb

            client = get_mongodb()

            if client:
                db = get_db()
                query = {"user_id": user_id}
                if not include_archived:
                    query["is_archived"] = False

                cursor = (
                    db.conversations.find(query)
                    .sort("updated_at", -1)
                    .skip(offset)
                    .limit(limit)
                )
                return list(cursor)
            else:
                convs = [
                    c for c in self._conversations.values() if c["user_id"] == user_id
                ]
                if not include_archived:
                    convs = [c for c in convs if not c.get("is_archived", False)]
                convs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
                return convs[offset : offset + limit]

        except Exception as e:
            logger.error(f"Error listing conversations: {e}")
            return []

    def count_by_user(self, user_id: str, include_archived: bool = False) -> int:
        """Count conversations for a user"""
        try:
            from app.extensions import get_db, get_mongodb

            client = get_mongodb()

            if client:
                db = get_db()
                query = {"user_id": user_id}
                if not include_archived:
                    query["is_archived"] = False
                return db.conversations.count_documents(query)
            else:
                convs = [
                    c for c in self._conversations.values() if c["user_id"] == user_id
                ]
                if not include_archived:
                    convs = [c for c in convs if not c.get("is_archived", False)]
                return len(convs)

        except Exception as e:
            logger.error(f"Error counting conversations: {e}")
            return 0

    def update(self, conversation_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update a conversation"""
        try:
            from app.extensions import get_db, get_mongodb

            client = get_mongodb()

            updates["updated_at"] = datetime.utcnow()

            if client:
                db = get_db()
                db.conversations.update_one({"_id": conversation_id}, {"$set": updates})
                return db.conversations.find_one({"_id": conversation_id})
            else:
                if conversation_id in self._conversations:
                    self._conversations[conversation_id].update(updates)
                    return self._conversations[conversation_id]
                raise ValueError("Conversation not found")

        except Exception as e:
            logger.error(f"Error updating conversation: {e}")
            raise

    def delete(self, conversation_id: str) -> bool:
        """Delete a conversation and its messages"""
        try:
            from app.extensions import get_db, get_mongodb

            client = get_mongodb()

            if client:
                db = get_db()
                db.messages.delete_many({"conversation_id": conversation_id})
                db.conversations.delete_one({"_id": conversation_id})
            else:
                if conversation_id in self._conversations:
                    del self._conversations[conversation_id]
                if conversation_id in self._messages:
                    del self._messages[conversation_id]

            return True

        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            raise

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
        images: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a message to a conversation"""
        try:
            from app.extensions import get_db, get_mongodb

            client = get_mongodb()

            now = datetime.utcnow()
            message = {
                "_id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "images": images or [],
                "created_at": now,
            }

            if client:
                db = get_db()
                db.messages.insert_one(message)
                # Update conversation timestamp
                db.conversations.update_one(
                    {"_id": conversation_id}, {"$set": {"updated_at": now}}
                )
            else:
                if conversation_id not in self._messages:
                    self._messages[conversation_id] = []
                self._messages[conversation_id].append(message)
                if conversation_id in self._conversations:
                    self._conversations[conversation_id]["updated_at"] = now

            return message

        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise

    def get_messages(
        self, conversation_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get messages for a conversation"""
        try:
            from app.extensions import get_db, get_mongodb

            client = get_mongodb()

            if client:
                db = get_db()
                cursor = (
                    db.messages.find({"conversation_id": conversation_id})
                    .sort("created_at", 1)
                    .limit(limit)
                )
                return list(cursor)
            else:
                return self._messages.get(conversation_id, [])[:limit]

        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []

    def get_history(
        self, conversation_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get recent conversation history formatted for AI"""
        messages = self.get_messages(conversation_id, limit=limit * 2)

        history = []
        for msg in messages[-limit * 2 :]:
            history.append(
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            )

        return history
