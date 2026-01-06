"""
Inpaint Anything Integration for Edit Image Service.

Inpaint Anything combines Segment Anything Model (SAM) for precise segmentation
with LaMa (Large Mask Inpainting) for high-quality object removal and inpainting.

Features:
- Click-to-select object removal
- Text-prompt based segmentation
- Precise mask generation
- Seamless inpainting with LaMa

References:
- https://github.com/geekyutao/Inpaint-Anything
- https://github.com/facebookresearch/segment-anything
- https://github.com/advimman/lama
"""

import logging
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Tuple

import torch
import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


# ==============================================================================
# Model Configuration
# ==============================================================================

SAM_MODELS = {
    "sam_vit_h": {
        "url": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
        "checkpoint": "sam_vit_h_4b8939.pth",
        "model_type": "vit_h",
    },
    "sam_vit_l": {
        "url": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth",
        "checkpoint": "sam_vit_l_0b3195.pth",
        "model_type": "vit_l",
    },
    "sam_vit_b": {
        "url": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth",
        "checkpoint": "sam_vit_b_01ec64.pth",
        "model_type": "vit_b",
    },
    "mobile_sam": {
        "url": "https://github.com/ChaoningZhang/MobileSAM/raw/master/weights/mobile_sam.pt",
        "checkpoint": "mobile_sam.pt",
        "model_type": "vit_t",
    },
}

LAMA_MODEL = {
    "big_lama": {
        "repo": "smartywu/big-lama",
        "filename": "big-lama.pt",
    },
}


# ==============================================================================
# Segment Anything Wrapper
# ==============================================================================

class SAMPredictor:
    """
    Wrapper for Segment Anything Model (SAM).
    
    Provides point-based and text-based segmentation.
    """
    
    def __init__(
        self,
        model_type: str = "sam_vit_h",
        device: str = "cuda",
        models_dir: str = "./models/sam",
    ):
        self.model_type = model_type
        self.device = device
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self._sam = None
        self._predictor = None
        self._current_image = None
        
        logger.info(f"SAMPredictor initialized with {model_type}")
    
    def _download_model(self) -> Path:
        """Download SAM model if not exists."""
        model_info = SAM_MODELS[self.model_type]
        checkpoint_path = self.models_dir / model_info["checkpoint"]
        
        if not checkpoint_path.exists():
            import urllib.request
            
            logger.info(f"Downloading SAM model: {model_info['checkpoint']}")
            urllib.request.urlretrieve(model_info["url"], checkpoint_path)
            logger.info("Download complete")
        
        return checkpoint_path
    
    def load_model(self):
        """Load SAM model."""
        if self._sam is not None:
            return
        
        try:
            from segment_anything import sam_model_registry, SamPredictor
            
            checkpoint_path = self._download_model()
            model_info = SAM_MODELS[self.model_type]
            
            logger.info(f"Loading SAM model: {self.model_type}")
            
            self._sam = sam_model_registry[model_info["model_type"]](
                checkpoint=str(checkpoint_path)
            ).to(self.device)
            
            self._predictor = SamPredictor(self._sam)
            
            logger.info("SAM model loaded successfully")
            
        except ImportError:
            logger.error("segment_anything not installed")
            logger.info("Install with: pip install segment-anything")
            raise
        except Exception as e:
            logger.error(f"Failed to load SAM: {e}")
            raise
    
    def set_image(self, image: Image.Image):
        """
        Set image for segmentation.
        
        Args:
            image: Input image
        """
        if self._predictor is None:
            self.load_model()
        
        img_array = np.array(image.convert("RGB"))
        self._predictor.set_image(img_array)
        self._current_image = image
        
        logger.debug(f"Image set for segmentation: {image.size}")
    
    def predict_point(
        self,
        point: Tuple[int, int],
        label: int = 1,
    ) -> Tuple[np.ndarray, float]:
        """
        Predict mask from point click.
        
        Args:
            point: (x, y) coordinates
            label: 1 for foreground, 0 for background
            
        Returns:
            Tuple of (mask array, confidence score)
        """
        if self._predictor is None or self._current_image is None:
            raise RuntimeError("Call set_image() first")
        
        point_coords = np.array([[point[0], point[1]]])
        point_labels = np.array([label])
        
        masks, scores, _ = self._predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            multimask_output=True,
        )
        
        # Return best mask
        best_idx = scores.argmax()
        return masks[best_idx], scores[best_idx]
    
    def predict_box(
        self,
        box: Tuple[int, int, int, int],
    ) -> Tuple[np.ndarray, float]:
        """
        Predict mask from bounding box.
        
        Args:
            box: (x1, y1, x2, y2) coordinates
            
        Returns:
            Tuple of (mask array, confidence score)
        """
        if self._predictor is None or self._current_image is None:
            raise RuntimeError("Call set_image() first")
        
        box_array = np.array(box)
        
        masks, scores, _ = self._predictor.predict(
            box=box_array,
            multimask_output=True,
        )
        
        best_idx = scores.argmax()
        return masks[best_idx], scores[best_idx]
    
    def predict_points_and_boxes(
        self,
        points: Optional[List[Tuple[int, int]]] = None,
        point_labels: Optional[List[int]] = None,
        boxes: Optional[List[Tuple[int, int, int, int]]] = None,
    ) -> List[Tuple[np.ndarray, float]]:
        """
        Predict masks from multiple points and boxes.
        
        Args:
            points: List of (x, y) coordinates
            point_labels: List of labels (1=foreground, 0=background)
            boxes: List of (x1, y1, x2, y2) boxes
            
        Returns:
            List of (mask, score) tuples
        """
        if self._predictor is None or self._current_image is None:
            raise RuntimeError("Call set_image() first")
        
        results = []
        
        if points is not None:
            point_coords = np.array(points)
            labels = np.array(point_labels) if point_labels else np.ones(len(points))
            
            masks, scores, _ = self._predictor.predict(
                point_coords=point_coords,
                point_labels=labels,
                multimask_output=True,
            )
            
            best_idx = scores.argmax()
            results.append((masks[best_idx], scores[best_idx]))
        
        if boxes is not None:
            for box in boxes:
                mask, score = self.predict_box(box)
                results.append((mask, score))
        
        return results
    
    def segment_everything(
        self,
        points_per_side: int = 32,
        pred_iou_thresh: float = 0.88,
        stability_score_thresh: float = 0.95,
    ) -> List[Dict[str, Any]]:
        """
        Segment all objects in image automatically.
        
        Args:
            points_per_side: Grid density for automatic segmentation
            pred_iou_thresh: Predicted IoU threshold
            stability_score_thresh: Stability score threshold
            
        Returns:
            List of segmentation results with masks and metadata
        """
        if self._sam is None or self._current_image is None:
            raise RuntimeError("Call set_image() first")
        
        try:
            from segment_anything import SamAutomaticMaskGenerator
            
            generator = SamAutomaticMaskGenerator(
                self._sam,
                points_per_side=points_per_side,
                pred_iou_thresh=pred_iou_thresh,
                stability_score_thresh=stability_score_thresh,
            )
            
            img_array = np.array(self._current_image.convert("RGB"))
            masks = generator.generate(img_array)
            
            return masks
            
        except Exception as e:
            logger.error(f"Automatic segmentation failed: {e}")
            return []
    
    def mask_to_image(
        self,
        mask: np.ndarray,
        color: Tuple[int, int, int] = (255, 255, 255),
    ) -> Image.Image:
        """
        Convert mask array to PIL Image.
        
        Args:
            mask: Boolean mask array
            color: Mask color
            
        Returns:
            Mask as PIL Image
        """
        h, w = mask.shape
        img_array = np.zeros((h, w, 3), dtype=np.uint8)
        img_array[mask] = color
        return Image.fromarray(img_array)
    
    def unload(self):
        """Unload model to free memory."""
        self._sam = None
        self._predictor = None
        self._current_image = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# ==============================================================================
# LaMa Inpainter
# ==============================================================================

class LaMaInpainter:
    """
    LaMa (Large Mask Inpainting) for high-quality object removal.
    """
    
    def __init__(
        self,
        device: str = "cuda",
        models_dir: str = "./models/lama",
    ):
        self.device = device
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self._model = None
        
        logger.info("LaMaInpainter initialized")
    
    def load_model(self):
        """Load LaMa model."""
        if self._model is not None:
            return
        
        try:
            from simple_lama_inpainting import SimpleLama
            
            logger.info("Loading LaMa model...")
            self._model = SimpleLama()
            logger.info("LaMa model loaded")
            
        except ImportError:
            # Try alternative loading
            logger.info("simple_lama_inpainting not found, trying diffusers...")
            self._load_diffusers_inpainter()
    
    def _load_diffusers_inpainter(self):
        """Load inpainting model from diffusers as fallback."""
        from diffusers import StableDiffusionInpaintPipeline
        
        logger.info("Loading SD inpainting as fallback...")
        
        self._model = StableDiffusionInpaintPipeline.from_pretrained(
            "runwayml/stable-diffusion-inpainting",
            torch_dtype=torch.float16,
        ).to(self.device)
        
        self._is_diffusers = True
        logger.info("SD inpainting loaded")
    
    def inpaint(
        self,
        image: Image.Image,
        mask: Union[Image.Image, np.ndarray],
        prompt: Optional[str] = None,
        dilate_mask: int = 0,
    ) -> Image.Image:
        """
        Inpaint masked region of image.
        
        Args:
            image: Input image
            mask: Mask image (white = inpaint region)
            prompt: Optional text prompt (for diffusers fallback)
            dilate_mask: Pixels to dilate mask
            
        Returns:
            Inpainted image
        """
        if self._model is None:
            self.load_model()
        
        # Convert mask if needed
        if isinstance(mask, np.ndarray):
            mask_img = Image.fromarray((mask * 255).astype(np.uint8))
        else:
            mask_img = mask.convert("L")
        
        # Dilate mask if requested
        if dilate_mask > 0:
            import cv2
            mask_array = np.array(mask_img)
            kernel = np.ones((dilate_mask, dilate_mask), np.uint8)
            mask_array = cv2.dilate(mask_array, kernel, iterations=1)
            mask_img = Image.fromarray(mask_array)
        
        # Ensure same size
        if image.size != mask_img.size:
            mask_img = mask_img.resize(image.size, Image.Resampling.NEAREST)
        
        # Inpaint
        if hasattr(self, "_is_diffusers") and self._is_diffusers:
            # Use diffusers inpainting
            if prompt is None:
                prompt = ""
            
            result = self._model(
                prompt=prompt,
                image=image,
                mask_image=mask_img,
                num_inference_steps=30,
            )
            return result.images[0]
        else:
            # Use SimpleLama
            result = self._model(image, mask_img)
            return result
    
    def remove_object(
        self,
        image: Image.Image,
        mask: Union[Image.Image, np.ndarray],
        dilate_pixels: int = 15,
    ) -> Image.Image:
        """
        Remove object defined by mask from image.
        
        Args:
            image: Input image
            mask: Object mask
            dilate_pixels: Mask dilation for cleaner removal
            
        Returns:
            Image with object removed
        """
        return self.inpaint(image, mask, dilate_mask=dilate_pixels)
    
    def unload(self):
        """Unload model."""
        self._model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# ==============================================================================
# Inpaint Anything Pipeline
# ==============================================================================

class InpaintAnything:
    """
    Inpaint Anything: Click to remove any object.
    
    Combines SAM for segmentation and LaMa for inpainting.
    
    Usage:
        inpainter = InpaintAnything()
        
        # Set image
        inpainter.set_image(image)
        
        # Click on object to remove
        result = inpainter.click_to_remove(point=(x, y))
    """
    
    def __init__(
        self,
        sam_model: str = "sam_vit_h",
        device: str = "cuda",
        models_dir: str = "./models",
    ):
        self.device = device
        self.models_dir = Path(models_dir)
        
        self._sam = SAMPredictor(
            model_type=sam_model,
            device=device,
            models_dir=self.models_dir / "sam",
        )
        
        self._lama = LaMaInpainter(
            device=device,
            models_dir=self.models_dir / "lama",
        )
        
        self._current_image = None
        self._current_masks = []
        
        logger.info("InpaintAnything initialized")
    
    def set_image(self, image: Image.Image):
        """Set image for editing."""
        self._current_image = image
        self._current_masks = []
        self._sam.set_image(image)
        
        logger.debug(f"Image set: {image.size}")
    
    def click_to_segment(
        self,
        point: Tuple[int, int],
        add_to_selection: bool = False,
    ) -> Image.Image:
        """
        Click on an object to segment it.
        
        Args:
            point: (x, y) click coordinates
            add_to_selection: Add to existing selection
            
        Returns:
            Visualization of segmented region
        """
        if self._current_image is None:
            raise RuntimeError("Call set_image() first")
        
        # Get mask from click
        mask, score = self._sam.predict_point(point, label=1)
        
        logger.debug(f"Segmented with confidence: {score:.3f}")
        
        if add_to_selection and self._current_masks:
            # Combine with existing masks
            combined = self._current_masks[-1] | mask
            self._current_masks.append(combined)
        else:
            self._current_masks.append(mask)
        
        # Create visualization
        return self._visualize_mask(mask)
    
    def _visualize_mask(
        self,
        mask: np.ndarray,
        color: Tuple[int, int, int] = (255, 0, 0),
        alpha: float = 0.5,
    ) -> Image.Image:
        """Create visualization overlay of mask on image."""
        if self._current_image is None:
            return self._sam.mask_to_image(mask, color)
        
        # Create colored overlay
        overlay = self._current_image.copy().convert("RGBA")
        mask_overlay = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
        
        mask_img = Image.fromarray((mask * 255).astype(np.uint8))
        mask_colored = Image.new("RGBA", overlay.size, (*color, int(alpha * 255)))
        mask_overlay.paste(mask_colored, mask=mask_img)
        
        return Image.alpha_composite(overlay, mask_overlay).convert("RGB")
    
    def click_to_remove(
        self,
        point: Tuple[int, int],
        dilate_mask: int = 15,
    ) -> Image.Image:
        """
        Click on object to remove it.
        
        Args:
            point: (x, y) click coordinates
            dilate_mask: Mask dilation for cleaner removal
            
        Returns:
            Image with object removed
        """
        if self._current_image is None:
            raise RuntimeError("Call set_image() first")
        
        # Segment
        mask, score = self._sam.predict_point(point, label=1)
        
        logger.info(f"Removing object at {point} (confidence: {score:.3f})")
        
        # Remove
        result = self._lama.remove_object(
            self._current_image,
            mask,
            dilate_pixels=dilate_mask,
        )
        
        return result
    
    def remove_selected(
        self,
        dilate_mask: int = 15,
    ) -> Image.Image:
        """
        Remove currently selected (segmented) region.
        
        Args:
            dilate_mask: Mask dilation
            
        Returns:
            Image with selected region removed
        """
        if not self._current_masks:
            raise RuntimeError("No selection. Call click_to_segment() first")
        
        mask = self._current_masks[-1]
        
        result = self._lama.remove_object(
            self._current_image,
            mask,
            dilate_pixels=dilate_mask,
        )
        
        return result
    
    def box_to_remove(
        self,
        box: Tuple[int, int, int, int],
        dilate_mask: int = 15,
    ) -> Image.Image:
        """
        Draw box around object to remove it.
        
        Args:
            box: (x1, y1, x2, y2) bounding box
            dilate_mask: Mask dilation
            
        Returns:
            Image with object removed
        """
        if self._current_image is None:
            raise RuntimeError("Call set_image() first")
        
        # Segment from box
        mask, score = self._sam.predict_box(box)
        
        logger.info(f"Removing object in box (confidence: {score:.3f})")
        
        # Remove
        result = self._lama.remove_object(
            self._current_image,
            mask,
            dilate_pixels=dilate_mask,
        )
        
        return result
    
    def segment_all(self) -> List[Dict[str, Any]]:
        """
        Automatically segment all objects in image.
        
        Returns:
            List of segmentation results
        """
        if self._current_image is None:
            raise RuntimeError("Call set_image() first")
        
        return self._sam.segment_everything()
    
    def remove_by_text(
        self,
        text_prompt: str,
        dilate_mask: int = 15,
    ) -> Image.Image:
        """
        Remove object described by text (requires GroundingDINO).
        
        Args:
            text_prompt: Object description
            dilate_mask: Mask dilation
            
        Returns:
            Image with object removed
        """
        if self._current_image is None:
            raise RuntimeError("Call set_image() first")
        
        try:
            # Try to use GroundingDINO for text-based detection
            from groundingdino.util.inference import load_model, predict
            
            # This would require GroundingDINO model
            logger.warning("GroundingDINO integration not yet implemented")
            raise NotImplementedError("Text-based removal requires GroundingDINO")
            
        except ImportError:
            logger.error("GroundingDINO not installed for text-based removal")
            raise
    
    def get_current_mask(self) -> Optional[np.ndarray]:
        """Get current selection mask."""
        if not self._current_masks:
            return None
        return self._current_masks[-1]
    
    def clear_selection(self):
        """Clear current selection."""
        self._current_masks = []
    
    def undo_selection(self):
        """Undo last selection."""
        if self._current_masks:
            self._current_masks.pop()
    
    def unload(self):
        """Unload all models."""
        self._sam.unload()
        self._lama.unload()
        self._current_image = None
        self._current_masks = []


# ==============================================================================
# Convenience Functions
# ==============================================================================

_inpainter: Optional[InpaintAnything] = None

def get_inpaint_anything() -> InpaintAnything:
    """Get singleton InpaintAnything instance."""
    global _inpainter
    if _inpainter is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _inpainter = InpaintAnything(device=device)
    return _inpainter


def quick_remove(
    image: Image.Image,
    point: Tuple[int, int],
    dilate_mask: int = 15,
) -> Image.Image:
    """
    Quick object removal by point click.
    
    Args:
        image: Input image
        point: Click coordinates
        dilate_mask: Mask dilation
        
    Returns:
        Image with object removed
    """
    inpainter = get_inpaint_anything()
    inpainter.set_image(image)
    return inpainter.click_to_remove(point, dilate_mask)


def quick_segment(
    image: Image.Image,
    point: Tuple[int, int],
) -> Tuple[Image.Image, np.ndarray]:
    """
    Quick segmentation by point click.
    
    Args:
        image: Input image
        point: Click coordinates
        
    Returns:
        Tuple of (visualization, mask array)
    """
    inpainter = get_inpaint_anything()
    inpainter.set_image(image)
    vis = inpainter.click_to_segment(point)
    mask = inpainter.get_current_mask()
    return vis, mask
