#!/usr/bin/env python
"""
Cleanup Script for Chatbot Service

Performs cleanup tasks:
- Remove temporary files
- Clean old logs
- Optimize database
- Clear expired cache
"""

import os
import sys
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path
CHATBOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(CHATBOT_DIR))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CleanupManager:
    """Manages cleanup tasks for the chatbot service"""
    
    def __init__(self, chatbot_dir: Path = None):
        self.chatbot_dir = chatbot_dir or CHATBOT_DIR
        self.results = {
            'files_removed': 0,
            'space_freed_mb': 0,
            'cache_cleared': 0,
            'logs_cleaned': 0
        }
    
    def cleanup_temp_files(self) -> int:
        """Remove temporary files"""
        temp_patterns = ['*.tmp', '*.pyc', '__pycache__', '.pytest_cache']
        removed = 0
        
        for pattern in temp_patterns:
            for path in self.chatbot_dir.rglob(pattern):
                try:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    removed += 1
                except Exception as e:
                    logger.warning(f"Could not remove {path}: {e}")
        
        self.results['files_removed'] += removed
        logger.info(f"Removed {removed} temporary files/directories")
        return removed
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """Remove log files older than specified days"""
        log_dirs = [
            self.chatbot_dir / 'logs',
            self.chatbot_dir.parent.parent / 'logs' / 'chatbot'
        ]
        
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0
        freed = 0
        
        for log_dir in log_dirs:
            if not log_dir.exists():
                continue
            
            for log_file in log_dir.glob('*.log*'):
                try:
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if mtime < cutoff:
                        size = log_file.stat().st_size
                        log_file.unlink()
                        removed += 1
                        freed += size
                except Exception as e:
                    logger.warning(f"Could not remove log {log_file}: {e}")
        
        self.results['logs_cleaned'] += removed
        self.results['space_freed_mb'] += freed / (1024 * 1024)
        logger.info(f"Removed {removed} old log files ({freed / (1024*1024):.2f} MB)")
        return removed
    
    def cleanup_cache(self) -> int:
        """Clear expired cache entries"""
        try:
            from database.cache.chatbot_cache import ChatbotCache
            
            # Clear all cache (optional - be careful in production)
            # ChatbotCache.clear_all()
            
            # Just log stats
            stats = ChatbotCache.get_stats()
            logger.info(f"Cache stats: {stats}")
            return 0
            
        except ImportError:
            logger.warning("Cache module not available")
            return 0
    
    def cleanup_old_backups(self, keep: int = 5) -> int:
        """Keep only the most recent backups"""
        backup_dir = self.chatbot_dir.parent.parent / 'backups'
        
        if not backup_dir.exists():
            return 0
        
        # Get backup files sorted by modification time
        backups = sorted(
            backup_dir.glob('chatbot_backup_*'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        removed = 0
        freed = 0
        
        # Remove old backups beyond the keep limit
        for backup in backups[keep:]:
            try:
                size = backup.stat().st_size
                backup.unlink()
                removed += 1
                freed += size
                logger.info(f"Removed old backup: {backup.name}")
            except Exception as e:
                logger.warning(f"Could not remove backup {backup}: {e}")
        
        self.results['files_removed'] += removed
        self.results['space_freed_mb'] += freed / (1024 * 1024)
        return removed
    
    def optimize_database(self) -> Dict:
        """Run database optimization tasks"""
        try:
            from config.mongodb_helpers import get_mongo_client
            from database.utils.optimizer import IndexManager
            
            client = get_mongo_client()
            if not client:
                logger.warning("MongoDB not available")
                return {"status": "skipped"}
            
            db = client['ai_assistant']
            
            # Ensure indexes
            IndexManager.ensure_indexes(db)
            
            # Get collection stats
            stats = {}
            for coll_name in ['conversations', 'messages', 'memories']:
                try:
                    stats[coll_name] = {
                        'count': db[coll_name].count_documents({}),
                        'indexes': len(list(db[coll_name].list_indexes()))
                    }
                except:
                    stats[coll_name] = {'error': 'Could not get stats'}
            
            logger.info(f"Database stats: {stats}")
            return stats
            
        except ImportError as e:
            logger.warning(f"Database modules not available: {e}")
            return {"status": "skipped", "error": str(e)}
    
    def run_all(self, include_db: bool = True) -> Dict:
        """Run all cleanup tasks"""
        logger.info("=" * 50)
        logger.info("Starting Chatbot Cleanup")
        logger.info("=" * 50)
        
        # Cleanup tasks
        self.cleanup_temp_files()
        self.cleanup_old_logs(days=30)
        self.cleanup_old_backups(keep=5)
        self.cleanup_cache()
        
        if include_db:
            self.results['database'] = self.optimize_database()
        
        # Summary
        logger.info("=" * 50)
        logger.info("Cleanup Complete")
        logger.info(f"Files removed: {self.results['files_removed']}")
        logger.info(f"Logs cleaned: {self.results['logs_cleaned']}")
        logger.info(f"Space freed: {self.results['space_freed_mb']:.2f} MB")
        logger.info("=" * 50)
        
        return self.results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Chatbot Cleanup Script')
    parser.add_argument('--skip-db', action='store_true', help='Skip database optimization')
    parser.add_argument('--log-days', type=int, default=30, help='Remove logs older than N days')
    parser.add_argument('--keep-backups', type=int, default=5, help='Number of backups to keep')
    
    args = parser.parse_args()
    
    manager = CleanupManager()
    
    # Custom settings
    if args.log_days != 30:
        manager.cleanup_old_logs(days=args.log_days)
    
    if args.keep_backups != 5:
        manager.cleanup_old_backups(keep=args.keep_backups)
    
    # Run all
    results = manager.run_all(include_db=not args.skip_db)
    
    print("\nCleanup Results:")
    print("-" * 30)
    for key, value in results.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
