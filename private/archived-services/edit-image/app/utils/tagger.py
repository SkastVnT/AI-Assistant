"""
Auto-tagging module for Edit Image Service.
Uses DeepDanbooru and WD14 Tagger for automatic anime tag prediction.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Lazy imports for optional dependencies
_DEEPDANBOORU_AVAILABLE = None
_WD14_AVAILABLE = None


def _check_deepdanbooru():
    """Check if DeepDanbooru is available."""
    global _DEEPDANBOORU_AVAILABLE
    if _DEEPDANBOORU_AVAILABLE is None:
        try:
            import tensorflow as tf
            import deepdanbooru as dd
            _DEEPDANBOORU_AVAILABLE = True
        except ImportError:
            _DEEPDANBOORU_AVAILABLE = False
    return _DEEPDANBOORU_AVAILABLE


def _check_wd14():
    """Check if WD14 Tagger dependencies are available."""
    global _WD14_AVAILABLE
    if _WD14_AVAILABLE is None:
        try:
            import onnxruntime
            _WD14_AVAILABLE = True
        except ImportError:
            _WD14_AVAILABLE = False
    return _WD14_AVAILABLE


class DeepDanbooruTagger:
    """
    DeepDanbooru tagger for anime images.
    
    Uses a CNN model trained on Danbooru dataset to predict tags.
    """
    
    MODEL_PATH = "./models/deepdanbooru"
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the DeepDanbooru tagger.
        
        Args:
            model_path: Path to the DeepDanbooru model directory
        """
        if not _check_deepdanbooru():
            raise ImportError(
                "DeepDanbooru requires tensorflow and deepdanbooru. "
                "Install with: pip install tensorflow deepdanbooru"
            )
        
        import deepdanbooru as dd
        
        self.model_path = model_path or self.MODEL_PATH
        self.model = None
        self.tags = None
        self._load_model()
    
    def _load_model(self):
        """Load the DeepDanbooru model."""
        import deepdanbooru as dd
        
        path = Path(self.model_path)
        if not path.exists():
            logger.info("Downloading DeepDanbooru model...")
            # Would need to implement download logic
            raise FileNotFoundError(
                f"DeepDanbooru model not found at {self.model_path}. "
                "Please download from: https://github.com/KichangKim/DeepDanbooru"
            )
        
        self.model = dd.project.load_model_from_project(
            str(path),
            compile_model=False
        )
        self.tags = dd.project.load_tags_from_project(str(path))
        logger.info(f"Loaded DeepDanbooru with {len(self.tags)} tags")
    
    def predict(
        self,
        image: Union[str, Path, Image.Image],
        threshold: float = 0.5,
        top_k: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Predict tags for an image.
        
        Args:
            image: Image path or PIL Image
            threshold: Minimum confidence threshold
            top_k: Return only top K tags
            
        Returns:
            Dict mapping tag names to confidence scores
        """
        import deepdanbooru as dd
        
        # Load image
        if isinstance(image, (str, Path)):
            img = Image.open(image).convert("RGB")
        else:
            img = image.convert("RGB")
        
        # Resize to model input size
        img = img.resize((512, 512))
        img_array = np.array(img) / 255.0
        
        # Predict
        predictions = self.model.predict(np.array([img_array]))[0]
        
        # Filter by threshold
        results = {}
        for i, score in enumerate(predictions):
            if score >= threshold:
                results[self.tags[i]] = float(score)
        
        # Sort by score
        results = dict(sorted(results.items(), key=lambda x: x[1], reverse=True))
        
        # Limit to top K
        if top_k is not None:
            results = dict(list(results.items())[:top_k])
        
        return results


class WD14Tagger:
    """
    WD14 Tagger for anime images.
    
    Uses a model trained on Waifu Diffusion 1.4 aesthetic dataset.
    Supports ONNX runtime for faster inference.
    """
    
    MODEL_REPO = "SmilingWolf/wd-v1-4-vit-tagger"
    MODELS = {
        "vit": "SmilingWolf/wd-v1-4-vit-tagger",
        "convnext": "SmilingWolf/wd-v1-4-convnext-tagger",
        "swinv2": "SmilingWolf/wd-v1-4-swinv2-tagger-v2",
        "moat": "SmilingWolf/wd-v1-4-moat-tagger-v2",
    }
    
    def __init__(
        self,
        model_name: str = "swinv2",
        cache_dir: str = "./models/wd14",
    ):
        """
        Initialize the WD14 Tagger.
        
        Args:
            model_name: Model variant (vit, convnext, swinv2, moat)
            cache_dir: Directory to cache models
        """
        if not _check_wd14():
            raise ImportError(
                "WD14 Tagger requires onnxruntime. "
                "Install with: pip install onnxruntime-gpu"
            )
        
        import onnxruntime as ort
        
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.model_repo = self.MODELS.get(model_name, model_name)
        self.session = None
        self.tags = None
        self._load_model()
    
    def _load_model(self):
        """Load the ONNX model and tags."""
        import onnxruntime as ort
        
        try:
            from huggingface_hub import hf_hub_download
        except ImportError:
            raise ImportError(
                "huggingface_hub is required. Install with: pip install huggingface_hub"
            )
        
        # Download model files
        model_path = hf_hub_download(
            repo_id=self.model_repo,
            filename="model.onnx",
            cache_dir=str(self.cache_dir),
        )
        
        tags_path = hf_hub_download(
            repo_id=self.model_repo,
            filename="selected_tags.csv",
            cache_dir=str(self.cache_dir),
        )
        
        # Load model
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self.session = ort.InferenceSession(model_path, providers=providers)
        
        # Load tags
        import csv
        with open(tags_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.tags = [row["name"] for row in reader]
        
        # Get input details
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape
        
        logger.info(f"Loaded WD14 Tagger ({self.model_name}) with {len(self.tags)} tags")
    
    def _preprocess(self, image: Image.Image) -> np.ndarray:
        """Preprocess image for model input."""
        # Get target size from model
        target_size = self.input_shape[1]  # Usually 448
        
        # Resize maintaining aspect ratio, then pad
        img = image.convert("RGB")
        
        # Calculate resize dimensions
        old_size = img.size
        ratio = target_size / max(old_size)
        new_size = tuple([int(x * ratio) for x in old_size])
        
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Pad to square
        new_img = Image.new("RGB", (target_size, target_size), (255, 255, 255))
        paste_pos = ((target_size - new_size[0]) // 2, (target_size - new_size[1]) // 2)
        new_img.paste(img, paste_pos)
        
        # Convert to numpy and normalize
        img_array = np.array(new_img).astype(np.float32)
        img_array = img_array[:, :, ::-1]  # RGB -> BGR
        
        return np.expand_dims(img_array, axis=0)
    
    def predict(
        self,
        image: Union[str, Path, Image.Image],
        general_threshold: float = 0.35,
        character_threshold: float = 0.85,
        top_k: Optional[int] = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        Predict tags for an image.
        
        Args:
            image: Image path or PIL Image
            general_threshold: Threshold for general tags
            character_threshold: Threshold for character tags
            top_k: Return only top K tags per category
            
        Returns:
            Dict with categories: rating, general, character
        """
        # Load image
        if isinstance(image, (str, Path)):
            img = Image.open(image)
        else:
            img = image
        
        # Preprocess
        input_data = self._preprocess(img)
        
        # Run inference
        outputs = self.session.run(None, {self.input_name: input_data})
        predictions = outputs[0][0]
        
        # Parse results by category
        # Tags are ordered: [rating (9), general, character]
        results = {
            "rating": {},
            "general": {},
            "character": {},
        }
        
        for i, score in enumerate(predictions):
            tag = self.tags[i]
            score = float(score)
            
            if i < 9:  # Rating tags
                results["rating"][tag] = score
            elif "character:" in tag or i > len(self.tags) - 1000:  # Approximate character section
                if score >= character_threshold:
                    results["character"][tag.replace("character:", "")] = score
            else:  # General tags
                if score >= general_threshold:
                    results["general"][tag] = score
        
        # Sort by score
        for category in results:
            results[category] = dict(
                sorted(results[category].items(), key=lambda x: x[1], reverse=True)
            )
            if top_k is not None:
                results[category] = dict(list(results[category].items())[:top_k])
        
        return results
    
    def get_prompt(
        self,
        image: Union[str, Path, Image.Image],
        threshold: float = 0.35,
        max_tags: int = 50,
        exclude_tags: List[str] = None,
    ) -> str:
        """
        Get a formatted prompt from image tags.
        
        Args:
            image: Image to analyze
            threshold: Tag confidence threshold
            max_tags: Maximum number of tags
            exclude_tags: Tags to exclude from output
            
        Returns:
            Comma-separated tag string suitable for SD prompt
        """
        exclude_tags = exclude_tags or []
        exclude_set = set(t.lower() for t in exclude_tags)
        
        results = self.predict(image, general_threshold=threshold)
        
        # Combine tags
        all_tags = []
        
        # Add character tags first
        for tag in results["character"]:
            if tag.lower() not in exclude_set:
                all_tags.append(tag.replace(" ", "_"))
        
        # Add general tags
        for tag in results["general"]:
            if tag.lower() not in exclude_set:
                all_tags.append(tag.replace(" ", "_"))
        
        # Limit and format
        all_tags = all_tags[:max_tags]
        return ", ".join(all_tags)


class AutoTagger:
    """
    Unified auto-tagger that can use multiple backends.
    """
    
    def __init__(
        self,
        backend: str = "wd14",
        **kwargs
    ):
        """
        Initialize the auto-tagger.
        
        Args:
            backend: Tagger backend ("wd14" or "deepdanbooru")
            **kwargs: Additional arguments for the backend
        """
        self.backend = backend
        
        if backend == "wd14":
            self.tagger = WD14Tagger(**kwargs)
        elif backend == "deepdanbooru":
            self.tagger = DeepDanbooruTagger(**kwargs)
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
    def tag_image(
        self,
        image: Union[str, Path, Image.Image],
        threshold: float = 0.35,
    ) -> Dict[str, float]:
        """
        Get tags for an image.
        
        Args:
            image: Image to analyze
            threshold: Confidence threshold
            
        Returns:
            Dict mapping tags to scores
        """
        if self.backend == "wd14":
            results = self.tagger.predict(image, general_threshold=threshold)
            # Flatten results
            all_tags = {}
            for category in ["character", "general"]:
                all_tags.update(results.get(category, {}))
            return all_tags
        else:
            return self.tagger.predict(image, threshold=threshold)
    
    def get_prompt(
        self,
        image: Union[str, Path, Image.Image],
        threshold: float = 0.35,
        max_tags: int = 50,
    ) -> str:
        """
        Get a formatted prompt from image tags.
        
        Args:
            image: Image to analyze
            threshold: Confidence threshold
            max_tags: Maximum number of tags
            
        Returns:
            Comma-separated prompt string
        """
        if self.backend == "wd14":
            return self.tagger.get_prompt(image, threshold=threshold, max_tags=max_tags)
        else:
            tags = self.tagger.predict(image, threshold=threshold, top_k=max_tags)
            return ", ".join(tags.keys())
    
    def batch_tag(
        self,
        images: List[Union[str, Path, Image.Image]],
        threshold: float = 0.35,
    ) -> List[Dict[str, float]]:
        """
        Tag multiple images.
        
        Args:
            images: List of images
            threshold: Confidence threshold
            
        Returns:
            List of tag dictionaries
        """
        return [self.tag_image(img, threshold) for img in images]


# Convenience functions

def get_tags(
    image: Union[str, Path, Image.Image],
    threshold: float = 0.35,
    backend: str = "wd14",
) -> Dict[str, float]:
    """
    Get tags for an image using the default tagger.
    
    Args:
        image: Image to analyze
        threshold: Confidence threshold
        backend: Tagger backend to use
        
    Returns:
        Dict mapping tags to scores
    """
    tagger = AutoTagger(backend=backend)
    return tagger.tag_image(image, threshold=threshold)


def image_to_prompt(
    image: Union[str, Path, Image.Image],
    threshold: float = 0.35,
    max_tags: int = 50,
) -> str:
    """
    Convert an image to a text prompt using auto-tagging.
    
    Args:
        image: Image to analyze
        threshold: Confidence threshold
        max_tags: Maximum number of tags
        
    Returns:
        Comma-separated prompt string
    """
    tagger = AutoTagger(backend="wd14")
    return tagger.get_prompt(image, threshold=threshold, max_tags=max_tags)
