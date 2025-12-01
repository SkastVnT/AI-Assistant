"""
Resume training from checkpoint
"""

import os
import argparse
import yaml
from pathlib import Path


def find_latest_checkpoint(checkpoint_dir: str) -> str:
    """
    Find the latest checkpoint in directory
    
    Args:
        checkpoint_dir: Directory containing checkpoints
    
    Returns:
        Path to latest checkpoint or None
    """
    checkpoint_path = Path(checkpoint_dir)
    
    if not checkpoint_path.exists():
        return None
    
    # Find all checkpoint files
    checkpoints = list(checkpoint_path.glob("checkpoint_epoch_*.pt"))
    
    if not checkpoints:
        return None
    
    # Sort by epoch number
    checkpoints.sort(key=lambda x: int(x.stem.split('_')[-1]))
    
    return str(checkpoints[-1])


def main():
    parser = argparse.ArgumentParser(description="Resume LoRA training from checkpoint")
    parser.add_argument(
        "--checkpoint_dir",
        type=str,
        default="outputs/checkpoints",
        help="Directory containing checkpoints"
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default=None,
        help="Specific checkpoint to resume from (optional)"
    )
    
    args = parser.parse_args()
    
    # Find checkpoint
    if args.checkpoint:
        checkpoint_path = args.checkpoint
    else:
        checkpoint_path = find_latest_checkpoint(args.checkpoint_dir)
    
    if checkpoint_path is None or not os.path.exists(checkpoint_path):
        print("ERROR: No checkpoint found!")
        print(f"Searched in: {args.checkpoint_dir}")
        return
    
    print(f"Found checkpoint: {checkpoint_path}")
    
    # Load checkpoint to get config
    import torch
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    
    print(f"\nCheckpoint info:")
    print(f"  Epoch: {checkpoint['epoch']}")
    print(f"  Global step: {checkpoint['global_step']}")
    print(f"  Loss: {checkpoint['loss']:.4f}")
    
    # Get config path from checkpoint
    config = checkpoint.get('config')
    
    if config:
        # Save temp config
        temp_config_path = "configs/resume_config.yaml"
        with open(temp_config_path, 'w') as f:
            yaml.dump(config, f)
        
        print(f"\nConfig saved to: {temp_config_path}")
    
    print(f"\nTo resume training, run:")
    print(f"python train_lora.py --config {temp_config_path} --resume {checkpoint_path}")


if __name__ == "__main__":
    main()
