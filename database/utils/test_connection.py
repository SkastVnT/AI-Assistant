"""
Test database connection and create tables

Run this script to verify PostgreSQL connection and initialize database schema
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect, text
from database.models import Base
from database.utils.engine import DatabaseEngine, get_session

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_connection() -> bool:
    """
    Test database connection
    
    Returns:
        True if connection successful
    """
    try:
        logger.info("Testing database connection...")
        
        engine = DatabaseEngine.get_engine()
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        
        logger.info("✅ Database connection successful")
        return True
    
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def get_database_info() -> dict:
    """
    Get database server information
    
    Returns:
        Dictionary with database info
    """
    try:
        engine = DatabaseEngine.get_engine()
        
        with engine.connect() as conn:
            # PostgreSQL version
            version_result = conn.execute(text("SELECT version()"))
            version = version_result.scalar()
            
            # Current database
            db_result = conn.execute(text("SELECT current_database()"))
            database = db_result.scalar()
            
            # Current user
            user_result = conn.execute(text("SELECT current_user"))
            user = user_result.scalar()
        
        return {
            "version": version,
            "database": database,
            "user": user
        }
    
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {}


def check_existing_tables() -> list:
    """
    Check for existing tables
    
    Returns:
        List of existing table names
    """
    try:
        engine = DatabaseEngine.get_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        return tables
    
    except Exception as e:
        logger.error(f"Failed to check existing tables: {e}")
        return []


def create_tables(drop_existing: bool = False) -> bool:
    """
    Create database tables
    
    Args:
        drop_existing: Whether to drop existing tables first
    
    Returns:
        True if successful
    """
    try:
        engine = DatabaseEngine.get_engine()
        
        if drop_existing:
            logger.warning("⚠️  Dropping existing tables...")
            Base.metadata.drop_all(engine)
            logger.info("Existing tables dropped")
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)
        
        logger.info("✅ All tables created successfully")
        return True
    
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        return False


def verify_tables() -> bool:
    """
    Verify all expected tables exist
    
    Returns:
        True if all tables exist
    """
    try:
        expected_tables = {
            'users',
            'conversations',
            'messages',
            'chatbot_memory',
            'uploaded_files'
        }
        
        existing_tables = set(check_existing_tables())
        
        logger.info(f"\nExpected tables: {len(expected_tables)}")
        logger.info(f"Existing tables: {len(existing_tables)}")
        
        missing_tables = expected_tables - existing_tables
        extra_tables = existing_tables - expected_tables
        
        if missing_tables:
            logger.error(f"❌ Missing tables: {missing_tables}")
            return False
        
        if extra_tables:
            logger.warning(f"⚠️  Extra tables found: {extra_tables}")
        
        logger.info("✅ All expected tables exist")
        
        # Show table details
        engine = DatabaseEngine.get_engine()
        inspector = inspect(engine)
        
        for table in sorted(expected_tables):
            columns = inspector.get_columns(table)
            indexes = inspector.get_indexes(table)
            foreign_keys = inspector.get_foreign_keys(table)
            
            logger.info(f"\nTable: {table}")
            logger.info(f"  - Columns: {len(columns)}")
            logger.info(f"  - Indexes: {len(indexes)}")
            logger.info(f"  - Foreign Keys: {len(foreign_keys)}")
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to verify tables: {e}")
        return False


def test_crud_operations() -> bool:
    """
    Test basic CRUD operations
    
    Returns:
        True if CRUD operations work
    """
    try:
        from database.models import User
        
        logger.info("\nTesting CRUD operations...")
        
        with get_session() as session:
            # Create
            test_user = User(
                username="test_user",
                email="test@example.com",
                full_name="Test User"
            )
            session.add(test_user)
            session.commit()
            logger.info(f"✅ CREATE: Created user with ID {test_user.id}")
            
            # Read
            user = session.query(User).filter_by(username="test_user").first()
            assert user is not None
            logger.info(f"✅ READ: Found user {user.username}")
            
            # Update
            user.full_name = "Updated Name"
            session.commit()
            logger.info("✅ UPDATE: Updated user name")
            
            # Delete
            session.delete(user)
            session.commit()
            logger.info("✅ DELETE: Deleted user")
        
        logger.info("✅ All CRUD operations successful")
        return True
    
    except Exception as e:
        logger.error(f"❌ CRUD operations failed: {e}")
        return False


def show_pool_status():
    """Show connection pool status"""
    status = DatabaseEngine.get_pool_status()
    logger.info("\nConnection Pool Status:")
    for key, value in status.items():
        logger.info(f"  {key}: {value}")


def main():
    """Main test function"""
    print("=" * 80)
    print("DATABASE CONNECTION TEST")
    print("=" * 80)
    
    # Check environment variable
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        logger.info(f"Using DATABASE_URL: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
    else:
        logger.warning("DATABASE_URL not set, using default")
    
    # Initialize engine
    try:
        DatabaseEngine.initialize(echo=True)
    except Exception as e:
        logger.error(f"Failed to initialize engine: {e}")
        return False
    
    # Test connection
    if not test_connection():
        logger.error("Database connection failed. Please check:")
        logger.error("  1. PostgreSQL is running")
        logger.error("  2. DATABASE_URL is correct")
        logger.error("  3. User has necessary permissions")
        return False
    
    # Get database info
    db_info = get_database_info()
    if db_info:
        logger.info("\nDatabase Information:")
        logger.info(f"  Version: {db_info.get('version', 'Unknown')[:50]}...")
        logger.info(f"  Database: {db_info.get('database', 'Unknown')}")
        logger.info(f"  User: {db_info.get('user', 'Unknown')}")
    
    # Check existing tables
    existing = check_existing_tables()
    if existing:
        logger.info(f"\nExisting tables: {existing}")
        
        # Ask user if they want to drop tables
        response = input("\n⚠️  Drop existing tables? (yes/no): ")
        drop_existing = response.lower() in ['yes', 'y']
    else:
        logger.info("\nNo existing tables found")
        drop_existing = False
    
    # Create tables
    if not create_tables(drop_existing=drop_existing):
        return False
    
    # Verify tables
    if not verify_tables():
        return False
    
    # Test CRUD
    if not test_crud_operations():
        return False
    
    # Show pool status
    show_pool_status()
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80)
    
    # Cleanup
    DatabaseEngine.dispose()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
