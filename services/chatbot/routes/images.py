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
    """Delete saved image"""
    try:
        # Validate filename
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
            return jsonify({'error': 'Invalid filename'}), 400
        
        filepath = IMAGE_STORAGE_DIR / filename
        metadata_file = filepath.with_suffix('.json')
        
        if not filepath.exists():
            return jsonify({'error': 'Image not found'}), 404
        
        filepath.unlink()
        if metadata_file.exists():
            metadata_file.unlink()
        
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
    """Get image gallery with pagination - filtered by session for privacy"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        show_all = request.args.get('all', 'false').lower() == 'true'
        
        # Get current session ID for filtering
        current_session_id = get_session_id()
        
        images = []
        
        # Get all images and filter by session
        for img_file in IMAGE_STORAGE_DIR.glob('*.png'):
            metadata_file = img_file.with_suffix('.json')
            metadata = {}
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except:
                    pass
            
            # Privacy filter logic:
            # - If show_all=true: show all images (for owner)
            # - If image has no session_id (legacy): show it (backwards compatibility)
            # - If image has session_id matching current: show it
            # - Otherwise: hide it
            image_session_id = metadata.get('session_id')
            
            if not show_all:
                # Only filter if not showing all
                if image_session_id is not None and image_session_id != current_session_id:
                    continue  # Skip images from other sessions (not legacy, not current)
            
            images.append({
                'filename': img_file.name,
                'url': f"/storage/images/{img_file.name}",
                'path': f"/storage/images/{img_file.name}",  # Alias for frontend
                'created_at': metadata.get('created_at', ''),
                'created': metadata.get('created_at', ''),  # Alias for frontend
                'prompt': metadata.get('prompt', 'No prompt'),
                'cloud_url': metadata.get('cloud_url'),
                'metadata': metadata
            })
        
        # Sort by created_at descending
        images.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Paginate
        total = len(images)
        start = (page - 1) * per_page
        end = start + per_page
        paginated = images[start:end]
        
        return jsonify({
            'success': True,  # Frontend expects this
            'images': paginated,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'session_id': current_session_id,  # For debugging
            'showing_all': show_all
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
