# -*- coding: utf-8 -*-
"""
Flask Web UI for Vietnamese Speech-to-Text
Simple drag & drop interface for audio transcription
"""

from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, flash
import os
import sys
import time
import json
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
import subprocess
import threading

# Add project paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
app.secret_key = 'vietnamese-speech-to-text-2025'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Directories
UPLOAD_FOLDER = Path('data/audio')
RESULTS_FOLDER = Path('data/results')
UPLOAD_FOLDER.mkdir(exist_ok=True)
RESULTS_FOLDER.mkdir(exist_ok=True)

# Allowed audio extensions
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma', '.mp4', '.avi'}

# Job storage (in production use Redis/Database)
jobs = {}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def run_transcription(job_id, audio_path, model):
    """Background task to run transcription"""
    try:
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['progress'] = 10
        
        start_time = time.time()
        
        if model == 't5':
            # Run T5 model
            result = subprocess.run([
                sys.executable, 'src/t5_model.py', audio_path
            ], capture_output=True, text=True, timeout=3600)
        elif model == 'gemini':
            # Run Gemini model
            result = subprocess.run([
                sys.executable, 'src/gemini_model.py', audio_path
            ], capture_output=True, text=True, timeout=3600)
        elif model == 'smart':
            # Run smart dual
            result = subprocess.run([
                sys.executable, 'core/run_dual_smart.py', audio_path
            ], capture_output=True, text=True, timeout=3600)
        elif model == 'fast':
            # Run fast dual
            result = subprocess.run([
                sys.executable, 'core/run_dual_fast.py', audio_path
            ], capture_output=True, text=True, timeout=3600)
        else:
            raise ValueError(f"Unknown model: {model}")
        
        processing_time = time.time() - start_time
        
        if result.returncode == 0:
            # Find result files
            result_files = []
            for ext in ['*.txt']:
                result_files.extend(RESULTS_FOLDER.glob(ext))
            
            # Get the most recent result
            if result_files:
                latest_result = max(result_files, key=os.path.getctime)
                with open(latest_result, 'r', encoding='utf-8') as f:
                    transcript = f.read()
            else:
                transcript = result.stdout or "Transcription completed but no output file found"
            
            jobs[job_id].update({
                'status': 'completed',
                'progress': 100,
                'transcript': transcript,
                'processing_time': processing_time,
                'result_file': str(latest_result) if result_files else None
            })
        else:
            jobs[job_id].update({
                'status': 'failed',
                'error': result.stderr or result.stdout or "Unknown error",
                'processing_time': processing_time
            })
            
    except subprocess.TimeoutExpired:
        jobs[job_id].update({
            'status': 'failed',
            'error': 'Transcription timeout (1 hour limit)',
            'processing_time': 3600
        })
    except Exception as e:
        jobs[job_id].update({
            'status': 'failed',
            'error': str(e),
            'processing_time': time.time() - start_time if 'start_time' in locals() else 0
        })

@app.route('/')
def index():
    """Main page with upload form"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start transcription"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not supported. Use: mp3, wav, m4a, flac, aac, ogg, wma'}), 400
    
    model = request.form.get('model', 'smart')
    
    # Save uploaded file
    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    file_extension = Path(filename).suffix
    saved_filename = f"{file_id}_{filename}"
    file_path = UPLOAD_FOLDER / saved_filename
    
    file.save(file_path)
    
    # Create job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'id': job_id,
        'filename': filename,
        'model': model,
        'status': 'queued',
        'progress': 0,
        'created_at': time.time(),
        'audio_path': str(file_path)
    }
    
    # Start background transcription
    thread = threading.Thread(
        target=run_transcription,
        args=(job_id, str(file_path), model)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'filename': filename,
        'model': model,
        'status': 'queued'
    })

@app.route('/status/<job_id>')
def job_status(job_id):
    """Get job status"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(jobs[job_id])

@app.route('/result/<job_id>')
def get_result(job_id):
    """Get transcription result"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    
    return jsonify({
        'transcript': job.get('transcript', ''),
        'processing_time': job.get('processing_time', 0),
        'model': job['model'],
        'filename': job['filename']
    })

@app.route('/download/<job_id>')
def download_result(job_id):
    """Download result as text file"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    
    # Create text file
    result_file = RESULTS_FOLDER / f"transcript_{job_id}.txt"
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(f"Filename: {job['filename']}\n")
        f.write(f"Model: {job['model']}\n")
        f.write(f"Processing Time: {job.get('processing_time', 0):.2f}s\n")
        f.write(f"Created: {time.ctime(job['created_at'])}\n")
        f.write("\n" + "="*50 + "\n")
        f.write("TRANSCRIPT:\n")
        f.write("="*50 + "\n\n")
        f.write(job.get('transcript', ''))
    
    return send_file(result_file, as_attachment=True)

@app.route('/cleanup')
def cleanup_files():
    """Clean up old files"""
    try:
        # Remove files older than 1 hour
        cutoff_time = time.time() - 3600
        
        cleaned = {'audio': 0, 'results': 0}
        
        # Clean audio files
        for audio_file in UPLOAD_FOLDER.glob('*'):
            if audio_file.stat().st_mtime < cutoff_time:
                audio_file.unlink()
                cleaned['audio'] += 1
        
        # Clean result files  
        for result_file in RESULTS_FOLDER.glob('*'):
            if result_file.stat().st_mtime < cutoff_time:
                result_file.unlink()
                cleaned['results'] += 1
        
        # Clean old jobs
        old_jobs = [job_id for job_id, job in jobs.items() 
                   if job['created_at'] < cutoff_time]
        for job_id in old_jobs:
            del jobs[job_id]
        
        cleaned['jobs'] = len(old_jobs)
        
        return jsonify({
            'message': 'Cleanup completed',
            'cleaned': cleaned
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/models')
def get_models():
    """Get available models"""
    return jsonify({
        'models': {
            'smart': 'Smart Dual (8-15 min, offline)',
            'fast': 'Fast Dual (2-5 min, offline)',
            't5': 'T5 AI Fusion (10-20 min, offline)',
            'gemini': 'Gemini AI (8-15 min, needs API key)'
        }
    })

@app.route('/jobs')
def list_jobs():
    """List all jobs"""
    return jsonify({'jobs': list(jobs.values())})

if __name__ == '__main__':
    print("[MIC] Vietnamese Speech-to-Text Web UI")
    print("[WEB] Starting Flask server...")
    print("[FOLDER] Upload folder:", UPLOAD_FOLDER.absolute())
    print("[FILE] Results folder:", RESULTS_FOLDER.absolute())
    print("")
    print("[LAUNCH] Open your browser at: http://localhost:5000")
    print("")
    
    app.run(debug=True, host='0.0.0.0', port=5000)