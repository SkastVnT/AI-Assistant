"""
Gemini 2.0 Flash Integration for LoRA Training
Provides AI-powered caption generation, quality checking, and training assistance
"""

import os
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
from PIL import Image
from google import genai


class GeminiLoRAAssistant:
    """
    Gemini 2.0 Flash assistant for LoRA training.
    
    Features:
    1. Auto-caption generation (better than BLIP/GIT)
    2. Dataset quality analysis
    3. Hyperparameter recommendations
    4. Tag optimization and cleaning
    
    WARNING: DO NOT USE FOR NSFW/R18+ CONTENT!
    - Google blocks explicit content (cannot be disabled)
    - Violates Terms of Service
    - May result in API key ban
    - Privacy concerns (images sent to Google servers)
    
    For NSFW content, use:
    - WD14 Tagger (local, private, NSFW-safe)
    - BLIP (local, but limited NSFW recognition)
    - Manual tagging (best control)
    See docs/NSFW_TRAINING_GUIDE.md for details.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini assistant.
        
        Args:
            api_key: Google API key (if None, reads from GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Gemini API key required! Set GEMINI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Configure Gemini
        self.client = genai.Client(api_key=self.api_key)
        
        # Safety settings (permissive for anime/art content)
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    
    def generate_caption(
        self,
        image_path: str,
        style: str = "detailed",
        focus: str = "character"
    ) -> str:
        """
        Generate high-quality caption for training image.
        
        Args:
            image_path: Path to image file
            style: Caption style ('detailed', 'concise', 'tags')
            focus: What to focus on ('character', 'style', 'scene', 'all')
            
        Returns:
            Generated caption string
        """
        # Load image
        image = Image.open(image_path)
        
        # Build prompt based on style and focus
        prompts = {
            "detailed": {
                "character": """Analyze this image and provide a detailed caption for LoRA training.
Focus on CHARACTER details:
- Physical appearance (hair, eyes, face, body)
- Clothing and accessories
- Expression and pose
- Art style and quality

Format: Natural language, training-optimized.""",
                
                "style": """Analyze this image and provide a detailed caption for LoRA training.
Focus on ART STYLE:
- Drawing/painting technique
- Color palette and lighting
- Line work and shading
- Overall aesthetic

Format: Natural language, training-optimized.""",
                
                "scene": """Analyze this image and provide a detailed caption for LoRA training.
Focus on SCENE/COMPOSITION:
- Background and environment
- Composition and framing
- Atmosphere and mood
- Context and setting

Format: Natural language, training-optimized.""",
                
                "all": """Analyze this image and provide a comprehensive caption for LoRA training.
Include ALL aspects:
1. Main subject (character/object)
2. Art style and quality
3. Scene and background
4. Technical details

Format: Natural language, detailed but concise."""
            },
            
            "concise": {
                "character": "Describe this character briefly: appearance, clothing, expression. For LoRA training.",
                "style": "Describe the art style briefly: technique, colors, aesthetic. For LoRA training.",
                "scene": "Describe the scene briefly: setting, composition, mood. For LoRA training.",
                "all": "Describe this image concisely for LoRA training. Key details only."
            },
            
            "tags": {
                "character": """Generate training tags for this character image.
Format: tag1, tag2, tag3, ...
Focus: character features, clothing, pose, quality
Example: 1girl, blue hair, red eyes, school uniform, smile, high quality, detailed""",
                
                "style": """Generate training tags for this image focusing on style.
Format: tag1, tag2, tag3, ...
Focus: art style, technique, quality markers
Example: anime style, cel shading, vibrant colors, masterpiece, high quality""",
                
                "scene": """Generate training tags for this scene.
Format: tag1, tag2, tag3, ...
Focus: background, setting, atmosphere
Example: outdoors, cherry blossoms, sunset, scenic, detailed background""",
                
                "all": """Generate comprehensive training tags for this image.
Format: quality_tags, subject_tags, style_tags, scene_tags
Example: masterpiece, best quality, 1girl, blue hair, anime style, outdoors, sunset"""
            }
        }
        
        prompt = prompts.get(style, prompts["detailed"]).get(focus, prompts["detailed"]["all"])
        
        # Generate caption
        response = self.client.models.generate_content(
            model='grok-3',
            contents=[prompt, image],
            safety_settings=self.safety_settings
        )
        
        return response.text.strip()
    
    def batch_generate_captions(
        self,
        image_dir: str,
        output_dir: Optional[str] = None,
        style: str = "tags",
        focus: str = "all",
        extension: str = ".txt"
    ) -> Dict[str, str]:
        """
        Generate captions for all images in directory.
        
        Args:
            image_dir: Directory containing images
            output_dir: Where to save caption files (if None, same as image_dir)
            style: Caption style
            focus: Caption focus
            extension: Caption file extension
            
        Returns:
            Dict mapping image paths to captions
        """
        image_dir = Path(image_dir)
        output_dir = Path(output_dir) if output_dir else image_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        
        for img_path in image_dir.iterdir():
            if img_path.suffix.lower() not in image_extensions:
                continue
            
            print(f"Processing {img_path.name}...")
            
            try:
                # Generate caption
                caption = self.generate_caption(str(img_path), style, focus)
                results[str(img_path)] = caption
                
                # Save to file
                caption_path = output_dir / f"{img_path.stem}{extension}"
                caption_path.write_text(caption, encoding='utf-8')
                
                print(f"  ✓ Saved: {caption_path.name}")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        return results
    
    def analyze_dataset_quality(self, image_dir: str) -> Dict[str, any]:
        """
        Analyze training dataset quality and provide recommendations.
        
        Args:
            image_dir: Directory containing training images
            
        Returns:
            Analysis report with scores and recommendations
        """
        image_dir = Path(image_dir)
        images = list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.png'))
        
        if not images:
            return {"error": "No images found"}
        
        # Sample images for analysis (max 10 for cost efficiency)
        sample_size = min(10, len(images))
        import random
        sampled = random.sample(images, sample_size)
        
        # Analyze samples
        prompt = f"""Analyze these {sample_size} training images for LoRA fine-tuning.

Provide assessment on:
1. Image Quality (resolution, clarity, artifacts)
2. Consistency (style, character appearance, art quality)
3. Diversity (poses, angles, expressions, backgrounds)
4. Potential Issues (low quality, inconsistent, problematic)

Output JSON format:
{{
    "overall_score": 0-10,
    "quality_score": 0-10,
    "consistency_score": 0-10,
    "diversity_score": 0-10,
    "total_images_analyzed": {sample_size},
    "issues": ["issue1", "issue2"],
    "recommendations": ["rec1", "rec2"],
    "suggested_filters": ["filter1", "filter2"]
}}"""
        
        # Load sample images
        image_objects = [Image.open(img) for img in sampled]
        
        # Generate analysis
        response = self.client.models.generate_content(
            model='grok-3',
            contents=[prompt] + image_objects,
            safety_settings=self.safety_settings
        )
        
        # Parse JSON response
        try:
            # Extract JSON from response
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            analysis = json.loads(text.strip())
            analysis['total_images_in_dataset'] = len(images)
            return analysis
            
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse analysis",
                "raw_response": response.text
            }
    
    def recommend_hyperparameters(
        self,
        dataset_info: Dict[str, any],
        training_goal: str = "character"
    ) -> Dict[str, any]:
        """
        Get AI-powered hyperparameter recommendations.
        
        Args:
            dataset_info: Info about dataset (num_images, quality_score, etc.)
            training_goal: 'character', 'style', 'concept', 'object'
            
        Returns:
            Recommended hyperparameters
        """
        prompt = f"""As a LoRA training expert, recommend optimal hyperparameters.

Dataset Info:
- Number of images: {dataset_info.get('num_images', 'unknown')}
- Quality score: {dataset_info.get('quality_score', 'unknown')}/10
- Training goal: {training_goal}
- GPU: RTX 3060 6GB VRAM

Recommend:
1. LoRA rank (4-128)
2. Learning rate
3. Number of epochs
4. Batch size
5. Advanced features to enable

Output JSON:
{{
    "rank": 32,
    "alpha": 64,
    "learning_rate": 1e-4,
    "epochs": 10,
    "batch_size": 2,
    "optimizer": "adamw",
    "use_loraplus": true,
    "loraplus_lr_ratio": 16.0,
    "loss_type": "smooth_l1",
    "min_snr_gamma": 5.0,
    "noise_offset": 0.1,
    "reasoning": "explanation here"
}}"""
        
        response = self.client.models.generate_content(
            model='grok-3',
            contents=prompt,
            safety_settings=self.safety_settings
        )
        
        try:
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except:
            return {"error": "Failed to parse recommendations", "raw": response.text}
    
    def optimize_tags(self, tags: str, focus: str = "quality") -> str:
        """
        Optimize and clean training tags.
        
        Args:
            tags: Original tags (comma-separated or line-separated)
            focus: Optimization focus ('quality', 'diversity', 'specificity')
            
        Returns:
            Optimized tags
        """
        prompts = {
            "quality": """Improve these training tags for LoRA quality:
1. Add quality markers (masterpiece, best quality, etc.)
2. Remove redundant tags
3. Fix grammar/spelling
4. Organize by importance

Original tags: {tags}

Output: optimized, comma-separated tags""",
            
            "diversity": """Diversify these training tags:
1. Add varied descriptors
2. Include style variations
3. Add context tags
4. Maintain core meaning

Original tags: {tags}

Output: diversified, comma-separated tags""",
            
            "specificity": """Make these tags more specific for training:
1. Replace generic with specific terms
2. Add detailed descriptors
3. Include technical details
4. Remove vague terms

Original tags: {tags}

Output: specific, comma-separated tags"""
        }
        
        prompt = prompts.get(focus, prompts["quality"]).format(tags=tags)
        
        response = self.client.models.generate_content(
            model='grok-3',
            contents=prompt,
            safety_settings=self.safety_settings
        )
        
        return response.text.strip()
    
    def detect_outliers(self, image_paths: List[str]) -> List[Tuple[str, str]]:
        """
        Detect potential outlier/problematic images.
        
        Args:
            image_paths: List of image paths to check
            
        Returns:
            List of (image_path, reason) for outliers
        """
        outliers = []
        
        for img_path in image_paths:
            try:
                image = Image.open(img_path)
                
                prompt = """Analyze if this image is suitable for LoRA training.
Check for:
- Low quality/resolution
- Artifacts or corruption
- Inconsistent style
- Inappropriate content

Answer: "OK" or "OUTLIER: reason"
Be concise."""
                
                response = self.client.models.generate_content(
                    model='grok-3',
                    contents=[prompt, image],
                    safety_settings=self.safety_settings
                )
                
                result = response.text.strip()
                if "OUTLIER" in result.upper():
                    reason = result.split(":", 1)[1].strip() if ":" in result else result
                    outliers.append((img_path, reason))
                    
            except Exception as e:
                outliers.append((img_path, f"Error: {e}"))
        
        return outliers


# Example usage
if __name__ == "__main__":
    # Initialize assistant
    assistant = GeminiLoRAAssistant()
    
    # Example 1: Generate captions
    print("🎨 Generating captions...")
    captions = assistant.batch_generate_captions(
        image_dir="data/train",
        style="tags",
        focus="all"
    )
    print(f"✓ Generated {len(captions)} captions")
    
    # Example 2: Analyze dataset
    print("\n📊 Analyzing dataset quality...")
    analysis = assistant.analyze_dataset_quality("data/train")
    print(f"Overall Score: {analysis.get('overall_score', 'N/A')}/10")
    print(f"Recommendations: {analysis.get('recommendations', [])}")
    
    # Example 3: Get hyperparameter recommendations
    print("\n⚙️ Getting hyperparameter recommendations...")
    recommendations = assistant.recommend_hyperparameters(
        dataset_info={
            "num_images": len(captions),
            "quality_score": analysis.get('quality_score', 7)
        },
        training_goal="character"
    )
    print(f"Recommended rank: {recommendations.get('rank')}")
    print(f"Recommended LR: {recommendations.get('learning_rate')}")
