"""
LoRA Training Script
Main training script for fine-tuning Stable Diffusion models using LoRA (Low-Rank Adaptation).
"""

import os
import sys
import argparse
import logging
import math
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import yaml
import torch
import torch.nn.functional as F
from accelerate import Accelerator
from diffusers import (
    AutoencoderKL,
    DDPMScheduler,
    StableDiffusionPipeline,
    UNet2DConditionModel,
)
from diffusers.optimization import get_scheduler
from transformers import CLIPTextModel, CLIPTokenizer
import numpy as np

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.dataset_loader import create_dataloader
from utils.logger import setup_logger, TrainingLogger
from utils.model_utils import load_pretrained_model, save_lora_weights
from utils.lora_layers import apply_lora_to_model
from utils.training_utils import (
    setup_optimizer,
    setup_scheduler,
    train_one_epoch,
    validate_model,
    save_checkpoint,
    load_checkpoint,
)
from utils.advanced_training import (
    EMAModel,
    compute_snr,
    compute_min_snr_loss_weight,
    apply_noise_offset,
    pyramid_noise_like,
    ProdigyOptimizer,
    compute_scheduled_huber_loss,
    apply_loraplus,
)


class LoRATrainer:
    """Main trainer class for LoRA fine-tuning."""
    
    def __init__(self, config: Dict[str, Any], resume_from: Optional[str] = None):
        """
        Initialize the LoRA trainer.
        
        Args:
            config: Training configuration dictionary
            resume_from: Path to checkpoint to resume from
        """
        self.config = config
        self.resume_from = resume_from
        
        # Setup accelerator for distributed training
        self.accelerator = Accelerator(
            mixed_precision=config['training'].get('mixed_precision', 'fp16'),
            gradient_accumulation_steps=config['training'].get('gradient_accumulation_steps', 4),
        )
        
        # Setup logging
        self.logger = setup_logger(
            name="LoRATrainer",
            log_file=Path(config['output']['output_dir']) / "logs" / "training.log"
        )
        
        # Initialize training logger
        self.training_logger = TrainingLogger(
            log_dir=Path(config['output']['output_dir']) / "logs",
            use_tensorboard=config['logging'].get('use_tensorboard', False),
            use_wandb=config['logging'].get('use_wandb', False),
            wandb_project=config['logging'].get('wandb_project'),
        )
        
        # Training state
        self.current_epoch = 0
        self.current_step = 0
        self.best_loss = float('inf')
        
        # Advanced training features
        self.use_ema = config['training'].get('use_ema', False)
        self.ema_decay = config['training'].get('ema_decay', 0.9999)
        self.ema_model = None
        
        # Min-SNR weighting (Hang et al. 2023)
        self.min_snr_gamma = config['training'].get('min_snr_gamma', None)
        
        # Noise offset (improves darker/lighter image generation)
        self.noise_offset = config['training'].get('noise_offset', 0.0)
        
        # Adaptive loss weighting
        self.adaptive_loss_weight = config['training'].get('adaptive_loss_weight', False)
        
        # Multi-resolution training (buckets)
        self.use_buckets = config['dataset'].get('use_buckets', False)
        self.bucket_sizes = config['dataset'].get('bucket_sizes', [(512, 512), (768, 512), (512, 768)])
        
        # LoRA+ (faster convergence with higher LR for B layers)
        self.use_loraplus = config['training'].get('use_loraplus', False)
        self.loraplus_lr_ratio = config['training'].get('loraplus_lr_ratio', 16.0)
        self.loraplus_unet_lr_ratio = config['training'].get('loraplus_unet_lr_ratio', None)
        self.loraplus_text_encoder_lr_ratio = config['training'].get('loraplus_text_encoder_lr_ratio', None)
        
        # Scheduled Huber Loss (robust against outliers)
        self.loss_type = config['training'].get('loss_type', 'l2')  # 'l2', 'huber', 'smooth_l1'
        self.huber_c = config['training'].get('huber_c', 0.1)
        self.huber_schedule = config['training'].get('huber_schedule', 'snr')  # 'snr', 'exponential', 'constant'
        
    def prepare_dataset(self):
        """Prepare training and validation datasets."""
        self.logger.info("Preparing datasets...")
        
        # Create data loaders
        self.train_loader = create_dataloader(
            data_dir=self.config['dataset']['train_data_dir'],
            batch_size=self.config['training']['train_batch_size'],
            resolution=self.config['dataset']['resolution'],
            center_crop=self.config['dataset'].get('center_crop', True),
            random_flip=self.config['dataset'].get('random_flip', True),
            num_workers=self.config['training'].get('dataloader_num_workers', 4),
        )
        
        # Validation loader (optional)
        val_dir = self.config['dataset'].get('validation_data_dir')
        if val_dir and os.path.exists(val_dir):
            self.val_loader = create_dataloader(
                data_dir=val_dir,
                batch_size=self.config['training']['train_batch_size'],
                resolution=self.config['dataset']['resolution'],
                center_crop=True,
                random_flip=False,
                num_workers=self.config['training'].get('dataloader_num_workers', 4),
            )
        else:
            self.val_loader = None
            
        self.logger.info(f"Training samples: {len(self.train_loader.dataset)}")
        if self.val_loader:
            self.logger.info(f"Validation samples: {len(self.val_loader.dataset)}")
    
    def setup_model(self):
        """Load and setup the model with LoRA layers."""
        self.logger.info("Setting up model...")
        
        model_path = self.config['model']['pretrained_model_name_or_path']
        
        # Load pretrained components
        self.tokenizer, self.text_encoder, self.vae, self.unet, self.noise_scheduler = \
            load_pretrained_model(model_path)
        
        # Apply LoRA to UNet
        lora_config = self.config['lora']
        self.unet = apply_lora_to_model(
            self.unet,
            rank=lora_config['rank'],
            alpha=lora_config['alpha'],
            dropout=lora_config.get('dropout', 0.0),
            target_modules=lora_config.get('target_modules', ['to_q', 'to_k', 'to_v', 'to_out.0']),
        )
        
        # Optionally apply LoRA to text encoder
        if self.config['training'].get('train_text_encoder', False):
            self.text_encoder = apply_lora_to_model(
                self.text_encoder,
                rank=lora_config['rank'] // 2,  # Use lower rank for text encoder
                alpha=lora_config['alpha'] // 2,
                target_modules=['q_proj', 'k_proj', 'v_proj', 'out_proj'],
            )
        
        # Freeze base model parameters
        self.vae.requires_grad_(False)
        if not self.config['training'].get('train_text_encoder', False):
            self.text_encoder.requires_grad_(False)
        
        # Enable gradient checkpointing if specified
        if self.config['training'].get('gradient_checkpointing', False):
            self.unet.enable_gradient_checkpointing()
            if self.config['training'].get('train_text_encoder', False):
                self.text_encoder.gradient_checkpointing_enable()
        
        self.logger.info(f"Model loaded: {model_path}")
        self.logger.info(f"LoRA rank: {lora_config['rank']}, alpha: {lora_config['alpha']}")
    
    def setup_training(self):
        """Setup optimizer, scheduler, and accelerator."""
        self.logger.info("Setting up training components...")
        
        # Get trainable parameters
        trainable_params = []
        for name, param in self.unet.named_parameters():
            if param.requires_grad:
                trainable_params.append(param)
        
        if self.config['training'].get('train_text_encoder', False):
            for name, param in self.text_encoder.named_parameters():
                if param.requires_grad:
                    trainable_params.append(param)
        
        self.logger.info(f"Trainable parameters: {sum(p.numel() for p in trainable_params):,}")
        
        # Setup optimizer
        self.optimizer = setup_optimizer(
            trainable_params,
            lr=self.config['training']['learning_rate'],
            optimizer_type=self.config['training'].get('optimizer', 'adamw'),
            weight_decay=self.config['training'].get('weight_decay', 0.01),
        )
        
        # Setup learning rate scheduler
        num_training_steps = len(self.train_loader) * self.config['training']['num_train_epochs']
        self.lr_scheduler = setup_scheduler(
            self.optimizer,
            scheduler_type=self.config['training'].get('lr_scheduler', 'cosine'),
            num_training_steps=num_training_steps,
            num_warmup_steps=self.config['training'].get('lr_warmup_steps', 500),
        )
        
        # Prepare with accelerator
        self.unet, self.optimizer, self.train_loader, self.lr_scheduler = \
            self.accelerator.prepare(
                self.unet, self.optimizer, self.train_loader, self.lr_scheduler
            )
        
        if self.config['training'].get('train_text_encoder', False):
            self.text_encoder = self.accelerator.prepare(self.text_encoder)
        
        if self.val_loader:
            self.val_loader = self.accelerator.prepare(self.val_loader)
    
    def train(self):
        """Main training loop."""
        self.logger.info("Starting training...")
        
        # Prepare everything
        self.prepare_dataset()
        self.setup_model()
        self.setup_training()
        
        # Resume from checkpoint if specified
        if self.resume_from:
            self.current_epoch, self.current_step = load_checkpoint(
                self.resume_from,
                self.unet,
                self.optimizer,
                self.lr_scheduler,
            )
            self.logger.info(f"Resumed from epoch {self.current_epoch}, step {self.current_step}")
        
        # Training loop
        num_epochs = self.config['training']['num_train_epochs']
        output_dir = Path(self.config['output']['output_dir'])
        
        for epoch in range(self.current_epoch, num_epochs):
            self.current_epoch = epoch
            
            # Train one epoch
            train_loss = train_one_epoch(
                epoch=epoch,
                model=self.unet,
                text_encoder=self.text_encoder if self.config['training'].get('train_text_encoder', False) else None,
                vae=self.vae,
                noise_scheduler=self.noise_scheduler,
                optimizer=self.optimizer,
                lr_scheduler=self.lr_scheduler,
                train_loader=self.train_loader,
                accelerator=self.accelerator,
                logger=self.training_logger,
                config=self.config,
            )
            
            self.logger.info(f"Epoch {epoch + 1}/{num_epochs} - Train Loss: {train_loss:.4f}")
            
            # Validation
            if self.val_loader and (epoch + 1) % self.config['training'].get('validation_epochs', 5) == 0:
                val_loss = validate_model(
                    model=self.unet,
                    text_encoder=self.text_encoder if self.config['training'].get('train_text_encoder', False) else None,
                    vae=self.vae,
                    noise_scheduler=self.noise_scheduler,
                    val_loader=self.val_loader,
                    accelerator=self.accelerator,
                )
                self.logger.info(f"Epoch {epoch + 1}/{num_epochs} - Val Loss: {val_loss:.4f}")
                
                # Save best model
                if val_loss < self.best_loss:
                    self.best_loss = val_loss
                    self.save_model(output_dir / "lora_models" / "best_model.safetensors")
            
            # Save checkpoint
            if (epoch + 1) % self.config['training'].get('checkpointing_steps', 5) == 0:
                checkpoint_path = output_dir / "checkpoints" / f"checkpoint_epoch_{epoch + 1}.pt"
                save_checkpoint(
                    checkpoint_path,
                    epoch=epoch + 1,
                    step=self.current_step,
                    model=self.unet,
                    optimizer=self.optimizer,
                    lr_scheduler=self.lr_scheduler,
                    config=self.config,
                )
                self.logger.info(f"Checkpoint saved: {checkpoint_path}")
        
        # Save final model
        self.save_model(output_dir / "lora_models" / "final_model.safetensors")
        self.logger.info("Training completed!")
    
    def save_model(self, save_path: Path):
        """Save LoRA weights."""
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Extract LoRA weights
        lora_state_dict = {}
        for name, param in self.unet.named_parameters():
            if 'lora' in name.lower():
                lora_state_dict[name] = param.cpu()
        
        if self.config['training'].get('train_text_encoder', False):
            for name, param in self.text_encoder.named_parameters():
                if 'lora' in name.lower():
                    lora_state_dict[f"text_encoder.{name}"] = param.cpu()
        
        # Save with metadata
        save_lora_weights(
            lora_state_dict,
            save_path,
            metadata={
                'rank': self.config['lora']['rank'],
                'alpha': self.config['lora']['alpha'],
                'base_model': self.config['model']['pretrained_model_name_or_path'],
                'epochs': self.current_epoch + 1,
            }
        )
        
        self.logger.info(f"Model saved: {save_path}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Train LoRA for Stable Diffusion")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to configuration YAML file"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Override output directory from config"
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to checkpoint to resume training from"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override output directory if specified
    if args.output_dir:
        config['output']['output_dir'] = args.output_dir
    
    # Create output directories
    output_dir = Path(config['output']['output_dir'])
    (output_dir / "lora_models").mkdir(parents=True, exist_ok=True)
    (output_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    (output_dir / "logs").mkdir(parents=True, exist_ok=True)
    (output_dir / "samples").mkdir(parents=True, exist_ok=True)
    
    # Initialize trainer
    trainer = LoRATrainer(config, resume_from=args.resume)
    
    # Start training
    trainer.train()


if __name__ == "__main__":
    main()
