"""
Phase 3 - Task 3.5: Validation Script
Validate migrated data to ensure data integrity

This script will:
1. Compare JSON files count with database records count
2. Verify message counts match
3. Check for data integrity issues
4. Generate validation report
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValidationScript:
    """Validate migrated data"""
    
    def __init__(self, source_path: str, verify_database: bool = False):
        """
        Initialize validation script
        
        Args:
            source_path: Path to JSON conversation files
            verify_database: If True, connect to database and verify data
        """
        self.source_path = Path(source_path)
        self.verify_database = verify_database
        
        self.results = {
            'json_files': 0,
            'json_conversations': 0,
            'json_messages': 0,
            'json_users': set(),
            'json_memories': 0,
            'db_conversations': 0,
            'db_messages': 0,
            'db_users': 0,
            'db_memories': 0,
            'issues': [],
            'checks_passed': 0,
            'checks_failed': 0
        }
    
    def count_json_data(self) -> Dict:
        """Count data in JSON files"""
        logger.info("Counting data in JSON files...")
        
        json_files = list(self.source_path.glob("*.json"))
        json_files = [f for f in json_files if not f.name.endswith('_index.json')]
        
        self.results['json_files'] = len(json_files)
        
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.results['json_conversations'] += 1
                
                messages = data.get('messages', [])
                self.results['json_messages'] += len(messages)
                
                # Count users
                user_id = data.get('metadata', {}).get('user_id', 'default_user')
                self.results['json_users'].add(user_id)
                
                # Count memories
                memories = data.get('metadata', {}).get('memories', [])
                self.results['json_memories'] += len(memories)
                
            except Exception as e:
                error = f"Error reading {file_path.name}: {e}"
                self.results['issues'].append(error)
                logger.error(error)
        
        logger.info(f"  JSON Files: {self.results['json_files']}")
        logger.info(f"  Conversations: {self.results['json_conversations']}")
        logger.info(f"  Messages: {self.results['json_messages']}")
        logger.info(f"  Users: {len(self.results['json_users'])}")
        logger.info(f"  Memories: {self.results['json_memories']}")
        
        return self.results
    
    def count_database_data(self) -> Dict:
        """Count data in database"""
        if not self.verify_database:
            logger.info("Database verification skipped (use --verify to enable)")
            return self.results
        
        logger.info("Counting data in database...")
        
        # TODO: Implement database connection and counting
        # This will be implemented when we have the database models ready
        
        # For now, just log that this feature is pending
        logger.warning("Database verification not yet implemented")
        logger.info("This will be available after Phase 1 (Database Models) is complete")
        
        return self.results
    
    def run_checks(self) -> Dict:
        """Run validation checks"""
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING VALIDATION CHECKS")
        logger.info("=" * 80)
        
        checks = []
        
        # Check 1: JSON files exist
        check_name = "JSON files exist"
        if self.results['json_files'] > 0:
            checks.append((check_name, True, f"Found {self.results['json_files']} files"))
            self.results['checks_passed'] += 1
        else:
            checks.append((check_name, False, "No JSON files found"))
            self.results['checks_failed'] += 1
        
        # Check 2: All files parsed successfully
        check_name = "All files parsed successfully"
        if len(self.results['issues']) == 0:
            checks.append((check_name, True, "All files valid"))
            self.results['checks_passed'] += 1
        else:
            checks.append((check_name, False, f"{len(self.results['issues'])} files had errors"))
            self.results['checks_failed'] += 1
        
        # Check 3: Conversations have messages
        check_name = "Conversations have messages"
        if self.results['json_messages'] > 0:
            avg_messages = self.results['json_messages'] / self.results['json_conversations']
            checks.append((check_name, True, f"Average {avg_messages:.2f} messages per conversation"))
            self.results['checks_passed'] += 1
        else:
            checks.append((check_name, False, "No messages found"))
            self.results['checks_failed'] += 1
        
        # Check 4: Database comparison (if enabled)
        if self.verify_database:
            check_name = "Database record count matches JSON"
            json_count = self.results['json_conversations']
            db_count = self.results['db_conversations']
            
            if json_count == db_count:
                checks.append((check_name, True, f"Both have {json_count} conversations"))
                self.results['checks_passed'] += 1
            else:
                checks.append((check_name, False, f"JSON: {json_count}, DB: {db_count}"))
                self.results['checks_failed'] += 1
            
            # Check message counts
            check_name = "Database message count matches JSON"
            json_msgs = self.results['json_messages']
            db_msgs = self.results['db_messages']
            
            if json_msgs == db_msgs:
                checks.append((check_name, True, f"Both have {json_msgs} messages"))
                self.results['checks_passed'] += 1
            else:
                checks.append((check_name, False, f"JSON: {json_msgs}, DB: {db_msgs}"))
                self.results['checks_failed'] += 1
        
        # Print check results
        for check_name, passed, message in checks:
            status = "PASS" if passed else "FAIL"
            icon = "✓" if passed else "✗"
            logger.info(f"  [{status}] {check_name}: {message}")
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate validation report"""
        report = []
        report.append("=" * 80)
        report.append("VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 80)
        report.append(f"JSON Files:          {self.results['json_files']}")
        report.append(f"JSON Conversations:  {self.results['json_conversations']}")
        report.append(f"JSON Messages:       {self.results['json_messages']}")
        report.append(f"JSON Users:          {len(self.results['json_users'])}")
        report.append(f"JSON Memories:       {self.results['json_memories']}")
        report.append("")
        
        if self.verify_database:
            report.append("DATABASE DATA")
            report.append("-" * 80)
            report.append(f"DB Conversations:    {self.results['db_conversations']}")
            report.append(f"DB Messages:         {self.results['db_messages']}")
            report.append(f"DB Users:            {self.results['db_users']}")
            report.append(f"DB Memories:         {self.results['db_memories']}")
            report.append("")
        
        # Check results
        report.append("VALIDATION CHECKS")
        report.append("-" * 80)
        report.append(f"Checks Passed:       {self.results['checks_passed']}")
        report.append(f"Checks Failed:       {self.results['checks_failed']}")
        
        total_checks = self.results['checks_passed'] + self.results['checks_failed']
        if total_checks > 0:
            success_rate = (self.results['checks_passed'] / total_checks) * 100
            report.append(f"Success Rate:        {success_rate:.2f}%")
        report.append("")
        
        # Issues
        if self.results['issues']:
            report.append("ISSUES FOUND")
            report.append("-" * 80)
            for issue in self.results['issues'][:20]:
                report.append(f"  • {issue}")
            if len(self.results['issues']) > 20:
                report.append(f"  ... and {len(self.results['issues']) - 20} more issues")
            report.append("")
        
        # Final status
        if self.results['checks_failed'] == 0:
            report.append("STATUS: VALIDATION PASSED")
            report.append("-" * 80)
            report.append("All validation checks passed successfully!")
            report.append("Data is ready for migration.")
        else:
            report.append("STATUS: VALIDATION FAILED")
            report.append("-" * 80)
            report.append(f"{self.results['checks_failed']} validation checks failed.")
            report.append("Please review the issues above before proceeding with migration.")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_report(self, output_path: str = None):
        """Save report to file"""
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Path(__file__).parent / f"validation_report_{timestamp}.txt"
        
        report = self.generate_report()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"\nReport saved to: {output_path}")
        
        return output_path


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Validate conversation data before/after migration'
    )
    parser.add_argument(
        '--source',
        type=str,
        default=None,
        help='Path to conversation JSON files'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify data in database (requires database connection)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Alias for validation without database verification'
    )
    
    args = parser.parse_args()
    
    # Determine source path
    source_path = args.source
    if not source_path:
        source_path = Path(__file__).parent.parent.parent / "ChatBot" / "data" / "conversations"
    
    source_path = Path(source_path)
    
    if not source_path.exists():
        logger.error(f"Source path does not exist: {source_path}")
        return 1
    
    # Run validation
    validator = ValidationScript(
        source_path=source_path,
        verify_database=args.verify
    )
    
    # Count JSON data
    validator.count_json_data()
    
    # Count database data (if enabled)
    if args.verify:
        validator.count_database_data()
    
    # Run validation checks
    validator.run_checks()
    
    # Generate report
    report = validator.generate_report()
    print("\n" + report)
    
    # Save report
    validator.save_report()
    
    # Return exit code
    if validator.results['checks_failed'] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
