"""
Dataset preprocessing utilities
Auto-captioning, tagging, and image validation
"""

import os
import shutil
from pathlib import Path
from PIL import Image
from typing import List, Dict, Optional, Tuple
import torch
from tqdm import tqdm


class DatasetValidator:
    """Validate and clean image dataset"""
    
    def __init__(self, data_dir: str, min_size: int = 256, max_size: int = 8192):
        """
        Initialize validator
        
        Args:
            data_dir: Directory containing images
            min_size: Minimum image dimension
            max_size: Maximum image dimension
        """
        self.data_dir = Path(data_dir)
        self.min_size = min_size
        self.max_size = max_size
    
    def validate_images(self, fix_issues: bool = False) -> Dict:
        """
        Validate all images in dataset
        
        Args:
            fix_issues: Whether to fix issues (resize, convert, etc.)
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'total': 0,
            'valid': 0,
            'corrupted': [],
            'too_small': [],
            'too_large': [],
            'wrong_format': [],
            'fixed': []
        }
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        image_paths = []
        
        for ext in image_extensions:
            image_paths.extend(self.data_dir.glob(f'*{ext}'))
            image_paths.extend(self.data_dir.glob(f'*{ext.upper()}'))
        
        results['total'] = len(image_paths)
        
        print(f"Validating {results['total']} images...")
        
        for image_path in tqdm(image_paths):
            try:
                # Try to open image
                img = Image.open(image_path)
                width, height = img.size
                
                # Check if corrupted
                img.verify()
                img = Image.open(image_path)  # Reopen after verify
                
                # Check size
                if width < self.min_size or height < self.min_size:
                    results['too_small'].append(str(image_path))
                    continue
                
                if width > self.max_size or height > self.max_size:
                    results['too_large'].append(str(image_path))
                    if fix_issues:
                        # Resize
                        img.thumbnail((self.max_size, self.max_size), Image.LANCZOS)
                        img.save(image_path)
                        results['fixed'].append(str(image_path))
                    continue
                
                # Check format
                if img.mode not in ['RGB', 'RGBA']:
                    results['wrong_format'].append(str(image_path))
                    if fix_issues:
                        # Convert to RGB
                        img = img.convert('RGB')
                        img.save(image_path)
                        results['fixed'].append(str(image_path))
                
                results['valid'] += 1
                
            except Exception as e:
                results['corrupted'].append(str(image_path))
                print(f"\nCorrupted image: {image_path} - {e}")
        
        # Print summary
        print("\n" + "="*60)
        print("Validation Summary:")
        print("="*60)
        print(f"Total images: {results['total']}")
        print(f"Valid images: {results['valid']}")
        print(f"Corrupted images: {len(results['corrupted'])}")
        print(f"Too small images: {len(results['too_small'])}")
        print(f"Too large images: {len(results['too_large'])}")
        print(f"Wrong format images: {len(results['wrong_format'])}")
        if fix_issues:
            print(f"Fixed images: {len(results['fixed'])}")
        print("="*60)
        
        return results
    
    def remove_corrupted(self, corrupted_list: List[str], backup_dir: Optional[str] = None):
        """
        Remove or backup corrupted images
        
        Args:
            corrupted_list: List of corrupted image paths
            backup_dir: Directory to backup corrupted images (optional)
        """
        if backup_dir:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
        
        for img_path in corrupted_list:
            if backup_dir:
                shutil.move(img_path, backup_path / Path(img_path).name)
                print(f"Moved to backup: {img_path}")
            else:
                os.remove(img_path)
                print(f"Removed: {img_path}")


class AutoCaptioner:
    """Auto-generate captions for images using BLIP or similar models"""
    
    def __init__(self, model_name: str = "Salesforce/blip-image-captioning-base"):
        """
        Initialize auto-captioner
        
        Args:
            model_name: HuggingFace model name for captioning
        """
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration
            
            print(f"Loading captioning model: {model_name}")
            self.processor = BlipProcessor.from_pretrained(model_name)
            self.model = BlipForConditionalGeneration.from_pretrained(model_name)
            
            # Move to GPU if available
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.to(self.device)
            
        except ImportError:
            print("Error: transformers library not found. Install with: pip install transformers")
            self.model = None
    
    def generate_caption(self, image_path: str, prefix: str = "") -> str:
        """
        Generate caption for a single image
        
        Args:
            image_path: Path to image
            prefix: Optional prefix for caption (e.g., "a photo of sks person")
        
        Returns:
            Generated caption
        """
        if self.model is None:
            return ""
        
        try:
            # Load image
            image = Image.open(image_path).convert('RGB')
            
            # Process image
            inputs = self.processor(image, return_tensors="pt").to(self.device)
            
            # Generate caption
            with torch.no_grad():
                out = self.model.generate(**inputs, max_length=75)
            
            caption = self.processor.decode(out[0], skip_special_tokens=True)
            
            # Add prefix if provided
            if prefix:
                caption = f"{prefix}, {caption}"
            
            return caption
            
        except Exception as e:
            print(f"Error generating caption for {image_path}: {e}")
            return ""
    
    def caption_dataset(
        self,
        data_dir: str,
        caption_extension: str = ".txt",
        prefix: str = "",
        overwrite: bool = False
    ):
        """
        Generate captions for all images in dataset
        
        Args:
            data_dir: Directory containing images
            caption_extension: Extension for caption files
            prefix: Optional prefix for all captions
            overwrite: Whether to overwrite existing captions
        """
        data_path = Path(data_dir)
        
        # Find all images
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        image_paths = []
        
        for ext in image_extensions:
            image_paths.extend(data_path.glob(f'*{ext}'))
            image_paths.extend(data_path.glob(f'*{ext.upper()}'))
        
        print(f"Generating captions for {len(image_paths)} images...")
        
        for image_path in tqdm(image_paths):
            caption_path = image_path.with_suffix(caption_extension)
            
            # Skip if caption exists and not overwriting
            if caption_path.exists() and not overwrite:
                continue
            
            # Generate caption
            caption = self.generate_caption(str(image_path), prefix=prefix)
            
            # Save caption
            if caption:
                with open(caption_path, 'w', encoding='utf-8') as f:
                    f.write(caption)


class DatasetSplitter:
    """Split dataset into train/validation sets"""
    
    @staticmethod
    def split_dataset(
        source_dir: str,
        train_dir: str,
        val_dir: str,
        val_ratio: float = 0.1,
        copy_files: bool = True
    ):
        """
        Split dataset into train and validation sets
        
        Args:
            source_dir: Source directory with all images
            train_dir: Output directory for training images
            val_dir: Output directory for validation images
            val_ratio: Ratio of validation images (0.0 to 1.0)
            copy_files: Whether to copy files (True) or move them (False)
        """
        import random
        
        source_path = Path(source_dir)
        train_path = Path(train_dir)
        val_path = Path(val_dir)
        
        # Create directories
        train_path.mkdir(parents=True, exist_ok=True)
        val_path.mkdir(parents=True, exist_ok=True)
        
        # Find all images
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        image_paths = []
        
        for ext in image_extensions:
            image_paths.extend(source_path.glob(f'*{ext}'))
            image_paths.extend(source_path.glob(f'*{ext.upper()}'))
        
        # Shuffle
        random.shuffle(image_paths)
        
        # Calculate split
        num_val = int(len(image_paths) * val_ratio)
        val_images = image_paths[:num_val]
        train_images = image_paths[num_val:]
        
        print(f"Splitting dataset:")
        print(f"  Total: {len(image_paths)}")
        print(f"  Training: {len(train_images)}")
        print(f"  Validation: {len(val_images)}")
        
        # Copy/move files
        file_operation = shutil.copy2 if copy_files else shutil.move
        
        # Process training set
        for img_path in tqdm(train_images, desc="Training set"):
            file_operation(str(img_path), str(train_path / img_path.name))
            
            # Copy caption if exists
            for ext in ['.txt', '.caption', '.tags']:
                caption_path = img_path.with_suffix(ext)
                if caption_path.exists():
                    file_operation(str(caption_path), str(train_path / caption_path.name))
        
        # Process validation set
        for img_path in tqdm(val_images, desc="Validation set"):
            file_operation(str(img_path), str(val_path / img_path.name))
            
            # Copy caption if exists
            for ext in ['.txt', '.caption', '.tags']:
                caption_path = img_path.with_suffix(ext)
                if caption_path.exists():
                    file_operation(str(caption_path), str(val_path / caption_path.name))
        
        print("Dataset split complete!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Dataset preprocessing utilities")
    parser.add_argument("--data_dir", type=str, required=True, help="Dataset directory")
    parser.add_argument("--action", type=str, choices=['validate', 'caption', 'split'], required=True)
    parser.add_argument("--fix", action='store_true', help="Fix issues during validation")
    parser.add_argument("--prefix", type=str, default="", help="Caption prefix")
    parser.add_argument("--val_ratio", type=float, default=0.1, help="Validation split ratio")
    
    args = parser.parse_args()
    
    if args.action == 'validate':
        validator = DatasetValidator(args.data_dir)
        validator.validate_images(fix_issues=args.fix)
    
    elif args.action == 'caption':
        captioner = AutoCaptioner()
        captioner.caption_dataset(args.data_dir, prefix=args.prefix)
    
    elif args.action == 'split':
        DatasetSplitter.split_dataset(
            args.data_dir,
            f"{args.data_dir}_train",
            f"{args.data_dir}_val",
            val_ratio=args.val_ratio
        )
