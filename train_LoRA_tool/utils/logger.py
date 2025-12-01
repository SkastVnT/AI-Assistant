"""
Logging utilities for LoRA training
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import sys


def setup_logger(log_dir: str, name: str = "lora_training") -> logging.Logger:
    """
    Setup logger with file and console handlers
    
    Args:
        log_dir: Directory to save log files
        name: Logger name
    
    Returns:
        Configured logger
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # File handler
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"training_{timestamp}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"Logger initialized. Log file: {log_file}")
    
    return logger


def log_training_info(logger: logging.Logger, config: Dict):
    """
    Log training configuration and system info
    
    Args:
        logger: Logger instance
        config: Training configuration
    """
    import torch
    
    logger.info("\n" + "="*80)
    logger.info("Training Configuration")
    logger.info("="*80)
    
    # Model info
    logger.info(f"Base Model: {config['model']['pretrained_model_name_or_path']}")
    logger.info(f"LoRA Rank: {config['lora']['rank']}")
    logger.info(f"LoRA Alpha: {config['lora']['alpha']}")
    logger.info(f"LoRA Dropout: {config['lora']['dropout']}")
    
    # Dataset info
    logger.info(f"\nDataset Directory: {config['dataset']['train_data_dir']}")
    logger.info(f"Image Resolution: {config['dataset']['resolution']}")
    logger.info(f"Center Crop: {config['dataset']['center_crop']}")
    logger.info(f"Random Flip: {config['dataset']['random_flip']}")
    
    # Training info
    logger.info(f"\nBatch Size: {config['training']['train_batch_size']}")
    logger.info(f"Gradient Accumulation Steps: {config['training']['gradient_accumulation_steps']}")
    logger.info(f"Effective Batch Size: {config['training']['train_batch_size'] * config['training']['gradient_accumulation_steps']}")
    logger.info(f"Learning Rate: {config['training']['learning_rate']}")
    logger.info(f"Optimizer: {config['training']['optimizer']}")
    logger.info(f"LR Scheduler: {config['training']['lr_scheduler']}")
    logger.info(f"Num Epochs: {config['training']['num_train_epochs']}")
    logger.info(f"Mixed Precision: {config['training']['mixed_precision']}")
    logger.info(f"Gradient Checkpointing: {config['training']['gradient_checkpointing']}")
    
    # System info
    logger.info(f"\nDevice: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"CUDA Version: {torch.version.cuda}")
        logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    
    logger.info("="*80 + "\n")


class TrainingLogger:
    """Training progress logger"""
    
    def __init__(self, logger: logging.Logger, total_steps: int, logging_steps: int = 10):
        """
        Initialize training logger
        
        Args:
            logger: Base logger
            total_steps: Total number of training steps
            logging_steps: Log every N steps
        """
        self.logger = logger
        self.total_steps = total_steps
        self.logging_steps = logging_steps
        self.losses = []
        self.lr_history = []
    
    def log_step(self, step: int, loss: float, lr: float, epoch: int):
        """
        Log training step
        
        Args:
            step: Current step
            loss: Current loss
            lr: Current learning rate
            epoch: Current epoch
        """
        self.losses.append(loss)
        self.lr_history.append(lr)
        
        if step % self.logging_steps == 0:
            avg_loss = sum(self.losses[-self.logging_steps:]) / min(len(self.losses), self.logging_steps)
            progress = (step / self.total_steps) * 100
            
            self.logger.info(
                f"Epoch: {epoch} | Step: {step}/{self.total_steps} ({progress:.1f}%) | "
                f"Loss: {loss:.4f} | Avg Loss: {avg_loss:.4f} | LR: {lr:.2e}"
            )
    
    def log_epoch_end(self, epoch: int, avg_loss: float, val_loss: Optional[float] = None):
        """
        Log end of epoch
        
        Args:
            epoch: Epoch number
            avg_loss: Average training loss
            val_loss: Validation loss (optional)
        """
        msg = f"Epoch {epoch} completed | Train Loss: {avg_loss:.4f}"
        if val_loss is not None:
            msg += f" | Val Loss: {val_loss:.4f}"
        
        self.logger.info("\n" + "="*80)
        self.logger.info(msg)
        self.logger.info("="*80 + "\n")
    
    def get_avg_loss(self, last_n: Optional[int] = None) -> float:
        """Get average loss over last N steps"""
        if last_n is None:
            return sum(self.losses) / len(self.losses) if self.losses else 0.0
        else:
            return sum(self.losses[-last_n:]) / min(len(self.losses), last_n) if self.losses else 0.0
