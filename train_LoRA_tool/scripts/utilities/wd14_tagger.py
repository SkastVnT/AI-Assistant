"""
WD14 Tagger - Local NSFW-safe image tagging
Runs 100% offline, no internet upload, complete privacy
Specialized for anime/manga artwork including NSFW content
"""

import os
import argparse
from pathlib import Path
from PIL import Image
import numpy as np
import csv

try:
    from huggingface_hub import hf_hub_download
    import onnxruntime as rt
except ImportError:
    print("ERROR: Required packages not installed!")
    print("Please run: pip install onnxruntime huggingface-hub")
    exit(1)


# Available WD14 models
MODELS = {
    'swinv2': 'SmilingWolf/wd-swinv2-tagger-v3',      # Best accuracy
    'convnext': 'SmilingWolf/wd-convnext-tagger-v3',  # Balanced
    'vit': 'SmilingWolf/wd-vit-tagger-v3'             # Fastest
}

# Tag categories
RATING_TAGS = ['rating:general', 'rating:sensitive', 'rating:questionable', 'rating:explicit']
GENERAL_TAGS_START = 9  # First 9 are usually rating/quality tags


def load_model(model_name='swinv2'):
    """
    Load WD14 ONNX model and tags CSV.
    Model files are downloaded once and cached locally.
    """
    print(f"\n📥 Loading WD14 model: {model_name}")
    model_repo = MODELS.get(model_name, MODELS['swinv2'])
    
    try:
        # Download model files (cached after first download)
        print("   Downloading model file...")
        model_path = hf_hub_download(model_repo, "model.onnx")
        
        print("   Downloading tags file...")
        tags_path = hf_hub_download(model_repo, "selected_tags.csv")
        
        # Load ONNX model
        print("   Initializing model...")
        model = rt.InferenceSession(model_path)
        
        # Load tags CSV
        print("   Loading tags...")
        with open(tags_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            tags = [row for row in reader]
        
        print(f"✓ Model loaded: {len(tags)} tags available\n")
        return model, tags
        
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        print("\nTroubleshooting:")
        print("1. Check internet connection (needed for first download)")
        print("2. Run: pip install --upgrade huggingface-hub onnxruntime")
        print("3. Clear cache: rm -rf ~/.cache/huggingface/")
        exit(1)


def preprocess_image(image_path, target_size=448):
    """
    Preprocess image for WD14 model.
    Handles various formats and sizes.
    """
    try:
        # Load image
        img = Image.open(image_path)
        
        # Convert to RGB (handle PNG with alpha, grayscale, etc.)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Pad to square
        width, height = img.size
        max_dim = max(width, height)
        
        # Create square canvas
        square_img = Image.new('RGB', (max_dim, max_dim), (255, 255, 255))
        
        # Paste image centered
        offset = ((max_dim - width) // 2, (max_dim - height) // 2)
        square_img.paste(img, offset)
        
        # Resize to target size
        square_img = square_img.resize((target_size, target_size), Image.LANCZOS)
        
        # Convert to numpy array and normalize
        img_array = np.array(square_img).astype(np.float32) / 255.0
        img_array = np.expand_dims(img_array, 0)  # Add batch dimension
        
        return img_array
        
    except Exception as e:
        print(f"   ✗ Error preprocessing image: {e}")
        return None


def predict_tags(model, tags, image_path, threshold=0.35, add_rating=True):
    """
    Predict tags for a single image.
    Returns sorted list of (tag, confidence) tuples.
    """
    # Preprocess image
    img_array = preprocess_image(image_path)
    if img_array is None:
        return []
    
    try:
        # Run inference
        input_name = model.get_inputs()[0].name
        outputs = model.run(None, {input_name: img_array})
        predictions = outputs[0][0]
        
        # Collect tags above threshold
        result_tags = []
        
        for i, score in enumerate(predictions):
            if score >= threshold:
                tag_info = tags[i]
                tag_name = tag_info['name']
                tag_category = tag_info.get('category', '0')
                
                # Format tag name (replace underscores with spaces)
                formatted_tag = tag_name.replace('_', ' ')
                
                result_tags.append({
                    'name': formatted_tag,
                    'score': float(score),
                    'category': tag_category
                })
        
        # Sort by confidence (highest first)
        result_tags.sort(key=lambda x: x['score'], reverse=True)
        
        return result_tags
        
    except Exception as e:
        print(f"   ✗ Error during prediction: {e}")
        return []


def format_tags(tag_results, format_style='danbooru', include_scores=False):
    """
    Format tags for output.
    
    Styles:
    - danbooru: tag1, tag2, tag3
    - weighted: (tag1:1.2), (tag2:0.9), tag3
    - line_by_line: one tag per line
    """
    if format_style == 'danbooru':
        # Standard comma-separated
        tags_str = ', '.join([tag['name'] for tag in tag_results])
        
    elif format_style == 'weighted':
        # Include confidence as weights
        weighted_tags = []
        for tag in tag_results:
            if tag['score'] > 0.8:
                weighted_tags.append(f"({tag['name']}:{tag['score']:.1f})")
            else:
                weighted_tags.append(tag['name'])
        tags_str = ', '.join(weighted_tags)
        
    elif format_style == 'line_by_line':
        # One tag per line
        tags_str = '\n'.join([tag['name'] for tag in tag_results])
        
    else:
        # Default
        tags_str = ', '.join([tag['name'] for tag in tag_results])
    
    # Optionally append scores as comment
    if include_scores and format_style != 'line_by_line':
        tags_str += '\n\n# Tag scores:\n'
        for tag in tag_results[:10]:  # Top 10
            tags_str += f"# {tag['name']}: {tag['score']:.3f}\n"
    
    return tags_str


def process_directory(input_dir, model, tags, args):
    """
    Process all images in directory.
    """
    input_path = Path(input_dir)
    
    # Supported image formats
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}
    
    # Find all images
    image_files = [
        f for f in input_path.iterdir()
        if f.suffix.lower() in image_extensions
    ]
    
    if not image_files:
        print(f"✗ No images found in {input_dir}")
        return
    
    print(f"📁 Found {len(image_files)} images to process\n")
    
    # Process each image
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for i, img_path in enumerate(image_files, 1):
        # Check if caption already exists
        txt_path = img_path.with_suffix('.txt')
        
        if txt_path.exists() and not args.overwrite:
            print(f"[{i}/{len(image_files)}] ⏭️  Skipping {img_path.name} (caption exists)")
            skip_count += 1
            continue
        
        print(f"[{i}/{len(image_files)}] 🔍 Processing {img_path.name}...")
        
        # Predict tags
        tag_results = predict_tags(model, tags, str(img_path), args.threshold)
        
        if not tag_results:
            print(f"   ✗ No tags found or error occurred")
            error_count += 1
            continue
        
        # Add custom prefix/suffix if specified
        final_tags = tag_results.copy()
        
        if args.prefix:
            # Add prefix tags at the beginning
            prefix_parts = [p.strip() for p in args.prefix.split(',')]
            for prefix_tag in reversed(prefix_parts):
                final_tags.insert(0, {'name': prefix_tag, 'score': 1.0, 'category': '9'})
        
        if args.suffix:
            # Add suffix tags at the end
            suffix_parts = [s.strip() for s in args.suffix.split(',')]
            for suffix_tag in suffix_parts:
                final_tags.append({'name': suffix_tag, 'score': 1.0, 'category': '9'})
        
        # Format tags
        tags_text = format_tags(final_tags, args.format, args.include_scores)
        
        # Save to .txt file
        try:
            txt_path.write_text(tags_text, encoding='utf-8')
            print(f"   ✓ Saved {len(tag_results)} tags (confidence ≥ {args.threshold})")
            success_count += 1
            
            # Show top tags
            if args.verbose:
                top_tags = [f"{t['name']} ({t['score']:.2f})" for t in tag_results[:5]]
                print(f"   📝 Top tags: {', '.join(top_tags)}")
            
        except Exception as e:
            print(f"   ✗ Error saving caption: {e}")
            error_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Processing Summary:")
    print(f"   ✓ Success: {success_count}")
    print(f"   ⏭️  Skipped: {skip_count}")
    print(f"   ✗ Errors:  {error_count}")
    print(f"   📁 Total:   {len(image_files)}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='WD14 Tagger - Local NSFW-safe anime image tagging',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python wd14_tagger.py --input data/train
  
  # Higher threshold for quality tags only
  python wd14_tagger.py --input data/train --threshold 0.5
  
  # Add custom prefix tags
  python wd14_tagger.py --input data/train --prefix "masterpiece, best quality"
  
  # Use different model
  python wd14_tagger.py --input data/train --model vit
  
  # Include confidence scores
  python wd14_tagger.py --input data/train --include-scores --verbose
        """
    )
    
    # Required arguments
    parser.add_argument('--input', '-i', required=True,
                       help='Input directory containing images')
    
    # Model selection
    parser.add_argument('--model', choices=['swinv2', 'convnext', 'vit'],
                       default='swinv2',
                       help='WD14 model to use (default: swinv2 - best accuracy)')
    
    # Threshold
    parser.add_argument('--threshold', '-t', type=float, default=0.35,
                       help='Confidence threshold (0.0-1.0, default: 0.35)')
    
    # Custom tags
    parser.add_argument('--prefix', type=str,
                       help='Comma-separated tags to add at beginning')
    parser.add_argument('--suffix', type=str,
                       help='Comma-separated tags to add at end')
    
    # Output format
    parser.add_argument('--format', choices=['danbooru', 'weighted', 'line_by_line'],
                       default='danbooru',
                       help='Output format (default: danbooru)')
    
    # Options
    parser.add_argument('--overwrite', action='store_true',
                       help='Overwrite existing caption files')
    parser.add_argument('--include-scores', action='store_true',
                       help='Include confidence scores in output')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed output')
    
    args = parser.parse_args()
    
    # Validate input directory
    if not Path(args.input).exists():
        print(f"✗ Error: Directory not found: {args.input}")
        exit(1)
    
    # Load model
    model, tags = load_model(args.model)
    
    # Process directory
    process_directory(args.input, model, tags, args)
    
    print("✅ Done! Your dataset is ready for training.")
    print(f"📁 Captions saved in: {args.input}")
    print("\nNext steps:")
    print("1. Review generated tags (optional)")
    print("2. Configure training: configs/loraplus_config.yaml")
    print("3. Start training: python scripts/training/train_lora.py")


if __name__ == '__main__':
    main()
