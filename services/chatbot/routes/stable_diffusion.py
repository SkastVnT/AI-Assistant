"""
Stable Diffusion routes
"""
import os
import sys
import json
import base64
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, session
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import IMAGE_STORAGE_DIR, OPENAI_API_KEY, DEEPSEEK_API_KEY
from core.extensions import (
    MONGODB_ENABLED, CLOUD_UPLOAD_ENABLED, 
    ConversationDB, logger
)
from core.db_helpers import get_user_id_from_session

# Import model presets - use direct file import to avoid path conflicts
try:
    import importlib.util
    _preset_path = CHATBOT_DIR / "config" / "model_presets.py"
    _spec = importlib.util.spec_from_file_location("model_presets", _preset_path)
    _presets_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_presets_module)
    
    MODEL_PRESETS = _presets_module.MODEL_PRESETS
    CATEGORIES = _presets_module.CATEGORIES
    QUICK_PRESETS = _presets_module.QUICK_PRESETS
    get_preset = _presets_module.get_preset
    get_all_presets = _presets_module.get_all_presets
    get_presets_by_category = _presets_module.get_presets_by_category
    PRESETS_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Model presets load failed: {e}")
    PRESETS_AVAILABLE = False
    MODEL_PRESETS = {}
    QUICK_PRESETS = []

# Import ImgBBUploader if available
ImgBBUploader = None
try:
    from src.utils.imgbb_uploader import ImgBBUploader
except ImportError:
    pass

sd_bp = Blueprint('sd', __name__)


# ============================================================================
# HEALTH & CONFIG
# ============================================================================

@sd_bp.route('/api/sd-health', methods=['GET'])
@sd_bp.route('/sd-api/status', methods=['GET'])
def sd_health():
    """Check Stable Diffusion API status (ComfyUI)"""
    try:
        # Try ComfyUI first
        try:
            from src.utils.comfyui_client import get_comfyui_client
            sd_api_url = os.getenv('COMFYUI_URL', os.getenv('SD_API_URL', 'http://127.0.0.1:8189'))
            sd_client = get_comfyui_client(sd_api_url)
        except ImportError:
            from src.utils.sd_client import get_sd_client
            sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:8189')
            sd_client = get_sd_client(sd_api_url)
        
        is_running = sd_client.check_health()
        
        if is_running:
            current_model = sd_client.get_current_model()
            response = jsonify({
                'status': 'online',
                'api_url': sd_api_url,
                'current_model': current_model,
                'backend': 'comfyui'
            })
        else:
            response = jsonify({
                'status': 'offline',
                'api_url': sd_api_url,
                'message': 'ComfyUI is not running'
            })
            response.status_code = 503
        
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response
        
    except Exception as e:
        logger.error(f"[SD Health Check] Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@sd_bp.route('/api/sd-models', methods=['GET'])
@sd_bp.route('/sd-api/models', methods=['GET'])
def sd_models():
    """Get checkpoint models list"""
    try:
        # Try ComfyUI first
        try:
            from src.utils.comfyui_client import get_comfyui_client
            sd_client = get_comfyui_client()
            models = sd_client.get_models()
            current = sd_client.get_current_model()
            return jsonify({
                'models': models,
                'current_model': current
            })
        except ImportError:
            from src.utils.sd_client import get_sd_client
            sd_client = get_sd_client()
            models = sd_client.get_models()
            current = sd_client.get_current_model()
            model_titles = [model.get('title', model.get('model_name', 'Unknown')) for model in models]
            return jsonify({
                'models': model_titles,
                'current_model': current['model']
            })
        
    except Exception as e:
        logger.error(f"[SD Models] Error: {e}")
        return jsonify({'error': 'Failed to retrieve SD models'}), 500


@sd_bp.route('/api/sd-change-model', methods=['POST'])
@sd_bp.route('/api/sd/change-model', methods=['POST'])
def sd_change_model():
    """Change checkpoint model"""
    try:
        from src.utils.sd_client import get_sd_client
        
        data = request.json
        model_name = data.get('model_name')
        
        if not model_name:
            return jsonify({'error': 'model_name is required'}), 400
        
        sd_client = get_sd_client()
        success = sd_client.change_model(model_name)
        
        if success:
            return jsonify({'success': True, 'message': f'Đã đổi model thành {model_name}'})
        else:
            return jsonify({'success': False, 'error': 'Không thể đổi model'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# MODEL PRESETS
# ============================================================================

@sd_bp.route('/api/sd-presets', methods=['GET'])
@sd_bp.route('/api/sd/presets', methods=['GET'])
def sd_presets():
    """Get all model presets"""
    try:
        if PRESETS_AVAILABLE:
            return jsonify({
                'success': True,
                'presets': MODEL_PRESETS,
                'quick_presets': QUICK_PRESETS,
                'categories': get_all_presets()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Presets not available'
            }), 404
    except Exception as e:
        logger.error(f"[Presets] Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sd_bp.route('/api/sd-presets/<preset_id>', methods=['GET'])
@sd_bp.route('/api/sd/presets/<preset_id>', methods=['GET'])
def sd_preset_detail(preset_id):
    """Get specific preset details"""
    try:
        if PRESETS_AVAILABLE:
            preset = get_preset(preset_id)
            if preset:
                return jsonify({
                    'success': True,
                    'preset_id': preset_id,
                    'preset': preset
                })
            else:
                return jsonify({'success': False, 'error': 'Preset not found'}), 404
        else:
            return jsonify({'success': False, 'error': 'Presets not available'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@sd_bp.route('/api/sd-samplers', methods=['GET'])
@sd_bp.route('/sd-api/samplers', methods=['GET'])
@sd_bp.route('/api/sd/samplers', methods=['GET'])
def sd_samplers():
    """Get samplers list"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_client = get_sd_client()
        samplers = sd_client.get_samplers()
        
        return jsonify({'success': True, 'samplers': samplers})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@sd_bp.route('/api/sd-loras', methods=['GET'])
@sd_bp.route('/sd-api/loras', methods=['GET'])
def sd_loras():
    """Get LoRA models list"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_client = get_sd_client()
        loras_raw = sd_client.get_loras()
        
        loras_simple = []
        if isinstance(loras_raw, list):
            for lora in loras_raw:
                if isinstance(lora, dict):
                    name = lora.get('alias') or lora.get('name') or str(lora)
                    loras_simple.append({'name': name})
                else:
                    loras_simple.append({'name': str(lora)})
        
        return jsonify({'loras': loras_simple})
        
    except Exception as e:
        logger.error(f"[LoRAs] Error: {e}")
        return jsonify({'error': 'Failed to retrieve LoRAs'}), 500


@sd_bp.route('/api/sd-vaes', methods=['GET'])
@sd_bp.route('/sd-api/vaes', methods=['GET'])
def sd_vaes():
    """Get VAE models list"""
    try:
        from src.utils.sd_client import get_sd_client
        
        sd_client = get_sd_client()
        vaes_raw = sd_client.get_vaes()
        
        vae_names = []
        if isinstance(vaes_raw, list):
            for vae in vaes_raw:
                if isinstance(vae, dict):
                    name = vae.get('model_name') or vae.get('name') or str(vae)
                    vae_names.append(name)
                else:
                    vae_names.append(str(vae))
        
        return jsonify({'vaes': vae_names})
        
    except Exception as e:
        logger.error(f"[VAEs] Error: {e}")
        return jsonify({'error': 'Failed to retrieve VAEs'}), 500


# ============================================================================
# IMAGE GENERATION
# ============================================================================

@sd_bp.route('/api/generate-image', methods=['POST'])
@sd_bp.route('/sd-api/text2img', methods=['POST'])
def generate_image():
    """Generate image from text prompt using ComfyUI"""
    try:
        # Try ComfyUI first
        try:
            from src.utils.comfyui_client import get_comfyui_client
            sd_client = get_comfyui_client()
            use_comfyui = True
        except ImportError:
            from src.utils.sd_client import get_sd_client
            sd_client = get_sd_client()
            use_comfyui = False
        
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        save_to_storage = data.get('save_to_storage', False)
        
        # Check if using preset
        preset_id = data.get('preset', data.get('style', None))
        preset_config = {}
        
        if preset_id and PRESETS_AVAILABLE:
            preset_config = get_preset(preset_id) or {}
            logger.info(f"[TEXT2IMG] Using preset: {preset_id}")
        
        # ComfyUI parameters - preset values as defaults, request values override
        params = {
            'prompt': prompt,
            'negative_prompt': data.get('negative_prompt') or preset_config.get('negative_prompt', 'bad quality, blurry, distorted'),
            'width': int(data.get('width') or preset_config.get('width', 1024)),
            'height': int(data.get('height') or preset_config.get('height', 1024)),
            'steps': int(data.get('steps') or preset_config.get('steps', 20)),
            'cfg_scale': float(data.get('cfg_scale') or preset_config.get('cfg_scale', 7.0)),
            'seed': int(data.get('seed') or -1),
            'model': data.get('model') or preset_config.get('model', None)
        }
        
        logger.info(f"[TEXT2IMG] Generating with model: {params.get('model')}, prompt: {prompt[:50]}...")
        
        if use_comfyui:
            # Use ComfyUI generate_image method
            image_bytes = sd_client.generate_image(**params)
            
            if image_bytes:
                import base64
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                base64_images = [base64_image]
            else:
                return jsonify({'error': 'Failed to generate image'}), 500
        else:
            # Fallback to A1111 API
            result = sd_client.txt2img(**params)
            if 'error' in result:
                return jsonify(result), 500
            base64_images = result.get('images', [])
        
        if not base64_images:
            return jsonify({'error': 'No images generated'}), 500
        
        saved_filenames = []
        cloud_urls = []
        
        if save_to_storage:
            saved_filenames, cloud_urls = _save_images_to_storage(
                base64_images, 'generated', prompt, params
            )
            
            if MONGODB_ENABLED and saved_filenames:
                _save_image_to_mongodb(saved_filenames, cloud_urls, prompt, params, 'text2img')
        
        response_data = {
            'success': True,
            'images': saved_filenames if saved_filenames else base64_images,
            'image': (saved_filenames[0] if saved_filenames else base64_images[0]) if (saved_filenames or base64_images) else None,
            'base64_images': base64_images,
            'cloud_urls': cloud_urls,
            'cloud_url': cloud_urls[0] if cloud_urls else None,
            'backend': 'comfyui' if use_comfyui else 'a1111'
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        logger.error(f"[TEXT2IMG] Error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@sd_bp.route('/api/img2img', methods=['POST'])
@sd_bp.route('/sd-api/img2img', methods=['POST'])
def img2img():
    """Generate image from image"""
    try:
        from src.utils.sd_client import get_sd_client
        
        data = request.json
        image = data.get('image', '')
        prompt = data.get('prompt', '')
        
        if not image:
            return jsonify({'error': 'Image không được để trống'}), 400
        
        if not prompt:
            return jsonify({'error': 'Prompt không được để trống'}), 400
        
        params = {
            'init_images': [image],
            'prompt': prompt,
            'negative_prompt': data.get('negative_prompt', ''),
            'denoising_strength': float(data.get('denoising_strength') or 0.8),
            'width': int(data.get('width') or 512),
            'height': int(data.get('height') or 512),
            'steps': int(data.get('steps') or 30),
            'cfg_scale': float(data.get('cfg_scale') or 7.0),
            'sampler_name': data.get('sampler_name') or 'DPM++ 2M Karras',
            'seed': int(data.get('seed') or -1),
            'restore_faces': data.get('restore_faces', False),
            'lora_models': data.get('lora_models', []),
            'vae': data.get('vae', None)
        }
        
        sd_client = get_sd_client()
        logger.info(f"[IMG2IMG] Generating with denoising={params['denoising_strength']}")
        result = sd_client.img2img(**params)
        
        if 'error' in result:
            return jsonify({'error': 'Failed to generate image'}), 500
        
        base64_images = result.get('images', [])
        
        if not base64_images:
            return jsonify({'error': 'No images generated'}), 500
        
        save_to_storage = data.get('save_to_storage', False)
        saved_filenames = []
        cloud_urls = []
        
        if save_to_storage:
            saved_filenames, cloud_urls = _save_images_to_storage(
                base64_images, 'img2img', prompt, params
            )
            
            if MONGODB_ENABLED and saved_filenames:
                _save_image_to_mongodb(saved_filenames, cloud_urls, prompt, params, 'img2img')
        
        return jsonify({
            'success': True,
            'image': base64_images[0] if base64_images else None,
            'images': base64_images,
            'filenames': saved_filenames,
            'cloud_urls': cloud_urls,
            'info': result.get('info', ''),
            'parameters': result.get('parameters', {})
        })
        
    except Exception as e:
        import traceback
        logger.error(f"[IMG2IMG] Error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': 'Failed to process img2img request'}), 500


# ============================================================================
# PROMPT GENERATION
# ============================================================================

@sd_bp.route('/api/generate-prompt-grok', methods=['POST'])
@sd_bp.route('/api/generate-prompt', methods=['POST'])
def generate_prompt():
    """Generate optimized prompt from tags"""
    try:
        data = request.json
        context = data.get('context', '')
        tags = data.get('tags', [])
        selected_model = data.get('model', 'grok').lower()
        
        if not tags:
            return jsonify({'error': 'Tags không được để trống'}), 400
        
        system_prompt = """You are an expert at creating high-quality Stable Diffusion prompts.

Task:
1. Generate a POSITIVE prompt combining extracted features with quality boosters
2. Generate a NEGATIVE prompt to avoid low quality and NSFW content
3. Return JSON: {"prompt": "...", "negative_prompt": "..."}

Rules:
- Start with: masterpiece, best quality, highly detailed
- Include visual features from tags
- Negative MUST include: nsfw, nude, sexual, explicit, bad quality
- Output ONLY valid JSON"""

        try:
            if selected_model == 'grok':
                result = _generate_with_grok(context, system_prompt, tags)
            elif selected_model == 'openai':
                result = _generate_with_openai(context, system_prompt, tags)
            elif selected_model == 'deepseek':
                result = _generate_with_deepseek(context, system_prompt, tags)
            else:
                result = _generate_fallback(tags)
            
            return jsonify(result)
            
        except Exception as model_error:
            logger.error(f"[Prompt Gen] Model error: {model_error}")
            result = _generate_fallback(tags)
            result['fallback'] = True
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"[Prompt Gen] Error: {e}")
        return jsonify({'error': 'Failed to generate prompt'}), 500


# ============================================================================
# SHARE / UPLOAD
# ============================================================================

@sd_bp.route('/api/share-image-imgbb', methods=['POST'])
def share_image_imgbb():
    """Upload image to ImgBB"""
    try:
        data = request.json
        base64_image = data.get('image', '')
        title = data.get('title', f'AI_Generated_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        
        if not base64_image:
            return jsonify({'error': 'No image provided'}), 400
        
        if ',' in base64_image:
            base64_image = base64_image.split(',')[1]
        
        uploader = ImgBBUploader()
        result = uploader.upload(base64_image, title=title)
        
        if result and result.get('url'):
            return jsonify({
                'success': True,
                'url': result['url'],
                'display_url': result.get('display_url', result['url']),
                'delete_url': result.get('delete_url'),
                'thumb_url': result.get('thumb', {}).get('url'),
                'title': title
            })
        else:
            return jsonify({'error': 'ImgBB upload failed'}), 500
            
    except Exception as e:
        logger.error(f"[ImgBB Share] Error: {e}")
        return jsonify({'error': 'Failed to upload image'}), 500


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _save_images_to_storage(base64_images, prefix, prompt, params):
    """Save images to storage and optionally upload to cloud"""
    saved_filenames = []
    cloud_urls = []
    
    for idx, image_base64 in enumerate(base64_images):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{prefix}_{timestamp}_{idx}.png"
            filepath = IMAGE_STORAGE_DIR / filename
            
            image_data = base64.b64decode(image_base64)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            saved_filenames.append(filename)
            logger.info(f"[SD] Saved locally: {filename}")
            
            # Upload to ImgBB
            cloud_url = None
            delete_url = None
            
            if CLOUD_UPLOAD_ENABLED:
                try:
                    uploader = ImgBBUploader()
                    upload_result = uploader.upload_image(str(filepath), title=f"AI: {prompt[:50]}")
                    
                    if upload_result:
                        cloud_url = upload_result['url']
                        delete_url = upload_result.get('delete_url', '')
                        cloud_urls.append(cloud_url)
                        logger.info(f"[SD] ☁️ ImgBB URL: {cloud_url}")
                except Exception as e:
                    logger.error(f"[SD] ImgBB error: {e}")
            
            # Save metadata
            metadata_file = filepath.with_suffix('.json')
            metadata = {
                'filename': filename,
                'created_at': datetime.now().isoformat(),
                'prompt': prompt,
                'negative_prompt': params.get('negative_prompt', ''),
                'parameters': {k: v for k, v in params.items() if k != 'init_images'},
                'cloud_url': cloud_url,
                'delete_url': delete_url,
                'service': 'imgbb' if cloud_url else 'local'
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"[SD] Error saving image {idx}: {e}")
    
    return saved_filenames, cloud_urls


def _save_image_to_mongodb(filenames, cloud_urls, prompt, params, model_type):
    """Save image info to MongoDB"""
    try:
        user_id = get_user_id_from_session()
        conversation_id = session.get('conversation_id')
        
        if not conversation_id:
            conversation = ConversationDB.create_conversation(
                user_id=user_id,
                model='stable-diffusion',
                title=f"{model_type}: {prompt[:30]}..."
            )
            conversation_id = str(conversation['_id'])
            session['conversation_id'] = conversation_id
        
        images_data = []
        for idx, filename in enumerate(filenames):
            cloud_url = cloud_urls[idx] if idx < len(cloud_urls) else None
            images_data.append({
                'url': f"/static/Storage/Image_Gen/{filename}",
                'cloud_url': cloud_url,
                'caption': f"{model_type}: {prompt[:50]}",
                'generated': True,
                'service': 'imgbb' if cloud_url else 'local',
                'mime_type': 'image/png'
            })
        
        save_message_to_db(
            conversation_id=conversation_id,
            role='assistant',
            content=f"✅ Generated {model_type} with prompt: {prompt}",
            metadata={
                'model': f'stable-diffusion-{model_type}',
                'prompt': prompt,
                'negative_prompt': params.get('negative_prompt', ''),
                'num_images': len(filenames)
            }
        )
        
        logger.info(f"💾 Saved {model_type} to MongoDB")
        
    except Exception as e:
        logger.error(f"❌ MongoDB save error: {e}")


def _generate_with_grok(context, system_prompt, tags):
    """Generate prompt using GROK"""
    from openai import OpenAI
    
    api_key = os.getenv('GROK_API_KEY') or os.getenv('XAI_API_KEY')
    if not api_key:
        raise ValueError('GROK API key not configured')
    
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
    
    response = client.chat.completions.create(
        model="grok-3",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ],
        temperature=0.7,
        max_tokens=500,
        response_format={"type": "json_object"}
    )
    
    result_json = json.loads(response.choices[0].message.content.strip())
    return _process_prompt_result(result_json, tags, 'grok')


def _generate_with_openai(context, system_prompt, tags):
    """Generate prompt using OpenAI"""
    import openai
    
    if not OPENAI_API_KEY:
        raise ValueError('OpenAI API key not configured')
    
    openai.api_key = OPENAI_API_KEY
    
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ],
        temperature=0.7,
        max_tokens=500,
        response_format={"type": "json_object"}
    )
    
    result_json = json.loads(response.choices[0].message.content.strip())
    return _process_prompt_result(result_json, tags, 'openai')


def _generate_with_deepseek(context, system_prompt, tags):
    """Generate prompt using DeepSeek"""
    from openai import OpenAI
    
    if not DEEPSEEK_API_KEY:
        raise ValueError('DeepSeek API key not configured')
    
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ],
        temperature=0.7,
        max_tokens=500,
        response_format={"type": "json_object"}
    )
    
    result_json = json.loads(response.choices[0].message.content.strip())
    return _process_prompt_result(result_json, tags, 'deepseek')


def _process_prompt_result(result_json, tags, model_name):
    """Process and validate prompt result"""
    generated_prompt = result_json.get('prompt', '').strip()
    generated_negative = result_json.get('negative_prompt', result_json.get('negative', '')).strip()
    
    if not generated_negative:
        generated_negative = 'nsfw, nude, sexual, explicit, bad quality, blurry, worst quality'
    elif 'nsfw' not in generated_negative.lower():
        generated_negative = 'nsfw, nude, sexual, explicit, ' + generated_negative
    
    return {
        'success': True,
        'prompt': generated_prompt,
        'negative_prompt': generated_negative,
        'tags_used': len(tags),
        'model': model_name
    }


def _generate_fallback(tags):
    """Fallback - simple tag joining"""
    prompt_parts = tags[:25]
    quality_tags = ['masterpiece', 'best quality', 'highly detailed', 'beautiful']
    
    return {
        'success': True,
        'prompt': ', '.join(quality_tags + prompt_parts),
        'negative_prompt': 'nsfw, nude, sexual, explicit, bad quality, blurry, distorted, worst quality',
        'tags_used': len(tags)
    }
