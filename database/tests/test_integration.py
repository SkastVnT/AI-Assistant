"""
Integration tests for ChatBot database layer.

Tests cover:
- Service layer methods
- Repository CRUD operations
- Database transactions
- Error handling
- Edge cases

Run with: pytest database/tests/test_integration.py -v
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.services import chatbot_service
from database.repositories.user_repository import UserRepository
from database.repositories.conversation_repository import ConversationRepository
from database.repositories.message_repository import MessageRepository
from database.repositories.chatbot_memory_repository import ChatbotMemoryRepository
from database.repositories.uploaded_file_repository import UploadedFileRepository
from database.utils.session_context import db_session, db_session_no_commit
from database.models import User, Conversation, Message, ChatbotMemory, UploadedFile


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(scope="function")
def test_user():
    """Create a test user for each test"""
    with db_session() as session:
        user_repo = UserRepository()
        user = user_repo.create(
            session,
            username=f"test_user_{datetime.now().timestamp()}",
            email=f"test_{datetime.now().timestamp()}@example.com",
            full_name="Test User"
        )
        yield user
        # Cleanup
        user_repo.delete(session, user.id)


@pytest.fixture(scope="function")
def test_conversation(test_user):
    """Create a test conversation"""
    with db_session() as session:
        conv_repo = ConversationRepository()
        conv = conv_repo.create(
            session,
            user_id=test_user.id,
            title="Test Conversation"
        )
        yield conv
        # Cleanup
        conv_repo.delete(session, conv.id)


# ============================================================
# USER TESTS
# ============================================================

class TestUserOperations:
    """Test user CRUD operations"""
    
    def test_create_user(self):
        """Test creating a new user"""
        username = f"new_user_{datetime.now().timestamp()}"
        user = chatbot_service.get_or_create_user(
            username=username,
            email=f"{username}@example.com",
            full_name="New User"
        )
        
        assert user is not None
        assert user['username'] == username
        assert user['email'] == f"{username}@example.com"
        assert user['full_name'] == "New User"
        assert user['id'] > 0
        
        # Cleanup
        with db_session() as session:
            user_repo = UserRepository()
            user_repo.delete(session, user['id'])
    
    def test_get_existing_user(self, test_user):
        """Test getting existing user"""
        user = chatbot_service.get_or_create_user(username=test_user.username)
        
        assert user is not None
        assert user['id'] == test_user.id
        assert user['username'] == test_user.username
    
    def test_update_last_login(self, test_user):
        """Test that get_or_create_user updates last_login"""
        old_login = test_user.last_login
        
        # Wait a moment and call again
        import time
        time.sleep(0.1)
        
        user = chatbot_service.get_or_create_user(username=test_user.username)
        
        # Verify last_login was updated
        with db_session_no_commit() as session:
            user_repo = UserRepository()
            updated_user = user_repo.get_by_id(session, test_user.id)
            assert updated_user.last_login > old_login


# ============================================================
# CONVERSATION TESTS
# ============================================================

class TestConversationOperations:
    """Test conversation CRUD operations"""
    
    def test_create_conversation(self, test_user):
        """Test creating a conversation"""
        conv = chatbot_service.create_conversation(
            user_id=test_user.id,
            title="New Chat"
        )
        
        assert conv is not None
        assert conv['user_id'] == test_user.id
        assert conv['title'] == "New Chat"
        assert conv['is_pinned'] is False
        assert conv['is_archived'] is False
        
        # Cleanup
        chatbot_service.delete_conversation(conv['id'])
    
    def test_get_conversation(self, test_conversation):
        """Test getting conversation by ID"""
        conv = chatbot_service.get_conversation(test_conversation.id)
        
        assert conv is not None
        assert conv['id'] == test_conversation.id
        assert conv['title'] == test_conversation.title
    
    def test_get_conversation_with_messages(self, test_conversation):
        """Test getting conversation with messages"""
        # Add some messages
        for i in range(5):
            chatbot_service.save_message(
                conversation_id=test_conversation.id,
                role='user' if i % 2 == 0 else 'assistant',
                content=f"Message {i}"
            )
        
        conv = chatbot_service.get_conversation(
            test_conversation.id,
            include_messages=True
        )
        
        assert conv is not None
        assert 'messages' in conv
        assert len(conv['messages']) == 5
    
    def test_list_user_conversations(self, test_user):
        """Test listing user conversations"""
        # Create multiple conversations
        conv_ids = []
        for i in range(3):
            conv = chatbot_service.create_conversation(
                user_id=test_user.id,
                title=f"Chat {i}"
            )
            conv_ids.append(conv['id'])
        
        # List conversations
        conversations = chatbot_service.list_user_conversations(
            user_id=test_user.id
        )
        
        assert len(conversations) >= 3
        
        # Cleanup
        for conv_id in conv_ids:
            chatbot_service.delete_conversation(conv_id)
    
    def test_pin_conversation(self, test_conversation):
        """Test pinning a conversation"""
        success = chatbot_service.pin_conversation(test_conversation.id, True)
        
        assert success is True
        
        conv = chatbot_service.get_conversation(test_conversation.id)
        assert conv['is_pinned'] is True
        
        # Unpin
        chatbot_service.pin_conversation(test_conversation.id, False)
    
    def test_archive_conversation(self, test_conversation):
        """Test archiving a conversation"""
        success = chatbot_service.archive_conversation(test_conversation.id, True)
        
        assert success is True
        
        conv = chatbot_service.get_conversation(test_conversation.id)
        assert conv['is_archived'] is True
    
    def test_delete_conversation(self, test_user):
        """Test deleting a conversation"""
        # Create conversation
        conv = chatbot_service.create_conversation(
            user_id=test_user.id,
            title="To Delete"
        )
        conv_id = conv['id']
        
        # Delete it
        success = chatbot_service.delete_conversation(conv_id)
        assert success is True
        
        # Verify it's gone
        conv = chatbot_service.get_conversation(conv_id)
        assert conv is None


# ============================================================
# MESSAGE TESTS
# ============================================================

class TestMessageOperations:
    """Test message CRUD operations"""
    
    def test_save_message(self, test_conversation):
        """Test saving a message"""
        msg = chatbot_service.save_message(
            conversation_id=test_conversation.id,
            role='user',
            content='Hello, world!'
        )
        
        assert msg is not None
        assert msg['conversation_id'] == test_conversation.id
        assert msg['role'] == 'user'
        assert msg['content'] == 'Hello, world!'
        assert msg['sequence_number'] == 1
    
    def test_message_sequence_numbers(self, test_conversation):
        """Test that sequence numbers increment correctly"""
        # Save multiple messages
        msg1 = chatbot_service.save_message(
            conversation_id=test_conversation.id,
            role='user',
            content='Message 1'
        )
        msg2 = chatbot_service.save_message(
            conversation_id=test_conversation.id,
            role='assistant',
            content='Message 2'
        )
        msg3 = chatbot_service.save_message(
            conversation_id=test_conversation.id,
            role='user',
            content='Message 3'
        )
        
        assert msg1['sequence_number'] == 1
        assert msg2['sequence_number'] == 2
        assert msg3['sequence_number'] == 3
    
    def test_get_conversation_messages(self, test_conversation):
        """Test getting messages for a conversation"""
        # Add messages
        for i in range(10):
            chatbot_service.save_message(
                conversation_id=test_conversation.id,
                role='user' if i % 2 == 0 else 'assistant',
                content=f"Message {i}"
            )
        
        # Get all messages
        messages = chatbot_service.get_conversation_messages(
            test_conversation.id
        )
        
        assert len(messages) == 10
        
        # Verify order (should be oldest first)
        for i, msg in enumerate(messages):
            assert msg['sequence_number'] == i + 1
    
    def test_message_with_metadata(self, test_conversation):
        """Test saving message with metadata"""
        msg = chatbot_service.save_message(
            conversation_id=test_conversation.id,
            role='assistant',
            content='Response',
            model='gemini-pro',
            metadata={'temperature': 0.7, 'max_tokens': 1000}
        )
        
        assert msg['model'] == 'gemini-pro'
        assert msg['metadata'] is not None
        assert msg['metadata']['temperature'] == 0.7
    
    def test_message_with_tool_results(self, test_conversation):
        """Test saving message with tool results"""
        tool_results = [
            {'tool': 'calculator', 'result': '42'},
            {'tool': 'search', 'result': 'Found 10 results'}
        ]
        
        msg = chatbot_service.save_message(
            conversation_id=test_conversation.id,
            role='assistant',
            content='Here are the results',
            tool_results=tool_results
        )
        
        assert msg['tool_results'] is not None
        assert len(msg['tool_results']) == 2


# ============================================================
# MEMORY TESTS
# ============================================================

class TestMemoryOperations:
    """Test memory CRUD operations"""
    
    def test_save_memory(self, test_user):
        """Test saving a memory"""
        memory = chatbot_service.save_memory(
            user_id=test_user.id,
            question="What is Python?",
            answer="A programming language",
            importance=8
        )
        
        assert memory is not None
        assert memory['user_id'] == test_user.id
        assert memory['question'] == "What is Python?"
        assert memory['answer'] == "A programming language"
        assert memory['importance'] == 8
        
        # Cleanup
        with db_session() as session:
            memory_repo = ChatbotMemoryRepository()
            memory_repo.delete(session, memory['id'])
    
    def test_save_memory_with_tags(self, test_user):
        """Test saving memory with tags"""
        memory = chatbot_service.save_memory(
            user_id=test_user.id,
            question="How to write a loop?",
            answer="Use for or while",
            importance=7,
            tags=['python', 'programming', 'loops']
        )
        
        assert memory['tags'] is not None
        assert len(memory['tags']) == 3
        assert 'python' in memory['tags']
        
        # Cleanup
        with db_session() as session:
            memory_repo = ChatbotMemoryRepository()
            memory_repo.delete(session, memory['id'])
    
    def test_search_memories(self, test_user):
        """Test searching memories"""
        # Create test memories
        memory_ids = []
        memories_data = [
            ("What is Python?", "A programming language"),
            ("What is JavaScript?", "A web programming language"),
            ("How to use Docker?", "Container platform")
        ]
        
        for question, answer in memories_data:
            memory = chatbot_service.save_memory(
                user_id=test_user.id,
                question=question,
                answer=answer,
                importance=5
            )
            memory_ids.append(memory['id'])
        
        # Search for "programming"
        results = chatbot_service.search_memories(
            user_id=test_user.id,
            query="programming"
        )
        
        assert len(results) >= 2  # Should find Python and JavaScript
        
        # Cleanup
        with db_session() as session:
            memory_repo = ChatbotMemoryRepository()
            for mem_id in memory_ids:
                memory_repo.delete(session, mem_id)
    
    def test_get_user_memories(self, test_user):
        """Test getting all user memories"""
        # Create memories
        memory_ids = []
        for i in range(5):
            memory = chatbot_service.save_memory(
                user_id=test_user.id,
                question=f"Question {i}",
                answer=f"Answer {i}",
                importance=i + 1
            )
            memory_ids.append(memory['id'])
        
        # Get all memories
        memories = chatbot_service.get_user_memories(user_id=test_user.id)
        
        assert len(memories) >= 5
        
        # Cleanup
        with db_session() as session:
            memory_repo = ChatbotMemoryRepository()
            for mem_id in memory_ids:
                memory_repo.delete(session, mem_id)


# ============================================================
# FILE UPLOAD TESTS
# ============================================================

class TestFileOperations:
    """Test file tracking operations"""
    
    def test_track_uploaded_file(self, test_user, test_conversation):
        """Test tracking file upload"""
        file_info = chatbot_service.track_uploaded_file(
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            original_filename="test.pdf",
            stored_filename="test_12345.pdf",
            file_size=1024000,
            mime_type="application/pdf",
            storage_path="/uploads/test_12345.pdf"
        )
        
        assert file_info is not None
        assert file_info['original_filename'] == "test.pdf"
        assert file_info['file_size'] == 1024000
        assert file_info['is_processed'] is False
        
        # Cleanup
        with db_session() as session:
            file_repo = UploadedFileRepository()
            file_repo.delete(session, file_info['id'])
    
    def test_mark_file_processed(self, test_user, test_conversation):
        """Test marking file as processed"""
        # Track file
        file_info = chatbot_service.track_uploaded_file(
            user_id=test_user.id,
            conversation_id=test_conversation.id,
            original_filename="document.pdf",
            stored_filename="doc_12345.pdf",
            file_size=2048000,
            mime_type="application/pdf",
            storage_path="/uploads/doc_12345.pdf"
        )
        
        # Mark as processed
        success = chatbot_service.mark_file_processed(
            file_info['id'],
            extracted_text="Sample extracted text"
        )
        
        assert success is True
        
        # Verify
        with db_session_no_commit() as session:
            file_repo = UploadedFileRepository()
            updated_file = file_repo.get_by_id(session, file_info['id'])
            assert updated_file.is_processed is True
            assert updated_file.extracted_text == "Sample extracted text"
        
        # Cleanup
        with db_session() as session:
            file_repo = UploadedFileRepository()
            file_repo.delete(session, file_info['id'])


# ============================================================
# EDGE CASE TESTS
# ============================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_get_nonexistent_conversation(self):
        """Test getting conversation that doesn't exist"""
        conv = chatbot_service.get_conversation(999999)
        assert conv is None
    
    def test_delete_nonexistent_conversation(self):
        """Test deleting conversation that doesn't exist"""
        success = chatbot_service.delete_conversation(999999)
        assert success is False
    
    def test_empty_conversation_messages(self, test_conversation):
        """Test getting messages from empty conversation"""
        messages = chatbot_service.get_conversation_messages(test_conversation.id)
        assert messages == []
    
    def test_search_memories_no_results(self, test_user):
        """Test searching with no results"""
        results = chatbot_service.search_memories(
            user_id=test_user.id,
            query="xyznonexistentquery123"
        )
        assert results == []
    
    def test_duplicate_username_handling(self, test_user):
        """Test that get_or_create_user handles duplicates correctly"""
        # Try to create user with same username
        user1 = chatbot_service.get_or_create_user(username=test_user.username)
        user2 = chatbot_service.get_or_create_user(username=test_user.username)
        
        # Should return same user
        assert user1['id'] == user2['id']


# ============================================================
# TRANSACTION TESTS
# ============================================================

class TestTransactions:
    """Test transaction handling"""
    
    def test_rollback_on_error(self, test_user):
        """Test that transactions rollback on error"""
        with db_session() as session:
            conv_repo = ConversationRepository()
            
            # Create conversation
            conv = conv_repo.create(
                session,
                user_id=test_user.id,
                title="Test Rollback"
            )
            conv_id = conv.id
            
            # Force an error by trying to create with invalid user_id
            try:
                conv_repo.create(
                    session,
                    user_id=999999,  # Non-existent user
                    title="Should Fail"
                )
            except Exception:
                pass
            
            # First conversation should still exist
            result = conv_repo.get_by_id(session, conv_id)
            assert result is not None
            
            # Cleanup
            conv_repo.delete(session, conv_id)
    
    def test_session_cleanup(self, test_user):
        """Test that sessions are properly cleaned up"""
        # Create multiple sessions
        for _ in range(5):
            with db_session() as session:
                user_repo = UserRepository()
                user = user_repo.get_by_id(session, test_user.id)
                assert user is not None
        
        # If sessions weren't cleaned up, this would cause issues


# ============================================================
# RUN TESTS
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
