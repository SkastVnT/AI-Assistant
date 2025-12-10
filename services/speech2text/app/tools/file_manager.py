# -*- coding: utf-8 -*-
"""
File Management Utilities
Clean up old audio and result files
"""

import os
import time
from pathlib import Path
import shutil

def cleanup_old_files(hours=24):
    """Remove files older than specified hours"""
    cutoff_time = time.time() - (hours * 3600)
    
    folders = {
        'data/audio': 'Audio files',
        'data/results': 'Result files', 
        'logs': 'Log files'
    }
    
    cleaned = {}
    
    for folder_path, description in folders.items():
        folder = Path(folder_path)
        if not folder.exists():
            continue
            
        count = 0
        size = 0
        
        for file_path in folder.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                size += file_path.stat().st_size
                file_path.unlink()
                count += 1
        
        cleaned[description] = {
            'count': count,
            'size_mb': size / (1024 * 1024)
        }
    
    return cleaned

def get_folder_sizes():
    """Get size of each folder"""
    folders = ['data/audio', 'data/results', 'logs', 'data/models']
    sizes = {}
    
    for folder_path in folders:
        folder = Path(folder_path)
        if not folder.exists():
            sizes[folder_path] = 0
            continue
            
        total_size = 0
        for file_path in folder.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        sizes[folder_path] = total_size / (1024 * 1024)  # MB
    
    return sizes

def list_recent_files(folder, limit=10):
    """List recent files in folder"""
    folder = Path(folder)
    if not folder.exists():
        return []
    
    files = []
    for file_path in folder.iterdir():
        if file_path.is_file():
            files.append({
                'name': file_path.name,
                'size_mb': file_path.stat().st_size / (1024 * 1024),
                'modified': time.ctime(file_path.stat().st_mtime)
            })
    
    return sorted(files, key=lambda x: x['name'])[-limit:]

def main():
    print("[?][?] File Management Utilities")
    print("=" * 50)
    
    print("\n[CHART] Folder Sizes:")
    sizes = get_folder_sizes()
    for folder, size_mb in sizes.items():
        print(f"  {folder}: {size_mb:.1f} MB")
    
    print(f"\n[FILE] Recent Audio Files:")
    audio_files = list_recent_files('data/audio', 5)
    if audio_files:
        for file_info in audio_files:
            print(f"  {file_info['name']} ({file_info['size_mb']:.1f} MB) - {file_info['modified']}")
    else:
        print("  No audio files found")
    
    print(f"\n[FILE] Recent Result Files:")
    result_files = list_recent_files('data/results', 5)
    if result_files:
        for file_info in result_files:
            print(f"  {file_info['name']} ({file_info['size_mb']:.1f} MB) - {file_info['modified']}")
    else:
        print("  No result files found")
    
    print("\n[TRASH] Cleanup Options:")
    print("1. Clean files older than 1 hour")
    print("2. Clean files older than 1 day")
    print("3. Clean files older than 1 week")
    print("4. Show files only")
    
    choice = input("\nEnter choice (1-4): ")
    
    if choice == '1':
        cleaned = cleanup_old_files(1)
    elif choice == '2':
        cleaned = cleanup_old_files(24)
    elif choice == '3':
        cleaned = cleanup_old_files(24 * 7)
    elif choice == '4':
        print("\nFile listing completed.")
        return
    else:
        print("Invalid choice")
        return
    
    print(f"\n[OK] Cleanup completed:")
    total_size = 0
    total_count = 0
    for desc, info in cleaned.items():
        print(f"  {desc}: {info['count']} files, {info['size_mb']:.1f} MB")
        total_size += info['size_mb']
        total_count += info['count']
    
    print(f"\nTotal: {total_count} files, {total_size:.1f} MB freed")

if __name__ == "__main__":
    main()