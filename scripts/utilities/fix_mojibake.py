# -*- coding: utf-8 -*-
"""
Script to fix UTF-8 encoding issues (mojibake) in Python files
Uses hex escapes to avoid encoding issues in the script itself
"""

import os
import re
from pathlib import Path

# Mapping using hex representations to avoid script encoding issues
# Format: (broken_hex, fixed_hex)
EMOJI_FIXES = [
    # Check mark emoji
    (b'\xc3\xa2\xc5\x93\xc2\x85', b'\xe2\x9c\x85'),
    # Warning emoji  
    (b'\xc3\xa2\xc5\xa1\x20\xc3\xaf\xc2\xb8\xc2\x8f', b'\xe2\x9a\xa0\xef\xb8\x8f'),
    # X mark emoji
    (b'\xc3\xa2\xc5\x92', b'\xe2\x9d\x8c'),
    # Star emoji
    (b'\xc3\xa2\xc2\xad', b'\xe2\xad\x90'),
]

# Pattern-based replacements for mojibake text
TEXT_FIXES = [
    # Common patterns - using raw strings
    (r'\xc3\xa2\xc5\x93\xc2\x85', '\u2705'),  # Check mark
    (r'\xc3\xa2\xc5\xa1\x20\xc3\xaf\xc2\xb8\xc2\x8f', '\u26a0\ufe0f'),  # Warning
    (r'\xc3\xa2\xc5\x92', '\u274c'),  # X mark
]


def decode_mojibake(text):
    """
    Attempt to fix mojibake by re-encoding
    Mojibake happens when UTF-8 bytes are incorrectly decoded as Latin-1/CP1252
    """
    try:
        # Try to reverse the double-encoding
        # Original UTF-8 -> wrongly decoded as Latin1 -> encoded back to UTF-8
        fixed = text.encode('latin-1').decode('utf-8')
        return fixed, True
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text, False


def fix_file_content(content):
    """Fix mojibake in file content"""
    # Try line by line to preserve as much as possible
    lines = content.split('\n')
    fixed_lines = []
    changes_made = False
    
    for line in lines:
        fixed_line, changed = decode_mojibake(line)
        if changed:
            changes_made = True
        fixed_lines.append(fixed_line)
    
    return '\n'.join(fixed_lines), changes_made


def has_mojibake_patterns(content):
    """Check if content has mojibake patterns"""
    # Common mojibake byte sequences when UTF-8 is read as Latin-1
    patterns = [
        '\xc3\xa2',  # Part of 'a' with diacritic
        '\xc4\x83',  # a breve
        '\xc4\x91',  # d stroke
        '\xc3\xa0',  # a grave
        '\xc3\xa1',  # a acute
        '\xc3\xa9',  # e acute
        '\xc3\xaa',  # e circumflex
        '\xc3\xb4',  # o circumflex
        '\xc3\xb9',  # u grave
        '\xc3\xba',  # u acute
        '\xc5\xa1',  # s caron
        '\xc5\x93',  # oe ligature - often part of broken emojis
    ]
    
    return any(p in content for p in patterns)


def scan_directory(directory, extensions=('.py',)):
    """Scan directory for files with encoding issues"""
    skip_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'env', '.idea', 'build', 'dist'}
    issues = []
    
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
        
        for file in files:
            if not any(file.endswith(ext) for ext in extensions):
                continue
            
            filepath = os.path.join(root, file)
            
            try:
                # Read as binary first to check for patterns
                with open(filepath, 'rb') as f:
                    raw_content = f.read()
                
                # Try to decode
                try:
                    content = raw_content.decode('utf-8')
                except UnicodeDecodeError:
                    content = raw_content.decode('latin-1')
                
                # Check for mojibake
                if has_mojibake_patterns(content):
                    rel_path = os.path.relpath(filepath, directory)
                    issues.append((filepath, rel_path))
                    
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    
    return issues


def fix_file(filepath):
    """Fix a single file"""
    try:
        # Read with replace errors to handle any encoding issues
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Fix the content
        fixed_content, changed = fix_file_content(content)
        
        if changed:
            # Write back
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        return False
        
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False


def main():
    import sys
    
    # Get project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent
    
    print("=" * 60)
    print("UTF-8 Mojibake Fixer")
    print("=" * 60)
    print(f"Scanning: {project_root}")
    print()
    
    # Find issues
    issues = scan_directory(project_root)
    
    if not issues:
        print("No encoding issues found!")
        return
    
    print(f"Found {len(issues)} files with potential mojibake:")
    for _, rel_path in issues:
        print(f"  - {rel_path}")
    
    print()
    
    # Check if --fix flag
    do_fix = len(sys.argv) > 1 and sys.argv[1] == '--fix'
    
    if not do_fix:
        print("Run with --fix to automatically fix these files.")
        return
    
    print("Fixing files...")
    print("-" * 60)
    
    fixed_count = 0
    for filepath, rel_path in issues:
        if fix_file(filepath):
            print(f"  [FIXED] {rel_path}")
            fixed_count += 1
        else:
            print(f"  [UNCHANGED] {rel_path}")
    
    print("-" * 60)
    print(f"Fixed {fixed_count}/{len(issues)} files")


if __name__ == "__main__":
    main()
