"""
Model utilities for loading and saving LoRA models
"""

import torch
import safetensors
from pathlib import Path
from typing import Dict, Optional, Tuple
from safetensors.torch import save_file, load_file


def load_pretrained_model(
    model_name: str,
    revision: Optional[str] = None,
    device: torch.device = torch.device("cuda")
) -> Tuple:
    """
    Load pretrained Stable Diffusion model
    
    Args:
        model_name: HuggingFace model name or path
        revision: Model revision
        device: Device to load model on
    
    Returns:
        Tuple of (pipeline, vae, text_encoder, tokenizer)
    """
    from diffusers import StableDiffusionPipeline, AutoencoderKL
    from transformers import CLIPTextModel, CLIPTokenizer
    
    print(f"Loading model: {model_name}")
    
    # Load pipeline
    pipeline = StableDiffusionPipeline.from_pretrained(
        model_name,
        revision=revision,
        torch_dtype=torch.float16 if device.type == "cuda" else torch.float32,
        safety_checker=None,
        requires_safety_checker=False
    )
    
    # Extract components
    vae = pipeline.vae
    text_encoder = pipeline.text_encoder
    tokenizer = pipeline.tokenizer
    unet = pipeline.unet
    
    # Create a simple container for the model
    class ModelContainer:
        def __init__(self, unet, vae, text_encoder):
            self.unet = unet
            self.vae = vae
            self.text_encoder = text_encoder
        
        def to(self, device):
            self.unet.to(device)
            self.vae.to(device)
            self.text_encoder.to(device)
            return self
    
    model = ModelContainer(unet, vae, text_encoder)
    
    print("Model loaded successfully!")
    
    return model, vae, text_encoder, tokenizer


def save_lora_weights(
    lora_layers,
    save_path: str,
    metadata: Optional[Dict] = None
):
    """
    Save LoRA weights to safetensors format
    
    Args:
        lora_layers: LoRA layer module
        save_path: Path to save weights
        metadata: Optional metadata to include
    """
    # Get state dict
    state_dict = lora_layers.state_dict()
    
    # Convert to CPU and float32 for compatibility
    state_dict = {k: v.cpu().float() for k, v in state_dict.items()}
    
    # Add metadata
    if metadata is None:
        metadata = {}
    
    # Convert metadata values to strings
    metadata_str = {k: str(v) for k, v in metadata.items()}
    
    # Save as safetensors
    save_file(state_dict, save_path, metadata=metadata_str)
    
    print(f"LoRA weights saved to: {save_path}")


def load_lora_weights(
    lora_layers,
    load_path: str,
    device: torch.device = torch.device("cuda")
):
    """
    Load LoRA weights from safetensors format
    
    Args:
        lora_layers: LoRA layer module
        load_path: Path to load weights from
        device: Device to load on
    """
    # Load state dict
    state_dict = load_file(load_path, device=str(device))
    
    # Load into model
    lora_layers.load_state_dict(state_dict)
    
    print(f"LoRA weights loaded from: {load_path}")
