"""
Training utilities
Optimizer, scheduler, training loop, and checkpoint management
"""

import torch
import torch.nn.functional as F
from torch.optim import AdamW, Adam, SGD
from torch.optim.lr_scheduler import (
    CosineAnnealingLR,
    LinearLR,
    ConstantLR,
    SequentialLR
)
from typing import Optional, Dict
from tqdm import tqdm
import os


def setup_optimizer(
    parameters,
    optimizer_type: str = "adamw",
    learning_rate: float = 1e-4,
    weight_decay: float = 0.01,
    adam_beta1: float = 0.9,
    adam_beta2: float = 0.999,
    adam_epsilon: float = 1e-8
):
    """
    Setup optimizer
    
    Args:
        parameters: Model parameters to optimize
        optimizer_type: Type of optimizer (adamw, adam, sgd)
        learning_rate: Learning rate
        weight_decay: Weight decay
        adam_beta1: Adam beta1
        adam_beta2: Adam beta2
        adam_epsilon: Adam epsilon
    
    Returns:
        Optimizer instance
    """
    if optimizer_type.lower() == "adamw":
        optimizer = AdamW(
            parameters,
            lr=learning_rate,
            betas=(adam_beta1, adam_beta2),
            eps=adam_epsilon,
            weight_decay=weight_decay
        )
    elif optimizer_type.lower() == "adam":
        optimizer = Adam(
            parameters,
            lr=learning_rate,
            betas=(adam_beta1, adam_beta2),
            eps=adam_epsilon,
            weight_decay=weight_decay
        )
    elif optimizer_type.lower() == "sgd":
        optimizer = SGD(
            parameters,
            lr=learning_rate,
            momentum=0.9,
            weight_decay=weight_decay
        )
    else:
        raise ValueError(f"Unsupported optimizer: {optimizer_type}")
    
    return optimizer


def setup_scheduler(
    optimizer,
    scheduler_type: str = "cosine",
    num_warmup_steps: int = 0,
    num_training_steps: int = 1000
):
    """
    Setup learning rate scheduler
    
    Args:
        optimizer: Optimizer instance
        scheduler_type: Type of scheduler (constant, linear, cosine)
        num_warmup_steps: Number of warmup steps
        num_training_steps: Total training steps
    
    Returns:
        Scheduler instance
    """
    if scheduler_type == "constant":
        scheduler = ConstantLR(optimizer, factor=1.0)
    
    elif scheduler_type == "linear":
        if num_warmup_steps > 0:
            warmup_scheduler = LinearLR(
                optimizer,
                start_factor=0.1,
                end_factor=1.0,
                total_iters=num_warmup_steps
            )
            main_scheduler = LinearLR(
                optimizer,
                start_factor=1.0,
                end_factor=0.0,
                total_iters=num_training_steps - num_warmup_steps
            )
            scheduler = SequentialLR(
                optimizer,
                schedulers=[warmup_scheduler, main_scheduler],
                milestones=[num_warmup_steps]
            )
        else:
            scheduler = LinearLR(
                optimizer,
                start_factor=1.0,
                end_factor=0.0,
                total_iters=num_training_steps
            )
    
    elif scheduler_type == "cosine":
        if num_warmup_steps > 0:
            warmup_scheduler = LinearLR(
                optimizer,
                start_factor=0.1,
                end_factor=1.0,
                total_iters=num_warmup_steps
            )
            main_scheduler = CosineAnnealingLR(
                optimizer,
                T_max=num_training_steps - num_warmup_steps,
                eta_min=0
            )
            scheduler = SequentialLR(
                optimizer,
                schedulers=[warmup_scheduler, main_scheduler],
                milestones=[num_warmup_steps]
            )
        else:
            scheduler = CosineAnnealingLR(
                optimizer,
                T_max=num_training_steps,
                eta_min=0
            )
    
    else:
        raise ValueError(f"Unsupported scheduler: {scheduler_type}")
    
    return scheduler


def compute_snr(timesteps, noise_scheduler):
    """
    Compute SNR (Signal-to-Noise Ratio) for Min-SNR weighting
    
    Args:
        timesteps: Current timesteps
        noise_scheduler: Noise scheduler
    
    Returns:
        SNR values
    """
    alphas_cumprod = noise_scheduler.alphas_cumprod
    sqrt_alphas_cumprod = alphas_cumprod**0.5
    sqrt_one_minus_alphas_cumprod = (1.0 - alphas_cumprod) ** 0.5
    
    # Expand dimensions
    sqrt_alphas_cumprod = sqrt_alphas_cumprod.to(device=timesteps.device)[timesteps].float()
    while len(sqrt_alphas_cumprod.shape) < len(timesteps.shape):
        sqrt_alphas_cumprod = sqrt_alphas_cumprod[..., None]
    
    sqrt_one_minus_alphas_cumprod = sqrt_one_minus_alphas_cumprod.to(device=timesteps.device)[timesteps].float()
    while len(sqrt_one_minus_alphas_cumprod.shape) < len(timesteps.shape):
        sqrt_one_minus_alphas_cumprod = sqrt_one_minus_alphas_cumprod[..., None]
    
    alpha = sqrt_alphas_cumprod
    sigma = sqrt_one_minus_alphas_cumprod
    snr = (alpha / sigma) ** 2
    
    return snr


def train_one_epoch(
    model,
    vae,
    text_encoder,
    tokenizer,
    lora_layers,
    dataloader,
    optimizer,
    lr_scheduler,
    device,
    epoch,
    logger,
    gradient_accumulation_steps=1,
    max_grad_norm=1.0,
    logging_steps=10,
    global_step=0,
    noise_offset=0.0,
    snr_gamma=None
):
    """
    Train for one epoch
    
    Args:
        model: Model container
        vae: VAE model
        text_encoder: Text encoder
        tokenizer: Tokenizer
        lora_layers: LoRA layers
        dataloader: Training dataloader
        optimizer: Optimizer
        lr_scheduler: Learning rate scheduler
        device: Device
        epoch: Current epoch
        logger: Logger
        gradient_accumulation_steps: Gradient accumulation steps
        max_grad_norm: Max gradient norm for clipping
        logging_steps: Log every N steps
        global_step: Global step counter
        noise_offset: Noise offset value
        snr_gamma: SNR gamma for Min-SNR weighting
    
    Returns:
        Average loss for the epoch
    """
    from diffusers import DDPMScheduler
    
    model.unet.train()
    lora_layers.train()
    
    # Setup noise scheduler
    noise_scheduler = DDPMScheduler.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        subfolder="scheduler"
    )
    
    total_loss = 0
    step_count = 0
    
    progress_bar = tqdm(dataloader, desc=f"Epoch {epoch}")
    
    for step, batch in enumerate(progress_bar):
        # Move to device
        pixel_values = batch["pixel_values"].to(device)
        
        # Encode text
        captions = batch["captions"]
        text_inputs = tokenizer(
            captions,
            padding="max_length",
            max_length=tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt"
        )
        text_input_ids = text_inputs.input_ids.to(device)
        
        # Get text embeddings
        with torch.no_grad():
            encoder_hidden_states = text_encoder(text_input_ids)[0]
        
        # Encode images to latent space
        with torch.no_grad():
            latents = vae.encode(pixel_values).latent_dist.sample()
            latents = latents * vae.config.scaling_factor
        
        # Sample noise
        noise = torch.randn_like(latents)
        if noise_offset > 0:
            noise += noise_offset * torch.randn(
                (latents.shape[0], latents.shape[1], 1, 1),
                device=latents.device
            )
        
        # Sample timesteps
        bsz = latents.shape[0]
        timesteps = torch.randint(
            0,
            noise_scheduler.config.num_train_timesteps,
            (bsz,),
            device=latents.device
        ).long()
        
        # Add noise to latents
        noisy_latents = noise_scheduler.add_noise(latents, noise, timesteps)
        
        # Predict noise
        model_pred = model.unet(
            noisy_latents,
            timesteps,
            encoder_hidden_states
        ).sample
        
        # Compute loss
        if noise_scheduler.config.prediction_type == "epsilon":
            target = noise
        elif noise_scheduler.config.prediction_type == "v_prediction":
            target = noise_scheduler.get_velocity(latents, noise, timesteps)
        else:
            raise ValueError(f"Unknown prediction type: {noise_scheduler.config.prediction_type}")
        
        loss = F.mse_loss(model_pred.float(), target.float(), reduction="none")
        loss = loss.mean([1, 2, 3])
        
        # Apply Min-SNR weighting if enabled
        if snr_gamma is not None:
            snr = compute_snr(timesteps, noise_scheduler)
            mse_loss_weights = (
                torch.stack([snr, snr_gamma * torch.ones_like(timesteps)], dim=1).min(dim=1)[0] / snr
            )
            loss = loss * mse_loss_weights
        
        loss = loss.mean()
        
        # Backward pass
        loss = loss / gradient_accumulation_steps
        loss.backward()
        
        # Update weights
        if (step + 1) % gradient_accumulation_steps == 0:
            # Gradient clipping
            if max_grad_norm > 0:
                torch.nn.utils.clip_grad_norm_(lora_layers.parameters(), max_grad_norm)
            
            optimizer.step()
            lr_scheduler.step()
            optimizer.zero_grad()
        
        # Logging
        total_loss += loss.item() * gradient_accumulation_steps
        step_count += 1
        
        current_lr = optimizer.param_groups[0]['lr']
        
        if step % logging_steps == 0:
            avg_loss = total_loss / step_count
            progress_bar.set_postfix({
                'loss': f'{loss.item() * gradient_accumulation_steps:.4f}',
                'avg_loss': f'{avg_loss:.4f}',
                'lr': f'{current_lr:.2e}'
            })
    
    avg_loss = total_loss / step_count
    return avg_loss


def validate_model(
    model,
    vae,
    text_encoder,
    tokenizer,
    dataloader,
    device,
    logger
):
    """
    Validate model
    
    Args:
        model: Model container
        vae: VAE model
        text_encoder: Text encoder
        tokenizer: Tokenizer
        dataloader: Validation dataloader
        device: Device
        logger: Logger
    
    Returns:
        Average validation loss
    """
    from diffusers import DDPMScheduler
    
    model.unet.eval()
    
    noise_scheduler = DDPMScheduler.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        subfolder="scheduler"
    )
    
    total_loss = 0
    step_count = 0
    
    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Validation"):
            pixel_values = batch["pixel_values"].to(device)
            captions = batch["captions"]
            
            # Encode text
            text_inputs = tokenizer(
                captions,
                padding="max_length",
                max_length=tokenizer.model_max_length,
                truncation=True,
                return_tensors="pt"
            )
            text_input_ids = text_inputs.input_ids.to(device)
            encoder_hidden_states = text_encoder(text_input_ids)[0]
            
            # Encode images
            latents = vae.encode(pixel_values).latent_dist.sample()
            latents = latents * vae.config.scaling_factor
            
            # Sample noise
            noise = torch.randn_like(latents)
            bsz = latents.shape[0]
            timesteps = torch.randint(
                0,
                noise_scheduler.config.num_train_timesteps,
                (bsz,),
                device=latents.device
            ).long()
            
            # Add noise
            noisy_latents = noise_scheduler.add_noise(latents, noise, timesteps)
            
            # Predict
            model_pred = model.unet(noisy_latents, timesteps, encoder_hidden_states).sample
            
            # Compute loss
            target = noise
            loss = F.mse_loss(model_pred.float(), target.float())
            
            total_loss += loss.item()
            step_count += 1
    
    avg_loss = total_loss / step_count
    logger.info(f"Validation Loss: {avg_loss:.4f}")
    
    return avg_loss


def save_checkpoint(
    checkpoint_path: str,
    epoch: int,
    global_step: int,
    lora_state_dict: Dict,
    optimizer_state_dict: Dict,
    lr_scheduler_state_dict: Dict,
    loss: float,
    config: Dict
):
    """
    Save training checkpoint
    
    Args:
        checkpoint_path: Path to save checkpoint
        epoch: Current epoch
        global_step: Global step
        lora_state_dict: LoRA state dict
        optimizer_state_dict: Optimizer state dict
        lr_scheduler_state_dict: Scheduler state dict
        loss: Current loss
        config: Training config
    """
    checkpoint = {
        'epoch': epoch,
        'global_step': global_step,
        'lora_state_dict': lora_state_dict,
        'optimizer_state_dict': optimizer_state_dict,
        'lr_scheduler_state_dict': lr_scheduler_state_dict,
        'loss': loss,
        'config': config
    }
    
    torch.save(checkpoint, checkpoint_path)


def load_checkpoint(
    checkpoint_path: str,
    lora_layers,
    optimizer,
    lr_scheduler,
    device
):
    """
    Load training checkpoint
    
    Args:
        checkpoint_path: Path to checkpoint
        lora_layers: LoRA layers
        optimizer: Optimizer
        lr_scheduler: Scheduler
        device: Device
    
    Returns:
        Tuple of (epoch, global_step, loss)
    """
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    lora_layers.load_state_dict(checkpoint['lora_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    lr_scheduler.load_state_dict(checkpoint['lr_scheduler_state_dict'])
    
    return checkpoint['epoch'], checkpoint['global_step'], checkpoint['loss']
