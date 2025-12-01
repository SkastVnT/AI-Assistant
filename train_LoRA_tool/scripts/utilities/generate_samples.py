"""
Sample Generation Script
Generate test images from trained LoRA models to evaluate quality and consistency.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.model_utils import load_lora_weights


class SampleGenerator:
    """Generator class for creating test images from LoRA models."""
    
    def __init__(
        self,
        base_model: str = "runwayml/stable-diffusion-v1-5",
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        """
        Initialize the sample generator.
        
        Args:
            base_model: Base Stable Diffusion model to use
            device: Device to run inference on
        """
        self.device = device
        self.base_model = base_model
        self.pipeline = None
        self.lora_loaded = False
        
        print(f"Using device: {self.device}")
    
    def load_lora(self, lora_path: str, lora_scale: float = 1.0):
        """
        Load a LoRA model into the pipeline.
        
        Args:
            lora_path: Path to the LoRA model file
            lora_scale: Scaling factor for LoRA weights (0.0-1.0)
        """
        print(f"Loading base model: {self.base_model}")
        
        # Load base pipeline
        self.pipeline = StableDiffusionPipeline.from_pretrained(
            self.base_model,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            safety_checker=None,
        ).to(self.device)
        
        # Use faster scheduler
        self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipeline.scheduler.config
        )
        
        # Load LoRA weights
        print(f"Loading LoRA: {lora_path}")
        lora_state_dict = load_lora_weights(lora_path)
        
        # Apply LoRA to pipeline
        self._apply_lora_to_pipeline(lora_state_dict, lora_scale)
        
        self.lora_loaded = True
        print("LoRA loaded successfully!")
    
    def _apply_lora_to_pipeline(self, lora_state_dict: dict, lora_scale: float):
        """Apply LoRA weights to the pipeline."""
        # This is a simplified version - in practice, you'd properly merge LoRA weights
        # with the base model weights based on the lora_scale
        
        unet_lora = {k: v for k, v in lora_state_dict.items() if 'text_encoder' not in k}
        text_encoder_lora = {k.replace('text_encoder.', ''): v 
                             for k, v in lora_state_dict.items() if 'text_encoder' in k}
        
        # Load into UNet
        if unet_lora:
            self.pipeline.unet.load_state_dict(unet_lora, strict=False)
        
        # Load into text encoder if present
        if text_encoder_lora:
            self.pipeline.text_encoder.load_state_dict(text_encoder_lora, strict=False)
    
    def generate_samples(
        self,
        prompts: List[str],
        negative_prompt: str = "blurry, low quality, distorted, ugly",
        num_images: int = 4,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 50,
        height: int = 512,
        width: int = 512,
        seed: Optional[int] = None,
    ) -> List[Image.Image]:
        """
        Generate sample images from prompts.
        
        Args:
            prompts: List of text prompts
            negative_prompt: Negative prompt to avoid
            num_images: Number of images per prompt
            guidance_scale: Classifier-free guidance scale
            num_inference_steps: Number of denoising steps
            height: Image height
            width: Image width
            seed: Random seed for reproducibility
            
        Returns:
            List of generated PIL Images
        """
        if not self.lora_loaded:
            raise RuntimeError("LoRA model not loaded. Call load_lora() first.")
        
        all_images = []
        
        for prompt in prompts:
            print(f"\nGenerating images for: '{prompt}'")
            
            for i in range(num_images):
                # Set seed for reproducibility
                generator = torch.Generator(device=self.device)
                if seed is not None:
                    generator.manual_seed(seed + i)
                
                # Generate image
                with torch.autocast(self.device):
                    output = self.pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale,
                        height=height,
                        width=width,
                        generator=generator,
                    )
                
                image = output.images[0]
                all_images.append(image)
                
                print(f"  Generated image {i + 1}/{num_images}")
        
        return all_images
    
    def generate_comparison_grid(
        self,
        prompt: str,
        lora_scales: List[float] = [0.0, 0.5, 0.75, 1.0],
        **kwargs
    ) -> Image.Image:
        """
        Generate a comparison grid showing different LoRA scales.
        
        Args:
            prompt: Text prompt
            lora_scales: List of LoRA scales to compare
            **kwargs: Additional arguments for generate_samples
            
        Returns:
            PIL Image grid
        """
        images = []
        
        for scale in lora_scales:
            # Reload with different scale
            # In practice, you'd adjust the LoRA scale without full reload
            print(f"\nGenerating with LoRA scale: {scale}")
            
            with torch.autocast(self.device):
                output = self.pipeline(
                    prompt=prompt,
                    **kwargs
                )
            
            image = output.images[0]
            images.append(image)
        
        # Create grid
        grid = self._create_image_grid(images, cols=len(lora_scales))
        return grid
    
    @staticmethod
    def _create_image_grid(images: List[Image.Image], cols: int = 4) -> Image.Image:
        """Create a grid from list of images."""
        rows = (len(images) + cols - 1) // cols
        w, h = images[0].size
        grid = Image.new('RGB', size=(cols * w, rows * h))
        
        for i, img in enumerate(images):
            grid.paste(img, box=((i % cols) * w, (i // cols) * h))
        
        return grid
    
    def save_images(
        self,
        images: List[Image.Image],
        output_dir: str,
        prefix: str = "sample",
    ):
        """
        Save generated images to directory.
        
        Args:
            images: List of PIL Images
            output_dir: Output directory path
            prefix: Filename prefix
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for i, img in enumerate(images):
            filename = output_path / f"{prefix}_{i:04d}.png"
            img.save(filename)
            print(f"Saved: {filename}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate samples from LoRA model")
    
    parser.add_argument(
        "--lora_path",
        type=str,
        required=True,
        help="Path to LoRA model file (.safetensors or .pt)"
    )
    parser.add_argument(
        "--base_model",
        type=str,
        default="runwayml/stable-diffusion-v1-5",
        help="Base Stable Diffusion model"
    )
    parser.add_argument(
        "--prompts",
        nargs="+",
        help="Text prompts for generation"
    )
    parser.add_argument(
        "--prompts_file",
        type=str,
        help="File containing prompts (one per line)"
    )
    parser.add_argument(
        "--negative_prompt",
        type=str,
        default="blurry, low quality, distorted, ugly",
        help="Negative prompt"
    )
    parser.add_argument(
        "--num_images",
        type=int,
        default=4,
        help="Number of images per prompt"
    )
    parser.add_argument(
        "--guidance_scale",
        type=float,
        default=7.5,
        help="Classifier-free guidance scale"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=50,
        help="Number of inference steps"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=512,
        help="Image height"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=512,
        help="Image width"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--lora_scale",
        type=float,
        default=1.0,
        help="LoRA scaling factor (0.0-1.0)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="outputs/generated",
        help="Output directory for generated images"
    )
    parser.add_argument(
        "--comparison_grid",
        action="store_true",
        help="Generate comparison grid with different LoRA scales"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Prepare prompts
    prompts = []
    if args.prompts:
        prompts.extend(args.prompts)
    
    if args.prompts_file:
        with open(args.prompts_file, 'r', encoding='utf-8') as f:
            prompts.extend([line.strip() for line in f if line.strip()])
    
    if not prompts:
        print("Error: No prompts provided. Use --prompts or --prompts_file")
        return
    
    # Initialize generator
    generator = SampleGenerator(base_model=args.base_model)
    
    # Load LoRA
    generator.load_lora(args.lora_path, lora_scale=args.lora_scale)
    
    # Generate samples
    if args.comparison_grid:
        print("\nGenerating comparison grid...")
        grid = generator.generate_comparison_grid(
            prompt=prompts[0],
            lora_scales=[0.0, 0.5, 0.75, 1.0],
            negative_prompt=args.negative_prompt,
            num_inference_steps=args.steps,
            height=args.height,
            width=args.width,
            guidance_scale=args.guidance_scale,
        )
        
        output_path = Path(args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        grid_path = output_path / "comparison_grid.png"
        grid.save(grid_path)
        print(f"\nComparison grid saved: {grid_path}")
    
    else:
        print(f"\nGenerating samples for {len(prompts)} prompts...")
        images = generator.generate_samples(
            prompts=prompts,
            negative_prompt=args.negative_prompt,
            num_images=args.num_images,
            guidance_scale=args.guidance_scale,
            num_inference_steps=args.steps,
            height=args.height,
            width=args.width,
            seed=args.seed,
        )
        
        # Save images
        generator.save_images(images, args.output_dir, prefix="sample")
        print(f"\nGenerated {len(images)} images saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
