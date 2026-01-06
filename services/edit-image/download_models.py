#!/usr/bin/env python3
"""
Download All Models for Edit Image Tool
========================================

This script downloads all required models for local inference.
Local models = MUCH FASTER than HuggingFace API

Usage:
    python download_models.py --all          # Download everything
    python download_models.py --essential    # Download only essential
    python download_models.py --anime        # Download anime models
    python download_models.py --list         # List all models
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import urllib.request
import hashlib


# ============================================================================
# Configuration
# ============================================================================

MODELS_DIR = Path(__file__).parent / "models"

@dataclass
class Model:
    """Model definition"""
    name: str
    local_path: str
    source: str  # "huggingface", "direct", "civitai"
    url_or_repo: str
    size_gb: float
    category: str
    priority: int  # 1=essential, 2=recommended, 3=optional
    description: str
    filename: Optional[str] = None  # For direct downloads


# ============================================================================
# Model Registry
# ============================================================================

MODELS = [
    # === PRIORITY 1: Essential Base Models ===
    Model(
        name="SDXL 1.0 Base",
        local_path="base/sdxl-base",
        source="huggingface",
        url_or_repo="stabilityai/stable-diffusion-xl-base-1.0",
        size_gb=6.5,
        category="base",
        priority=1,
        description="Core SDXL model for high-quality generation"
    ),
    Model(
        name="InstructPix2Pix",
        local_path="base/instruct-pix2pix",
        source="huggingface",
        url_or_repo="timbrooks/instruct-pix2pix",
        size_gb=5.1,
        category="base",
        priority=1,
        description="Instruction-based image editing"
    ),
    Model(
        name="SD 1.5 Inpainting",
        local_path="base/sd15-inpainting",
        source="huggingface",
        url_or_repo="runwayml/stable-diffusion-inpainting",
        size_gb=4.3,
        category="base",
        priority=1,
        description="Inpainting model"
    ),
    
    # === PRIORITY 1: ControlNet Essential ===
    Model(
        name="ControlNet SDXL Canny",
        local_path="controlnet/sdxl-canny",
        source="huggingface",
        url_or_repo="diffusers/controlnet-canny-sdxl-1.0",
        size_gb=2.5,
        category="controlnet",
        priority=1,
        description="Edge detection control"
    ),
    Model(
        name="ControlNet SDXL Depth",
        local_path="controlnet/sdxl-depth",
        source="huggingface",
        url_or_repo="diffusers/controlnet-depth-sdxl-1.0",
        size_gb=2.5,
        category="controlnet",
        priority=1,
        description="Depth map control"
    ),
    
    # === PRIORITY 1: IP-Adapter Essential ===
    Model(
        name="IP-Adapter SDXL",
        local_path="ip-adapter/h94",
        source="huggingface",
        url_or_repo="h94/IP-Adapter",
        size_gb=0.5,
        category="ip-adapter",
        priority=1,
        description="Image prompt adapter"
    ),
    Model(
        name="IP-Adapter FaceID",
        local_path="ip-adapter/faceid",
        source="huggingface",
        url_or_repo="h94/IP-Adapter-FaceID",
        size_gb=0.5,
        category="ip-adapter",
        priority=1,
        description="Face identity adapter"
    ),
    
    # === PRIORITY 1: InstantID ===
    Model(
        name="InstantID",
        local_path="instantid/model",
        source="huggingface",
        url_or_repo="InstantX/InstantID",
        size_gb=1.5,
        category="face",
        priority=1,
        description="Zero-shot face swap"
    ),
    Model(
        name="Antelopev2 (InsightFace)",
        local_path="face/antelopev2",
        source="huggingface",
        url_or_repo="DIAMONIK7777/antelopev2",
        size_gb=0.36,
        category="face",
        priority=1,
        description="Face detection and embedding"
    ),
    
    # === PRIORITY 1: SAM for Inpaint Anything ===
    Model(
        name="SAM ViT-L",
        local_path="inpaint/sam_vit_l_0b3195.pth",
        source="direct",
        url_or_repo="https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth",
        size_gb=1.2,
        category="inpaint",
        priority=1,
        description="Segment Anything Model (balanced)"
    ),
    Model(
        name="LaMa Big",
        local_path="inpaint/big-lama.pt",
        source="direct",
        url_or_repo="https://huggingface.co/smartywu/big-lama/resolve/main/big-lama.pt",
        size_gb=0.2,
        category="inpaint",
        priority=1,
        description="LaMa inpainting model"
    ),
    
    # === PRIORITY 1: Upscaler ===
    Model(
        name="Real-ESRGAN x4plus",
        local_path="upscaler/RealESRGAN_x4plus.pth",
        source="direct",
        url_or_repo="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        size_gb=0.067,
        category="upscaler",
        priority=1,
        description="4x upscaling"
    ),
    Model(
        name="GFPGAN v1.4",
        local_path="upscaler/GFPGANv1.4.pth",
        source="direct",
        url_or_repo="https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth",
        size_gb=0.348,
        category="upscaler",
        priority=1,
        description="Face restoration"
    ),
    
    # === PRIORITY 2: Anime Models ===
    Model(
        name="Animagine XL 3.1",
        local_path="anime/animagine-xl-31",
        source="huggingface",
        url_or_repo="cagliostrolab/animagine-xl-3.1",
        size_gb=6.5,
        category="anime",
        priority=2,
        description="Best anime model for SDXL"
    ),
    Model(
        name="ControlNet Lineart Anime",
        local_path="controlnet/lineart-anime",
        source="huggingface",
        url_or_repo="lllyasviel/control_v11p_sd15_lineart_anime",
        size_gb=1.4,
        category="anime",
        priority=2,
        description="Anime line art control"
    ),
    Model(
        name="IP-Adapter Anime",
        local_path="ip-adapter/anime",
        source="huggingface",
        url_or_repo="r3gm/ip-adapter-anime",
        size_gb=0.1,
        category="anime",
        priority=2,
        description="Anime character adapter"
    ),
    Model(
        name="Real-ESRGAN Anime",
        local_path="upscaler/RealESRGAN_x4plus_anime_6B.pth",
        source="direct",
        url_or_repo="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
        size_gb=0.017,
        category="anime",
        priority=2,
        description="Anime-specific upscaler"
    ),
    
    # === PRIORITY 2: Tagger ===
    Model(
        name="WD14 ViT Tagger v2",
        local_path="tagger/wd14-vit-v2",
        source="huggingface",
        url_or_repo="SmilingWolf/wd-v1-4-vit-tagger-v2",
        size_gb=0.4,
        category="tagger",
        priority=2,
        description="Auto-tagging for anime images"
    ),
    
    # === PRIORITY 2: Additional ControlNet ===
    Model(
        name="ControlNet SD1.5 OpenPose",
        local_path="controlnet/sd15-openpose",
        source="huggingface",
        url_or_repo="lllyasviel/sd-controlnet-openpose",
        size_gb=1.4,
        category="controlnet",
        priority=2,
        description="Pose control for SD1.5"
    ),
    Model(
        name="ControlNet SD1.5 Canny",
        local_path="controlnet/sd15-canny",
        source="huggingface",
        url_or_repo="lllyasviel/sd-controlnet-canny",
        size_gb=1.4,
        category="controlnet",
        priority=2,
        description="Edge detection for SD1.5"
    ),
    
    # === PRIORITY 3: SOTA Edit Models ===
    Model(
        name="Step1X-Edit",
        local_path="edit/step1x",
        source="huggingface",
        url_or_repo="stepfun-ai/Step1X-Edit",
        size_gb=7.0,
        category="sota",
        priority=3,
        description="SOTA instruction-based editing with reasoning"
    ),
    
    # === PRIORITY 3: Additional ===
    Model(
        name="SDXL Refiner",
        local_path="base/sdxl-refiner",
        source="huggingface",
        url_or_repo="stabilityai/stable-diffusion-xl-refiner-1.0",
        size_gb=6.2,
        category="base",
        priority=3,
        description="SDXL refiner for better quality"
    ),
    Model(
        name="Waifu Diffusion 1.4",
        local_path="anime/waifu-diffusion",
        source="huggingface",
        url_or_repo="hakurei/waifu-diffusion-v1-4",
        size_gb=4.0,
        category="anime",
        priority=3,
        description="Classic anime model"
    ),
    Model(
        name="Ghibli Diffusion",
        local_path="anime/ghibli-diffusion",
        source="huggingface",
        url_or_repo="nitrosocke/Ghibli-Diffusion",
        size_gb=4.0,
        category="anime",
        priority=3,
        description="Studio Ghibli style"
    ),
    Model(
        name="SAM ViT-H (Best Quality)",
        local_path="inpaint/sam_vit_h_4b8939.pth",
        source="direct",
        url_or_repo="https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
        size_gb=2.6,
        category="inpaint",
        priority=3,
        description="Segment Anything Model (highest quality)"
    ),
    Model(
        name="SD Reference-Only",
        local_path="tools/reference-only",
        source="huggingface",
        url_or_repo="aihao2000/stable-diffusion-reference-only",
        size_gb=2.0,
        category="tools",
        priority=3,
        description="Style transfer and coloring"
    ),
]


# ============================================================================
# Download Functions
# ============================================================================

def get_hf_cli_available() -> bool:
    """Check if huggingface-cli is available"""
    try:
        result = subprocess.run(
            ["huggingface-cli", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def download_huggingface(model: Model) -> bool:
    """Download from HuggingFace Hub"""
    local_path = MODELS_DIR / model.local_path
    local_path.mkdir(parents=True, exist_ok=True)
    
    if get_hf_cli_available():
        cmd = [
            "huggingface-cli", "download",
            model.url_or_repo,
            "--local-dir", str(local_path),
            "--local-dir-use-symlinks", "False"
        ]
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        return result.returncode == 0
    else:
        # Fallback to Python API
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=model.url_or_repo,
                local_dir=str(local_path),
                local_dir_use_symlinks=False
            )
            return True
        except ImportError:
            print("  ERROR: huggingface_hub not installed. Run: pip install huggingface_hub")
            return False
        except Exception as e:
            print(f"  ERROR: {e}")
            return False


def download_direct(model: Model) -> bool:
    """Direct URL download"""
    local_path = MODELS_DIR / model.local_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    if local_path.exists():
        print(f"  Already exists: {local_path}")
        return True
    
    try:
        print(f"  Downloading from: {model.url_or_repo}")
        
        # Use urllib for progress
        def progress_hook(count, block_size, total_size):
            percent = count * block_size * 100 / total_size
            sys.stdout.write(f"\r  Progress: {percent:.1f}%")
            sys.stdout.flush()
        
        urllib.request.urlretrieve(
            model.url_or_repo,
            str(local_path),
            reporthook=progress_hook
        )
        print()  # New line after progress
        return True
    except Exception as e:
        print(f"\n  ERROR: {e}")
        # Fallback to curl/wget
        if os.name == 'nt':
            cmd = f'curl -L -o "{local_path}" "{model.url_or_repo}"'
        else:
            cmd = f'wget -O "{local_path}" "{model.url_or_repo}"'
        result = subprocess.run(cmd, shell=True)
        return result.returncode == 0


def download_model(model: Model) -> bool:
    """Download a model based on its source"""
    print(f"\n{'='*60}")
    print(f"Downloading: {model.name}")
    print(f"Size: ~{model.size_gb}GB | Category: {model.category}")
    print(f"{'='*60}")
    
    if model.source == "huggingface":
        return download_huggingface(model)
    elif model.source == "direct":
        return download_direct(model)
    else:
        print(f"  Unknown source: {model.source}")
        return False


# ============================================================================
# Main Functions
# ============================================================================

def list_models(priority: Optional[int] = None, category: Optional[str] = None):
    """List all available models"""
    print("\n" + "="*80)
    print("AVAILABLE MODELS")
    print("="*80)
    
    filtered = MODELS
    if priority:
        filtered = [m for m in filtered if m.priority == priority]
    if category:
        filtered = [m for m in filtered if m.category == category]
    
    total_size = 0
    for m in filtered:
        priority_emoji = {1: "🔴", 2: "🟡", 3: "🟢"}[m.priority]
        print(f"\n{priority_emoji} [{m.category.upper()}] {m.name}")
        print(f"   Size: {m.size_gb}GB | Priority: {m.priority}")
        print(f"   Path: models/{m.local_path}")
        print(f"   {m.description}")
        total_size += m.size_gb
    
    print("\n" + "-"*80)
    print(f"Total: {len(filtered)} models, ~{total_size:.1f}GB")
    print("-"*80)


def download_by_priority(max_priority: int):
    """Download models up to a certain priority level"""
    models_to_download = [m for m in MODELS if m.priority <= max_priority]
    
    total_size = sum(m.size_gb for m in models_to_download)
    print(f"\nWill download {len(models_to_download)} models (~{total_size:.1f}GB)")
    
    response = input("Continue? [y/N]: ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    success = 0
    failed = []
    
    for model in models_to_download:
        if download_model(model):
            success += 1
        else:
            failed.append(model.name)
    
    print("\n" + "="*60)
    print("DOWNLOAD SUMMARY")
    print("="*60)
    print(f"Success: {success}/{len(models_to_download)}")
    if failed:
        print(f"Failed: {', '.join(failed)}")


def download_category(category: str):
    """Download models of a specific category"""
    models_to_download = [m for m in MODELS if m.category == category]
    
    if not models_to_download:
        print(f"No models found for category: {category}")
        return
    
    total_size = sum(m.size_gb for m in models_to_download)
    print(f"\nWill download {len(models_to_download)} {category} models (~{total_size:.1f}GB)")
    
    response = input("Continue? [y/N]: ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    for model in models_to_download:
        download_model(model)


def main():
    parser = argparse.ArgumentParser(
        description="Download models for Edit Image Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_models.py --list              # List all models
  python download_models.py --essential         # Download priority 1 only (~25GB)
  python download_models.py --recommended       # Download priority 1+2 (~40GB)
  python download_models.py --all               # Download everything (~65GB+)
  python download_models.py --category anime    # Download anime models only
  python download_models.py --model "SDXL 1.0"  # Download specific model
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all available models")
    group.add_argument("--essential", action="store_true", help="Download essential models only (priority 1)")
    group.add_argument("--recommended", action="store_true", help="Download essential + recommended (priority 1-2)")
    group.add_argument("--all", action="store_true", help="Download all models")
    group.add_argument("--category", type=str, help="Download models of a specific category")
    group.add_argument("--model", type=str, help="Download a specific model by name")
    
    args = parser.parse_args()
    
    # Create models directory
    MODELS_DIR.mkdir(exist_ok=True)
    
    if args.list:
        list_models()
    elif args.essential:
        download_by_priority(1)
    elif args.recommended:
        download_by_priority(2)
    elif args.all:
        download_by_priority(3)
    elif args.category:
        download_category(args.category)
    elif args.model:
        matching = [m for m in MODELS if args.model.lower() in m.name.lower()]
        if not matching:
            print(f"No model found matching: {args.model}")
            return
        for model in matching:
            download_model(model)


if __name__ == "__main__":
    main()
