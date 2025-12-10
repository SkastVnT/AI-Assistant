"""
Gemini-powered dataset preparation tool for LoRA training
Auto-generate captions, analyze quality, optimize tags
"""

import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.gemini_assistant import GeminiLoRAAssistant


def main():
    parser = argparse.ArgumentParser(
        description="Gemini AI-powered dataset preparation for LoRA training"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Caption generation
    caption_parser = subparsers.add_parser('caption', help='Generate captions')
    caption_parser.add_argument('--input', '-i', required=True, help='Input directory with images')
    caption_parser.add_argument('--output', '-o', help='Output directory for captions (default: same as input)')
    caption_parser.add_argument('--style', choices=['detailed', 'concise', 'tags'], default='tags',
                               help='Caption style')
    caption_parser.add_argument('--focus', choices=['character', 'style', 'scene', 'all'], default='all',
                               help='What to focus on')
    
    # Quality analysis
    analyze_parser = subparsers.add_parser('analyze', help='Analyze dataset quality')
    analyze_parser.add_argument('--input', '-i', required=True, help='Dataset directory')
    analyze_parser.add_argument('--output', '-o', help='Output JSON file for report')
    
    # Hyperparameter recommendations
    recommend_parser = subparsers.add_parser('recommend', help='Get hyperparameter recommendations')
    recommend_parser.add_argument('--dataset', '-d', required=True, help='Dataset directory')
    recommend_parser.add_argument('--goal', choices=['character', 'style', 'concept', 'object'],
                                 default='character', help='Training goal')
    recommend_parser.add_argument('--output', '-o', help='Output config file')
    
    # Outlier detection
    outlier_parser = subparsers.add_parser('outliers', help='Detect problematic images')
    outlier_parser.add_argument('--input', '-i', required=True, help='Dataset directory')
    outlier_parser.add_argument('--remove', action='store_true', help='Remove detected outliers')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize Gemini assistant
    print("🤖 Initializing Gemini 2.0 Flash...")
    assistant = GeminiLoRAAssistant()
    
    # Execute command
    if args.command == 'caption':
        print(f"\n🎨 Generating captions for: {args.input}")
        print(f"   Style: {args.style}, Focus: {args.focus}")
        
        captions = assistant.batch_generate_captions(
            image_dir=args.input,
            output_dir=args.output,
            style=args.style,
            focus=args.focus
        )
        
        print(f"\n✓ Generated {len(captions)} captions!")
    
    elif args.command == 'analyze':
        print(f"\n📊 Analyzing dataset: {args.input}")
        
        analysis = assistant.analyze_dataset_quality(args.input)
        
        if 'error' not in analysis:
            print(f"\n📈 Analysis Results:")
            print(f"   Overall Score: {analysis.get('overall_score', 'N/A')}/10")
            print(f"   Quality: {analysis.get('quality_score', 'N/A')}/10")
            print(f"   Consistency: {analysis.get('consistency_score', 'N/A')}/10")
            print(f"   Diversity: {analysis.get('diversity_score', 'N/A')}/10")
            print(f"\n   Issues: {', '.join(analysis.get('issues', []))}")
            print(f"\n   Recommendations:")
            for rec in analysis.get('recommendations', []):
                print(f"   - {rec}")
            
            if args.output:
                import json
                Path(args.output).write_text(json.dumps(analysis, indent=2))
                print(f"\n✓ Saved report to: {args.output}")
        else:
            print(f"✗ Error: {analysis.get('error')}")
    
    elif args.command == 'recommend':
        print(f"\n⚙️ Getting hyperparameter recommendations...")
        print(f"   Dataset: {args.dataset}")
        print(f"   Goal: {args.goal}")
        
        # Get dataset info
        dataset_path = Path(args.dataset)
        num_images = len(list(dataset_path.glob('*.jpg')) + list(dataset_path.glob('*.png')))
        
        # Get quality score from analysis
        print("\n   Analyzing dataset quality...")
        analysis = assistant.analyze_dataset_quality(args.dataset)
        quality_score = analysis.get('quality_score', 7)
        
        # Get recommendations
        recommendations = assistant.recommend_hyperparameters(
            dataset_info={
                'num_images': num_images,
                'quality_score': quality_score
            },
            training_goal=args.goal
        )
        
        if 'error' not in recommendations:
            print(f"\n📋 Recommended Hyperparameters:")
            print(f"   Rank: {recommendations.get('rank')}")
            print(f"   Alpha: {recommendations.get('alpha')}")
            print(f"   Learning Rate: {recommendations.get('learning_rate')}")
            print(f"   Epochs: {recommendations.get('epochs')}")
            print(f"   Batch Size: {recommendations.get('batch_size')}")
            print(f"   Optimizer: {recommendations.get('optimizer')}")
            print(f"\n   Advanced Features:")
            print(f"   - LoRA+: {recommendations.get('use_loraplus')}")
            print(f"   - LoRA+ Ratio: {recommendations.get('loraplus_lr_ratio')}")
            print(f"   - Loss Type: {recommendations.get('loss_type')}")
            print(f"   - Min-SNR Gamma: {recommendations.get('min_snr_gamma')}")
            print(f"\n   Reasoning: {recommendations.get('reasoning')}")
            
            if args.output:
                import yaml
                config = {
                    'model': {
                        'pretrained_model_name_or_path': 'runwayml/stable-diffusion-v1-5'
                    },
                    'lora': {
                        'rank': recommendations.get('rank'),
                        'alpha': recommendations.get('alpha')
                    },
                    'training': {
                        'num_train_epochs': recommendations.get('epochs'),
                        'train_batch_size': recommendations.get('batch_size'),
                        'optimizer': recommendations.get('optimizer'),
                        'learning_rate': recommendations.get('learning_rate'),
                        'use_loraplus': recommendations.get('use_loraplus'),
                        'loraplus_lr_ratio': recommendations.get('loraplus_lr_ratio'),
                        'loss_type': recommendations.get('loss_type'),
                        'min_snr_gamma': recommendations.get('min_snr_gamma'),
                        'noise_offset': recommendations.get('noise_offset', 0.1)
                    }
                }
                
                Path(args.output).write_text(yaml.dump(config, sort_keys=False))
                print(f"\n✓ Saved config to: {args.output}")
        else:
            print(f"✗ Error: {recommendations.get('error')}")
    
    elif args.command == 'outliers':
        print(f"\n🔍 Detecting outliers in: {args.input}")
        
        dataset_path = Path(args.input)
        images = list(dataset_path.glob('*.jpg')) + list(dataset_path.glob('*.png'))
        
        print(f"   Found {len(images)} images to check")
        
        outliers = assistant.detect_outliers([str(img) for img in images])
        
        if outliers:
            print(f"\n⚠️ Found {len(outliers)} potential outliers:")
            for img_path, reason in outliers:
                print(f"   - {Path(img_path).name}: {reason}")
            
            if args.remove:
                print(f"\n🗑️ Removing outliers...")
                for img_path, _ in outliers:
                    Path(img_path).unlink()
                    # Also remove caption file if exists
                    caption_path = Path(img_path).with_suffix('.txt')
                    if caption_path.exists():
                        caption_path.unlink()
                print(f"✓ Removed {len(outliers)} outliers")
        else:
            print(f"\n✓ No outliers detected! Dataset looks good.")


if __name__ == '__main__':
    main()
