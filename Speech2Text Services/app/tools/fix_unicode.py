# -*- coding: utf-8 -*-
"""
Unicode Fix Script
Replaces all emoji Unicode characters with ASCII equivalents for Windows compatibility
"""

import os
import re
import glob

# Emoji mapping - replace Unicode emojis with ASCII equivalents
EMOJI_REPLACEMENTS = {
    # Audio/Music related
    '[MIC]': '[MIC]',
    '[MUSIC]': '[MUSIC]',
    '[NOTES]': '[NOTES]',
    
    # Files/Folders
    '[FOLDER]': '[FOLDER]',
    '[FILE]': '[FILE]',
    '[CHART]': '[CHART]',
    '[SAVE]': '[SAVE]',
    '[TRASH]': '[TRASH]',
    
    # Actions/Status
    '[LAUNCH]': '[LAUNCH]',
    '[FAST]': '[FAST]',
    '[AI]': '[AI]',
    '[STAR]': '[STAR]',
    '[OK]': '[OK]',
    '[ERROR]': '[ERROR]',
    '[TOOL]': '[TOOL]',
    '[SUCCESS]': '[SUCCESS]',
    '[BEST]': '[BEST]',
    
    # UI/Web
    '[UI]': '[UI]',
    '[MOBILE]': '[MOBILE]',
    '[WEB]': '[WEB]',
    '[STAR]': '[STAR]',
    '[TARGET]': '[TARGET]',
    
    # Navigation/Direction  
    '->': '->',
    '<-': '<-',
    '^': '^',
    'v': 'v',
    
    # Common symbols that might cause issues
    '[IDEA]': '[IDEA]',
    '[HOT]': '[HOT]',
    '[HEART]': '[HEART]',
    '[THUMBS_UP]': '[THUMBS_UP]',
    '[THUMBS_DOWN]': '[THUMBS_DOWN]',
    '[PARTY]': '[PARTY]',
    '[SEARCH]': '[SEARCH]',
    '[GROWTH]': '[GROWTH]',
    '[DOWN]': '[DOWN]',
    '[LOCK]': '[LOCK]',
    '[UNLOCK]': '[UNLOCK]',
    
    # Unicode escape sequences that commonly cause issues
    '[FOLDER]': '[FOLDER]',  # [FOLDER]
    '[MIC]': '[MIC]',     # [MIC]  
    '[LAUNCH]': '[LAUNCH]',  # [LAUNCH]
    '[FAST]': '[FAST]',        # [FAST]
    '[AI]': '[AI]',      # [AI]
    '[STAR]': '[STAR]',    # [STAR]
}

def fix_unicode_in_file(file_path):
    """Fix Unicode encoding issues in a single file"""
    try:
        # Read file with UTF-8 encoding
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Track if any changes were made
        original_content = content
        
        # Replace emoji characters
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            content = content.replace(emoji, replacement)
        
        # Also handle Unicode escape sequences
        content = re.sub(r'\\U[0-9a-fA-F]{8}', lambda m: EMOJI_REPLACEMENTS.get(m.group(0), '[EMOJI]'), content)
        content = re.sub(r'\\u[0-9a-fA-F]{4}', lambda m: EMOJI_REPLACEMENTS.get(m.group(0), '[EMOJI]'), content)
        
        # If changes were made, write back
        if content != original_content:
            # Add UTF-8 encoding declaration at the top if it's a Python file
            if file_path.endswith('.py') and not content.startswith('# -*- coding: utf-8 -*-'):
                content = '# -*- coding: utf-8 -*-\n' + content
            
            # Write back with UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"[FIXED] {file_path}")
            return True
        else:
            print(f"[SKIP]  {file_path} - No emojis found")
            return False
            
    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
        return False

def fix_all_python_files():
    """Fix all Python files in the project"""
    
    # Find all Python files
    python_files = []
    
    # Common locations for Python files
    search_patterns = [
        '*.py',
        'src/*.py',
        'core/*.py', 
        'api/*.py',
        'tools/*.py',
        'scripts/*.py',
        '**/*.py'  # Recursive
    ]
    
    for pattern in search_patterns:
        files = glob.glob(pattern, recursive=True)
        python_files.extend(files)
    
    # Remove duplicates
    python_files = list(set(python_files))
    
    print(f"Found {len(python_files)} Python files to check...")
    print("=" * 50)
    
    fixed_count = 0
    
    for file_path in python_files:
        if os.path.isfile(file_path):
            if fix_unicode_in_file(file_path):
                fixed_count += 1
    
    print("=" * 50)
    print(f"Fixed {fixed_count} files")
    
    return fixed_count

def fix_batch_files():
    """Fix batch files that might have Unicode issues"""
    
    batch_files = glob.glob('*.bat') + glob.glob('**/*.bat', recursive=True)
    
    for file_path in batch_files:
        if os.path.isfile(file_path):
            try:
                # Read as UTF-8
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                original_content = content
                
                # Replace emojis in batch files
                for emoji, replacement in EMOJI_REPLACEMENTS.items():
                    content = content.replace(emoji, replacement)
                
                if content != original_content:
                    # Write back as UTF-8 with BOM for Windows batch files
                    with open(file_path, 'w', encoding='utf-8-sig') as f:
                        f.write(content)
                    
                    print(f"[FIXED] {file_path}")
                    
            except Exception as e:
                print(f"[ERROR] {file_path}: {e}")

if __name__ == "__main__":
    print("[MIC] Unicode Fix Script")
    print("Fixing emoji/Unicode encoding issues...")
    print("=" * 50)
    
    # Fix Python files
    python_fixed = fix_all_python_files()
    
    # Fix batch files  
    print("\nFixing batch files...")
    fix_batch_files()
    
    print("\n[SUCCESS] Unicode fix complete!")
    print(f"Python files fixed: {python_fixed}")
    print("\nAll files should now run without Unicode errors on Windows.")