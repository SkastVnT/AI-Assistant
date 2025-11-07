"""
Database setup script

Initialize database, create tables, and seed initial data
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.models import Base, User
from database.utils.engine import DatabaseEngine, get_session

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_tables(drop_existing: bool = False) -> bool:
    """
    Create all database tables
    
    Args:
        drop_existing: Whether to drop existing tables first
        
    Returns:
        True if successful
    """
    try:
        engine = DatabaseEngine.get_engine()
        
        if drop_existing:
            logger.warning("⚠️  Dropping all existing tables...")
            Base.metadata.drop_all(engine)
            logger.info("✅ Tables dropped")
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)
        
        logger.info("✅ All tables created successfully")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Created {len(tables)} tables: {', '.join(tables)}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        return False


def seed_admin_user() -> bool:
    """
    Create default admin user
    
    Returns:
        True if successful
    """
    try:
        logger.info("Seeding admin user...")
        
        with get_session() as session:
            # Check if admin exists
            existing_admin = session.query(User).filter_by(username="admin").first()
            
            if existing_admin:
                logger.info("⚠️  Admin user already exists, skipping")
                return True
            
            # Create admin user
            admin = User(
                username="admin",
                email="admin@aiassistant.local",
                full_name="System Administrator",
                is_active=True,
                is_admin=True,
                last_login=datetime.utcnow()
            )
            
            session.add(admin)
            session.commit()
            
            logger.info(f"✅ Admin user created with ID: {admin.id}")
            logger.info(f"   Username: {admin.username}")
            logger.info(f"   Email: {admin.email}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to seed admin user: {e}")
        return False


def seed_demo_data() -> bool:
    """
    Create demo data for testing
    
    Returns:
        True if successful
    """
    try:
        logger.info("Seeding demo data...")
        
        from database.models import Conversation, Message, MessageRole, ChatbotMemory
        
        with get_session() as session:
            # Create demo user
            demo_user = session.query(User).filter_by(username="demo").first()
            
            if not demo_user:
                demo_user = User(
                    username="demo",
                    email="demo@aiassistant.local",
                    full_name="Demo User",
                    is_active=True,
                    is_admin=False
                )
                session.add(demo_user)
                session.flush()
            
            # Check if demo conversation exists
            existing_conv = session.query(Conversation).filter_by(
                user_id=demo_user.id,
                title="Welcome to AI-Assistant"
            ).first()
            
            if existing_conv:
                logger.info("⚠️  Demo data already exists, skipping")
                return True
            
            # Create demo conversation
            conversation = Conversation(
                user_id=demo_user.id,
                title="Welcome to AI-Assistant",
                tags=["demo", "welcome"],
                is_pinned=True
            )
            session.add(conversation)
            session.flush()
            
            # Add welcome messages
            messages = [
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.SYSTEM,
                    content="You are a helpful AI assistant.",
                    sequence_number=0
                ),
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.USER,
                    content="Hello! What can you help me with?",
                    sequence_number=1
                ),
                Message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content="Welcome to AI-Assistant! I can help you with:\n\n"
                            "1. 💬 Natural conversations and questions\n"
                            "2. 📄 Document analysis and summarization\n"
                            "3. 🗣️ Speech-to-text transcription\n"
                            "4. 🗄️ Text-to-SQL database queries\n"
                            "5. 🎨 Image generation with Stable Diffusion\n\n"
                            "Feel free to ask me anything!",
                    model="gpt-4",
                    sequence_number=2
                )
            ]
            
            session.add_all(messages)
            conversation.message_count = len(messages)
            
            # Add demo memory
            memory = ChatbotMemory(
                user_id=demo_user.id,
                conversation_id=conversation.id,
                question="What is AI-Assistant?",
                answer="AI-Assistant is a comprehensive platform that integrates multiple AI services including "
                       "ChatBot, Document Intelligence, Speech-to-Text, Text-to-SQL, and Stable Diffusion.",
                importance=8,
                tags=["ai-assistant", "introduction"]
            )
            session.add(memory)
            
            session.commit()
            
            logger.info("✅ Demo data seeded successfully")
            logger.info(f"   Demo user ID: {demo_user.id}")
            logger.info(f"   Demo conversation ID: {conversation.id}")
            logger.info(f"   Messages: {len(messages)}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to seed demo data: {e}")
        return False


def verify_setup() -> bool:
    """
    Verify database setup is correct
    
    Returns:
        True if verification passed
    """
    try:
        logger.info("\nVerifying database setup...")
        
        with get_session() as session:
            # Count users
            user_count = session.query(User).count()
            logger.info(f"✅ Users: {user_count}")
            
            # Count conversations
            from database.models import Conversation
            conv_count = session.query(Conversation).count()
            logger.info(f"✅ Conversations: {conv_count}")
            
            # Count messages
            from database.models import Message
            msg_count = session.query(Message).count()
            logger.info(f"✅ Messages: {msg_count}")
            
            # Count memories
            from database.models import ChatbotMemory
            mem_count = session.query(ChatbotMemory).count()
            logger.info(f"✅ Memories: {mem_count}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


def main():
    """Main setup function"""
    print("=" * 80)
    print("AI-ASSISTANT DATABASE SETUP")
    print("=" * 80)
    
    # Check environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.warning("DATABASE_URL not set, using default")
        database_url = "postgresql://postgres:postgres@localhost:5432/ai_assistant"
    
    logger.info(f"Database: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
    
    # Initialize engine
    try:
        DatabaseEngine.initialize(database_url=database_url, echo=False)
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error("\nPlease ensure:")
        logger.error("  1. PostgreSQL is running (docker-compose up postgres)")
        logger.error("  2. DATABASE_URL is correct")
        logger.error("  3. Database exists and user has permissions")
        return False
    
    # Ask user for confirmation
    print("\nThis will:")
    print("  1. Create all database tables")
    print("  2. Create admin user (admin@aiassistant.local)")
    print("  3. Create demo data for testing")
    print()
    
    response = input("Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        logger.info("Setup cancelled")
        return False
    
    # Ask if should drop existing tables
    response = input("\n⚠️  Drop existing tables? (yes/no): ")
    drop_existing = response.lower() in ['yes', 'y']
    
    # Create tables
    if not create_tables(drop_existing=drop_existing):
        return False
    
    # Seed admin user
    if not seed_admin_user():
        return False
    
    # Seed demo data
    response = input("\nCreate demo data? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        if not seed_demo_data():
            return False
    
    # Verify setup
    if not verify_setup():
        return False
    
    print("\n" + "=" * 80)
    print("✅ DATABASE SETUP COMPLETE")
    print("=" * 80)
    print("\nAccess pgAdmin at: http://localhost:5050")
    print("  Email: admin@aiassistant.local")
    print("  Password: admin123")
    print()
    
    # Cleanup
    DatabaseEngine.dispose()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
