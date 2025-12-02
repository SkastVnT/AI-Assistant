"""
Test script for upscale tool
"""
import unittest
import numpy as np
from pathlib import Path
from PIL import Image
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from upscale_tool import ImageUpscaler
from upscale_tool.config import UpscaleConfig, load_config, save_config


class TestUpscaler(unittest.TestCase):
    """Test upscaler functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.test_dir = Path(__file__).parent / 'test_data'
        cls.test_dir.mkdir(exist_ok=True)
        
        # Create test image
        cls.test_image_path = cls.test_dir / 'test.png'
        if not cls.test_image_path.exists():
            img = Image.new('RGB', (100, 100), color='red')
            img.save(cls.test_image_path)
    
    def test_config(self):
        """Test configuration"""
        config = UpscaleConfig()
        self.assertEqual(config.default_model, 'RealESRGAN_x4plus')
        self.assertEqual(config.default_scale, 4)
    
    def test_config_save_load(self):
        """Test config save and load"""
        config = UpscaleConfig()
        config.default_model = 'test_model'
        
        config_path = self.test_dir / 'test_config.yaml'
        save_config(config, str(config_path))
        
        loaded_config = load_config(str(config_path))
        self.assertEqual(loaded_config.default_model, 'test_model')
    
    def test_list_models(self):
        """Test model listing"""
        models = ImageUpscaler.list_models()
        self.assertIsInstance(models, dict)
        self.assertIn('RealESRGAN_x4plus', models)
    
    def test_upscaler_init(self):
        """Test upscaler initialization"""
        # This will fail if dependencies not installed
        try:
            upscaler = ImageUpscaler(
                model='RealESRGAN_x4plus',
                device='cpu'  # Use CPU for testing
            )
            self.assertIsNotNone(upscaler)
        except ImportError:
            self.skipTest("Dependencies not installed")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up"""
        import shutil
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)


if __name__ == '__main__':
    unittest.main()
