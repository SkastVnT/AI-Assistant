"""
CLI interface for upscale tool
"""
import argparse
import sys
from pathlib import Path

from .upscaler import ImageUpscaler, upscale
from .config import load_config


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Image Upscaling Tool - Upscale images from low to high resolution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upscale single image
  upscale-tool upscale -i input.jpg -o output.png --scale 4
  
  # Upscale folder
  upscale-tool upscale-folder -i ./inputs -o ./outputs --scale 2
  
  # Use specific model
  upscale-tool upscale -i anime.jpg -o result.png -m RealESRGAN_x4plus_anime_6B
  
  # Use config file
  upscale-tool upscale -i input.jpg --config config.yaml
  
  # List available models
  upscale-tool list-models
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Upscale single image command
    upscale_parser = subparsers.add_parser('upscale', help='Upscale single image')
    upscale_parser.add_argument('-i', '--input', required=True, help='Input image path')
    upscale_parser.add_argument('-o', '--output', help='Output image path')
    upscale_parser.add_argument('-m', '--model', default='RealESRGAN_x4plus',
                               help='Model name (default: RealESRGAN_x4plus)')
    upscale_parser.add_argument('-s', '--scale', type=int, default=4,
                               help='Upscale ratio (default: 4)')
    upscale_parser.add_argument('-d', '--device', default='cuda',
                               help='Device to use: cuda or cpu (default: cuda)')
    upscale_parser.add_argument('--tile-size', type=int, default=400,
                               help='Tile size for large images (default: 400)')
    upscale_parser.add_argument('--half-precision', action='store_true',
                               help='Use fp16 for faster processing')
    upscale_parser.add_argument('--config', help='Path to config file')
    
    # Upscale folder command
    folder_parser = subparsers.add_parser('upscale-folder', help='Upscale all images in folder')
    folder_parser.add_argument('-i', '--input', required=True, help='Input folder path')
    folder_parser.add_argument('-o', '--output', help='Output folder path')
    folder_parser.add_argument('-m', '--model', default='RealESRGAN_x4plus',
                              help='Model name')
    folder_parser.add_argument('-s', '--scale', type=int, default=4,
                              help='Upscale ratio')
    folder_parser.add_argument('-d', '--device', default='cuda',
                              help='Device to use')
    folder_parser.add_argument('--tile-size', type=int, default=400,
                              help='Tile size')
    folder_parser.add_argument('--half-precision', action='store_true',
                              help='Use fp16')
    folder_parser.add_argument('--config', help='Path to config file')
    
    # List models command
    list_parser = subparsers.add_parser('list-models', help='List available models')
    
    # Download models command
    download_parser = subparsers.add_parser('download-models', help='Download pretrained models')
    download_parser.add_argument('--models', nargs='+', help='Specific models to download')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    # Handle commands
    if args.command == 'list-models':
        print("Available Models:")
        print("-" * 80)
        models = ImageUpscaler.list_models()
        for name, desc in models.items():
            print(f"{name:35s} - {desc}")
        sys.exit(0)
    
    elif args.command == 'download-models':
        from .utils import download_file
        from .config import UpscaleConfig
        
        config = UpscaleConfig()
        models_to_download = args.models or list(config.model_urls.keys())
        
        print(f"Downloading {len(models_to_download)} model(s)...")
        for model_name in models_to_download:
            if model_name in config.model_urls:
                url = config.model_urls[model_name]
                output_path = Path(config.model_dir) / f"{model_name}.pth"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                print(f"\nDownloading {model_name}...")
                download_file(url, str(output_path))
            else:
                print(f"Unknown model: {model_name}")
        
        print("\nDownload complete!")
        sys.exit(0)
    
    elif args.command == 'upscale':
        # Default output to data/output/ if not specified
        output_path = args.output
        if output_path is None:
            input_path = Path(args.input)
            data_output_dir = Path('./data/output')
            data_output_dir.mkdir(parents=True, exist_ok=True)
            output_path = data_output_dir / f"{input_path.stem}_upscaled{input_path.suffix}"
        
        # Load config if provided
        if args.config:
            config = load_config(args.config)
            upscaler = ImageUpscaler.from_config(config)
        else:
            upscaler = ImageUpscaler(
                model=args.model,
                device=args.device,
                tile_size=args.tile_size,
                half_precision=args.half_precision
            )
        
        print(f"Upscaling {args.input}...")
        output_result = upscaler.upscale_image(
            input_path=args.input,
            output_path=str(output_path),
            scale=args.scale
        )
        print(f"✅ Done! Output saved to: {output_result}")
    
    elif args.command == 'upscale-folder':
        # Default output to data/output/ if not specified
        output_folder = args.output
        if output_folder is None:
            output_folder = Path('./data/output')
            output_folder.mkdir(parents=True, exist_ok=True)
        
        # Load config if provided
        if args.config:
            config = load_config(args.config)
            upscaler = ImageUpscaler.from_config(config)
        else:
            upscaler = ImageUpscaler(
                model=args.model,
                device=args.device,
                tile_size=args.tile_size,
                half_precision=args.half_precision
            )
        
        print(f"Upscaling folder {args.input}...")
        output_paths = upscaler.upscale_folder(
            input_folder=args.input,
            output_folder=str(output_folder),
            scale=args.scale
        )
        print(f"\n✅ Done! Upscaled {len(output_paths)} images")
        print(f"Output folder: {output_folder}")


if __name__ == '__main__':
    main()
