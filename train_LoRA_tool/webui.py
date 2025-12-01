"""
LoRA Training WebUI
Real-time training monitoring with Socket.IO
Similar to Stable Diffusion WebUI interface
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import queue
import yaml
import json
from datetime import datetime

# Redis integration (optional)
try:
    from utils.redis_manager import (
        redis_manager, 
        task_queue, 
        cache, 
        is_redis_available,
        queue_training,
        get_cached_metadata,
        cache_metadata
    )
    REDIS_ENABLED = is_redis_available()
    if REDIS_ENABLED:
        print("✅ Redis enabled - Using task queue and caching")
    else:
        print("⚠️ Redis not available - Using in-memory mode")
except ImportError:
    print("⚠️ Redis module not installed - Using in-memory mode")
    REDIS_ENABLED = False

app = Flask(__name__, 
           template_folder='webui/templates',
           static_folder='webui/static')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state
training_state = {
    'is_training': False,
    'current_epoch': 0,
    'total_epochs': 0,
    'current_step': 0,
    'total_steps': 0,
    'loss': 0.0,
    'lr': 0.0,
    'progress': 0.0,
    'eta': 'N/A',
    'status': 'Idle',
    'config': None,
    'logs': []
}

training_thread = None
log_queue = queue.Queue()


class WebUIMonitor:
    """Monitor for WebUI real-time updates"""
    
    def __init__(self, socketio):
        self.socketio = socketio
        
    def on_epoch_begin(self, epoch, epochs):
        training_state['current_epoch'] = epoch
        training_state['total_epochs'] = epochs
        training_state['status'] = f'Training Epoch {epoch}/{epochs}'
        self.emit_update()
        
    def on_epoch_end(self, epoch, loss, lr):
        training_state['loss'] = loss
        training_state['lr'] = lr
        self.emit_update()
        
    def on_step(self, step, total_steps, loss, lr):
        training_state['current_step'] = step
        training_state['total_steps'] = total_steps
        training_state['loss'] = loss
        training_state['lr'] = lr
        training_state['progress'] = (step / total_steps) * 100 if total_steps > 0 else 0
        self.emit_update()
        
    def on_log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        training_state['logs'].append(log_entry)
        if len(training_state['logs']) > 1000:  # Keep last 1000 logs
            training_state['logs'] = training_state['logs'][-1000:]
        self.socketio.emit('log', {'message': log_entry}, namespace='/')
        
    def emit_update(self):
        self.socketio.emit('training_update', training_state, namespace='/')


monitor = WebUIMonitor(socketio)


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/configs')
def get_configs():
    """Get available config files"""
    configs_dir = Path('configs')
    configs = []
    for config_file in configs_dir.glob('*.yaml'):
        configs.append({
            'name': config_file.stem,
            'path': str(config_file)
        })
    return jsonify(configs)


@app.route('/api/config/<name>')
def get_config(name):
    """Get specific config content"""
    config_path = Path('configs') / f"{name}.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return jsonify(config)
    return jsonify({'error': 'Config not found'}), 404


@app.route('/api/config/<name>', methods=['POST'])
def save_config(name):
    """Save config"""
    config_path = Path('configs') / f"{name}.yaml"
    config_data = request.json
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, sort_keys=False)
    return jsonify({'success': True})


@app.route('/api/datasets')
def get_datasets():
    """Get available datasets"""
    data_dir = Path('data')
    datasets = []
    for folder in data_dir.iterdir():
        if folder.is_dir() and folder.name not in ['examples', '.gitkeep']:
            image_count = len(list(folder.glob('*.jpg')) + list(folder.glob('*.png')))
            datasets.append({
                'name': folder.name,
                'path': str(folder),
                'image_count': image_count
            })
    return jsonify(datasets)


@app.route('/api/models')
def get_models():
    """Get available base models"""
    models = [
        {'name': 'Stable Diffusion 1.5', 'path': 'runwayml/stable-diffusion-v1-5'},
        {'name': 'Stable Diffusion 2.1', 'path': 'stabilityai/stable-diffusion-2-1'},
        {'name': 'SDXL Base', 'path': 'stabilityai/stable-diffusion-xl-base-1.0'},
        {'name': 'SDXL Refiner', 'path': 'stabilityai/stable-diffusion-xl-refiner-1.0'},
    ]
    
    # Check for local models
    models_dir = Path('models')
    if models_dir.exists():
        for model_folder in models_dir.iterdir():
            if model_folder.is_dir():
                models.append({
                    'name': f'Local: {model_folder.name}',
                    'path': str(model_folder)
                })
    
    return jsonify(models)


@app.route('/api/start_training', methods=['POST'])
def start_training():
    """Start training"""
    global training_thread, training_state
    
    if training_state['is_training']:
        return jsonify({'error': 'Training already in progress'}), 400
    
    config_data = request.json
    
    # Save temporary config
    temp_config_path = Path('configs/webui_temp.yaml')
    with open(temp_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, sort_keys=False)
    
    training_state['is_training'] = True
    training_state['status'] = 'Starting training...'
    training_state['config'] = config_data
    training_state['logs'] = []
    
    # Start training in background thread
    def train_worker():
        try:
            monitor.on_log("Starting training...")
            monitor.on_log(f"Config: {config_data.get('model', {}).get('pretrained_model_name_or_path', 'Unknown')}")
            monitor.on_log(f"Dataset: {config_data.get('training', {}).get('train_data_dir', 'Unknown')}")
            
            # TODO: Integrate with actual training script
            # For now, simulate training
            import time
            total_epochs = config_data.get('training', {}).get('num_train_epochs', 10)
            for epoch in range(1, total_epochs + 1):
                monitor.on_epoch_begin(epoch, total_epochs)
                for step in range(1, 101):
                    if not training_state['is_training']:
                        break
                    monitor.on_step(step, 100, 0.5 - (step * 0.005), 1e-4)
                    time.sleep(0.1)
                if not training_state['is_training']:
                    break
                monitor.on_epoch_end(epoch, 0.5 - (epoch * 0.05), 1e-4)
            
            monitor.on_log("Training completed successfully!")
        except Exception as e:
            monitor.on_log(f"Error: {str(e)}")
            import traceback
            monitor.on_log(traceback.format_exc())
        finally:
            training_state['is_training'] = False
            training_state['status'] = 'Completed'
    
    training_thread = threading.Thread(target=train_worker, daemon=True)
    training_thread.start()
    
    return jsonify({'success': True, 'message': 'Training started'})


@app.route('/api/stop_training', methods=['POST'])
def stop_training():
    """Stop training"""
    global training_state
    
    if not training_state['is_training']:
        return jsonify({'error': 'No training in progress'}), 400
    
    # Signal to stop (training script should check this flag)
    training_state['status'] = 'Stopping...'
    
    return jsonify({'success': True, 'message': 'Stopping training...'})


@app.route('/api/recommend_config', methods=['POST'])
def recommend_config():
    """Get AI-powered config recommendations from Gemini"""
    data = request.json
    dataset_path = data.get('dataset_path')
    training_goal = data.get('training_goal', 'high_quality')  # high_quality, balanced, fast
    
    if not dataset_path:
        return jsonify({'error': 'Dataset path required'}), 400
    
    try:
        # Check cache first (if Redis enabled)
        if REDIS_ENABLED:
            cached_config = cache.get_ai_recommendation(dataset_path, training_goal)
            if cached_config:
                monitor.on_log("📦 Using cached AI recommendations")
                return jsonify({
                    'success': True,
                    'config': cached_config,
                    'cached': True
                })
        
        from utils.config_recommender import quick_recommend
        
        monitor.on_log("🤖 Analyzing dataset metadata...")
        monitor.on_log("⚠️ No images sent to Gemini - privacy preserved!")
        
        # Get recommendations
        config = quick_recommend(dataset_path, training_goal)
        
        # Cache result (if Redis enabled)
        if REDIS_ENABLED:
            cache.cache_ai_recommendation(dataset_path, training_goal, config)
            monitor.on_log("💾 Cached AI recommendations for future use")
        
        monitor.on_log(f"✅ AI recommendations ready!")
        monitor.on_log(f"Recommended LR: {config['learning_rate']}")
        monitor.on_log(f"Network Dim: {config['network_dim']}")
        monitor.on_log(f"Epochs: {config['epochs']}")
        
        return jsonify({
            'success': True,
            'config': config
        })
        
    except Exception as e:
        error_msg = f"Error getting recommendations: {str(e)}"
        monitor.on_log(f"❌ {error_msg}")
        return jsonify({'error': error_msg}), 500


@app.route('/api/tag_dataset', methods=['POST'])
def tag_dataset():
    """Tag dataset with WD14"""
    data = request.json
    dataset_path = data.get('dataset_path')
    threshold = data.get('threshold', 0.35)
    
    if not dataset_path:
        return jsonify({'error': 'Dataset path required'}), 400
    
    # Run WD14 tagger
    def tag_worker():
        try:
            monitor.on_log(f"Starting WD14 tagging for {dataset_path}...")
            monitor.on_log(f"Threshold: {threshold}")
            
            # TODO: Integrate with WD14 tagger script
            # For now, just log
            import time
            time.sleep(2)
            monitor.on_log("Tagging completed!")
        except Exception as e:
            monitor.on_log(f"Tagging error: {str(e)}")
    
    thread = threading.Thread(target=tag_worker, daemon=True)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Tagging started'})



@app.route('/api/analyze_dataset', methods=['POST'])
def analyze_dataset():
    """Analyze dataset quality"""
    data = request.json
    dataset_path = data.get('dataset_path')
    
    if not dataset_path:
        return jsonify({'error': 'Dataset path required'}), 400
    
    # Get dataset stats
    from pathlib import Path
    dataset_dir = Path(dataset_path)
    
    if not dataset_dir.exists():
        return jsonify({'error': 'Dataset not found'}), 404
    
    # Count images
    image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    images = [f for f in dataset_dir.iterdir() if f.suffix.lower() in image_exts]
    captions = [f for f in dataset_dir.iterdir() if f.suffix == '.txt']
    
    stats = {
        'total_images': len(images),
        'captioned_images': len(captions),
        'avg_resolution': '512x512',  # TODO: Calculate actual
        'quality_score': 8.5  # TODO: Calculate actual
    }
    
    return jsonify(stats)


@app.route('/api/resize_dataset', methods=['POST'])
def resize_dataset_endpoint():
    """Resize all images in dataset"""
    data = request.json
    dataset_path = data.get('dataset_path')
    target_width = data.get('target_width', 512)
    target_height = data.get('target_height', 512)
    keep_aspect = data.get('keep_aspect_ratio', True)
    quality = data.get('quality', 95)
    
    if not dataset_path:
        return jsonify({'error': 'Dataset path required'}), 400
    
    def resize_worker():
        try:
            from utils.dataset_tools import DatasetResizer
            
            monitor.on_log(f"🖼️ Resizing images to {target_width}x{target_height}...")
            
            resizer = DatasetResizer(dataset_path, on_progress=monitor.on_log)
            stats = resizer.resize_dataset(
                target_resolution=(target_width, target_height),
                keep_aspect_ratio=keep_aspect,
                quality=quality
            )
            
            monitor.on_log(f"✅ Resize complete!")
            monitor.on_log(f"Processed: {stats['processed']}, Saved: {stats['size_saved_mb']:.2f} MB")
            
        except Exception as e:
            monitor.on_log(f"❌ Error: {str(e)}")
    
    thread = threading.Thread(target=resize_worker, daemon=True)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Resize started'})


@app.route('/api/convert_format', methods=['POST'])
def convert_format_endpoint():
    """Convert image formats"""
    data = request.json
    dataset_path = data.get('dataset_path')
    target_format = data.get('target_format', 'webp')
    quality = data.get('quality', 95)
    delete_original = data.get('delete_original', False)
    
    if not dataset_path:
        return jsonify({'error': 'Dataset path required'}), 400
    
    def convert_worker():
        try:
            from utils.dataset_tools import ImageFormatConverter
            
            monitor.on_log(f"🔄 Converting images to {target_format.upper()}...")
            
            converter = ImageFormatConverter(dataset_path, on_progress=monitor.on_log)
            stats = converter.convert_all(
                target_format=target_format,
                quality=quality,
                delete_original=delete_original
            )
            
            monitor.on_log(f"✅ Conversion complete!")
            monitor.on_log(f"Converted: {stats['converted']}, Size change: {stats['size_saved_mb']:+.2f} MB")
            
        except Exception as e:
            monitor.on_log(f"❌ Error: {str(e)}")
    
    thread = threading.Thread(target=convert_worker, daemon=True)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Conversion started'})


@app.route('/api/deduplicate', methods=['POST'])
def deduplicate_endpoint():
    """Remove duplicate images"""
    data = request.json
    dataset_path = data.get('dataset_path')
    keep_strategy = data.get('keep', 'first')  # first, last, largest, smallest
    
    if not dataset_path:
        return jsonify({'error': 'Dataset path required'}), 400
    
    def dedupe_worker():
        try:
            from utils.dataset_tools import ImageDeduplicator
            
            monitor.on_log(f"🔍 Scanning for duplicate images...")
            
            deduper = ImageDeduplicator(dataset_path, on_progress=monitor.on_log)
            stats = deduper.remove_duplicates(keep=keep_strategy)
            
            monitor.on_log(f"✅ Deduplication complete!")
            monitor.on_log(f"Removed: {stats['removed']}, Freed: {stats['space_freed_mb']:.2f} MB")
            
        except Exception as e:
            monitor.on_log(f"❌ Error: {str(e)}")
    
    thread = threading.Thread(target=dedupe_worker, daemon=True)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Deduplication started'})


@app.route('/api/organize_dataset', methods=['POST'])
def organize_dataset_endpoint():
    """Organize dataset by resolution"""
    data = request.json
    dataset_path = data.get('dataset_path')
    
    if not dataset_path:
        return jsonify({'error': 'Dataset path required'}), 400
    
    def organize_worker():
        try:
            from utils.dataset_tools import DatasetOrganizer
            
            monitor.on_log(f"📁 Organizing dataset by resolution...")
            
            organizer = DatasetOrganizer(dataset_path, on_progress=monitor.on_log)
            stats = organizer.organize_by_resolution()
            
            monitor.on_log(f"✅ Organization complete!")
            monitor.on_log(f"Moved: {stats['moved']} images")
            
        except Exception as e:
            monitor.on_log(f"❌ Error: {str(e)}")
    
    thread = threading.Thread(target=organize_worker, daemon=True)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Organization started'})


@app.route('/api/validate_dataset', methods=['POST'])
def validate_dataset_endpoint():
    """Validate dataset for issues"""
    data = request.json
    dataset_path = data.get('dataset_path')
    
    if not dataset_path:
        return jsonify({'error': 'Dataset path required'}), 400
    
    def validate_worker():
        try:
            from utils.dataset_tools import DatasetValidator
            
            monitor.on_log(f"🔍 Validating dataset...")
            
            validator = DatasetValidator(dataset_path, on_progress=monitor.on_log)
            issues = validator.validate()
            
            total_issues = sum(len(items) for items in issues.values())
            
            if total_issues == 0:
                monitor.on_log(f"✅ No issues found! Dataset is clean.")
            else:
                monitor.on_log(f"⚠️ Found {total_issues} issues. Check logs above for details.")
            
        except Exception as e:
            monitor.on_log(f"❌ Error: {str(e)}")
    
    thread = threading.Thread(target=validate_worker, daemon=True)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Validation started'})


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    emit('connected', {'status': 'Connected to LoRA Training WebUI'})
    emit('training_update', training_state)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    pass



@socketio.on('request_update')
def handle_update_request():
    """Send current state to client"""
    emit('training_update', training_state)


def main():
    parser = argparse.ArgumentParser(description='LoRA Training WebUI')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=7860, help='Port to bind to')
    parser.add_argument('--share', action='store_true', help='Create public URL (gradio share)')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("LoRA Training WebUI")
    print("="*60)
    print(f"Starting server on http://{args.host}:{args.port}")
    print(f"Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    # Run server
    socketio.run(
        app,
        host=args.host,
        port=args.port,
        debug=args.debug,
        allow_unsafe_werkzeug=True
    )


if __name__ == '__main__':
    main()
