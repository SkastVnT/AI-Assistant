"""
Dataset utilities for LoRA training
Handles image loading, preprocessing, and caption management
"""

import os
import torch
import numpy as np
from pathlib import Path
from PIL import Image
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from typing import List, Optional, Tuple, Dict
import random


class ImageDataset(Dataset):
    """
    Dataset for loading images and their captions for LoRA training
    Supports various image formats and caption files
    """
    
    def __init__(
        self,
        data_dir: str,
        resolution: int = 512,
        center_crop: bool = True,
        random_flip: bool = True,
        caption_extension: str = ".txt",
        tokenizer = None,
        color_jitter: bool = False,
        random_rotation: bool = False
    ):
        """
        Initialize dataset
        
        Args:
            data_dir: Directory containing images and captions
            resolution: Target image resolution
            center_crop: Whether to center crop images
            random_flip: Whether to randomly flip images horizontally
            caption_extension: Caption file extension (.txt, .caption, .tags)
            tokenizer: Tokenizer for encoding captions
            color_jitter: Apply color jitter augmentation
            random_rotation: Apply random rotation augmentation
        """
        self.data_dir = Path(data_dir)
        self.resolution = resolution
        self.caption_extension = caption_extension
        self.tokenizer = tokenizer
        
        # Find all image files
        self.image_paths = self._find_images()
        
        if len(self.image_paths) == 0:
            raise ValueError(f"No images found in {data_dir}")
        
        # Setup transforms
        self.transform = self._setup_transforms(
            resolution, center_crop, random_flip, color_jitter, random_rotation
        )
    
    def _find_images(self) -> List[Path]:
        """Find all image files in directory"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        image_paths = []
        
        for ext in image_extensions:
            image_paths.extend(self.data_dir.glob(f'*{ext}'))
            image_paths.extend(self.data_dir.glob(f'*{ext.upper()}'))
        
        # Sort for consistency
        image_paths = sorted(image_paths)
        
        return image_paths
    
    def _setup_transforms(
        self,
        resolution: int,
        center_crop: bool,
        random_flip: bool,
        color_jitter: bool,
        random_rotation: bool
    ):
        """Setup image transformation pipeline"""
        transform_list = []
        
        # Resize
        transform_list.append(transforms.Resize(resolution, interpolation=transforms.InterpolationMode.BILINEAR))
        
        # Center crop
        if center_crop:
            transform_list.append(transforms.CenterCrop(resolution))
        else:
            transform_list.append(transforms.RandomCrop(resolution))
        
        # Random horizontal flip
        if random_flip:
            transform_list.append(transforms.RandomHorizontalFlip())
        
        # Color jitter
        if color_jitter:
            transform_list.append(
                transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1, hue=0.05)
            )
        
        # Random rotation
        if random_rotation:
            transform_list.append(transforms.RandomRotation(15))
        
        # Convert to tensor
        transform_list.append(transforms.ToTensor())
        
        # Normalize to [-1, 1]
        transform_list.append(transforms.Normalize([0.5], [0.5]))
        
        return transforms.Compose(transform_list)
    
    def _load_caption(self, image_path: Path) -> str:
        """Load caption from text file"""
        caption_path = image_path.with_suffix(self.caption_extension)
        
        if caption_path.exists():
            with open(caption_path, 'r', encoding='utf-8') as f:
                caption = f.read().strip()
                return caption
        else:
            # Use filename as caption if no caption file exists
            return image_path.stem.replace('_', ' ').replace('-', ' ')
    
    def __len__(self) -> int:
        return len(self.image_paths)
    
    def __getitem__(self, idx: int) -> Dict:
        """Get a single item from dataset"""
        image_path = self.image_paths[idx]
        
        # Load image
        try:
            image = Image.open(image_path).convert('RGB')
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            # Return a random other image
            return self.__getitem__(random.randint(0, len(self) - 1))
        
        # Apply transforms
        pixel_values = self.transform(image)
        
        # Load caption
        caption = self._load_caption(image_path)
        
        # Create return dict
        example = {
            'pixel_values': pixel_values,
            'caption': caption,
            'image_path': str(image_path)
        }
        
        # Tokenize caption if tokenizer is provided
        if self.tokenizer is not None:
            tokens = self.tokenizer(
                caption,
                padding="max_length",
                max_length=self.tokenizer.model_max_length,
                truncation=True,
                return_tensors="pt"
            )
            example['input_ids'] = tokens.input_ids[0]
        
        return example


def create_dataloader(
    dataset: Dataset,
    batch_size: int,
    shuffle: bool = True,
    num_workers: int = 4,
    pin_memory: bool = True
) -> DataLoader:
    """
    Create DataLoader for training
    
    Args:
        dataset: Dataset to load from
        batch_size: Batch size
        shuffle: Whether to shuffle data
        num_workers: Number of data loading workers
        pin_memory: Pin memory for faster GPU transfer
    
    Returns:
        DataLoader instance
    """
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=True  # Drop last incomplete batch
    )


def collate_fn(examples):
    """Custom collate function for batching"""
    pixel_values = torch.stack([example["pixel_values"] for example in examples])
    pixel_values = pixel_values.to(memory_format=torch.contiguous_format).float()
    
    captions = [example["caption"] for example in examples]
    
    batch = {
        "pixel_values": pixel_values,
        "captions": captions,
    }
    
    # Add input_ids if available
    if "input_ids" in examples[0]:
        input_ids = torch.stack([example["input_ids"] for example in examples])
        batch["input_ids"] = input_ids
    
    return batch
