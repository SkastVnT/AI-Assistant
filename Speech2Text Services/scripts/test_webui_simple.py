"""
Simple Web UI Test với FORCE_CPU
Test basic functionality without complex models
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO
from dotenv import load_dotenv

# Load environment
load_dotenv("app/config/.env")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>VistralS2T - Force CPU Test</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <h1>🎤 VistralS2T - Force CPU Test</h1>
    
    <div>
        <h2>Environment Status</h2>
        <p><strong>FORCE_CPU:</strong> {{ force_cpu }}</p>
        <p><strong>PyTorch Available:</strong> {{ torch_available }}</p>
        <p><strong>CUDA Available:</strong> {{ cuda_available }}</p>
        <p><strong>Device Selected:</strong> {{ device }}</p>
    </div>
    
    <div>
        <h2>Test Upload</h2>
        <input type="file" id="audioFile" accept=".mp3,.wav,.m4a,.flac">
        <button onclick="testUpload()">Test Upload</button>
    </div>
    
    <div id="results"></div>
    
    <script>
        const socket = io();
        
        socket.on('progress', function(data) {
            const results = document.getElementById('results');
            results.innerHTML += '<p>[' + data.step + '] ' + data.progress + '% - ' + data.message + '</p>';
        });
        
        function testUpload() {
            const file = document.getElementById('audioFile').files[0];
            if (!file) {
                alert('Please select an audio file');
                return;
            }
            
            const formData = new FormData();
            formData.append('audio', file);
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log('Upload result:', data);
                document.getElementById('results').innerHTML += '<p><strong>Upload Result:</strong> ' + JSON.stringify(data) + '</p>';
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('results').innerHTML += '<p style="color: red;"><strong>Error:</strong> ' + error + '</p>';
            });
        }
    </script>
</body>
</html>
    ''', 
    force_cpu=os.getenv("FORCE_CPU", "false"),
    torch_available=test_torch(),
    cuda_available=test_cuda(),
    device=get_safe_device()
    )

@app.route('/upload', methods=['POST'])
def upload():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Just test the upload without processing
    return jsonify({
        'status': 'success',
        'filename': file.filename,
        'size': len(file.read()),
        'force_cpu': os.getenv("FORCE_CPU", "false"),
        'device': get_safe_device()
    })

def test_torch():
    try:
        import torch
        return f"✅ {torch.__version__}"
    except Exception as e:
        return f"❌ {str(e)}"

def test_cuda():
    try:
        import torch
        return torch.cuda.is_available()
    except:
        return "N/A"

def get_safe_device():
    try:
        force_cpu = os.getenv("FORCE_CPU", "false").lower() in ["true", "1", "yes"]
        if force_cpu:
            return "cpu (forced)"
        
        import torch
        if torch.cuda.is_available():
            try:
                test_tensor = torch.randn(1).cuda()
                _ = test_tensor + 1
                return "cuda (working)"
            except Exception as e:
                return f"cpu (cuda failed: {str(e)[:50]}...)"
        else:
            return "cpu (no cuda)"
    except Exception as e:
        return f"cpu (error: {str(e)[:50]}...)"

if __name__ == '__main__':
    print("=" * 60)
    print("SIMPLE WEB UI TEST")
    print("=" * 60)
    print(f"FORCE_CPU: {os.getenv('FORCE_CPU', 'false')}")
    print(f"PyTorch: {test_torch()}")
    print(f"CUDA Available: {test_cuda()}")
    print(f"Device: {get_safe_device()}")
    print("=" * 60)
    print("Starting server at http://localhost:5001")
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)