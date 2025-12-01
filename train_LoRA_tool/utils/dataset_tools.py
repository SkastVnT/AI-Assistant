"""
Dataset Processing Tools for LoRA Training
===========================================

Tổng hợp các tools hữu ích để xử lý dataset trước khi train:
- Resize images (giảm resolution tự động)
- Convert image formats (PNG → WebP, JPG, etc.)
- Deduplicate images (phát hiện ảnh trùng)
- Auto-organize by resolution
- Balance dataset (đảm bảo số lượng cân bằng)
- Validate dataset (check lỗi)

Created: 2024-12-01
Version: 1.0.0
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from PIL import Image
import hashlib
from collections import Counter, defaultdict
import json


class DatasetResizer:
    """Resize tất cả images trong dataset về resolution nhất định"""
    
    def __init__(self, dataset_path: str, on_progress: Optional[Callable] = None):
        self.dataset_path = Path(dataset_path)
        self.on_progress = on_progress or (lambda msg: print(msg))
        
    def resize_dataset(self, 
                      target_resolution: Tuple[int, int],
                      keep_aspect_ratio: bool = True,
                      quality: int = 95,
                      backup: bool = True) -> Dict:
        """
        Resize tất cả images
        
        Args:
            target_resolution: (width, height) - VD: (512, 512)
            keep_aspect_ratio: Giữ tỷ lệ khung hình (crop/pad nếu cần)
            quality: JPEG quality (1-100)
            backup: Backup ảnh gốc trước khi resize
            
        Returns:
            Dict với stats: processed, errors, size_saved
        """
        
        image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        images = [f for f in self.dataset_path.iterdir() 
                 if f.suffix.lower() in image_exts]
        
        if not images:
            raise ValueError(f"No images found in {self.dataset_path}")
        
        # Create backup folder
        if backup:
            backup_dir = self.dataset_path / '_backup_original'
            backup_dir.mkdir(exist_ok=True)
            self.on_progress(f"📦 Backup folder: {backup_dir}")
        
        stats = {
            'processed': 0,
            'errors': 0,
            'size_before': 0,
            'size_after': 0,
            'skipped': 0
        }
        
        target_w, target_h = target_resolution
        
        for idx, img_path in enumerate(images):
            try:
                # Progress
                progress = (idx + 1) / len(images) * 100
                self.on_progress(f"[{idx+1}/{len(images)}] Processing {img_path.name}... ({progress:.1f}%)")
                
                # Get original size
                orig_size = img_path.stat().st_size
                stats['size_before'] += orig_size
                
                # Open image
                with Image.open(img_path) as img:
                    orig_w, orig_h = img.size
                    
                    # Skip if already target resolution
                    if orig_w == target_w and orig_h == target_h:
                        stats['skipped'] += 1
                        stats['size_after'] += orig_size
                        continue
                    
                    # Backup original
                    if backup:
                        backup_path = backup_dir / img_path.name
                        if not backup_path.exists():
                            shutil.copy2(img_path, backup_path)
                    
                    # Resize
                    if keep_aspect_ratio:
                        # Resize and crop to fit
                        img_resized = self._resize_and_crop(img, target_w, target_h)
                    else:
                        # Simple resize (may distort)
                        img_resized = img.resize((target_w, target_h), Image.LANCZOS)
                    
                    # Save
                    save_kwargs = {}
                    if img_path.suffix.lower() in ['.jpg', '.jpeg']:
                        save_kwargs = {'quality': quality, 'optimize': True}
                    elif img_path.suffix.lower() == '.png':
                        save_kwargs = {'optimize': True}
                    
                    img_resized.save(img_path, **save_kwargs)
                
                # Get new size
                new_size = img_path.stat().st_size
                stats['size_after'] += new_size
                stats['processed'] += 1
                
            except Exception as e:
                self.on_progress(f"❌ Error processing {img_path.name}: {e}")
                stats['errors'] += 1
        
        # Calculate savings
        stats['size_saved'] = stats['size_before'] - stats['size_after']
        stats['size_saved_mb'] = stats['size_saved'] / (1024 * 1024)
        stats['compression_ratio'] = (1 - stats['size_after'] / stats['size_before']) * 100 if stats['size_before'] > 0 else 0
        
        self.on_progress(f"\n✅ Done! Processed: {stats['processed']}, Errors: {stats['errors']}, Skipped: {stats['skipped']}")
        self.on_progress(f"💾 Size saved: {stats['size_saved_mb']:.2f} MB ({stats['compression_ratio']:.1f}%)")
        
        return stats
    
    def _resize_and_crop(self, img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """Resize giữ aspect ratio, crop phần thừa"""
        orig_w, orig_h = img.size
        orig_ratio = orig_w / orig_h
        target_ratio = target_w / target_h
        
        if orig_ratio > target_ratio:
            # Image quá rộng → resize theo height, crop width
            new_h = target_h
            new_w = int(target_h * orig_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            # Crop center
            left = (new_w - target_w) // 2
            img = img.crop((left, 0, left + target_w, target_h))
        else:
            # Image quá cao → resize theo width, crop height
            new_w = target_w
            new_h = int(target_w / orig_ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            # Crop center
            top = (new_h - target_h) // 2
            img = img.crop((0, top, target_w, top + target_h))
        
        return img


class ImageFormatConverter:
    """Convert image formats (PNG → WebP, JPG, etc.)"""
    
    def __init__(self, dataset_path: str, on_progress: Optional[Callable] = None):
        self.dataset_path = Path(dataset_path)
        self.on_progress = on_progress or (lambda msg: print(msg))
    
    def convert_all(self, 
                   target_format: str = 'webp',
                   quality: int = 95,
                   delete_original: bool = False) -> Dict:
        """
        Convert tất cả images sang format khác
        
        Args:
            target_format: 'webp', 'jpg', 'png'
            quality: 1-100 (for lossy formats)
            delete_original: Xóa file gốc sau khi convert
            
        Returns:
            Stats dict
        """
        
        image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        images = [f for f in self.dataset_path.iterdir() 
                 if f.suffix.lower() in image_exts]
        
        stats = {
            'converted': 0,
            'errors': 0,
            'size_before': 0,
            'size_after': 0,
            'skipped': 0
        }
        
        target_ext = f'.{target_format.lower()}'
        
        for idx, img_path in enumerate(images):
            try:
                # Skip if already target format
                if img_path.suffix.lower() == target_ext:
                    stats['skipped'] += 1
                    continue
                
                progress = (idx + 1) / len(images) * 100
                self.on_progress(f"[{idx+1}/{len(images)}] Converting {img_path.name}... ({progress:.1f}%)")
                
                orig_size = img_path.stat().st_size
                stats['size_before'] += orig_size
                
                # Open and convert
                with Image.open(img_path) as img:
                    # Convert RGBA to RGB if saving as JPEG
                    if target_format.lower() in ['jpg', 'jpeg'] and img.mode in ['RGBA', 'LA']:
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    
                    # New filename
                    new_path = img_path.with_suffix(target_ext)
                    
                    # Save
                    save_kwargs = {}
                    if target_format.lower() in ['jpg', 'jpeg']:
                        save_kwargs = {'quality': quality, 'optimize': True}
                    elif target_format.lower() == 'webp':
                        save_kwargs = {'quality': quality, 'method': 6}
                    elif target_format.lower() == 'png':
                        save_kwargs = {'optimize': True}
                    
                    img.save(new_path, **save_kwargs)
                
                # Also convert caption file if exists
                caption_file = img_path.with_suffix('.txt')
                if caption_file.exists():
                    new_caption = new_path.with_suffix('.txt')
                    if not new_caption.exists():
                        shutil.copy2(caption_file, new_caption)
                
                new_size = new_path.stat().st_size
                stats['size_after'] += new_size
                
                # Delete original
                if delete_original:
                    img_path.unlink()
                    if caption_file.exists() and new_path != img_path:
                        caption_file.unlink()
                
                stats['converted'] += 1
                
            except Exception as e:
                self.on_progress(f"❌ Error: {e}")
                stats['errors'] += 1
        
        stats['size_saved_mb'] = (stats['size_before'] - stats['size_after']) / (1024 * 1024)
        
        self.on_progress(f"\n✅ Converted: {stats['converted']}, Errors: {stats['errors']}, Skipped: {stats['skipped']}")
        self.on_progress(f"💾 Size change: {stats['size_saved_mb']:+.2f} MB")
        
        return stats


class ImageDeduplicator:
    """Phát hiện và xóa ảnh trùng lặp"""
    
    def __init__(self, dataset_path: str, on_progress: Optional[Callable] = None):
        self.dataset_path = Path(dataset_path)
        self.on_progress = on_progress or (lambda msg: print(msg))
    
    def find_duplicates(self, method: str = 'hash') -> Dict[str, List[Path]]:
        """
        Tìm ảnh trùng
        
        Args:
            method: 'hash' (exact) hoặc 'perceptual' (similar)
            
        Returns:
            Dict: {hash: [list of duplicate files]}
        """
        
        image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        images = [f for f in self.dataset_path.iterdir() 
                 if f.suffix.lower() in image_exts]
        
        self.on_progress(f"🔍 Scanning {len(images)} images for duplicates...")
        
        hash_map = defaultdict(list)
        
        for idx, img_path in enumerate(images):
            try:
                progress = (idx + 1) / len(images) * 100
                if (idx + 1) % 10 == 0:
                    self.on_progress(f"Progress: {progress:.1f}%")
                
                if method == 'hash':
                    # Exact hash
                    img_hash = self._file_hash(img_path)
                else:
                    # Perceptual hash
                    img_hash = self._perceptual_hash(img_path)
                
                hash_map[img_hash].append(img_path)
                
            except Exception as e:
                self.on_progress(f"⚠️ Error hashing {img_path.name}: {e}")
        
        # Filter only duplicates
        duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}
        
        total_dupes = sum(len(files) - 1 for files in duplicates.values())
        self.on_progress(f"\n🔍 Found {len(duplicates)} groups with {total_dupes} duplicate images")
        
        return duplicates
    
    def remove_duplicates(self, keep: str = 'first') -> Dict:
        """
        Xóa ảnh trùng
        
        Args:
            keep: 'first', 'last', 'largest', 'smallest'
            
        Returns:
            Stats dict
        """
        
        duplicates = self.find_duplicates()
        
        stats = {
            'removed': 0,
            'kept': 0,
            'space_freed_mb': 0
        }
        
        for hash_val, files in duplicates.items():
            # Decide which to keep
            if keep == 'first':
                keep_file = files[0]
                remove_files = files[1:]
            elif keep == 'last':
                keep_file = files[-1]
                remove_files = files[:-1]
            elif keep == 'largest':
                keep_file = max(files, key=lambda f: f.stat().st_size)
                remove_files = [f for f in files if f != keep_file]
            else:  # smallest
                keep_file = min(files, key=lambda f: f.stat().st_size)
                remove_files = [f for f in files if f != keep_file]
            
            # Remove duplicates
            for remove_file in remove_files:
                size = remove_file.stat().st_size
                stats['space_freed_mb'] += size / (1024 * 1024)
                
                # Remove image
                remove_file.unlink()
                
                # Remove caption if exists
                caption_file = remove_file.with_suffix('.txt')
                if caption_file.exists():
                    caption_file.unlink()
                
                stats['removed'] += 1
                self.on_progress(f"🗑️ Removed: {remove_file.name}")
            
            stats['kept'] += 1
            self.on_progress(f"✅ Kept: {keep_file.name}")
        
        self.on_progress(f"\n✅ Removed {stats['removed']} duplicates, freed {stats['space_freed_mb']:.2f} MB")
        
        return stats
    
    def _file_hash(self, file_path: Path) -> str:
        """Calculate exact file hash"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _perceptual_hash(self, img_path: Path) -> str:
        """Simple perceptual hash (average hash)"""
        with Image.open(img_path) as img:
            # Resize to 8x8
            img = img.convert('L').resize((8, 8), Image.LANCZOS)
            # Get average
            pixels = list(img.getdata())
            avg = sum(pixels) / len(pixels)
            # Create hash
            hash_str = ''.join('1' if p > avg else '0' for p in pixels)
            return hash_str


class DatasetOrganizer:
    """Tự động organize dataset theo resolution, tags, etc."""
    
    def __init__(self, dataset_path: str, on_progress: Optional[Callable] = None):
        self.dataset_path = Path(dataset_path)
        self.on_progress = on_progress or (lambda msg: print(msg))
    
    def organize_by_resolution(self) -> Dict:
        """Tạo subfolder cho mỗi resolution khác nhau"""
        
        image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        images = [f for f in self.dataset_path.iterdir() 
                 if f.suffix.lower() in image_exts]
        
        # Group by resolution
        resolution_groups = defaultdict(list)
        
        for img_path in images:
            try:
                with Image.open(img_path) as img:
                    res = f"{img.width}x{img.height}"
                    resolution_groups[res].append(img_path)
            except Exception as e:
                self.on_progress(f"⚠️ Error reading {img_path.name}: {e}")
        
        # Create folders and move
        stats = {'moved': 0, 'errors': 0}
        
        for resolution, files in resolution_groups.items():
            folder = self.dataset_path / resolution
            folder.mkdir(exist_ok=True)
            
            for img_path in files:
                try:
                    new_path = folder / img_path.name
                    shutil.move(str(img_path), str(new_path))
                    
                    # Move caption too
                    caption_file = img_path.with_suffix('.txt')
                    if caption_file.exists():
                        new_caption = folder / caption_file.name
                        shutil.move(str(caption_file), str(new_caption))
                    
                    stats['moved'] += 1
                    
                except Exception as e:
                    self.on_progress(f"❌ Error moving {img_path.name}: {e}")
                    stats['errors'] += 1
            
            self.on_progress(f"📁 {resolution}/: {len(files)} images")
        
        self.on_progress(f"\n✅ Organized into {len(resolution_groups)} folders")
        
        return stats


class DatasetValidator:
    """Validate dataset - check lỗi, corrupted files, etc."""
    
    def __init__(self, dataset_path: str, on_progress: Optional[Callable] = None):
        self.dataset_path = Path(dataset_path)
        self.on_progress = on_progress or (lambda msg: print(msg))
    
    def validate(self) -> Dict:
        """
        Validate dataset
        
        Returns:
            Dict with issues found
        """
        
        image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        images = [f for f in self.dataset_path.iterdir() 
                 if f.suffix.lower() in image_exts]
        
        issues = {
            'corrupted': [],
            'missing_captions': [],
            'empty_captions': [],
            'small_images': [],
            'large_images': [],
            'unusual_aspect_ratios': []
        }
        
        for idx, img_path in enumerate(images):
            try:
                # Try to open image
                with Image.open(img_path) as img:
                    w, h = img.size
                    
                    # Check size
                    if w < 256 or h < 256:
                        issues['small_images'].append(f"{img_path.name} ({w}x{h})")
                    
                    if w > 2048 or h > 2048:
                        issues['large_images'].append(f"{img_path.name} ({w}x{h})")
                    
                    # Check aspect ratio
                    ratio = max(w, h) / min(w, h)
                    if ratio > 3:
                        issues['unusual_aspect_ratios'].append(f"{img_path.name} ({w}x{h}, ratio {ratio:.2f})")
                
                # Check caption
                caption_file = img_path.with_suffix('.txt')
                if not caption_file.exists():
                    issues['missing_captions'].append(img_path.name)
                else:
                    caption = caption_file.read_text(encoding='utf-8').strip()
                    if not caption:
                        issues['empty_captions'].append(img_path.name)
                
            except Exception as e:
                issues['corrupted'].append(f"{img_path.name}: {str(e)}")
        
        # Report
        self.on_progress("\n📋 Validation Report:")
        self.on_progress("=" * 50)
        
        for issue_type, items in issues.items():
            if items:
                self.on_progress(f"\n⚠️ {issue_type.replace('_', ' ').title()}: {len(items)}")
                for item in items[:5]:  # Show first 5
                    self.on_progress(f"   - {item}")
                if len(items) > 5:
                    self.on_progress(f"   ... and {len(items) - 5} more")
        
        total_issues = sum(len(items) for items in issues.values())
        if total_issues == 0:
            self.on_progress("\n✅ No issues found! Dataset looks good.")
        else:
            self.on_progress(f"\n⚠️ Total issues: {total_issues}")
        
        return issues


# Quick helper functions
def quick_resize(dataset_path: str, target_resolution: Tuple[int, int], **kwargs):
    """Quick resize helper"""
    resizer = DatasetResizer(dataset_path)
    return resizer.resize_dataset(target_resolution, **kwargs)

def quick_convert(dataset_path: str, target_format: str = 'webp', **kwargs):
    """Quick convert helper"""
    converter = ImageFormatConverter(dataset_path)
    return converter.convert_all(target_format, **kwargs)

def quick_dedupe(dataset_path: str, **kwargs):
    """Quick deduplicate helper"""
    deduper = ImageDeduplicator(dataset_path)
    return deduper.remove_duplicates(**kwargs)

def quick_validate(dataset_path: str):
    """Quick validate helper"""
    validator = DatasetValidator(dataset_path)
    return validator.validate()
