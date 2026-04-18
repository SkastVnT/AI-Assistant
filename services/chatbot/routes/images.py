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


def _to_iso(value):
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value or ''


def _load_local_image_record(filename: str):
    filepath = IMAGE_STORAGE_DIR / filename
    if not filepath.exists():
        return None, None
    metadata_file = filepath.with_suffix('.json')
    payload = {}
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                payload = json.load(f)
        except Exception:
            payload = {}
    return filepath, payload


def _check_db_presence(filename: str):
    status = {
        'mongodb': False,
        'firebase': False,
        'mongodb_id': None,
        'firebase_id': None,
    }

    try:
        from core.image_storage import images_collection
        if images_collection is not None:
            doc = images_collection.find_one({'filename': filename}, {'_id': 1})
            if doc:
                status['mongodb'] = True
                status['mongodb_id'] = str(doc.get('_id'))
    except Exception as e:
        logger.warning(f"[ImageInfo] Mongo presence check failed: {e}")

    try:
        from core.image_storage import firebase_db, rtdb_get
        if firebase_db is not None:
            docs = firebase_db.collection('generated_images_v2').where('filename', '==', filename).limit(1).stream()
            for doc in docs:
                status['firebase'] = True
                status['firebase_id'] = doc.id
                break

        if not status['firebase']:
            safe_key = re.sub(r'[.$#\[\]/]', '_', filename)
            idx = rtdb_get(f'generated_images_index/by_filename/{safe_key}') or {}
            doc_id = idx.get('doc_id') if isinstance(idx, dict) else None
            if doc_id:
                node = rtdb_get(f'generated_images_v2/{doc_id}')
                if node:
                    status['firebase'] = True
                    status['firebase_id'] = doc_id
    except Exception as e:
        logger.warning(f"[ImageInfo] Firebase presence check failed: {e}")

    return status


@images_bp.route('/api/save-image', methods=['POST'])
@images_bp.route('/api/save-generated-image', methods=['POST'])
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
        
        # Add filename/session_id to metadata for cloud storage
        metadata['filename'] = filename
        metadata['session_id'] = session_id
        
        # Upload to cloud (ImgBB + MongoDB/Firebase)
        cloud_url = None
        drive_url = None
        drive_file_id = None
        mongodb_saved = False
        firebase_saved = False
        try:
            from core.image_storage import store_generated_image
            storage_result = store_generated_image(
                image_base64=image_base64,
                prompt=metadata.get('prompt', ''),
                negative_prompt=metadata.get('negative_prompt', ''),
                metadata=metadata,
                raw_legacy_payload=data,
            )
            if storage_result.get('success'):
                cloud_url = storage_result.get('imgbb_url')
                drive_url = storage_result.get('drive_url')
                drive_file_id = storage_result.get('drive_file_id')
                mongodb_saved = bool(storage_result.get('saved_to_mongodb'))
                firebase_saved = bool(storage_result.get('saved_to_firebase'))
        except Exception as e:
            logger.warning(f"[SaveImage] Cloud upload failed: {e}")
        
        # Save metadata with session_id
        metadata_file = IMAGE_STORAGE_DIR / f"generated_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'filename': filename,
                'created_at': datetime.now().isoformat(),
                'cloud_url': cloud_url,
                'drive_url': drive_url,
                'drive_file_id': drive_file_id,
                'session_id': session_id,  # Track session for privacy
                'metadata': metadata,
                'db_status': {
                    'mongodb': mongodb_saved,
                    'firebase': firebase_saved,
                }
            }, f, ensure_ascii=False, indent=2)
        
        image_url = f"/storage/images/{filename}"
        primary_url = drive_url or cloud_url or image_url
        
        return jsonify({
            'success': True,
            'filename': filename,
            'url': image_url,
            'imageURL': primary_url,
            'image_url': primary_url,
            'cloud_url': cloud_url,
            'drive_url': drive_url,
            'drive_file_id': drive_file_id,
            'db_status': {
                'mongodb': mongodb_saved,
                'firebase': firebase_saved,
            },
            'path': str(filepath)
        })
        
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return jsonify({'error': 'Failed to save image'}), 500


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
        
        # â”€â”€ Try MongoDB first (generated_images collection) â”€â”€
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
                    drive_url = doc.get('drive_url')
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
                        'drive_url': drive_url,
                        'share_url': drive_url or cloud_url or local_path,
                        'local_path': local_path,
                        'created_at': created,
                        'created': created,
                        'prompt': doc.get('prompt', 'No prompt'),
                        'creator': doc.get('creator') or doc.get('session_id') or 'unknown',
                        'db_status': {
                            'mongodb': True,
                            'firebase': bool(doc.get('firebase_id')),
                        },
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
                            'drive_url': drive_url,
                            'cloud_url': cloud_url,
                            'filename': filename,
                        }
                    })
                
                if images:
                    source = 'mongodb'
                    logger.info(f"[Gallery] Loaded {len(images)} images from MongoDB")
        except Exception as mongo_err:
            logger.warning(f"[Gallery] MongoDB fetch failed, falling back to local: {mongo_err}")
        
        # ── Fallback: local disk (flat + date-based subdirs from image_gen_v2) ──
        if not images:
            for img_file in IMAGE_STORAGE_DIR.rglob('*.png'):
                # Support both flat (.json) and date-based subdirs (.meta.json)
                metadata_file = img_file.with_suffix('.meta.json') if not img_file.with_suffix('.json').exists() else img_file.with_suffix('.json')
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

                # Build a servable URL: image_gen_v2 images served via /api/image-gen/images/<id>
                image_id = metadata.get('image_id', '')
                if image_id:
                    serve_url = f"/api/image-gen/images/{image_id}"
                else:
                    serve_url = f"/storage/images/{img_file.name}"

                images.append({
                    'filename': img_file.name,
                    'url': serve_url,
                    'path': serve_url,
                    'cloud_url': metadata.get('cloud_url'),
                    'drive_url': metadata.get('drive_url'),
                    'share_url': metadata.get('drive_url') or metadata.get('cloud_url') or serve_url,
                    'local_path': serve_url,
                    'created_at': metadata.get('created_at', ''),
                    'created': metadata.get('created_at', ''),
                    'prompt': metadata.get('prompt', 'No prompt'),
                    'creator': metadata.get('creator') or metadata.get('session_id') or 'local-session',
                    'db_status': metadata.get('db_status', {'mongodb': False, 'firebase': False}),
                    'metadata': metadata.get('metadata', metadata)
                })
            
            images.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            source = 'local'

        # ── Additional source: AI-generated image URLs from assistant messages ──
        # (cloud-hosted images, e.g. ImgBB, that never landed in generated_images collection)
        try:
            from config.mongodb_config import get_db as _get_mongo_db
            import re as _re
            _url_pat = _re.compile(
                r'https?://\S+\.(?:png|jpg|jpeg|gif|webp)(?:\?\S*)?',
                _re.IGNORECASE,
            )
            _db = _get_mongo_db()
            if _db is not None:
                msg_query: dict = {'role': 'assistant', 'content': {'$regex': r'https?://', '$options': 'i'}}
                existing_urls = {img.get('cloud_url') or img.get('url') or img.get('path') for img in images}
                for msg in _db.messages.find(msg_query).sort('created_at', -1).limit(500):
                    content = msg.get('content', '')
                    for url in _url_pat.findall(content):
                        if url in existing_urls:
                            continue
                        # Skip tiny icons / avatars
                        if any(skip in url for skip in ('/favicon', '/icon', '/logo', '/avatar')):
                            continue
                        existing_urls.add(url)
                        created = msg.get('created_at', '')
                        if hasattr(created, 'isoformat'):
                            created = created.isoformat()
                        images.append({
                            'filename': url.split('/')[-1].split('?')[0],
                            'url': url,
                            'path': url,
                            'cloud_url': url,
                            'drive_url': None,
                            'share_url': url,
                            'local_path': '',
                            'created_at': created,
                            'created': created,
                            'prompt': (content[:80] + '...') if len(content) > 80 else content,
                            'creator': 'assistant',
                            'db_status': {'mongodb': True, 'firebase': False},
                            'metadata': {'source': 'message'},
                        })
            source = source or 'messages'
        except Exception as msg_err:
            logger.debug(f"[Gallery] Message scan skipped: {msg_err}")

        # Sort all sources by created_at descending
        images.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
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


@images_bp.route('/api/gallery/image-info', methods=['GET'])
def get_image_info():
    """Get full metadata and database status for one image."""
    try:
        filename = request.args.get('filename', '').strip()
        if not filename or not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
            return jsonify({'error': 'Invalid filename'}), 400

        filepath, local_payload = _load_local_image_record(filename)
        db_status = _check_db_presence(filename)

        # Try enrich from MongoDB document if available
        mongo_doc = None
        try:
            from core.image_storage import images_collection
            if images_collection is not None:
                mongo_doc = images_collection.find_one({'filename': filename})
        except Exception as e:
            logger.warning(f"[ImageInfo] Mongo fetch failed: {e}")

        created_at = ''
        if mongo_doc:
            created_at = _to_iso(mongo_doc.get('created_at'))
        elif local_payload:
            created_at = local_payload.get('created_at', '')
        elif filepath:
            created_at = datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()

        metadata = {}
        if local_payload:
            metadata = local_payload.get('metadata', local_payload)
        if mongo_doc:
            metadata = {
                **metadata,
                'prompt': mongo_doc.get('prompt', metadata.get('prompt', '')),
                'negative_prompt': mongo_doc.get('negative_prompt', metadata.get('negative_prompt', '')),
                'model': mongo_doc.get('model', metadata.get('model', '')),
                'sampler': mongo_doc.get('sampler', metadata.get('sampler', '')),
                'steps': mongo_doc.get('steps', metadata.get('steps', '')),
                'cfg_scale': mongo_doc.get('cfg_scale', metadata.get('cfg_scale', '')),
                'width': mongo_doc.get('width', metadata.get('width', '')),
                'height': mongo_doc.get('height', metadata.get('height', '')),
                'seed': mongo_doc.get('seed', metadata.get('seed', '')),
                'vae': mongo_doc.get('vae', metadata.get('vae', '')),
                'lora_models': mongo_doc.get('lora_models', metadata.get('lora_models', '')),
                'denoising_strength': mongo_doc.get('denoising_strength', metadata.get('denoising_strength', '')),
            }

        cloud_url = (mongo_doc or {}).get('cloud_url') or (mongo_doc or {}).get('url') or (local_payload or {}).get('cloud_url')
        drive_url = (mongo_doc or {}).get('drive_url') or (local_payload or {}).get('drive_url')
        local_url = f"/storage/images/{filename}" if filepath else None
        primary_url = drive_url or cloud_url or local_url

        return jsonify({
            'success': True,
            'filename': filename,
            'creator': (mongo_doc or {}).get('creator') or (local_payload or {}).get('session_id') or 'unknown',
            'created_at': created_at,
            'metadata': metadata,
            'links': {
                'local_url': local_url,
                'cloud_url': cloud_url,
                'drive_url': drive_url,
                'imageURL': primary_url,
                'share_url': drive_url or cloud_url or local_url,
                'drive_folder_url': os.getenv('GOOGLE_DRIVE_FOLDER_URL', 'https://drive.google.com/drive/folders/11MN5m72gl84LsP1NMfBjeX9YAzsIlRxz?usp=sharing'),
            },
            'db_status': db_status,
        })
    except Exception as e:
        logger.error(f"[ImageInfo] Error: {e}")
        return jsonify({'error': 'Failed to load image info'}), 500


@images_bp.route('/api/gallery/upload-db', methods=['POST'])
def upload_image_to_db():
    """Manual upload one local image + full metadata to cloud/db."""
    try:
        data = request.get_json(silent=True) or {}
        filename = str(data.get('filename', '')).strip()
        if not filename or not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
            return jsonify({'error': 'Invalid filename'}), 400

        filepath, local_payload = _load_local_image_record(filename)
        if not filepath:
            return jsonify({'error': 'Image not found locally'}), 404

        with open(filepath, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')

        metadata = local_payload.get('metadata', local_payload if isinstance(local_payload, dict) else {})
        metadata['filename'] = filename
        metadata['session_id'] = metadata.get('session_id') or get_session_id()

        from core.image_storage import store_generated_image
        result = store_generated_image(
            image_base64=image_b64,
            prompt=metadata.get('prompt', ''),
            negative_prompt=metadata.get('negative_prompt', ''),
            metadata=metadata,
            raw_legacy_payload=local_payload if isinstance(local_payload, dict) else {},
        )

        db_status = {
            'mongodb': bool(result.get('saved_to_mongodb')),
            'firebase': bool(result.get('saved_to_firebase')),
        }

        # Update local metadata snapshot
        meta_file = filepath.with_suffix('.json')
        merged_local = {
            **(local_payload if isinstance(local_payload, dict) else {}),
            'filename': filename,
            'created_at': (local_payload or {}).get('created_at', datetime.now().isoformat()),
            'cloud_url': result.get('imgbb_url') or (local_payload or {}).get('cloud_url'),
            'drive_url': result.get('drive_url') or (local_payload or {}).get('drive_url'),
            'drive_file_id': result.get('drive_file_id') or (local_payload or {}).get('drive_file_id'),
            'db_status': db_status,
            'metadata': metadata,
        }
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(merged_local, f, ensure_ascii=False, indent=2)

        return jsonify({
            'success': True,
            'filename': filename,
            'imageURL': result.get('drive_url') or result.get('imgbb_url') or f"/storage/images/{filename}",
            'cloud_url': result.get('imgbb_url'),
            'drive_url': result.get('drive_url'),
            'db_status': db_status,
            'storage_result': result,
        })
    except Exception as e:
        logger.error(f"[UploadDB] Error: {e}")
        return jsonify({'error': 'Failed to upload to database'}), 500


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
        return jsonify({'error': 'Failed to upload image'}), 500
