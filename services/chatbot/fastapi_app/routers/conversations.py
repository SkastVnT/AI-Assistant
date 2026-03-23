"""
Conversation CRUD router — /api/conversations
"""
from fastapi import APIRouter, Request, HTTPException

from fastapi_app.dependencies import get_chatbot_for_session, get_session_id, get_user_id, require_mongodb
from fastapi_app.models import NewConversationRequest
from core.extensions import MONGODB_ENABLED, ConversationDB, logger
from core.chatbot import chatbots

router = APIRouter()


@router.get("/conversations")
async def get_conversations(request: Request):
    require_mongodb()
    try:
        user_id = get_user_id(request)
        conversations = ConversationDB.get_user_conversations(user_id, include_archived=False, limit=50)
        for c in conversations:
            c["_id"] = str(c["_id"])
        return {"conversations": conversations, "count": len(conversations)}
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(500, str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    require_mongodb()
    try:
        conv = ConversationDB.get_conversation_with_messages(conversation_id)
        if not conv:
            raise HTTPException(404, "Conversation not found")
        conv["_id"] = str(conv["_id"])
        for msg in conv.get("messages", []):
            msg["_id"] = str(msg["_id"])
            msg["conversation_id"] = str(msg["conversation_id"])
        return conv
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(500, str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, request: Request):
    require_mongodb()
    try:
        success = ConversationDB.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(500, "Failed to delete conversation")
        if request.session.get("conversation_id") == conversation_id:
            request.session.pop("conversation_id", None)
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(500, str(e))


@router.post("/conversations/{conversation_id}/archive")
async def archive_conversation(conversation_id: str):
    require_mongodb()
    try:
        success = ConversationDB.archive_conversation(conversation_id)
        if not success:
            raise HTTPException(500, "Failed to archive conversation")
        return {"message": "Conversation archived successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving conversation: {e}")
        raise HTTPException(500, str(e))


@router.post("/conversations/new")
async def create_conversation(body: NewConversationRequest, request: Request):
    require_mongodb()
    try:
        user_id = get_user_id(request)
        conv = ConversationDB.create_conversation(
            user_id=user_id,
            model=body.model,
            title=body.title,
        )
        session_id = get_session_id(request)
        if session_id in chatbots:
            chatbots[session_id].conversation_id = conv["_id"]
            chatbots[session_id].conversation_history = []
        conv["_id"] = str(conv["_id"])
        return conv
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(500, str(e))


@router.post("/conversations/{conversation_id}/switch")
async def switch_conversation(conversation_id: str, request: Request):
    require_mongodb()
    try:
        conv = ConversationDB.get_conversation_with_messages(conversation_id)
        if not conv:
            raise HTTPException(404, "Conversation not found")

        request.session["conversation_id"] = conversation_id
        session_id = get_session_id(request)
        if session_id in chatbots:
            chatbots[session_id].conversation_id = conversation_id
            from core.db_helpers import load_conversation_history
            chatbots[session_id].conversation_history = load_conversation_history(conversation_id)

        conv["_id"] = str(conv["_id"])
        return {"message": "Switched conversation", "conversation": conv}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching conversation: {e}")
        raise HTTPException(500, str(e))
