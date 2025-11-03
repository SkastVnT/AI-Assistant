# -*- coding: utf-8 -*-
"""
Enhanced Unicode Fix Script
Fix all remaining Unicode issues comprehensively  
"""

import os
import re
import glob

# Extended emoji mapping
EXTENDED_REPLACEMENTS = {
    # Basic emojis already covered
    '[MIC]': '[MIC]', '[FOLDER]': '[FOLDER]', '[LAUNCH]': '[LAUNCH]', '[FAST]': '[FAST]',
    '[AI]': '[AI]', '[STAR]': '[STAR]', '[OK]': '[OK]', '[ERROR]': '[ERROR]',
    '[TOOL]': '[TOOL]', '[SUCCESS]': '[SUCCESS]', '[BEST]': '[BEST]', '[UI]': '[UI]',
    '[MOBILE]': '[MOBILE]', '[WEB]': '[WEB]', '[STAR]': '[STAR]', '[TARGET]': '[TARGET]',
    '[SAVE]': '[SAVE]', '[TRASH]': '[TRASH]', '[CHART]': '[CHART]', '[FILE]': '[FILE]',
    
    # Additional special characters that cause issues
    '[OK]': '[OK]', '[OK]': '[OK]', '[WARN]': '[WARN]', '[WARN]': '[WARN]',
    '[AI]': '[AI]', '[MIC]': '[MIC]', '[FOLDER]': '[FOLDER]', '[IDEA]': '[IDEA]',
    '[HOT]': '[HOT]', '[HEART]': '[HEART]', '[THUMBS_UP]': '[THUMBS_UP]', '[THUMBS_DOWN]': '[THUMBS_DOWN]',
    '[PARTY]': '[PARTY]', '[SEARCH]': '[SEARCH]', '[GROWTH]': '[GROWTH]', '[DOWN]': '[DOWN]',
    '[LOCK]': '[LOCK]', '[UNLOCK]': '[UNLOCK]', '[UP]': '[UP]', '[DOWN]': '[DOWN]',
    '[RIGHT]': '[RIGHT]', '[LEFT]': '[LEFT]', '[UP_RIGHT]': '[UP_RIGHT]', '[DOWN_RIGHT]': '[DOWN_RIGHT]',
    
    # Vietnamese-specific characters that might cause issues
    'D': 'D', 'd': 'd',
    
    # Unicode escapes
    '[FOLDER]': '[FOLDER]', '[MIC]': '[MIC]', '[LAUNCH]': '[LAUNCH]',
    '[FAST]': '[FAST]', '[AI]': '[AI]', '[STAR]': '[STAR]',
    '[AI]': '[AI]', '[OK]': '[OK]', '[WARN]': '[WARN]',
    '[FOLDER]': '[FOLDER]', '[CHART]': '[CHART]', '[FILE]': '[FILE]'
}

def fix_python_file(file_path):
    """Fix Unicode issues in a Python file."""
    
    # Skip critical library files that need Unicode box-drawing characters
    skip_files = [
        'dill/logger.py',
        'dill\\_dill.py',
        'rich/',  # Rich library uses Unicode for terminal formatting
        'tqdm/',  # Progress bars use Unicode
        'idna/core.py',  # Unicode domain name handling
        'yaml/reader.py',  # YAML Unicode processing
        'yaml\\reader.py',
        'librosa/core/notation.py',  # Superscript/subscript Unicode
        'librosa\\core\\notation.py',
        'pyparsing/unicode.py',  # Pyparsing language sets
        'pyparsing\\unicode.py',
        '_vendor/pyparsing/unicode.py',  # Vendor copies
        '\\_vendor\\pyparsing\\unicode.py',
    ]
    
    normalized_path = file_path.replace('\\', '/')
    if any(skip in normalized_path for skip in skip_files):
        print(f"[SKIP] {file_path} - Critical library file")
        return False
    
    try:
        # Try reading with different encodings
        content = None
        for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                break
            except:
                continue
        
        if content is None:
            print(f"[ERROR] Could not read {file_path}")
            return False
        
        original_content = content
        
        # Fix BOM issues
        if content.startswith('[UNICODE]'):
            content = content[1:]
        
        # Replace all extended characters
        for char, replacement in EXTENDED_REPLACEMENTS.items():
            content = content.replace(char, replacement)
        
        # Handle Unicode escape sequences more aggressively
        content = re.sub(r'\\U[0-9a-fA-F]{8}', lambda m: EXTENDED_REPLACEMENTS.get(m.group(0), '[UNICODE]'), content)
        content = re.sub(r'\\u[0-9a-fA-F]{4}', lambda m: EXTENDED_REPLACEMENTS.get(m.group(0), '[UNICODE]'), content)
        
        # Remove problematic Unicode characters but KEEP Vietnamese characters
        # Keep: ASCII printable + Vietnamese characters (U+00C0-U+1EFF)
        # Remove: Emoji and other special Unicode that cause terminal issues
        vietnamese_chars = 'àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸ'
        # Don't replace Vietnamese characters - only replace problematic emoji/symbols
        # Comment out the aggressive replacement line:
        # content = re.sub(r'[^\x20-\x7E\r\n\t]', '[?]', content)
        
        # Fix specific Vietnamese comments to English
        vietnamese_to_english = {
            'CONFIGURATION': 'CONFIGURATION',
            'Create directories': 'Create directories',
            'No API key required': 'No API key required',
            'using Smart Rule-Based Fusion': 'using Smart Rule-Based Fusion',
            'Audio file not found': 'Audio file not found',
            'Clean text first': 'Clean text first',
            'Remove strange characters': 'Remove strange characters',
            'normalize punctuation': 'normalize punctuation',
            'Remove extra spaces': 'Remove extra spaces'
        }
        
        for vn, en in vietnamese_to_english.items():
            content = content.replace(vn, en)
        
        # Write back if changes were made
        if content != original_content:
            # Write with UTF-8 without BOM
            with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            
            print(f"[FIXED] {file_path}")
            return True
        else:
            print(f"[SKIP] {file_path} - No changes needed")
            return False
            
    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
        return False

def fix_all_files():
    """Fix all files in the project"""
    
    # Python files
    python_files = glob.glob('**/*.py', recursive=True)
    
    print(f"Fixing {len(python_files)} Python files...")
    fixed_count = 0
    
    for file_path in python_files:
        if os.path.isfile(file_path):
            if aggressive_unicode_fix(file_path):
                fixed_count += 1
    
    # Batch files
    batch_files = glob.glob('**/*.bat', recursive=True)
    
    print(f"\nFixing {len(batch_files)} batch files...")
    
    for file_path in batch_files:
        if os.path.isfile(file_path):
            try:
                # Read as UTF-8
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Remove BOM
                if content.startswith('[UNICODE]'):
                    content = content[1:]
                
                original_content = content
                
                # Replace emojis in batch files
                for emoji, replacement in EXTENDED_REPLACEMENTS.items():
                    content = content.replace(emoji, replacement)
                
                if content != original_content:
                    # Write back as plain ASCII
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"[FIXED] {file_path}")
                    fixed_count += 1
                    
            except Exception as e:
                print(f"[ERROR] {file_path}: {e}")
    
    return fixed_count

if __name__ == "__main__":
    print("[MIC] Enhanced Unicode Fix Script")
    print("Aggressively fixing ALL Unicode issues...")
    print("=" * 60)
    
    fixed_count = fix_all_files()
    
    print("\n" + "=" * 60)
    print(f"[SUCCESS] Enhanced Unicode fix complete!")
    print(f"Files fixed: {fixed_count}")
    print("\nAll files should now be fully compatible with Windows terminals.")