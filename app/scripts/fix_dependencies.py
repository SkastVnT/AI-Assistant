#!/usr/bin/env python3
"""
Dependency Conflict Resolver for AI-Assistant
Handles protobuf and other version conflicts.

Usage:
    python scripts/fix_dependencies.py
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def run_pip(args: list, check: bool = True) -> subprocess.CompletedProcess:
    """Run pip with given arguments."""
    cmd = [sys.executable, '-m', 'pip'] + args
    logger.info(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def fix_protobuf_conflict():
    """
    Fix protobuf version conflict.
    
    Issue: onnx requires protobuf>=4.25.1 but some packages need 3.20.x
    Solution: Use protobuf 4.x and skip onnx if not needed, or use compatible version
    """
    logger.info("=" * 60)
    logger.info("Fixing protobuf version conflict...")
    logger.info("=" * 60)
    
    # Check if onnx is actually needed
    try:
        import onnx
        onnx_needed = True
        logger.info(f"onnx is installed: {onnx.__version__}")
    except ImportError:
        onnx_needed = False
        logger.info("onnx is not installed")
    
    if onnx_needed:
        # Install protobuf 4.x for onnx compatibility
        logger.info("Installing protobuf 4.x for onnx compatibility...")
        result = run_pip(['install', 'protobuf>=4.25.1', '--upgrade'], check=False)
        if result.returncode != 0:
            logger.warning(f"Failed to upgrade protobuf: {result.stderr}")
    else:
        # Keep protobuf 3.x for other packages
        logger.info("Keeping protobuf 3.x (onnx not needed)")
        
    logger.info("Protobuf conflict resolution complete.")


def fix_numpy_conflict():
    """
    Fix numpy version conflict.
    
    Issue: Different packages require different numpy versions
    Solution: Install a version compatible with most packages
    """
    logger.info("=" * 60)
    logger.info("Fixing numpy version conflict...")
    logger.info("=" * 60)
    
    # Numpy 2.2.x is compatible with most modern packages
    result = run_pip(['install', 'numpy>=2.2.0,<2.3.0', '--upgrade'], check=False)
    if result.returncode == 0:
        logger.info("Numpy version fixed successfully")
    else:
        logger.warning(f"Failed to fix numpy: {result.stderr}")


def fix_opencv_conflict():
    """
    Fix opencv version conflict.
    
    Issue: opencv-python and opencv-python-headless conflict
    Solution: Remove one and keep the other
    """
    logger.info("=" * 60)
    logger.info("Fixing OpenCV conflict...")
    logger.info("=" * 60)
    
    # Check which is installed
    try:
        import cv2
        logger.info(f"OpenCV is installed: {cv2.__version__}")
    except ImportError:
        logger.info("OpenCV is not installed")
        return
    
    # Remove headless if regular is needed (for GUI support)
    result = run_pip(['uninstall', 'opencv-python-headless', '-y'], check=False)
    if "not installed" not in result.stderr.lower():
        logger.info("Removed opencv-python-headless")
    
    logger.info("OpenCV conflict resolution complete.")


def verify_dependencies():
    """Verify that key dependencies are working."""
    logger.info("=" * 60)
    logger.info("Verifying dependencies...")
    logger.info("=" * 60)
    
    test_imports = [
        ('numpy', 'np'),
        ('torch', 'torch'),
        ('PIL', 'Image'),
        ('flask', 'Flask'),
        ('pymongo', 'MongoClient'),
        ('redis', 'Redis'),
    ]
    
    for module, attr in test_imports:
        try:
            exec(f"import {module}")
            logger.info(f"✅ {module} - OK")
        except ImportError as e:
            logger.warning(f"❌ {module} - FAILED: {e}")
    
    logger.info("Dependency verification complete.")


def main():
    """Run all fixes."""
    logger.info("AI-Assistant Dependency Conflict Resolver")
    logger.info("=" * 60)
    
    fix_numpy_conflict()
    fix_protobuf_conflict()
    fix_opencv_conflict()
    verify_dependencies()
    
    logger.info("=" * 60)
    logger.info("All dependency fixes applied!")
    logger.info("Please restart your services.")


if __name__ == '__main__':
    main()
