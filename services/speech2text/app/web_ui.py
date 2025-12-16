# -*- coding: utf-8 -*-
"""
VistralS2T Web UI - Flask Application
Features:
- Audio upload
- Real-time diarization + transcription
- Live progress updates via WebSocket
- Results visualization
"""
import os
import sys
import time
import datetime
import threading
import warnings
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from dotenv import load_dotenv

# Force CPU-only (cuDNN not installed properly on this system)
os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Suppress torchcodec warnings (non-critical, PhoWhisper has fallback)
warnings.filterwarnings('ignore', message='.*torchcodec.*')
warnings.filterwarnings('ignore', message='.*libtorchcodec.*')

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.llm import SpeakerDiarizationClient, WhisperClient, PhoWhisperClient, GeminiClient, MultiLLMClient
from core.utils import preprocess_audio

# Load environment with absolute path
env_path = Path(__file__).parent / "config" / ".env"
load_dotenv(env_path)
print(f"[ENV] Loading environment from: {env_path}")
print(f"[ENV] HF_TOKEN loaded: {'YES' if os.getenv('HUGGINGFACE_TOKEN') else 'NO'}")

# Get base directory
BASE_DIR = Path(__file__).parent  # app directory
TEMPLATE_DIR = BASE_DIR / 'templates'
STATIC_DIR = BASE_DIR / 'static'

# Initialize Flask app
app = Flask(__name__, 
            template_folder=str(TEMPLATE_DIR),
            static_folder=str(STATIC_DIR))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'vistral-s2t-secret-key-2025')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'data/audio/raw'

# Enable CORS and WebSocket
CORS(app)
# Use threading async mode for better Windows compatibility
# eventlet has DNS resolution issues on Windows
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
print("[WebSocket] Using threading async mode")

# Global state for processing
processing_state = {
    'is_processing': False,
    'current_step': None,
    'progress': 0,
    'session_id': None,
    'error': None
}

# Global state for model selection
model_selection_state = {
    'waiting': False,
    'selected_model': None,
    'session_id': None
}

# Allowed extensions
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'flac', 'ogg'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def emit_progress(step, progress, message):
    """Emit progress update to client"""
    global processing_state
    processing_state['current_step'] = step
    processing_state['progress'] = progress
    
    socketio.emit('progress', {
        'step': step,
        'progress': progress,
        'message': message
    })
    
    # Also print to console for debugging
    print(f"[PROGRESS] {step}: {progress}% - {message}")

def wait_for_model_selection(session_id, timeout=30):
    """
    Wait for user to select a model, with timeout
    
    Args:
        session_id: Current session ID
        timeout: Maximum wait time in seconds (default: 30)
    
    Returns:
        str: Selected model ('gemini', 'openai', 'deepseek') or 'gemini' if timeout
    """
    import time
    global model_selection_state
    
    # Initialize selection state
    model_selection_state['waiting'] = True
    model_selection_state['selected_model'] = None
    model_selection_state['session_id'] = session_id
    
    # Emit request to frontend
    socketio.emit('model_selection_request', {
        'session_id': session_id,
        'timeout': timeout,
        'available_models': ['gemini', 'openai', 'deepseek']
    })
    
    # Wait for selection with timeout
    start_time = time.time()
    while time.time() - start_time < timeout:
        if model_selection_state['selected_model'] is not None:
            selected = model_selection_state['selected_model']
            # Reset state
            model_selection_state['waiting'] = False
            model_selection_state['selected_model'] = None
            return selected
        time.sleep(0.1)  # Check every 100ms
    
    # Timeout - reset state and return default
    model_selection_state['waiting'] = False
    model_selection_state['selected_model'] = None
    print(f"[TIMEOUT] No model selected in {timeout}s, defaulting to Gemini")
    return 'gemini'

def process_audio_with_diarization(audio_path, session_id):
    """
    Process audio with diarization + dual model transcription
    Emits real-time progress via WebSocket
    """
    import time
    start_time = time.time()
    
    # Track timing for each model
    timings = {
        'preprocessing': 0,
        'diarization': 0,
        'whisper': 0,
        'phowhisper': 0,
        'gemini': 0,
        'total': 0
    }
    
    global processing_state
    
    try:
        processing_state['is_processing'] = True
        processing_state['session_id'] = session_id
        processing_state['error'] = None
        
        # Initialize variables
        segments_file = None
        
        # Session directory
        SESSION_DIR = f"data/results/sessions/{session_id}"
        os.makedirs(SESSION_DIR, exist_ok=True)
        
        # ============= STEP 1: PREPROCESSING =============
        step_start = time.time()
        emit_progress('preprocessing', 10, 'Preprocessing audio...')
        
        import librosa
        import soundfile as sf
        
        audio, sr = librosa.load(audio_path, sr=16000)
        duration = len(audio) / sr
        
        preprocessed_path = f"{SESSION_DIR}/preprocessed.wav"
        sf.write(preprocessed_path, audio, sr)
        
        timings['preprocessing'] = time.time() - step_start
        emit_progress('preprocessing', 15, f'Audio loaded: {duration:.1f}s')
        
        # ============= STEP 2: DIARIZATION =============
        step_start = time.time()
        emit_progress('diarization', 20, 'Loading diarization model...')
        
        try:
            diarizer = SpeakerDiarizationClient(
                min_speakers=2,
                max_speakers=5,
                hf_token=os.getenv('HF_TOKEN') or os.getenv('HF_API_TOKEN')
            )
            diarizer.load()
            
            emit_progress('diarization', 30, 'Detecting speakers...')
            segments = diarizer.diarize(preprocessed_path, min_duration=1.0)
            
            # Save segments
            segments_file = f"{SESSION_DIR}/speaker_segments.txt"
            diarizer.save_segments(segments, segments_file)
            
            num_speakers = len(set(seg.speaker_id for seg in segments))
            timings['diarization'] = time.time() - step_start
            emit_progress('diarization', 40, f'Detected {num_speakers} speakers, {len(segments)} segments')
            
        except Exception as e:
            print(f"[ERROR] Diarization failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            emit_progress('diarization', 40, f'Diarization failed, using full audio: {str(e)}')
            from core.llm.diarization_client import SpeakerSegment
            segments = [SpeakerSegment(
                speaker_id="SPEAKER_00",
                start_time=0.0,
                end_time=duration,
                duration=duration
            )]
            segments_file = None  # No segments file when diarization fails
        
        # ============= STEP 3: EXTRACT SEGMENTS =============
        emit_progress('segmentation', 45, 'Extracting audio segments...')
        
        segment_dir = f"{SESSION_DIR}/audio_segments"
        os.makedirs(segment_dir, exist_ok=True)
        
        segment_files = []
        for i, seg in enumerate(segments):
            start_sample = int(seg.start_time * sr)
            end_sample = int(seg.end_time * sr)
            segment_audio = audio[start_sample:end_sample]
            
            segment_path = f"{segment_dir}/segment_{i:03d}_{seg.speaker_id}.wav"
            sf.write(segment_path, segment_audio, sr)
            segment_files.append((seg, segment_path))
        
        emit_progress('segmentation', 50, f'Extracted {len(segment_files)} segments')
        
        # ============= STEP 4: WHISPER TRANSCRIPTION =============
        step_start = time.time()
        emit_progress('whisper', 55, 'Loading Whisper model...')
        
        whisper = WhisperClient(model_name="large-v3")
        whisper.load()
        
        segment_transcripts = []
        total_segments = len(segment_files)
        
        for i, (seg, seg_path) in enumerate(segment_files):
            progress = 55 + int((i / total_segments) * 20)  # 55-75%
            emit_progress('whisper', progress, 
                         f'Transcribing segment {i+1}/{total_segments} ({seg.speaker_id})...')
            
            transcript, _ = whisper.transcribe(seg_path)
            segment_transcripts.append({
                'segment': seg,
                'transcript': transcript.strip(),
                'path': seg_path
            })
        
        timings['whisper'] = time.time() - step_start
        emit_progress('whisper', 75, 'Whisper transcription complete')
        
        # ============= STEP 5: PHOWHISPER TRANSCRIPTION =============
        step_start = time.time()
        emit_progress('phowhisper', 78, 'Loading PhoWhisper model...')
        
        try:
            phowhisper = PhoWhisperClient()
            phowhisper.load()
            
            pho_transcripts = []
            for i, (seg, seg_path) in enumerate(segment_files):
                progress = 78 + int((i / total_segments) * 10)  # 78-88%
                emit_progress('phowhisper', progress,
                             f'PhoWhisper segment {i+1}/{total_segments}...')
                
                transcript, _ = phowhisper.transcribe(seg_path)
                pho_transcripts.append(transcript.strip())
            
            timings['phowhisper'] = time.time() - step_start
            emit_progress('phowhisper', 88, 'PhoWhisper transcription complete')
            
        except Exception as e:
            timings['phowhisper'] = time.time() - step_start
            emit_progress('phowhisper', 88, f'PhoWhisper skipped: {str(e)}')
            pho_transcripts = [t['transcript'] for t in segment_transcripts]
        
        # ============= STEP 6: BUILD TIMELINE =============
        emit_progress('timeline', 90, 'Building timeline transcript...')
        
        timeline = []
        timeline.append("=" * 80)
        timeline.append("TIMELINE TRANSCRIPT WITH SPEAKER DIARIZATION")
        timeline.append("=" * 80)
        timeline.append("")
        
        for i, trans_data in enumerate(segment_transcripts):
            seg = trans_data['segment']
            text = trans_data['transcript']
            
            timeline.append(f"[{seg.start_time:7.2f}s - {seg.end_time:7.2f}s] {seg.speaker_id}:")
            timeline.append(f"  {text}")
            timeline.append("")
        
        timeline_text = "\n".join(timeline)
        timeline_file = f"{SESSION_DIR}/timeline_transcript.txt"
        with open(timeline_file, 'w', encoding='utf-8') as f:
            f.write(timeline_text)
        
        # ============= STEP 7: MODEL SELECTION & WAIT =============
        emit_progress('model_selection', 90, 'Waiting for model selection...')
        
        # Wait for user to select a model (30s timeout, defaults to Gemini)
        selected_model = wait_for_model_selection(session_id, timeout=30)
        emit_progress('model_selection', 92, f'Selected model: {selected_model}')
        
        # ============= STEP 8: LLM ENHANCEMENT WITH AUTO-FALLBACK CHAIN =============
        step_start = time.time()
        
        clean_text = None
        llm_success = False
        enhanced_file = None
        
        # Build dual transcript for LLM (build once, use for all models)
        dual_text = f"WHISPER TRANSCRIPT:\n{timeline_text}\n\n"
        dual_text += "PHOWHISPER TRANSCRIPT:\n"
        for i, (trans, pho) in enumerate(zip(segment_transcripts, pho_transcripts)):
            seg = trans['segment']
            dual_text += f"[{seg.start_time:.2f}s - {seg.end_time:.2f}s] {seg.speaker_id}: {pho}\n"
        
        # Define fallback chain: selected model -> grok -> deepseek -> openai
        fallback_chain = [selected_model]
        
        # Add fallback models (avoid duplicates)
        for fallback in ['grok', 'deepseek', 'openai']:
            if fallback not in fallback_chain:
                fallback_chain.append(fallback)
        
        print(f"[LLM FALLBACK] Chain: {' -> '.join(fallback_chain)}")
        
        # Try each model in the chain
        for model_idx, current_model in enumerate(fallback_chain):
            if llm_success:
                break  # Already succeeded, skip remaining models
            
            try:
                emit_progress('llm_enhancement', 93, f'Loading {current_model.upper()} model for transcript cleaning...')
                
                # Initialize MultiLLMClient with current model
                multi_llm = MultiLLMClient(model_type=current_model)
                multi_llm.load()
                
                emit_progress('llm_enhancement', 95, f'Cleaning transcript with {current_model.upper()} AI...')
                
                # Define progress callback for detailed monitoring
                def llm_progress_callback(message):
                    """Forward LLM progress to frontend"""
                    socketio.emit('llm_progress', {
                        'message': message,
                        'model': current_model
                    })
                    print(f"[LLM PROGRESS] {message}")
                
                # Use clean_transcript with 30s timeout
                import signal
                from contextlib import contextmanager
                
                class TimeoutException(Exception):
                    pass
                
                @contextmanager
                def time_limit(seconds):
                    """Context manager for timeout (Windows compatible using threading)"""
                    import threading
                    
                    timer = None
                    timed_out = [False]  # Use list to allow modification in nested function
                    
                    def timeout_handler():
                        timed_out[0] = True
                    
                    try:
                        timer = threading.Timer(seconds, timeout_handler)
                        timer.start()
                        yield timed_out
                    finally:
                        if timer:
                            timer.cancel()
                
                # Try with 30s timeout
                clean_text = None
                gen_time = 0
                
                with time_limit(30) as timed_out:
                    model_start = time.time()
                    clean_text, gen_time = multi_llm.clean_transcript(
                        whisper_text=timeline_text,
                        phowhisper_text=dual_text,
                        max_new_tokens=4096,
                        progress_callback=llm_progress_callback
                    )
                    
                    # Check if we timed out during processing
                    if timed_out[0]:
                        raise TimeoutException(f"{current_model.upper()} timeout after 30s")
                
                if clean_text:
                    llm_success = True
                    enhanced_file = f"{SESSION_DIR}/enhanced_transcript.txt"
                    with open(enhanced_file, 'w', encoding='utf-8') as f:
                        f.write(clean_text)
                    
                    timings[current_model] = time.time() - step_start
                    success_msg = f'{current_model.upper()} enhancement complete ({gen_time:.2f}s)'
                    emit_progress('llm_enhancement', 98, success_msg)
                    socketio.emit('llm_progress', {
                        'message': f'✅ {success_msg}',
                        'model': current_model
                    })
                    selected_model = current_model  # Update selected model for results
                    break  # Success! Exit fallback chain
                else:
                    raise Exception("LLM returned empty result")
                
            except Exception as e:
                timings[current_model] = time.time() - step_start
                error_msg = f'LLM enhancement failed: {str(e)[:100]}'
                error_type = type(e).__name__
                
                # Provide helpful error messages
                if "timeout" in str(e).lower() or isinstance(e, TimeoutException):
                    error_msg = f'❌ {current_model.upper()} timeout after 30s'
                elif "quota" in str(e).lower() or "429" in str(e):
                    error_msg = f'❌ {current_model.upper()} quota exhausted'
                elif "api key" in str(e).lower() or "404" in str(e) or "not found" in str(e).lower():
                    error_msg = f'❌ {current_model.upper()} API key invalid or model not available'
                elif "not installed" in str(e).lower():
                    error_msg = f'❌ {current_model.upper()} dependencies not installed'
                elif "network" in str(e).lower() or "connection" in str(e).lower():
                    error_msg = f'❌ {current_model.upper()} network error'
                else:
                    error_msg = f'❌ {current_model.upper()} error ({error_type}): {str(e)[:80]}'
                
                emit_progress('llm_enhancement', 94, error_msg)
                print(f"[ERROR] {current_model.upper()} failed ({error_type}): {str(e)}")
                
                socketio.emit('llm_progress', {
                    'message': error_msg,
                    'model': current_model,
                    'error': True,
                    'error_type': error_type
                })
                
                # If not last model in chain, try next one
                if model_idx < len(fallback_chain) - 1:
                    next_model = fallback_chain[model_idx + 1]
                    fallback_msg = f'🔄 Trying fallback: {next_model.upper()}'
                    emit_progress('llm_enhancement', 94, fallback_msg)
                    socketio.emit('llm_progress', {
                        'message': fallback_msg,
                        'model': next_model
                    })
                    print(f"[FALLBACK] Switching to {next_model.upper()}")
                    continue  # Try next model
                else:
                    # Last model failed, give up
                    print(f"[ERROR] All models in chain failed")
                    break
        
        # ============= FINALIZE =============
        emit_progress('complete', 100, 'Processing complete!')
        
        # Calculate processing time
        end_time = time.time()
        processing_time = end_time - start_time
        timings['total'] = processing_time
        
        # Get prompt version for cache validation
        from core.prompts.templates import PromptTemplates
        prompt_version = PromptTemplates.VERSION
        
        # Build results
        results = {
            'session_id': session_id,
            'duration': duration,
            'num_speakers': len(set(seg.speaker_id for seg in segments)),
            'num_segments': len(segments),
            'timeline': timeline_text,
            'enhanced': clean_text if llm_success else timeline_text,  # Fallback to timeline if LLM failed
            'clean_text': clean_text,  # Separate field for clean text (None if failed)
            'llm_success': llm_success,  # Flag to indicate if LLM succeeded
            'selected_model': selected_model,  # Which model was used
            'files': {
                'timeline': timeline_file,
                'enhanced': enhanced_file if llm_success else timeline_file,
                'segments': segments_file,
                'audio_segments': segment_dir
            },
            'processingTime': processing_time,  # Add processing time in seconds
            'promptVersion': prompt_version,     # Add prompt version for cache validation
            'timings': timings  # Add detailed timings for each model
        }
    
        # Emit completion with explicit broadcast
        print(f"[COMPLETE] Emitting results: session={session_id}, speakers={results['num_speakers']}, segments={results['num_segments']}")
        socketio.emit('complete', results, namespace='/')
        print(f"[COMPLETE] Processing finished! Session: {session_id}")
        
        processing_state['is_processing'] = False
        return results
        
    except Exception as e:
        processing_state['is_processing'] = False
        processing_state['error'] = str(e)
        emit_progress('error', 0, f'Error: {str(e)}')
        socketio.emit('error', {'message': str(e)})
        print(f"[ERROR] Processing failed: {str(e)}")
        raise


@app.route('/')
def index():
    """Main page (original UI)"""
    return render_template('index.html')

@app.route('/test')
def test_simple():
    """Simple test page for debugging"""
    return render_template('test_simple.html')

@app.route('/debug/info')
def debug_info():
    """Debug endpoint to check server status"""
    import flask_socketio
    return jsonify({
        'status': 'running',
        'flask_socketio_version': flask_socketio.__version__,
        'processing_state': processing_state,
        'endpoints': [str(rule) for rule in app.url_map.iter_rules()],
        'socketio_async_mode': socketio.async_mode
    })

@app.route('/modern')
def modern():
    """Modern UI (ChatBot-style)"""
    return render_template('index_modern.html')

@app.route('/chatbot')
@app.route('/chatbot-ui')
def chatbot_ui():
    """ChatBot-style UI (New Modern Design)"""
    return render_template('index_chatbot_style.html')

@app.route('/upload', methods=['POST'])
@app.route('/api/process', methods=['POST'])  # Alias for modern UI
def upload_file():
    """Handle file upload and start processing"""
    global processing_state
    
    if processing_state['is_processing']:
        return jsonify({'error': 'Already processing another file'}), 400
    
    # Support both 'file' (old UI) and 'audio' (new UI)
    file = request.files.get('file') or request.files.get('audio')
    
    if not file:
        return jsonify({'error': 'No file provided'}), 400
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    try:
        # Save file
        filename = secure_filename(file.filename)
        
        # Get session_id from form data or generate new one
        session_id = request.form.get('session_id') or f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(audio_path)
        
        # Start processing in background thread
        thread = threading.Thread(
            target=process_audio_with_diarization,
            args=(audio_path, session_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': 'Upload successful, processing started',
            'session_id': session_id,
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def get_status():
    """Get current processing status"""
    return jsonify(processing_state)

@socketio.on('model_selected')
def handle_model_selection(data):
    """
    Handle model selection from client
    
    Expected data:
        {
            'session_id': str,
            'model': str  # 'gemini', 'openai', or 'deepseek'
        }
    """
    global model_selection_state
    
    session_id = data.get('session_id')
    selected_model = data.get('model', 'gemini')
    
    # Validate model
    valid_models = ['gemini', 'openai', 'deepseek']
    if selected_model not in valid_models:
        selected_model = 'gemini'
    
    # Only accept if we're waiting for this session
    if model_selection_state['waiting'] and model_selection_state['session_id'] == session_id:
        model_selection_state['selected_model'] = selected_model
        print(f"[MODEL SELECTED] Session {session_id}: {selected_model}")
        
        # Emit confirmation
        socketio.emit('model_selection_confirmed', {
            'session_id': session_id,
            'model': selected_model
        })

@app.route('/download/<session_id>/<file_type>')
def download_file(session_id, file_type):
    """Download result files"""
    session_dir = f"data/results/sessions/{session_id}"
    
    file_map = {
        'timeline': 'timeline_transcript.txt',
        'enhanced': 'enhanced_transcript.txt',
        'segments': 'speaker_segments.txt'
    }
    
    if file_type not in file_map:
        return jsonify({'error': 'Invalid file type'}), 400
    
    file_path = os.path.join(session_dir, file_map[file_type])
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/clear-sessions', methods=['POST'])
def clear_sessions():
    """Force clear all session folders on server"""
    import shutil
    
    try:
        sessions_dir = "data/results/sessions"
        
        if os.path.exists(sessions_dir):
            # Count sessions before delete
            session_count = len([d for d in os.listdir(sessions_dir) if os.path.isdir(os.path.join(sessions_dir, d))])
            
            # Remove all session folders
            shutil.rmtree(sessions_dir)
            
            # Recreate empty directory
            os.makedirs(sessions_dir, exist_ok=True)
            
            print(f"[CLEAR SESSIONS] Deleted {session_count} session folders")
            
            return jsonify({
                'success': True,
                'message': f'Cleared {session_count} session(s)',
                'sessions_deleted': session_count
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Sessions folder does not exist',
                'sessions_deleted': 0
            })
            
    except Exception as e:
        print(f"[ERROR] Failed to clear sessions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'message': 'Connected to VistralS2T server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('[WEBSOCKET] Client disconnected')

@socketio.on('cancel')
def handle_cancel():
    """Handle processing cancellation"""
    global processing_state
    processing_state['is_processing'] = False
    emit('cancelled', {'message': 'Processing cancelled'})


if __name__ == '__main__':
    # Set UTF-8 encoding for Windows console
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("=" * 80)
    print("VISTRAL S2T - WEB UI SERVER")
    print("=" * 80)
    print()
    print("Starting server...")
    # Get port from environment
    port = int(os.getenv('SPEECH2TEXT_PORT', 5001))
    print(f"Open browser at: http://localhost:{port}")
    print()
    print("Features:")
    print("  [OK] Audio upload (mp3, wav, m4a, flac)")
    print("  [OK] Real-time progress tracking")
    print("  [OK] Speaker diarization")
    print("  [OK] Dual model transcription (Whisper + PhoWhisper)")
    print("  [OK] Gemini AI transcript cleaning (free)")
    print("  [OK] Results download")
    print()
    print("=" * 80)
    
    # Get port from environment or use default
    port = int(os.getenv('SPEECH2TEXT_PORT', 5001))
    host = os.getenv('FLASK_HOST', '127.0.0.1')  # Localhost only for security
    
    # Run with socketio for WebSocket support
    # Use debug=False to avoid issues with reloader
    socketio.run(app, 
                 host=host, 
                 port=port, 
                 debug=False,  # Changed from True to False to prevent crash
                 use_reloader=False,
                 log_output=True)
