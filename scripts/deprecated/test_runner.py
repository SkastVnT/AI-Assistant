"""
Quick Test Runner Script
Run specific test categories or all tests
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and print results"""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print(f"\n✅ {description} - PASSED")
    else:
        print(f"\n❌ {description} - FAILED")
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description='AI-Assistant Test Runner')
    parser.add_argument(
        'category',
        nargs='?',
        default='all',
        choices=['all', 'unit', 'integration', 'hub', 'chatbot', 'text2sql', 'smoke', 'fast'],
        help='Test category to run'
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-c', '--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('-f', '--failfast', action='store_true', help='Stop on first failure')
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd_parts = ['pytest']
    
    # Verbosity
    if args.verbose:
        cmd_parts.append('-vv')
    else:
        cmd_parts.append('-v')
    
    # Coverage
    if args.coverage:
        cmd_parts.extend([
            '--cov=src',
            '--cov=ChatBot/src',
            '--cov-report=html',
            '--cov-report=term-missing',
            '--cov-branch'
        ])
    
    # Fail fast
    if args.failfast:
        cmd_parts.append('-x')
    
    # Test selection based on category
    if args.category == 'unit':
        cmd_parts.extend(['-m', 'unit', 'tests/unit/'])
        description = 'Running Unit Tests'
    elif args.category == 'integration':
        cmd_parts.extend(['-m', 'integration', 'tests/integration/'])
        description = 'Running Integration Tests'
    elif args.category == 'hub':
        cmd_parts.extend(['-m', 'hub', 'tests/unit/test_hub.py'])
        description = 'Running Hub Gateway Tests'
    elif args.category == 'chatbot':
        cmd_parts.extend(['-m', 'chatbot', 'tests/unit/test_chatbot.py'])
        description = 'Running ChatBot Tests'
    elif args.category == 'text2sql':
        cmd_parts.extend(['-m', 'text2sql', 'tests/unit/test_text2sql.py'])
        description = 'Running Text2SQL Tests'
    elif args.category == 'smoke':
        cmd_parts.extend(['-m', 'smoke'])
        description = 'Running Smoke Tests'
    elif args.category == 'fast':
        cmd_parts.extend(['-m', 'unit and not slow'])
        description = 'Running Fast Unit Tests'
    else:  # all
        cmd_parts.append('tests/')
        description = 'Running All Tests'
    
    # Build command
    cmd = ' '.join(cmd_parts)
    
    # Run tests
    print("\n" + "="*60)
    print("🚀 AI-Assistant Test Suite")
    print("="*60)
    print(f"📦 Category: {args.category}")
    print(f"🔧 Command: {cmd}")
    
    exit_code = run_command(cmd, description)
    
    # Summary
    print("\n" + "="*60)
    if exit_code == 0:
        print("✅ Test Suite PASSED")
    else:
        print("❌ Test Suite FAILED")
    print("="*60 + "\n")
    
    # Open coverage report if generated
    if args.coverage and exit_code == 0:
        coverage_html = Path('htmlcov/index.html')
        if coverage_html.exists():
            print(f"📊 Coverage report: {coverage_html}")
            print("   Open in browser to view detailed coverage\n")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
