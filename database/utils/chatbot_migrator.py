"""
ChatBot JSON to Database Migrator

Imports existing JSON conversation files into the database
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from database.services import chatbot_service
from database.utils.session_context import db_session
from database.repositories import UserRepository, ConversationRepository, MessageRepository

logger = logging.getLogger(__name__)


class ChatBotMigrator:
    """
    Migrates ChatBot conversations from JSON files to database
    
    Usage:
        migrator = ChatBotMigrator()
        results = migrator.migrate_all("ChatBot/Storage/conversations")
    """
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.conv_repo = ConversationRepository()
        self.msg_repo = MessageRepository()
        
        self.stats = {
            'conversations_imported': 0,
            'messages_imported': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def migrate_json_file(
        self,
        json_file_path: Path,
        default_user_id: int,
        dry_run: bool = False
    ) -> bool:
        """
        Migrate single JSON conversation file
        
        Args:
            json_file_path: Path to JSON file
            default_user_id: User ID to assign conversation to
            dry_run: If True, don't actually save to database
            
        Returns:
            True if successful
        """
        try:
            # Load JSON
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Processing {json_file_path.name}...")
            
            # Extract conversation data
            title = data.get('title', f"Imported - {json_file_path.stem}")
            messages = data.get('messages', [])
            metadata = data.get('metadata', {})
            tags = data.get('tags', [])
            created_at_str = data.get('created_at')
            
            if not messages:
                logger.warning(f"No messages in {json_file_path.name}, skipping")
                self.stats['skipped'] += 1
                return False
            
            if dry_run:
                logger.info(f"DRY RUN: Would import conversation '{title}' with {len(messages)} messages")
                return True
            
            # Create conversation
            conv = chatbot_service.create_conversation(
                user_id=default_user_id,
                title=title,
                tags=tags,
                metadata=metadata
            )
            
            conversation_id = conv['id']
            logger.info(f"Created conversation {conversation_id}: {title}")
            
            # Import messages
            with db_session() as session:
                seq_num = 1
                for msg in messages:
                    try:
                        role = msg.get('role', 'user')
                        content = msg.get('content', '')
                        model = msg.get('model')
                        msg_metadata = msg.get('metadata', {})
                        
                        # Create message
                        self.msg_repo.create(
                            session,
                            conversation_id=conversation_id,
                            role=role,
                            content=content,
                            model=model,
                            sequence_number=seq_num,
                            metadata=msg_metadata
                        )
                        
                        seq_num += 1
                        self.stats['messages_imported'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error importing message: {e}")
                        self.stats['errors'] += 1
                
                # Update message count
                self.conv_repo.update_message_count(session, conversation_id)
            
            self.stats['conversations_imported'] += 1
            logger.info(f"✅ Imported {len(messages)} messages to conversation {conversation_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error migrating {json_file_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def migrate_all(
        self,
        conversations_dir: str,
        default_username: str = "migrated_user",
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Migrate all JSON files in directory
        
        Args:
            conversations_dir: Directory containing JSON files
            default_username: Username to create/use for migrated conversations
            dry_run: If True, don't actually save to database
            
        Returns:
            Migration statistics
        """
        conversations_path = Path(conversations_dir)
        
        if not conversations_path.exists():
            logger.error(f"Directory not found: {conversations_dir}")
            return self.stats
        
        # Get or create user
        user = chatbot_service.get_or_create_user(
            username=default_username,
            full_name="Migrated User"
        )
        user_id = user['id']
        logger.info(f"Using user {user_id} ({default_username}) for migration")
        
        # Find all JSON files
        json_files = list(conversations_path.glob("*.json"))
        total_files = len(json_files)
        
        logger.info(f"Found {total_files} JSON files to migrate")
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be saved")
        
        # Migrate each file
        for i, json_file in enumerate(json_files, 1):
            logger.info(f"\n[{i}/{total_files}] Processing {json_file.name}")
            self.migrate_json_file(json_file, user_id, dry_run=dry_run)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Conversations imported: {self.stats['conversations_imported']}")
        logger.info(f"Messages imported:      {self.stats['messages_imported']}")
        logger.info(f"Skipped:                {self.stats['skipped']}")
        logger.info(f"Errors:                 {self.stats['errors']}")
        logger.info("="*60)
        
        return self.stats
    
    def migrate_memory_files(
        self,
        memory_dir: str,
        default_user_id: int,
        dry_run: bool = False
    ) -> int:
        """
        Migrate memory JSON files to database
        
        Args:
            memory_dir: Directory containing memory JSON files
            default_user_id: User ID to assign memories to
            dry_run: If True, don't actually save
            
        Returns:
            Number of memories imported
        """
        memory_path = Path(memory_dir)
        
        if not memory_path.exists():
            logger.error(f"Memory directory not found: {memory_dir}")
            return 0
        
        json_files = list(memory_path.glob("*.json"))
        count = 0
        
        logger.info(f"\n📚 Migrating {len(json_files)} memory files...")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                question = data.get('title', data.get('question', ''))
                answer = data.get('content', data.get('answer', ''))
                importance = int(data.get('importance', 5))
                tags = data.get('tags', [])
                
                if not question or not answer:
                    continue
                
                if dry_run:
                    logger.info(f"DRY RUN: Would import memory '{question[:50]}...'")
                else:
                    chatbot_service.save_memory(
                        user_id=default_user_id,
                        question=question,
                        answer=answer,
                        importance=importance,
                        tags=tags
                    )
                
                count += 1
                
            except Exception as e:
                logger.error(f"Error migrating memory {json_file}: {e}")
        
        logger.info(f"✅ Imported {count} memories")
        return count


def main():
    """
    Main migration script
    
    Usage:
        python -m database.utils.chatbot_migrator
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate ChatBot JSON files to database")
    parser.add_argument(
        '--conversations-dir',
        default='ChatBot/Storage/conversations',
        help='Directory containing conversation JSON files'
    )
    parser.add_argument(
        '--memory-dir',
        default='ChatBot/data/memory',
        help='Directory containing memory JSON files'
    )
    parser.add_argument(
        '--username',
        default='migrated_user',
        help='Username for migrated data'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run (don\'t actually save to database)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create migrator
    migrator = ChatBotMigrator()
    
    # Migrate conversations
    logger.info("🚀 Starting migration...")
    stats = migrator.migrate_all(
        args.conversations_dir,
        args.username,
        dry_run=args.dry_run
    )
    
    # Get user for memory migration
    user = chatbot_service.get_or_create_user(username=args.username)
    
    # Migrate memories
    memory_count = migrator.migrate_memory_files(
        args.memory_dir,
        user['id'],
        dry_run=args.dry_run
    )
    
    logger.info("\n✅ Migration complete!")


if __name__ == '__main__':
    main()
