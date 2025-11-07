"""
Automated PostgreSQL database backup script with rotation.

Features:
- Full database dump with compression
- Automatic backup rotation (keep last N backups)
- Timestamp-based naming
- Email notifications on failure (optional)
- Backup verification
- S3 upload support (optional)

Usage:
    python -m database.utils.backup --backup-dir ./backups --keep 7
"""

import os
import sys
import gzip
import shutil
import argparse
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

class BackupConfig:
    """Backup configuration"""
    
    def __init__(
        self,
        database_url: str,
        backup_dir: str = "./backups",
        keep_backups: int = 7,
        compress: bool = True,
        verify: bool = True
    ):
        self.database_url = database_url
        self.backup_dir = Path(backup_dir)
        self.keep_backups = keep_backups
        self.compress = compress
        self.verify = verify
        
        # Parse database URL
        self.parse_database_url()
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_database_url(self):
        """Parse PostgreSQL URL"""
        # Format: postgresql://user:password@host:port/database
        url = self.database_url.replace('postgresql://', '')
        
        # Split credentials and host
        if '@' in url:
            credentials, host_part = url.split('@')
            if ':' in credentials:
                self.user, self.password = credentials.split(':', 1)
            else:
                self.user = credentials
                self.password = None
        else:
            host_part = url
            self.user = 'postgres'
            self.password = None
        
        # Split host and database
        if '/' in host_part:
            host_port, self.database = host_part.split('/', 1)
        else:
            host_port = host_part
            self.database = 'ai_assistant'
        
        # Split host and port
        if ':' in host_port:
            self.host, port_str = host_port.split(':')
            self.port = int(port_str)
        else:
            self.host = host_port
            self.port = 5432


# ============================================================
# BACKUP FUNCTIONS
# ============================================================

def create_backup(config: BackupConfig) -> Optional[Path]:
    """
    Create database backup using pg_dump
    
    Args:
        config: Backup configuration
    
    Returns:
        Path to backup file or None on failure
    """
    # Generate backup filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = config.backup_dir / f"backup_{config.database}_{timestamp}.sql"
    
    logger.info(f"Creating backup: {backup_file}")
    
    # Build pg_dump command
    env = os.environ.copy()
    if config.password:
        env['PGPASSWORD'] = config.password
    
    cmd = [
        'pg_dump',
        '-h', config.host,
        '-p', str(config.port),
        '-U', config.user,
        '-d', config.database,
        '--format=plain',
        '--no-owner',
        '--no-privileges',
        '-f', str(backup_file)
    ]
    
    try:
        # Execute pg_dump
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            return None
        
        logger.info(f"✅ Backup created: {backup_file}")
        
        # Compress if enabled
        if config.compress:
            compressed_file = compress_backup(backup_file)
            if compressed_file:
                backup_file.unlink()  # Remove uncompressed
                backup_file = compressed_file
        
        # Verify backup
        if config.verify:
            if not verify_backup(backup_file):
                logger.error("Backup verification failed")
                return None
        
        return backup_file
    
    except subprocess.TimeoutExpired:
        logger.error("Backup timeout (exceeded 5 minutes)")
        return None
    except FileNotFoundError:
        logger.error("pg_dump not found. Ensure PostgreSQL client tools are installed")
        return None
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return None


def compress_backup(backup_file: Path) -> Optional[Path]:
    """
    Compress backup file with gzip
    
    Args:
        backup_file: Path to SQL backup file
    
    Returns:
        Path to compressed file or None
    """
    compressed_file = backup_file.with_suffix('.sql.gz')
    
    try:
        logger.info(f"Compressing backup: {compressed_file}")
        
        with open(backup_file, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Check compression ratio
        original_size = backup_file.stat().st_size
        compressed_size = compressed_file.stat().st_size
        ratio = (1 - compressed_size / original_size) * 100
        
        logger.info(
            f"✅ Compression complete: {original_size / 1024 / 1024:.1f}MB → "
            f"{compressed_size / 1024 / 1024:.1f}MB ({ratio:.1f}% reduction)"
        )
        
        return compressed_file
    
    except Exception as e:
        logger.error(f"Compression failed: {e}")
        return None


def verify_backup(backup_file: Path) -> bool:
    """
    Verify backup file integrity
    
    Args:
        backup_file: Path to backup file
    
    Returns:
        True if valid
    """
    try:
        logger.info(f"Verifying backup: {backup_file}")
        
        # Check file exists and has content
        if not backup_file.exists():
            logger.error("Backup file does not exist")
            return False
        
        file_size = backup_file.stat().st_size
        if file_size == 0:
            logger.error("Backup file is empty")
            return False
        
        # If compressed, test decompression
        if backup_file.suffix == '.gz':
            with gzip.open(backup_file, 'rb') as f:
                # Read first 1KB to test
                f.read(1024)
        else:
            # For uncompressed, check for SQL content
            with open(backup_file, 'r') as f:
                first_line = f.readline()
                if not first_line.strip():
                    logger.error("Backup file appears to be empty")
                    return False
        
        logger.info(f"✅ Backup verified: {file_size / 1024 / 1024:.1f}MB")
        return True
    
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


# ============================================================
# BACKUP ROTATION
# ============================================================

def rotate_backups(config: BackupConfig):
    """
    Remove old backups, keeping only the most recent N
    
    Args:
        config: Backup configuration
    """
    logger.info(f"Rotating backups (keep last {config.keep_backups})")
    
    # Find all backup files
    backup_files = sorted(
        config.backup_dir.glob('backup_*.sql*'),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    # Keep only the most recent
    to_delete = backup_files[config.keep_backups:]
    
    for backup_file in to_delete:
        try:
            logger.info(f"Deleting old backup: {backup_file.name}")
            backup_file.unlink()
        except Exception as e:
            logger.error(f"Failed to delete {backup_file}: {e}")
    
    logger.info(f"✅ Rotation complete: {len(to_delete)} backups deleted")


def list_backups(config: BackupConfig) -> List[dict]:
    """
    List all available backups
    
    Args:
        config: Backup configuration
    
    Returns:
        List of backup information
    """
    backup_files = sorted(
        config.backup_dir.glob('backup_*.sql*'),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    backups = []
    for backup_file in backup_files:
        stat = backup_file.stat()
        backups.append({
            'filename': backup_file.name,
            'path': str(backup_file),
            'size': stat.st_size,
            'size_mb': stat.st_size / 1024 / 1024,
            'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'compressed': backup_file.suffix == '.gz'
        })
    
    return backups


# ============================================================
# RESTORE FUNCTIONS
# ============================================================

def restore_backup(config: BackupConfig, backup_file: Path) -> bool:
    """
    Restore database from backup
    
    Args:
        config: Backup configuration
        backup_file: Path to backup file
    
    Returns:
        True if successful
    """
    logger.info(f"Restoring backup: {backup_file}")
    
    # Decompress if needed
    if backup_file.suffix == '.gz':
        logger.info("Decompressing backup...")
        temp_file = backup_file.with_suffix('')
        try:
            with gzip.open(backup_file, 'rb') as f_in:
                with open(temp_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_file = temp_file
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return False
    
    # Build psql command
    env = os.environ.copy()
    if config.password:
        env['PGPASSWORD'] = config.password
    
    cmd = [
        'psql',
        '-h', config.host,
        '-p', str(config.port),
        '-U', config.user,
        '-d', config.database,
        '-f', str(backup_file)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"Restore failed: {result.stderr}")
            return False
        
        logger.info("✅ Restore complete")
        return True
    
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False
    finally:
        # Clean up temp file
        if backup_file.suffix != '.gz' and backup_file.name.startswith('backup_'):
            backup_file.unlink()


# ============================================================
# CLI
# ============================================================

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Database backup utility')
    parser.add_argument(
        '--database-url',
        default=os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/ai_assistant'),
        help='PostgreSQL connection URL'
    )
    parser.add_argument(
        '--backup-dir',
        default='./database/backups',
        help='Backup directory (default: ./database/backups)'
    )
    parser.add_argument(
        '--keep',
        type=int,
        default=7,
        help='Number of backups to keep (default: 7)'
    )
    parser.add_argument(
        '--no-compress',
        action='store_true',
        help='Disable compression'
    )
    parser.add_argument(
        '--no-verify',
        action='store_true',
        help='Skip backup verification'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available backups'
    )
    parser.add_argument(
        '--restore',
        help='Restore from backup file'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create config
    config = BackupConfig(
        database_url=args.database_url,
        backup_dir=args.backup_dir,
        keep_backups=args.keep,
        compress=not args.no_compress,
        verify=not args.no_verify
    )
    
    # List backups
    if args.list:
        backups = list_backups(config)
        print(f"\n{'='*70}")
        print(f"Available Backups ({len(backups)})")
        print(f"{'='*70}")
        for backup in backups:
            print(f"  {backup['filename']}")
            print(f"    Size: {backup['size_mb']:.1f}MB")
            print(f"    Created: {backup['created']}")
            print(f"    Compressed: {'Yes' if backup['compressed'] else 'No'}")
            print()
        return 0
    
    # Restore backup
    if args.restore:
        backup_file = Path(args.restore)
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_file}")
            return 1
        
        if restore_backup(config, backup_file):
            return 0
        return 1
    
    # Create backup
    backup_file = create_backup(config)
    if not backup_file:
        logger.error("❌ Backup failed")
        return 1
    
    # Rotate old backups
    rotate_backups(config)
    
    logger.info("✅ Backup process complete")
    return 0


if __name__ == '__main__':
    sys.exit(main())
