"""
Image storage routes with session-based privacy
Each user session can only see their own images
But all images are still stored in MongoDB/Firebase for the owner
"""
import os
import sys
import json
import base64
import re
import uuid
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, session
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import IMAGE_STORAGE_DIR
from core.extensions import logger

images_bp = Blueprint('images', __name__)


def get_session_id():
    """Get or create a unique session ID for privacy filtering"""
    if 'gallery_session_id' not in session:
        session['gallery_session_id'] = str(uuid.uuid4())
        session.permanent = True  # Session persists across browser restarts
    return session['gallery_session_id']


@images_bp.route('/api/save-image', methods=['POST'])
def save_image():
    """Save generated image to disk and upload to cloud with session tracking"""
    try:
        data = request.json
        image_base64 = data.get('image')
        metadata = data.get('metadata', {})
        
        if not image_base64:
            return jsonify({'error': 'No image data provided'}), 400
        
        # Get session ID for privacy filtering
        session_id = get_session_id()
        
        # Remove data URL prefix if present
        if 'base64,' in image_base64:
            image_base64 = image_base64.split('base64,')[1]
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"generated_{timestamp}.png"
        filepath = IMAGE_STORAGE_DIR / filename
        
        # Decode and save image locally
        image_data = base64.b64decode(image_base64)
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        # Add session_id to metadata for cloud storage
        metadata['session_id'] = session_id
        
        # Upload to cloud (ImgBB + MongoDB/Firebase)
        cloud_url = None
        try:
            from core.image_storage import store_generated_image
            storage_result = store_generated_image(
                image_base64=image_base64,
                prompt=metadata.get('prompt', ''),
                negative_prompt=metadata.get('negative_prompt', ''),
                metadata=metadata
            )
            if storage_result.get('success'):
                cloud_url = storage_result.get('imgbb_url')
        except Exception as e:
            logger.warning(f"[SaveImage] Cloud upload failed: {e}")
        
        # Save metadata with session_id
        metadata_file = IMAGE_STORAGE_DIR / f"generated_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'filename': filename,
                'created_at': datetime.now().isoformat(),
                'cloud_url': cloud_url,
                'session_id': session_id,  # Track session for privacy
                'metadata': metadata
            }, f, ensure_ascii=False, indent=2)
        
        image_url = f"/storage/images/{filename}"
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': image_url,
            'cloud_url': cloud_url,
            'path': str(filepath)
        })
        
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return jsonify({'error': str(e)}), 500


@images_bp.route('/storage/images/<filename>')
def serve_image(filename):
    """Serve saved images"""
    try:
        # Validate filename to prevent path traversal attacks
        if '/' in filename or '\\' in filename or '..' in filename or '\0' in filename:
            logger.warning("Path traversal attempt detected")
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Only allow alphanumeric, underscore, dash, and dot
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
            logger.warning("Invalid filename format detected")
            return jsonify({'error': 'Invalid filename format'}), 400
        
        # Resolve the allowed directory
        allowed_dir = IMAGE_STORAGE_DIR.resolve()
        
        # Build and resolve path
        file_path = Path(str(allowed_dir)) / filename
        
        try:
            resolved_file_path = file_path.resolve()
        except (ValueError, OSError):
            return jsonify({'error': 'Invalid file path'}), 400
        
        # Verify path is within allowed directory
        try:
            resolved_file_path.relative_to(allowed_dir)
        except ValueError:
            return jsonify({'error': 'Access denied'}), 403
        
        if not resolved_file_path.exists():
            return jsonify({'error': 'Image not found'}), 404
        
        if not resolved_file_path.is_file():
            return jsonify({'error': 'Invalid file type'}), 400
        
        return send_file(str(resolved_file_path), mimetype='image/png')
        
    except Exception as e:
        logger.error(f"[Get Image] Error: {e}")
        return jsonify({'error': 'Failed to retrieve image'}), 500


@images_bp.route('/api/list-images', methods=['GET'])
def list_images():
    """List all saved images"""
    try:
        images = []
        
        for img_file in IMAGE_STORAGE_DIR.glob('generated_*.png'):
            metadata_file = img_file.with_suffix('.json')
            metadata = {}
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading metadata for {img_file}: {e}")
            
            images.append({
                'filename': img_file.name,
                'url': f"/storage/images/{img_file.name}",
                'created_at': metadata.get('created_at', ''),
                'metadata': metadata.get('metadata', {})
            })
        
        images.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({
            'images': images,
            'count': len(images)
        })
        
    except Exception as e:
        logger.error(f"[List Images] Error: {e}")
        return jsonify({'error': 'Failed to list images'}), 500


@images_bp.route('/api/delete-image/<filename>', methods=['DELETE'])
def delete_image(filename):
    """Delete saved image from local disk and MongoDB"""
    try:
        # Validate filename
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
            return jsonify({'error': 'Invalid filename'}), 400
        
        filepath = IMAGE_STORAGE_DIR / filename
        metadata_file = filepath.with_suffix('.json')
        
        # Delete from local disk
        if filepath.exists():
            filepath.unlink()
        if metadata_file.exists():
            metadata_file.unlink()
        
        # Delete from MongoDB generated_images collection
        try:
            from core.image_storage import images_collection
            if images_collection is not None:
                result = images_collection.delete_one({'filename': filename})
                if result.deleted_count:
                    logger.info(f"[Delete Image] Removed from MongoDB: {filename}")
        except Exception as mongo_err:
            logger.warning(f"[Delete Image] MongoDB delete failed: {mongo_err}")
        
        return jsonify({
            'success': True,
            'message': 'Image deleted'
        })
        
    except Exception as e:
        logger.error(f"[Delete Image] Error: {e}")
        return jsonify({'error': 'Failed to delete image'}), 500


@images_bp.route('/api/gallery', methods=['GET'])
@images_bp.route('/api/gallery/images', methods=['GET'])  # Alias for frontend compatibility
def get_gallery():
    """Get image gallery - MongoDB first, local disk fallback"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        show_all = request.args.get('all', 'false').lower() == 'true'
        
        current_session_id = get_session_id()
        images = []
        source = 'local'
        
        # ── Try MongoDB first (generated_images collection) ──
        try:
            from core.image_storage import images_collection
            if images_collection is not None:
                query = {}
                if not show_all:
                    query = {'$or': [
                        {'session_id': current_session_id},
                        {'session_id': {'$exists': False}},
                        {'session_id': ''},
                    ]}
                
                cursor = images_collection.find(query).sort('created_at', -1).limit(per_page * page)
                for doc in cursor:
                    doc_id = str(doc.get('_id', ''))
                    created = doc.get('created_at', '')
                    if hasattr(created, 'isoformat'):
                        created = created.isoformat()
                    
                    cloud_url = doc.get('cloud_url') or doc.get('url')
                    local_path = doc.get('local_path', '')
                    filename = doc.get('filename', '')
                    
                    # Use cloud URL (ImgBB CDN) if available, otherwise local
                    display_url = cloud_url if cloud_url else local_path
                    
                    images.append({
                        'id': doc_id,
                        'filename': filename,
                        'url': display_url,
                        'path': display_url,
                        'cloud_url': cloud_url,
                        'local_path': local_path,
                        'created_at': created,
                        'created': created,
                        'prompt': doc.get('prompt', 'No prompt'),
                        'metadata': {
                            'prompt': doc.get('prompt', ''),
                            'negative_prompt': doc.get('negative_prompt', ''),
                            'model': doc.get('model', ''),
                            'sampler': doc.get('sampler', ''),
                            'steps': doc.get('steps', ''),
                            'cfg_scale': doc.get('cfg_scale', ''),
                            'width': doc.get('width', ''),
                            'height': doc.get('height', ''),
                            'seed': doc.get('seed', ''),
                            'vae': doc.get('vae', ''),
                            'lora_models': doc.get('lora_models', ''),
                            'denoising_strength': doc.get('denoising_strength', ''),
                        }
                    })
                
                if images:
                    source = 'mongodb'
                    logger.info(f"[Gallery] Loaded {len(images)} images from MongoDB")
        except Exception as mongo_err:
            logger.warning(f"[Gallery] MongoDB fetch failed, falling back to local: {mongo_err}")
        
        # ── Fallback: local disk ──
        if not images:
            for img_file in IMAGE_STORAGE_DIR.glob('*.png'):
                metadata_file = img_file.with_suffix('.json')
                metadata = {}
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except:
                        pass
                
                image_session_id = metadata.get('session_id')
                if not show_all:
                    if image_session_id is not None and image_session_id != current_session_id:
                        continue
                
                images.append({
                    'filename': img_file.name,
                    'url': f"/storage/images/{img_file.name}",
                    'path': f"/storage/images/{img_file.name}",
                    'cloud_url': metadata.get('cloud_url'),
                    'local_path': f"/storage/images/{img_file.name}",
                    'created_at': metadata.get('created_at', ''),
                    'created': metadata.get('created_at', ''),
                    'prompt': metadata.get('prompt', 'No prompt'),
                    'metadata': metadata
                })
            
            images.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            source = 'local'
        
        # Paginate
        total = len(images)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = images[start:end]
        
        return jsonify({
            'success': True,
            'images': paginated,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'session_id': current_session_id,
            'showing_all': show_all,
            'source': source
        })
        
    except Exception as e:
        logger.error(f"[Gallery] Error: {e}")
        return jsonify({'error': 'Failed to get gallery'}), 500


@images_bp.route('/api/gallery/cloud', methods=['GET'])
def get_cloud_gallery():
    """Get images from cloud storage (MongoDB/Firebase)"""
    try:
        limit = int(request.args.get('limit', 50))
        
        try:
            from core.image_storage import get_images_from_cloud
            images = get_images_from_cloud(limit=limit)
        except Exception as e:
            logger.warning(f"[CloudGallery] Error fetching from cloud: {e}")
            images = []
        
        return jsonify({
            'success': True,
            'images': images,
            'total': len(images),
            'source': 'cloud'
        })
        
    except Exception as e:
        logger.error(f"[CloudGallery] Error: {e}")
        return jsonify({'error': 'Failed to get cloud gallery'}), 500


@images_bp.route('/api/upload-imgbb', methods=['POST'])
def upload_to_imgbb():
    """Upload image to ImgBB"""
    try:
        data = request.json
        image_base64 = data.get('image')
        name = data.get('name')
        
        if not image_base64:
            return jsonify({'error': 'No image data provided'}), 400
        
        from core.image_storage import upload_to_imgbb as imgbb_upload
        url = imgbb_upload(image_base64, name)
        
        if url:
            return jsonify({
                'success': True,
                'url': url
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Upload failed'
            }), 500
            
    except Exception as e:
        logger.error(f"[UploadImgBB] Error: {e}")
        return jsonify({'error': str(e)}), 500
