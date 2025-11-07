"""
Phase 3 - Task 3.6: Rollback Script
Rollback migration if something goes wrong

This script will:
1. Clear database tables (conversations, messages, memories, files)
2. Optionally restore from JSON backup
3. Generate rollback report
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import logging
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RollbackScript:
    """Rollback migration and restore from backup"""
    
    def __init__(self, backup_path: str = None, dry_run: bool = True):
        """
        Initialize rollback script
        
        Args:
            backup_path: Path to backup directory or tar.gz file
            dry_run: If True, don't actually perform rollback
        """
        self.backup_path = Path(backup_path) if backup_path else None
        self.dry_run = dry_run
        
        self.stats = {
            'start_time': datetime.now(),
            'end_time': None,
            'database_cleared': False,
            'backup_restored': False,
            'errors': []
        }
        
        logger.info("Rollback script initialized")
        logger.info(f"  Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        logger.info(f"  Backup: {backup_path if backup_path else 'None'}")
    
    def clear_database(self) -> bool:
        """
        Clear database tables
        
        Returns:
            bool: Success status
        """
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: CLEAR DATABASE")
        logger.info("=" * 80)
        
        if self.dry_run:
            logger.info("DRY RUN: Would clear the following tables:")
            logger.info("  - uploaded_files")
            logger.info("  - chatbot_memory")
            logger.info("  - messages")
            logger.info("  - conversations")
            logger.info("  - users (optional - preserve users)")
            
            self.stats['database_cleared'] = True
            return True
        
        # TODO: Implement actual database clearing
        # This will be implemented when we have database connection ready
        
        logger.warning("Database clearing not yet implemented")
        logger.info("SQL commands that would be executed:")
        logger.info("""
            DELETE FROM chatbot.uploaded_files;
            DELETE FROM chatbot.chatbot_memory;
            DELETE FROM chatbot.messages;
            DELETE FROM chatbot.conversations;
            -- Optionally: DELETE FROM chatbot.users;
        """)
        
        self.stats['database_cleared'] = False
        return False
    
    def restore_backup(self) -> bool:
        """
        Restore from backup
        
        Returns:
            bool: Success status
        """
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: RESTORE FROM BACKUP")
        logger.info("=" * 80)
        
        if not self.backup_path:
            logger.warning("No backup path specified. Skipping restore.")
            return False
        
        if not self.backup_path.exists():
            error = f"Backup path does not exist: {self.backup_path}"
            self.stats['errors'].append(error)
            logger.error(error)
            return False
        
        if self.dry_run:
            logger.info(f"DRY RUN: Would restore from: {self.backup_path}")
            
            if self.backup_path.suffix == '.gz':
                logger.info("  - Extract tar.gz archive")
                logger.info("  - Copy JSON files back to Storage/conversations/")
            else:
                logger.info("  - Copy JSON files from backup directory")
            
            self.stats['backup_restored'] = True
            return True
        
        # TODO: Implement actual backup restoration
        logger.warning("Backup restoration not yet implemented")
        
        self.stats['backup_restored'] = False
        return False
    
    def create_backup(self, source_path: str, backup_name: str = None) -> str:
        """
        Create backup before rollback
        
        Args:
            source_path: Path to data to backup
            backup_name: Optional backup name
        
        Returns:
            str: Path to backup file
        """
        logger.info("\n" + "=" * 80)
        logger.info("CREATING BACKUP")
        logger.info("=" * 80)
        
        source_path = Path(source_path)
        
        if not source_path.exists():
            logger.error(f"Source path does not exist: {source_path}")
            return None
        
        if backup_name is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"chatbot_backup_{timestamp}.tar.gz"
        
        backup_path = Path(__file__).parent / backup_name
        
        if self.dry_run:
            logger.info(f"DRY RUN: Would create backup at: {backup_path}")
            return str(backup_path)
        
        logger.info(f"Creating backup: {backup_path}")
        
        try:
            import tarfile
            
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(source_path, arcname=source_path.name)
            
            logger.info(f"Backup created successfully: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            error = f"Failed to create backup: {e}"
            self.stats['errors'].append(error)
            logger.error(error)
            return None
    
    def run(self) -> dict:
        """
        Run rollback
        
        Returns:
            dict: Rollback statistics
        """
        logger.info("\n" + "=" * 80)
        logger.info("STARTING ROLLBACK")
        logger.info("=" * 80)
        
        # Step 1: Clear database
        success = self.clear_database()
        if not success and not self.dry_run:
            logger.error("Failed to clear database")
            return self.stats
        
        # Step 2: Restore from backup
        if self.backup_path:
            success = self.restore_backup()
            if not success and not self.dry_run:
                logger.error("Failed to restore from backup")
                return self.stats
        
        # Finalize
        self.stats['end_time'] = datetime.now()
        
        logger.info("\n" + "=" * 80)
        logger.info("ROLLBACK COMPLETED")
        logger.info("=" * 80)
        
        return self.stats
    
    def generate_report(self) -> str:
        """Generate rollback report"""
        duration = None
        if self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        report = []
        report.append("=" * 80)
        report.append("ROLLBACK REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Mode
        mode = "DRY RUN (No changes made)" if self.dry_run else "EXECUTE (Changes applied)"
        report.append(f"Mode: {mode}")
        report.append("")
        
        # Timing
        report.append("TIMING")
        report.append("-" * 80)
        report.append(f"Start Time:   {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        if self.stats['end_time']:
            report.append(f"End Time:     {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"Duration:     {duration:.2f} seconds")
        report.append("")
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 80)
        
        db_status = "YES" if self.stats['database_cleared'] else "NO"
        report.append(f"Database Cleared:    {db_status}")
        
        backup_status = "YES" if self.stats['backup_restored'] else "NO"
        report.append(f"Backup Restored:     {backup_status}")
        report.append("")
        
        # Errors
        if self.stats['errors']:
            report.append("ERRORS")
            report.append("-" * 80)
            for error in self.stats['errors']:
                report.append(f"  • {error}")
            report.append("")
        else:
            report.append("NO ERRORS")
            report.append("")
        
        # Next steps
        if self.dry_run:
            report.append("NEXT STEPS")
            report.append("-" * 80)
            report.append("Dry-run completed. To actually perform rollback:")
            report.append("  python database/scripts/rollback_migration.py --execute")
            report.append("")
            report.append("WARNING: This will delete all data in the database!")
        else:
            report.append("STATUS")
            report.append("-" * 80)
            if self.stats['errors']:
                report.append("Rollback completed with errors")
            else:
                report.append("Rollback completed successfully")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Rollback migration and restore from backup'
    )
    parser.add_argument(
        '--backup',
        type=str,
        default=None,
        help='Path to backup directory or tar.gz file'
    )
    parser.add_argument(
        '--create-backup',
        type=str,
        default=None,
        help='Create backup of specified directory before rollback'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no changes)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute rollback (WARNING: will delete database data!)'
    )
    
    args = parser.parse_args()
    
    # Determine mode
    if args.execute:
        dry_run = False
        logger.warning("=" * 80)
        logger.warning("WARNING: EXECUTE MODE")
        logger.warning("This will DELETE all data in the database!")
        logger.warning("=" * 80)
        
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Rollback cancelled")
            return 0
    else:
        dry_run = True
        logger.info("DRY RUN MODE - No changes will be made")
    
    # Create backup if requested
    if args.create_backup:
        logger.info(f"Creating backup of: {args.create_backup}")
        rollback = RollbackScript(dry_run=dry_run)
        backup_path = rollback.create_backup(args.create_backup)
        if backup_path:
            logger.info(f"Backup created: {backup_path}")
        return 0
    
    # Run rollback
    rollback = RollbackScript(
        backup_path=args.backup,
        dry_run=dry_run
    )
    
    stats = rollback.run()
    
    # Generate report
    report = rollback.generate_report()
    print("\n" + report)
    
    # Return exit code
    if stats['errors']:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
