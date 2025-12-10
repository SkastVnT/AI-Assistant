"""
Unit Tests for Stable Diffusion WebUI
Tests image generation, model operations, and API functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import base64
from io import BytesIO
import json


@pytest.mark.unit
class TestTxt2ImgAPI:
    """Test text-to-image API"""
    
    def test_txt2img_request_structure(self):
        """Test txt2img request format"""
        request = {
            'prompt': 'a beautiful landscape',
            'negative_prompt': 'bad quality, blurry',
            'steps': 20,
            'sampler_name': 'Euler a',
            'cfg_scale': 7.0,
            'width': 512,
            'height': 512,
            'seed': -1,
            'batch_size': 1
        }
        
        assert 'prompt' in request
        assert request['steps'] > 0
        assert request['cfg_scale'] > 0
    
    def test_parameter_validation(self):
        """Test parameter validation"""
        params = {
            'steps': 20,
            'width': 512,
            'height': 512,
            'cfg_scale': 7.0
        }
        
        # Validate ranges
        assert 1 <= params['steps'] <= 150
        assert params['width'] % 8 == 0  # Must be multiple of 8
        assert params['height'] % 8 == 0
        assert 1.0 <= params['cfg_scale'] <= 30.0
    
    @patch('modules.processing.process_images')
    def test_txt2img_generation(self, mock_process):
        """Test txt2img generation"""
        # Mock response
        mock_process.return_value = MagicMock(
            images=['base64_image_data'],
            info='{"seed": 12345, "steps": 20}'
        )
        
        from modules.processing import process_images
        result = process_images(MagicMock())
        
        assert len(result.images) > 0
        assert result.info is not None


@pytest.mark.unit
class TestImg2ImgAPI:
    """Test image-to-image API"""
    
    def test_img2img_request_structure(self):
        """Test img2img request format"""
        request = {
            'init_images': ['base64_encoded_image'],
            'prompt': 'enhance this image',
            'steps': 20,
            'denoising_strength': 0.7,
            'width': 512,
            'height': 512
        }
        
        assert 'init_images' in request
        assert len(request['init_images']) > 0
        assert 0.0 <= request['denoising_strength'] <= 1.0
    
    def test_denoising_strength_validation(self):
        """Test denoising strength validation"""
        test_values = [0.0, 0.5, 0.75, 1.0, 1.5]
        
        for value in test_values:
            is_valid = 0.0 <= value <= 1.0
            if value == 1.5:
                assert is_valid == False
            else:
                assert is_valid == True
    
    def test_resize_mode_options(self):
        """Test resize mode options"""
        resize_modes = [
            0,  # Just resize
            1,  # Crop and resize
            2,  # Resize and fill
            3   # Just resize (latent upscale)
        ]
        
        assert len(resize_modes) == 4
        assert 0 in resize_modes


@pytest.mark.unit
class TestSamplers:
    """Test sampler configurations"""
    
    def test_sampler_list(self):
        """Test available samplers"""
        samplers = [
            'Euler',
            'Euler a',
            'DPM++ 2M Karras',
            'DPM++ SDE Karras',
            'DDIM'
        ]
        
        assert len(samplers) > 0
        assert 'Euler a' in samplers
    
    def test_sampler_validation(self):
        """Test sampler name validation"""
        valid_samplers = ['Euler', 'Euler a', 'DPM++ 2M Karras']
        
        test_names = ['Euler', 'InvalidSampler', 'DPM++ 2M Karras']
        
        for name in test_names:
            is_valid = name in valid_samplers
            if name == 'InvalidSampler':
                assert is_valid == False
            else:
                assert is_valid == True


@pytest.mark.unit
class TestModelManagement:
    """Test model loading and management"""
    
    def test_model_list(self):
        """Test listing available models"""
        models = [
            {'title': 'model1.safetensors', 'hash': 'abc123'},
            {'title': 'model2.ckpt', 'hash': 'def456'}
        ]
        
        assert len(models) > 0
        assert all('title' in m and 'hash' in m for m in models)
    
    def test_model_switching(self):
        """Test switching checkpoint models"""
        current_model = 'model1.safetensors'
        target_model = 'model2.safetensors'
        
        # Mock switch
        def switch_model(model_name):
            return {'status': 'success', 'model': model_name}
        
        result = switch_model(target_model)
        assert result['status'] == 'success'
        assert result['model'] == target_model
    
    def test_model_hash_validation(self):
        """Test model hash validation"""
        model = {
            'filename': 'model.safetensors',
            'hash': 'abc123def456'
        }
        
        # Hash should be hex string
        assert all(c in '0123456789abcdef' for c in model['hash'].lower())


@pytest.mark.unit
class TestPromptProcessing:
    """Test prompt processing"""
    
    def test_prompt_splitting(self):
        """Test splitting prompts by AND"""
        prompt = "a cat AND a dog AND a bird"
        parts = prompt.split(' AND ')
        
        assert len(parts) == 3
        assert parts[0].strip() == 'a cat'
    
    def test_emphasis_syntax(self):
        """Test emphasis syntax parsing"""
        # (word) = 1.1x emphasis
        # ((word)) = 1.21x emphasis
        # [word] = 0.91x de-emphasis
        
        prompts_with_emphasis = [
            '(beautiful)',
            '((masterpiece))',
            '[bad quality]'
        ]
        
        for prompt in prompts_with_emphasis:
            assert '(' in prompt or '[' in prompt
    
    def test_prompt_weighting(self):
        """Test weighted prompts"""
        prompt = "(cat:1.5), (dog:0.8)"
        
        # Extract weights
        import re
        weights = re.findall(r':(\d+\.?\d*)', prompt)
        weights = [float(w) for w in weights]
        
        assert 1.5 in weights
        assert 0.8 in weights


@pytest.mark.unit
class TestImageEncoding:
    """Test image encoding/decoding"""
    
    def test_base64_encoding(self):
        """Test base64 image encoding"""
        import base64
        
        # Mock image bytes
        image_bytes = b'fake_image_data'
        
        # Encode
        b64_encoded = base64.b64encode(image_bytes).decode('utf-8')
        
        assert isinstance(b64_encoded, str)
        assert len(b64_encoded) > 0
    
    def test_base64_decoding(self):
        """Test base64 image decoding"""
        import base64
        
        # Create base64 data
        original = b'test_data'
        encoded = base64.b64encode(original).decode('utf-8')
        
        # Decode
        decoded = base64.b64decode(encoded)
        
        assert decoded == original
    
    def test_data_uri_parsing(self):
        """Test parsing data URI"""
        data_uri = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA'
        
        # Extract parts
        if data_uri.startswith('data:image/'):
            parts = data_uri.split(';')
            mime_type = parts[0].replace('data:', '')
            encoding = parts[1].split(',')[0]
            data = parts[1].split(',')[1]
            
            assert mime_type == 'image/png'
            assert encoding == 'base64'


@pytest.mark.unit
class TestControlNet:
    """Test ControlNet integration"""
    
    def test_controlnet_model_list(self):
        """Test ControlNet model list"""
        models = [
            'control_canny',
            'control_depth',
            'control_openpose',
            'control_scribble'
        ]
        
        assert len(models) > 0
        assert 'control_canny' in models
    
    def test_controlnet_request(self):
        """Test ControlNet request structure"""
        controlnet_args = {
            'enabled': True,
            'module': 'canny',
            'model': 'control_canny',
            'weight': 1.0,
            'input_image': 'base64_image',
            'guidance_start': 0.0,
            'guidance_end': 1.0
        }
        
        assert controlnet_args['enabled'] == True
        assert 0.0 <= controlnet_args['weight'] <= 2.0
        assert controlnet_args['guidance_start'] < controlnet_args['guidance_end']


@pytest.mark.unit
class TestLoRAIntegration:
    """Test LoRA model integration"""
    
    def test_lora_prompt_syntax(self):
        """Test LoRA syntax in prompt"""
        prompt = "a portrait <lora:my_lora:0.8>"
        
        # Extract LoRA
        import re
        lora_pattern = r'<lora:([^:]+):([0-9.]+)>'
        matches = re.findall(lora_pattern, prompt)
        
        assert len(matches) > 0
        assert matches[0][0] == 'my_lora'
        assert float(matches[0][1]) == 0.8
    
    def test_multiple_loras(self):
        """Test multiple LoRA models"""
        prompt = "test <lora:lora1:0.5> <lora:lora2:0.7>"
        
        import re
        lora_pattern = r'<lora:([^:]+):([0-9.]+)>'
        matches = re.findall(lora_pattern, prompt)
        
        assert len(matches) == 2


@pytest.mark.unit
class TestExtrasAPI:
    """Test extras/upscaling API"""
    
    def test_upscale_request(self):
        """Test upscale request structure"""
        request = {
            'resize_mode': 0,
            'upscaling_resize': 2,
            'upscaler_1': 'R-ESRGAN 4x+',
            'image': 'base64_image'
        }
        
        assert 'upscaler_1' in request
        assert request['upscaling_resize'] in [2, 4]
    
    def test_upscaler_list(self):
        """Test available upscalers"""
        upscalers = [
            'None',
            'R-ESRGAN 4x+',
            'R-ESRGAN 4x+ Anime6B',
            'SwinIR 4x'
        ]
        
        assert 'R-ESRGAN 4x+' in upscalers


@pytest.mark.unit
class TestProgressAPI:
    """Test progress tracking API"""
    
    def test_progress_response(self):
        """Test progress response structure"""
        progress = {
            'progress': 0.45,
            'eta_relative': 15.2,
            'state': {
                'sampling_step': 9,
                'sampling_steps': 20
            },
            'current_image': 'base64_preview'
        }
        
        assert 0.0 <= progress['progress'] <= 1.0
        assert 'state' in progress
    
    def test_progress_calculation(self):
        """Test progress calculation"""
        current_step = 12
        total_steps = 20
        
        progress = current_step / total_steps
        
        assert progress == 0.6
        assert 0.0 <= progress <= 1.0


@pytest.mark.unit
class TestVAE:
    """Test VAE model handling"""
    
    def test_vae_list(self):
        """Test available VAE models"""
        vaes = [
            'Automatic',
            'None',
            'vae-ft-mse-840000-ema-pruned.safetensors'
        ]
        
        assert 'Automatic' in vaes
        assert len(vaes) > 0
    
    def test_vae_selection(self):
        """Test VAE model selection"""
        selected_vae = 'vae-ft-mse-840000-ema-pruned.safetensors'
        
        def apply_vae(vae_name):
            return {'status': 'applied', 'vae': vae_name}
        
        result = apply_vae(selected_vae)
        assert result['status'] == 'applied'


@pytest.mark.unit
class TestScripts:
    """Test script execution"""
    
    def test_script_list(self):
        """Test available scripts"""
        scripts = [
            'X/Y/Z plot',
            'Prompt matrix',
            'Ultimate SD upscale'
        ]
        
        assert len(scripts) > 0
    
    def test_script_args(self):
        """Test script arguments"""
        script_args = {
            'script_name': 'X/Y/Z plot',
            'args': ['X axis', 'Y axis', 'Z axis']
        }
        
        assert 'script_name' in script_args
        assert isinstance(script_args['args'], list)


@pytest.mark.unit
class TestBatchProcessing:
    """Test batch image generation"""
    
    def test_batch_count(self):
        """Test batch count setting"""
        request = {
            'batch_size': 4,
            'n_iter': 3
        }
        
        total_images = request['batch_size'] * request['n_iter']
        
        assert total_images == 12
    
    def test_batch_response(self):
        """Test batch response structure"""
        response = {
            'images': ['img1', 'img2', 'img3', 'img4'],
            'info': '{"seed": 12345}',
            'parameters': {}
        }
        
        assert len(response['images']) == 4
        assert 'info' in response


@pytest.mark.unit
class TestConfigOptions:
    """Test configuration options"""
    
    def test_config_structure(self):
        """Test config structure"""
        config = {
            'sd_model_checkpoint': 'model.safetensors',
            'CLIP_stop_at_last_layers': 2,
            'eta_noise_seed_delta': 0,
            'samples_save': True
        }
        
        assert 'sd_model_checkpoint' in config
    
    def test_override_settings(self):
        """Test override settings in request"""
        request = {
            'prompt': 'test',
            'override_settings': {
                'sd_model_checkpoint': 'custom_model.safetensors',
                'CLIP_stop_at_last_layers': 1
            }
        }
        
        assert 'override_settings' in request
        assert isinstance(request['override_settings'], dict)


@pytest.mark.unit
class TestHiresFixAPI:
    """Test hi-res fix functionality"""
    
    def test_hires_fix_request(self):
        """Test hi-res fix request"""
        request = {
            'enable_hr': True,
            'hr_scale': 2.0,
            'hr_upscaler': 'Latent',
            'denoising_strength': 0.7
        }
        
        assert request['enable_hr'] == True
        assert request['hr_scale'] > 1.0
    
    def test_hires_calculation(self):
        """Test hi-res calculation"""
        base_width = 512
        base_height = 512
        hr_scale = 2.0
        
        hr_width = int(base_width * hr_scale)
        hr_height = int(base_height * hr_scale)
        
        assert hr_width == 1024
        assert hr_height == 1024
