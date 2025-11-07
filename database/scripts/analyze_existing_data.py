"""
Phase 3 - Task 3.1: Analyze Existing Data
Analyze existing JSON conversation files to understand the data structure and identify issues
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataAnalyzer:
    """Analyze existing conversation data"""
    
    def __init__(self, storage_path: str):
        """
        Initialize analyzer
        
        Args:
            storage_path: Path to conversation storage directory
        """
        self.storage_path = Path(storage_path)
        self.stats = {
            'total_files': 0,
            'total_conversations': 0,
            'total_messages': 0,
            'total_size_bytes': 0,
            'conversations_by_date': defaultdict(int),
            'messages_per_conversation': [],
            'file_sizes': [],
            'issues': [],
            'users': set(),
            'tags': set(),
            'models_used': set(),
            'has_images': 0,
            'has_files': 0,
            'has_memories': 0,
            'branches': 0
        }
    
    def analyze_file(self, file_path: Path) -> dict:
        """
        Analyze single conversation file
        
        Args:
            file_path: Path to conversation JSON file
        
        Returns:
            dict: File analysis results
        """
        try:
            # Get file size
            file_size = file_path.stat().st_size
            self.stats['file_sizes'].append(file_size)
            self.stats['total_size_bytes'] += file_size
            
            # Load JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Basic info
            conv_id = data.get('id', file_path.stem)
            title = data.get('title', 'Untitled')
            created_at = data.get('created_at')
            messages = data.get('messages', [])
            
            # Count messages
            message_count = len(messages)
            self.stats['messages_per_conversation'].append(message_count)
            self.stats['total_messages'] += message_count
            
            # Extract date
            if created_at:
                try:
                    date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_key = date.strftime('%Y-%m')
                    self.stats['conversations_by_date'][date_key] += 1
                except:
                    pass
            
            # Extract users
            if 'user_id' in data:
                self.stats['users'].add(data['user_id'])
            
            # Extract tags
            if 'tags' in data:
                self.stats['tags'].update(data['tags'])
            
            # Check for branches
            if data.get('branches'):
                self.stats['branches'] += len(data['branches'])
            
            # Analyze messages
            for msg in messages:
                # Check for models used
                if 'model' in msg:
                    self.stats['models_used'].add(msg['model'])
                
                # Check for images
                if msg.get('images') or msg.get('image_data'):
                    self.stats['has_images'] += 1
                
                # Check for files
                if msg.get('files') or msg.get('file_data'):
                    self.stats['has_files'] += 1
            
            # Check for memories
            if data.get('memories') or data.get('metadata', {}).get('memories'):
                self.stats['has_memories'] += 1
            
            return {
                'id': conv_id,
                'title': title,
                'message_count': message_count,
                'size_bytes': file_size,
                'created_at': created_at,
                'has_issues': False
            }
            
        except json.JSONDecodeError as e:
            error = f"Invalid JSON in {file_path.name}: {e}"
            self.stats['issues'].append(error)
            logger.error(error)
            return None
        except Exception as e:
            error = f"Error analyzing {file_path.name}: {e}"
            self.stats['issues'].append(error)
            logger.error(error)
            return None
    
    def analyze_all(self) -> dict:
        """
        Analyze all conversation files
        
        Returns:
            dict: Complete analysis results
        """
        logger.info(f"🔍 Analyzing conversations in: {self.storage_path}")
        
        if not self.storage_path.exists():
            logger.error(f"❌ Storage path does not exist: {self.storage_path}")
            return self.stats
        
        # Find all JSON files
        json_files = list(self.storage_path.glob("*.json"))
        
        # Exclude index file
        json_files = [f for f in json_files if not f.name.endswith('_index.json')]
        
        self.stats['total_files'] = len(json_files)
        logger.info(f"📁 Found {len(json_files)} conversation files")
        
        # Analyze each file
        successful = 0
        for i, file_path in enumerate(json_files, 1):
            if i % 10 == 0:
                logger.info(f"  Progress: {i}/{len(json_files)}")
            
            result = self.analyze_file(file_path)
            if result:
                successful += 1
        
        self.stats['total_conversations'] = successful
        
        return self.stats
    
    def generate_report(self) -> str:
        """
        Generate analysis report
        
        Returns:
            str: Formatted report
        """
        report = []
        report.append("=" * 80)
        report.append("DATA ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        report.append("📊 SUMMARY")
        report.append("-" * 80)
        report.append(f"Total Files:                {self.stats['total_files']}")
        report.append(f"Successfully Analyzed:      {self.stats['total_conversations']}")
        report.append(f"Failed/Invalid:             {self.stats['total_files'] - self.stats['total_conversations']}")
        report.append(f"Total Messages:             {self.stats['total_messages']:,}")
        report.append(f"Total Size:                 {self.stats['total_size_bytes'] / (1024*1024):.2f} MB")
        report.append("")
        
        # Average stats
        if self.stats['total_conversations'] > 0:
            avg_messages = sum(self.stats['messages_per_conversation']) / len(self.stats['messages_per_conversation'])
            avg_size = sum(self.stats['file_sizes']) / len(self.stats['file_sizes'])
            
            report.append("📈 AVERAGES")
            report.append("-" * 80)
            report.append(f"Avg Messages/Conversation:  {avg_messages:.2f}")
            report.append(f"Avg File Size:              {avg_size / 1024:.2f} KB")
            report.append("")
        
        # Distribution
        report.append("📅 CONVERSATIONS BY MONTH")
        report.append("-" * 80)
        if self.stats['conversations_by_date']:
            for month in sorted(self.stats['conversations_by_date'].keys()):
                count = self.stats['conversations_by_date'][month]
                report.append(f"{month}: {count} conversations")
        else:
            report.append("No date information available")
        report.append("")
        
        # Features
        report.append("🎯 FEATURE USAGE")
        report.append("-" * 80)
        report.append(f"Unique Users:               {len(self.stats['users'])}")
        report.append(f"Unique Tags:                {len(self.stats['tags'])}")
        report.append(f"Models Used:                {', '.join(self.stats['models_used']) if self.stats['models_used'] else 'N/A'}")
        report.append(f"Conversations with Images:  {self.stats['has_images']}")
        report.append(f"Conversations with Files:   {self.stats['has_files']}")
        report.append(f"Conversations with Memories: {self.stats['has_memories']}")
        report.append(f"Total Branches:             {self.stats['branches']}")
        report.append("")
        
        # Issues
        if self.stats['issues']:
            report.append("⚠️ ISSUES FOUND")
            report.append("-" * 80)
            for issue in self.stats['issues'][:10]:  # Show first 10
                report.append(f"  • {issue}")
            if len(self.stats['issues']) > 10:
                report.append(f"  ... and {len(self.stats['issues']) - 10} more issues")
        else:
            report.append("✅ NO ISSUES FOUND")
        report.append("")
        
        # Recommendations
        report.append("💡 MIGRATION RECOMMENDATIONS")
        report.append("-" * 80)
        
        total_conversations = self.stats['total_conversations']
        if total_conversations == 0:
            report.append("❌ No valid conversations found. Cannot proceed with migration.")
        elif total_conversations < 100:
            report.append("✅ Small dataset - Migration should be quick (~5 minutes)")
        elif total_conversations < 1000:
            report.append("⚠️ Medium dataset - Migration will take ~30 minutes")
        else:
            report.append("⚠️ Large dataset - Migration will take 1+ hours")
        
        report.append("")
        report.append(f"Estimated database size:    {self.stats['total_size_bytes'] * 1.2 / (1024*1024):.2f} MB")
        report.append("")
        
        # Next steps
        report.append("📝 NEXT STEPS")
        report.append("-" * 80)
        report.append("1. Review this report for any issues")
        report.append("2. Backup existing data: tar -czf backup.tar.gz ChatBot/data/")
        report.append("3. Run dry-run migration: python database/scripts/migrate_conversations.py --dry-run")
        report.append("4. If dry-run successful, run actual migration")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_report(self, output_path: str = None):
        """Save report to file"""
        if output_path is None:
            output_path = Path(__file__).parent / "data_analysis_report.txt"
        
        report = self.generate_report()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"✅ Report saved to: {output_path}")
        
        return output_path


def main():
    """Main function"""
    # Determine storage path
    # Try ChatBot/data/conversations first
    chatbot_path = Path(__file__).parent.parent.parent / "ChatBot" / "data" / "conversations"
    
    if not chatbot_path.exists():
        logger.error(f"❌ Conversation storage not found at: {chatbot_path}")
        logger.info("Please specify the correct path to your conversation storage")
        return
    
    # Run analysis
    analyzer = DataAnalyzer(chatbot_path)
    stats = analyzer.analyze_all()
    
    # Generate and print report
    report = analyzer.generate_report()
    print(report)
    
    # Save report
    report_path = analyzer.save_report()
    print(f"\n✅ Analysis complete! Report saved to: {report_path}")


if __name__ == "__main__":
    main()
