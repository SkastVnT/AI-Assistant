"""
Gemini-powered LoRA Training Config Recommender
================================================

**PRIVACY-FIRST APPROACH FOR NSFW DATASETS:**
- Gemini NEVER sees your NSFW images
- Only sends dataset METADATA (image count, resolutions, tag statistics)
- Uses WD14 tags to build profile without uploading images
- 100% safe for NSFW/R18+ content

Workflow:
1. WD14 Tagger analyzes images locally → generates tags
2. Extract metadata: image count, avg resolution, tag distribution
3. Send ONLY metadata to Gemini (no images!)
4. Gemini analyzes metadata → recommends optimal hyperparameters
5. Apply recommendations to your training config

Example metadata sent to Gemini:
{
    "total_images": 150,
    "avg_resolution": "768x1024",
    "tag_categories": {
        "character_focus": 0.8,
        "style_tags": ["anime", "detailed"],
        "complexity_score": 7.5
    }
}

Created: 2024-12-01
Version: 1.0.0
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
from collections import Counter
import google.generativeai as genai


class DatasetMetadataAnalyzer:
    """Analyze dataset metadata without accessing image content"""
    
    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        self.metadata = {}
        
    def analyze(self) -> Dict[str, Any]:
        """
        Extract metadata from dataset
        
        Returns:
            Dict with:
            - total_images: int
            - avg_resolution: str (e.g., "512x768")
            - resolutions: List of tuples
            - tag_stats: Dict of tag frequencies
            - caption_lengths: List of caption word counts
            - complexity_score: float (0-10)
        """
        from PIL import Image
        
        image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        images = [f for f in self.dataset_path.iterdir() if f.suffix.lower() in image_exts]
        
        if not images:
            raise ValueError(f"No images found in {self.dataset_path}")
        
        # Analyze images
        resolutions = []
        for img_path in images:
            try:
                with Image.open(img_path) as img:
                    resolutions.append((img.width, img.height))
            except Exception as e:
                print(f"Warning: Could not read {img_path}: {e}")
        
        # Analyze captions/tags
        all_tags = []
        caption_lengths = []
        
        for img_path in images:
            caption_file = img_path.with_suffix('.txt')
            if caption_file.exists():
                try:
                    caption = caption_file.read_text(encoding='utf-8').strip()
                    tags = [t.strip() for t in caption.split(',')]
                    all_tags.extend(tags)
                    caption_lengths.append(len(tags))
                except Exception as e:
                    print(f"Warning: Could not read caption {caption_file}: {e}")
        
        # Calculate statistics
        avg_width = sum(r[0] for r in resolutions) / len(resolutions) if resolutions else 512
        avg_height = sum(r[1] for r in resolutions) / len(resolutions) if resolutions else 512
        avg_resolution = f"{int(avg_width)}x{int(avg_height)}"
        
        # Tag analysis
        tag_counter = Counter(all_tags)
        most_common_tags = tag_counter.most_common(50)
        
        # Complexity scoring
        complexity_factors = {
            'tag_diversity': len(tag_counter) / max(len(all_tags), 1) * 10,
            'avg_tags_per_image': sum(caption_lengths) / max(len(caption_lengths), 1),
            'resolution_variance': self._calculate_resolution_variance(resolutions),
        }
        complexity_score = min(10, sum(complexity_factors.values()) / len(complexity_factors))
        
        self.metadata = {
            'total_images': len(images),
            'avg_resolution': avg_resolution,
            'resolution_stats': {
                'min': f"{min(r[0] for r in resolutions)}x{min(r[1] for r in resolutions)}",
                'max': f"{max(r[0] for r in resolutions)}x{max(r[1] for r in resolutions)}",
                'avg': avg_resolution
            },
            'tag_stats': {
                'total_tags': len(all_tags),
                'unique_tags': len(tag_counter),
                'avg_tags_per_image': sum(caption_lengths) / max(len(caption_lengths), 1),
                'most_common': dict(most_common_tags[:20])
            },
            'caption_stats': {
                'min_length': min(caption_lengths) if caption_lengths else 0,
                'max_length': max(caption_lengths) if caption_lengths else 0,
                'avg_length': sum(caption_lengths) / max(len(caption_lengths), 1) if caption_lengths else 0
            },
            'complexity_score': complexity_score,
            'complexity_factors': complexity_factors
        }
        
        return self.metadata
    
    def _calculate_resolution_variance(self, resolutions: List[tuple]) -> float:
        """Calculate how varied the resolutions are (0-10 scale)"""
        if not resolutions:
            return 0
        
        widths = [r[0] for r in resolutions]
        heights = [r[1] for r in resolutions]
        
        width_range = max(widths) - min(widths)
        height_range = max(heights) - min(heights)
        
        # Normalize to 0-10 scale
        variance = (width_range + height_range) / 200
        return min(10, variance)


class GeminiConfigRecommender:
    """Use Gemini to recommend optimal LoRA training config based on metadata"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini recommender
        
        Args:
            api_key: Gemini API key (or use GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Set it in environment or pass as parameter.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def recommend_config(self, metadata: Dict[str, Any], 
                        training_goal: str = "high_quality") -> Dict[str, Any]:
        """
        Get AI-powered config recommendations
        
        Args:
            metadata: Dataset metadata from DatasetMetadataAnalyzer
            training_goal: One of:
                - "high_quality": Best quality, slower (default)
                - "balanced": Good quality, reasonable speed
                - "fast": Quick results, lower quality
                - "experimental": Latest techniques, may be unstable
        
        Returns:
            Dict with recommended config:
            {
                "learning_rate": 1e-4,
                "batch_size": 4,
                "epochs": 10,
                "network_dim": 32,
                "network_alpha": 16,
                "optimizer": "AdamW8bit",
                "lr_scheduler": "cosine",
                "reasoning": "Explanation of choices..."
            }
        """
        
        # Build prompt for Gemini
        prompt = f"""You are an expert in LoRA (Low-Rank Adaptation) training for Stable Diffusion models.

**DATASET METADATA** (NO IMAGES INCLUDED - PRIVACY PRESERVED):
```json
{json.dumps(metadata, indent=2)}
```

**TRAINING GOAL**: {training_goal}

**TASK**: Based on this metadata, recommend optimal hyperparameters for LoRA training.

**IMPORTANT CONTEXT**:
- This is for fine-tuning Stable Diffusion models
- Dataset may contain NSFW/R18+ content (you're only seeing metadata, not images)
- User wants best results for this specific dataset profile
- Consider dataset size, complexity, and tag diversity

**PROVIDE RECOMMENDATIONS FOR**:
1. **Learning Rate** (e.g., 1e-4, 5e-5)
2. **Batch Size** (1-8, consider VRAM limits)
3. **Training Epochs** (how many passes through dataset)
4. **Network Dimension (rank)** (4, 8, 16, 32, 64, 128)
5. **Network Alpha** (typically half of dim, or equal)
6. **Optimizer** (AdamW8bit, AdamW, Lion, Prodigy, DAdaptation)
7. **LR Scheduler** (constant, cosine, cosine_with_restarts, polynomial)
8. **Additional Settings**:
   - Min SNR Gamma (0 or 5)
   - LoRA+ (enable/disable, lr_ratio if enabled)
   - Training resolution (based on dataset resolution)
   - Caption dropout rate (0-0.1)

**RESPOND IN JSON FORMAT**:
```json
{{
    "learning_rate": <float>,
    "batch_size": <int>,
    "epochs": <int>,
    "network_dim": <int>,
    "network_alpha": <int>,
    "optimizer": "<optimizer_name>",
    "lr_scheduler": "<scheduler_name>",
    "min_snr_gamma": <float>,
    "use_lora_plus": <bool>,
    "lora_plus_lr_ratio": <float or null>,
    "train_resolution": "<widthxheight>",
    "caption_dropout_rate": <float>,
    "reasoning": "<detailed explanation of your choices>",
    "warnings": [<list of potential issues or considerations>],
    "estimated_vram": "<VRAM requirement>",
    "estimated_time": "<rough training time estimate>"
}}
```

**GUIDELINES**:
- Small datasets (<100 images): Lower learning rate, more epochs, higher network dim
- Large datasets (>500 images): Can use higher LR, fewer epochs
- High complexity (varied content): Use higher network dim (32-128)
- Low complexity (consistent style): Lower network dim (8-32) is sufficient
- High resolution images (>768px): Adjust batch size down, consider training resolution
- For {training_goal} goal, balance quality vs speed appropriately

Provide your recommendation:"""

        try:
            # Call Gemini API
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extract JSON from response
            # Gemini might wrap JSON in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            config = json.loads(response_text)
            
            # Validate required fields
            required_fields = ['learning_rate', 'batch_size', 'epochs', 
                             'network_dim', 'network_alpha', 'optimizer']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field: {field}")
            
            return config
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            # Fallback to rule-based recommendations
            return self._fallback_recommendation(metadata, training_goal)
    
    def _fallback_recommendation(self, metadata: Dict[str, Any], 
                                training_goal: str) -> Dict[str, Any]:
        """Rule-based fallback if Gemini API fails"""
        
        total_images = metadata.get('total_images', 100)
        complexity = metadata.get('complexity_score', 5.0)
        
        # Basic heuristics
        if total_images < 50:
            lr, epochs, dim = 5e-5, 20, 64
        elif total_images < 200:
            lr, epochs, dim = 1e-4, 15, 32
        else:
            lr, epochs, dim = 2e-4, 10, 32
        
        # Adjust for complexity
        if complexity > 7:
            dim = min(128, dim * 2)
        
        # Adjust for goal
        if training_goal == "fast":
            epochs = max(5, epochs // 2)
            lr *= 1.5
        elif training_goal == "high_quality":
            epochs = int(epochs * 1.5)
            lr *= 0.8
        
        return {
            "learning_rate": lr,
            "batch_size": 4,
            "epochs": epochs,
            "network_dim": dim,
            "network_alpha": dim // 2,
            "optimizer": "AdamW8bit",
            "lr_scheduler": "cosine",
            "min_snr_gamma": 5,
            "use_lora_plus": False,
            "lora_plus_lr_ratio": None,
            "train_resolution": metadata.get('avg_resolution', '512x512'),
            "caption_dropout_rate": 0.05,
            "reasoning": "Fallback recommendation based on rule-based heuristics (Gemini API unavailable)",
            "warnings": ["This is a fallback recommendation. For best results, ensure Gemini API is available."],
            "estimated_vram": "8-12GB",
            "estimated_time": f"{epochs * total_images // 200} hours (approx)"
        }


def quick_recommend(dataset_path: str, 
                   training_goal: str = "high_quality",
                   api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick function to get config recommendations
    
    Args:
        dataset_path: Path to dataset folder
        training_goal: "high_quality", "balanced", "fast", or "experimental"
        api_key: Gemini API key (optional, uses env var if not provided)
    
    Returns:
        Dict with recommended config
    
    Example:
        >>> config = quick_recommend("./my_nsfw_dataset", "high_quality")
        >>> print(f"Recommended LR: {config['learning_rate']}")
        >>> print(f"Reasoning: {config['reasoning']}")
    """
    
    print("🔍 Analyzing dataset metadata (no images sent to Gemini)...")
    analyzer = DatasetMetadataAnalyzer(dataset_path)
    metadata = analyzer.analyze()
    
    print(f"📊 Dataset stats:")
    print(f"   - Images: {metadata['total_images']}")
    print(f"   - Avg resolution: {metadata['avg_resolution']}")
    print(f"   - Unique tags: {metadata['tag_stats']['unique_tags']}")
    print(f"   - Complexity: {metadata['complexity_score']:.1f}/10")
    
    print("\n🤖 Getting AI recommendations from Gemini...")
    recommender = GeminiConfigRecommender(api_key)
    config = recommender.recommend_config(metadata, training_goal)
    
    print("\n✅ Recommendations ready!")
    return config


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python config_recommender.py <dataset_path> [training_goal]")
        print("Training goals: high_quality, balanced, fast, experimental")
        sys.exit(1)
    
    dataset_path = sys.argv[1]
    training_goal = sys.argv[2] if len(sys.argv) > 2 else "high_quality"
    
    try:
        config = quick_recommend(dataset_path, training_goal)
        
        print("\n" + "="*60)
        print("RECOMMENDED CONFIG")
        print("="*60)
        print(json.dumps(config, indent=2))
        print("="*60)
        
        # Save to file
        output_file = Path(dataset_path) / "recommended_config.json"
        output_file.write_text(json.dumps(config, indent=2), encoding='utf-8')
        print(f"\n💾 Saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
