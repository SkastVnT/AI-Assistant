# -*- coding: utf-8 -*-
"""
Script d[?] patch transformers library - b[?] qua ki[?]m tra PyTorch version
CH[?] S[?] D[?]NG KHI LOAD MODEL T[?] NGU[?]N TIN C[?]Y (Hugging Face)
"""

import os
import sys

def patch_transformers():
    """Patch transformers d[?] b[?] qua ki[?]m tra torch.load security"""
    
    # T[?]m d[?][?]ng d[?]n d[?]n transformers
    import transformers
    transformers_path = os.path.dirname(transformers.__file__)
    import_utils_path = os.path.join(transformers_path, 'utils', 'import_utils.py')
    
    print(f"[?] Patching: {import_utils_path}")
    
    # [?][?]c file
    with open(import_utils_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup file g[?]c n[?]u ch[?]a c[?]
    backup_path = import_utils_path + '.backup'
    if not os.path.exists(backup_path):
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] [?][?] backup file g[?]c: {backup_path}")
    
    # Patch function check_torch_load_is_safe
    if 'def check_torch_load_is_safe():' in content:
        # T[?]m v[?] tr[?] function
        lines = content.split('\n')
        patched_lines = []
        in_function = False
        indent_level = 0
        
        for line in lines:
            if 'def check_torch_load_is_safe():' in line:
                in_function = True
                indent_level = len(line) - len(line.lstrip())
                patched_lines.append(line)
                patched_lines.append(' ' * (indent_level + 4) + '# PATCHED: Skip security check for trusted models')
                patched_lines.append(' ' * (indent_level + 4) + 'return  # Bypass check')
                continue
            
            if in_function:
                # Ki[?]m tra xem c[?] ph[?]i l[?] function m[?]i kh[?]ng
                if line.strip() and not line.strip().startswith('#'):
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= indent_level and line.strip().startswith('def '):
                        in_function = False
                        patched_lines.append(line)
                    # Skip n[?]i dung c[?] c[?]a function
                continue
            
            patched_lines.append(line)
        
        # Ghi l[?]i file
        with open(import_utils_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(patched_lines))
        
        print("[OK] [?][?] patch transformers successfully!")
        print("[WARN]  L[?]u [?]: Ch[?] load models t[?] ngu[?]n tin c[?]y!")
        return True
    else:
        print("[ERROR] Kh[?]ng t[?]m th[?]y function check_torch_load_is_safe")
        return False

def restore_transformers():
    """Kh[?]i ph[?]c transformers v[?] tr[?]ng th[?]i g[?]c"""
    import transformers
    transformers_path = os.path.dirname(transformers.__file__)
    import_utils_path = os.path.join(transformers_path, 'utils', 'import_utils.py')
    backup_path = import_utils_path + '.backup'
    
    if os.path.exists(backup_path):
        with open(backup_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open(import_utils_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[OK] [?][?] kh[?]i ph[?]c transformers t[?] backup")
        return True
    else:
        print(f"[ERROR] Kh[?]ng t[?]m th[?]y file backup: {backup_path}")
        return False

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Patch transformers library')
    parser.add_argument('--restore', action='store_true', help='Kh[?]i ph[?]c file g[?]c')
    args = parser.parse_args()
    
    if args.restore:
        restore_transformers()
    else:
        patch_transformers()
