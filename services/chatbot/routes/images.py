"""
Image storage routes
"""
import os
import sys
import json
import base64
import re
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import IMAGE_STORAGE_DIR
from core.extensions import logger

images_bp = Blueprint('images', __name__)


@images_bp.route('/api/save-image', methods=['POST'])
def save_image():
    """Save generated image to disk and return URL"""
    try:
        data = request.json
        image_base64 = data.get('image')
        metadata = data.get('metadata', {})
        
        if not image_base64:
            return jsonify({'error': 'No image data provided'}), 400
        
        # Remove data URL prefix if present
        if 'base64,' in image_base64:
            image_base64 = image_base64.split('base64,')[1]
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"generated_{timestamp}.png"
        filepath = IMAGE_STORAGE_DIR / filename
        
        # Decode and save image
        image_data = base64.b64decode(image_base64)
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        # Save metadata
        metadata_file = IMAGE_STORAGE_DIR / f"generated_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'filename': filename,
                'created_at': datetime.now().isoformat(),
                'metadata': metadata
            }, f, ensure_ascii=False, indent=2)
        
        image_url = f"/storage/images/{filename}"
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': image_url,
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
def get_gallery():
    """Get image gallery with pagination"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        images = []
        
        # Get all images
        for img_file in IMAGE_STORAGE_DIR.glob('*.png'):
            metadata_file = img_file.with_suffix('.json')
            metadata = {}
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except:
                    pass
            
            images.append({
                'filename': img_file.name,
                'url': f"/storage/images/{img_file.name}",
                'created_at': metadata.get('created_at', ''),
                'prompt': metadata.get('prompt', ''),
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
            'images': paginated,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
        
    except Exception as e:
        logger.error(f"[Gallery] Error: {e}")
        return jsonify({'error': 'Failed to get gallery'}), 500
