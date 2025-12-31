"""
Memory routes for AI learning/knowledge base
"""
import os
import sys
import json
import base64
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import MEMORY_DIR, IMAGE_STORAGE_DIR
from core.extensions import logger

memory_bp = Blueprint('memory', __name__)


@memory_bp.route('/save', methods=['POST'])
def save_memory():
    """Save a conversation as a learning memory with images"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        title = data.get('title', '')
        content = data.get('content', '')
        tags = data.get('tags', [])
        images = data.get('images', [])
        
        if not title or not content:
            return jsonify({'error': 'Title and content are required'}), 400
        
        # Create memory object
        memory_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = title[:30].replace('/', '-').replace('\\', '-')
        folder_name = f"{safe_title}_{timestamp}"
        
        # Create memory folder structure
        memory_folder = MEMORY_DIR / folder_name
        memory_folder.mkdir(parents=True, exist_ok=True)
        
        image_folder = memory_folder / 'image_gen'
        image_folder.mkdir(parents=True, exist_ok=True)
        
        # Save images
        saved_images = []
        for idx, img_data in enumerate(images):
            try:
                img_url = img_data.get('url', '')
                img_base64 = img_data.get('base64', '')
                
                if img_url and img_url.startswith('/storage/images/'):
                    source_filename = img_url.split('/')[-1]
                    source_path = IMAGE_STORAGE_DIR / source_filename
                    
                    if source_path.exists():
                        dest_filename = f"image_{idx + 1}_{source_filename}"
                        dest_path = image_folder / dest_filename
                        shutil.copy2(source_path, dest_path)
                        saved_images.append(dest_filename)
                        
                        meta_source = source_path.with_suffix('.json')
                        if meta_source.exists():
                            meta_dest = dest_path.with_suffix('.json')
                            shutil.copy2(meta_source, meta_dest)
                            
                elif img_base64:
                    if ',' in img_base64:
                        img_base64 = img_base64.split(',')[1]
                    
                    image_bytes = base64.b64decode(img_base64)
                    dest_filename = f"image_{idx + 1}.png"
                    dest_path = image_folder / dest_filename
                    
                    with open(dest_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    saved_images.append(dest_filename)
                    
            except Exception as e:
                logger.error(f"Error saving image {idx}: {e}")
        
        memory = {
            'id': memory_id,
            'folder_name': folder_name,
            'title': title,
            'content': content,
            'tags': tags,
            'images': saved_images,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        memory_file = memory_folder / 'memory.json'
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'memory': memory,
            'message': f'Saved with {len(saved_images)} images'
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Error saving memory: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@memory_bp.route('/list', methods=['GET'])
def list_memories():
    """List all saved memories"""
    try:
        memories = []
        
        # Old format (direct .json files)
        for memory_file in MEMORY_DIR.glob('*.json'):
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memories.append(json.load(f))
            except Exception as e:
                logger.error(f"Error loading {memory_file}: {e}")
        
        # New format (folders with memory.json)
        for memory_folder in MEMORY_DIR.iterdir():
            if memory_folder.is_dir():
                memory_file = memory_folder / 'memory.json'
                if memory_file.exists():
                    try:
                        with open(memory_file, 'r', encoding='utf-8') as f:
                            memories.append(json.load(f))
                    except Exception as e:
                        logger.error(f"Error loading {memory_file}: {e}")
        
        memories.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({'memories': memories})
        
    except Exception as e:
        logger.error(f"[Memory List] Error: {e}")
        return jsonify({'error': 'Failed to retrieve memories'}), 500


@memory_bp.route('/get/<memory_id>', methods=['GET'])
def get_memory(memory_id):
    """Get a specific memory by ID"""
    try:
        # Old format
        memory_file = MEMORY_DIR / f"{memory_id}.json"
        if memory_file.exists():
            with open(memory_file, 'r', encoding='utf-8') as f:
                return jsonify({'memory': json.load(f)})
        
        # New format - search in folders
        for folder in MEMORY_DIR.iterdir():
            if folder.is_dir():
                memory_file = folder / 'memory.json'
                if memory_file.exists():
                    with open(memory_file, 'r', encoding='utf-8') as f:
                        memory = json.load(f)
                        if memory.get('id') == memory_id:
                            return jsonify({'memory': memory})
        
        return jsonify({'error': 'Memory not found'}), 404
        
    except Exception as e:
        logger.error(f"[Get Memory] Error: {e}")
        return jsonify({'error': 'Failed to retrieve memory'}), 500


@memory_bp.route('/delete/<memory_id>', methods=['DELETE'])
def delete_memory(memory_id):
    """Delete a memory"""
    try:
        logger.info(f"[DELETE] Deleting memory ID: {memory_id}")
        
        # Old format
        memory_file = MEMORY_DIR / f"{memory_id}.json"
        if memory_file.exists():
            memory_file.unlink()
            return jsonify({'success': True, 'message': 'Memory deleted'})
        
        # New format - search in folders
        for folder in MEMORY_DIR.iterdir():
            if folder.is_dir():
                memory_file = folder / 'memory.json'
                if memory_file.exists():
                    try:
                        with open(memory_file, 'r', encoding='utf-8') as f:
                            memory = json.load(f)
                            if memory.get('id') == memory_id:
                                shutil.rmtree(folder)
                                logger.info(f"[DELETE] Deleted folder: {folder}")
                                return jsonify({'success': True, 'message': 'Memory deleted'})
                    except Exception as e:
                        logger.error(f"Error checking {memory_file}: {e}")
        
        return jsonify({'error': 'Memory not found'}), 404
        
    except Exception as e:
        logger.error(f"[Delete Memory] Error: {e}")
        return jsonify({'error': str(e)}), 500


@memory_bp.route('/update/<memory_id>', methods=['PUT'])
def update_memory(memory_id):
    """Update a memory"""
    try:
        data = request.json
        
        # Find memory file
        memory_file = None
        memory_folder = None
        
        # Old format
        old_file = MEMORY_DIR / f"{memory_id}.json"
        if old_file.exists():
            memory_file = old_file
        else:
            # New format
            for folder in MEMORY_DIR.iterdir():
                if folder.is_dir():
                    mf = folder / 'memory.json'
                    if mf.exists():
                        with open(mf, 'r', encoding='utf-8') as f:
                            memory = json.load(f)
                            if memory.get('id') == memory_id:
                                memory_file = mf
                                memory_folder = folder
                                break
        
        if not memory_file:
            return jsonify({'error': 'Memory not found'}), 404
        
        # Load existing
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)
        
        # Update fields
        if 'title' in data:
            memory['title'] = data['title']
        if 'content' in data:
            memory['content'] = data['content']
        if 'tags' in data:
            memory['tags'] = data['tags']
        
        memory['updated_at'] = datetime.now().isoformat()
        
        # Save
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'memory': memory})
        
    except Exception as e:
        logger.error(f"[Update Memory] Error: {e}")
        return jsonify({'error': str(e)}), 500


@memory_bp.route('/search', methods=['GET'])
def search_memories():
    """Search memories by keyword"""
    try:
        query = request.args.get('q', '').lower()
        if not query:
            return jsonify({'memories': []})
        
        memories = []
        
        # Search all memories
        for folder in MEMORY_DIR.iterdir():
            if folder.is_dir():
                memory_file = folder / 'memory.json'
                if memory_file.exists():
                    try:
                        with open(memory_file, 'r', encoding='utf-8') as f:
                            memory = json.load(f)
                            
                            # Search in title, content, tags
                            title = memory.get('title', '').lower()
                            content = memory.get('content', '').lower()
                            tags = [t.lower() for t in memory.get('tags', [])]
                            
                            if query in title or query in content or any(query in t for t in tags):
                                memories.append(memory)
                                
                    except Exception as e:
                        logger.error(f"Error searching {memory_file}: {e}")
        
        # Also check old format
        for memory_file in MEMORY_DIR.glob('*.json'):
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
                    
                    title = memory.get('title', '').lower()
                    content = memory.get('content', '').lower()
                    tags = [t.lower() for t in memory.get('tags', [])]
                    
                    if query in title or query in content or any(query in t for t in tags):
                        memories.append(memory)
                        
            except Exception as e:
                logger.error(f"Error searching {memory_file}: {e}")
        
        memories.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify({'memories': memories, 'count': len(memories)})
        
    except Exception as e:
        logger.error(f"[Search Memory] Error: {e}")
        return jsonify({'error': str(e)}), 500
