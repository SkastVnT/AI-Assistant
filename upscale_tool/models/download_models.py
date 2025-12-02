"""
Script to download pretrained models
"""
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from upscale_tool.config import UpscaleConfig
from upscale_tool.utils import download_file


def download_models(models_to_download=None):
    """
    Download pretrained models
    
    Args:
        models_to_download: List of model names, or None to download all
    """
    config = UpscaleConfig()
    model_dir = Path(config.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    if models_to_download is None:
        models_to_download = list(config.model_urls.keys())
    
    print(f"Downloading {len(models_to_download)} models to {model_dir}")
    print(f"Models: {', '.join(models_to_download)}\n")
    
    for model_name in models_to_download:
        if model_name not in config.model_urls:
            print(f"Warning: Unknown model '{model_name}', skipping")
            continue
        
        url = config.model_urls[model_name]
        output_path = model_dir / f"{model_name}.pth"
        
        if output_path.exists():
            print(f"✓ {model_name} already downloaded")
            continue
        
        try:
            print(f"\n📥 Downloading {model_name}...")
            download_file(url, str(output_path))
            print(f"✓ {model_name} downloaded successfully")
        except Exception as e:
            print(f"✗ Failed to download {model_name}: {e}")
    
    print("\n✨ Download complete!")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Download pretrained models')
    parser.add_argument(
        '--models',
        nargs='+',
        help='Specific models to download (default: all)'
    )
    parser.add_argument(
        '--model-dir',
        default='./models',
        help='Directory to save models'
    )
    
    args = parser.parse_args()
    
    # Update config if model_dir specified
    if args.model_dir != './models':
        config = UpscaleConfig()
        config.model_dir = args.model_dir
    
    download_models(args.models)
