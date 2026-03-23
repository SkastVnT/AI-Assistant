"""
ControlNet preprocessing utilities.
"""

import logging
from typing import Optional, Tuple

from PIL import Image
import numpy as np

try:
    from controlnet_aux import (
        CannyDetector,
        OpenposeDetector,
        MidasDetector,
        LineartDetector,
        LineartAnimeDetector,
        HEDdetector,
        PidiNetDetector,
    )
    CONTROLNET_AUX_AVAILABLE = True
except ImportError:
    CONTROLNET_AUX_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


logger = logging.getLogger(__name__)


class ControlNetPreprocessor:
    """
    Preprocessor for ControlNet condition images.
    
    Supports various preprocessing methods:
    - canny: Edge detection
    - openpose: Pose estimation
    - depth: Depth map estimation
    - lineart: Line art extraction
    - lineart_anime: Anime-style line art
    - softedge: Soft edge detection (HED/PidiNet)
    - scribble: Scribble/sketch simulation
    """
    
    def __init__(self):
        self._detectors = {}
    
    def _get_detector(self, detector_type: str):
        """Get or create a detector instance."""
        if detector_type in self._detectors:
            return self._detectors[detector_type]
        
        if not CONTROLNET_AUX_AVAILABLE:
            raise ImportError(
                "controlnet_aux is required for preprocessing. "
                "Install with: pip install controlnet-aux"
            )
        
        detector_classes = {
            "canny": CannyDetector,
            "openpose": OpenposeDetector,
            "depth": MidasDetector,
            "lineart": LineartDetector,
            "lineart_anime": LineartAnimeDetector,
            "softedge": HEDdetector,
            "pidinet": PidiNetDetector,
        }
        
        if detector_type not in detector_classes:
            raise ValueError(f"Unknown detector type: {detector_type}")
        
        detector = detector_classes[detector_type]()
        self._detectors[detector_type] = detector
        return detector
    
    def preprocess(
        self,
        image: Image.Image,
        method: str,
        **kwargs
    ) -> Image.Image:
        """
        Preprocess an image for ControlNet.
        
        Args:
            image: Input PIL Image
            method: Preprocessing method name
            **kwargs: Additional arguments for the detector
            
        Returns:
            Preprocessed PIL Image
        """
        method = method.lower()
        
        # Simple canny using OpenCV (faster, no model needed)
        if method == "canny" and CV2_AVAILABLE:
            return self._canny_opencv(
                image,
                low_threshold=kwargs.get("low_threshold", 100),
                high_threshold=kwargs.get("high_threshold", 200),
            )
        
        # Use controlnet_aux for other methods
        detector = self._get_detector(method)
        result = detector(image, **kwargs)
        
        return result
    
    def _canny_opencv(
        self,
        image: Image.Image,
        low_threshold: int = 100,
        high_threshold: int = 200,
    ) -> Image.Image:
        """
        Apply Canny edge detection using OpenCV.
        
        Args:
            image: Input PIL Image
            low_threshold: Low threshold for hysteresis
            high_threshold: High threshold for hysteresis
            
        Returns:
            Edge map as PIL Image
        """
        # Convert to numpy
        img_array = np.array(image.convert("RGB"))
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Apply Canny
        edges = cv2.Canny(gray, low_threshold, high_threshold)
        
        # Convert back to PIL (invert for white edges on black)
        return Image.fromarray(edges)
    
    def batch_preprocess(
        self,
        images: list,
        method: str,
        **kwargs
    ) -> list:
        """
        Preprocess multiple images.
        
        Args:
            images: List of PIL Images
            method: Preprocessing method name
            **kwargs: Additional arguments
            
        Returns:
            List of preprocessed PIL Images
        """
        return [self.preprocess(img, method, **kwargs) for img in images]


# Global preprocessor instance
_preprocessor: Optional[ControlNetPreprocessor] = None


def get_preprocessor() -> ControlNetPreprocessor:
    """Get or create the global preprocessor instance."""
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = ControlNetPreprocessor()
    return _preprocessor


def preprocess_for_controlnet(
    image: Image.Image,
    method: str,
    **kwargs
) -> Image.Image:
    """
    Convenience function to preprocess an image for ControlNet.
    
    Args:
        image: Input PIL Image
        method: Preprocessing method
        **kwargs: Additional arguments
        
    Returns:
        Preprocessed PIL Image
    """
    preprocessor = get_preprocessor()
    return preprocessor.preprocess(image, method, **kwargs)
