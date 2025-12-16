// VistralS2T - Main JavaScript
// Socket.IO connection and real-time updates

console.log('[LOAD] main.js loaded');

// Initialize Socket.IO
const socket = io({
    transports: ['polling', 'websocket'],
    upgrade: true,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5,
    timeout: 10000
});

console.log('[SOCKET] Socket.IO initialized');

// Global variables
let selectedFile = null;
let currentSessionId = null;
let lastUploadedFile = null;

// State persistence
const STATE_KEY = 'vistral_s2t_state';

// DOM Elements (will be initialized in DOMContentLoaded)
let uploadArea, fileInput, uploadBtn;
let progressContainer, resultsContainer, errorMessage;
let progressBar, progressText, stepLabel, stepProgress;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DOM] Content loaded, initializing...');
    
    // Get DOM elements
    uploadArea = document.getElementById('uploadArea');
    fileInput = document.getElementById('fileInput');
    uploadBtn = document.getElementById('uploadBtn');
    progressContainer = document.getElementById('progressContainer');
    resultsContainer = document.getElementById('resultsContainer');
    errorMessage = document.getElementById('errorMessage');
    progressBar = document.getElementById('progressBar');
    progressText = document.getElementById('progressText');
    stepLabel = document.getElementById('stepLabel');
    stepProgress = document.getElementById('stepProgress');
    
    // Check if elements exist
    console.log('[DOM] Elements found:', {
        uploadArea: !!uploadArea,
        fileInput: !!fileInput,
        uploadBtn: !!uploadBtn
    });
    
    if (!uploadArea || !fileInput || !uploadBtn) {
        console.error('[FATAL] Required elements not found!');
        alert('❌ ERROR: UI elements not found!\n\nPlease refresh the page.');
        return;
    }
    
    // Setup event listeners
    setupEventListeners();
    setupSocketListeners();
    
    // Clear cache on load
    clearState();
    console.log('[CACHE] Auto-cleared localStorage on page load');
    
    console.log('[INIT] Initialization complete');
});

// Setup Socket.IO Event Listeners
function setupSocketListeners() {
    socket.on('connect', function() {
        console.log('[WebSocket] ✅ Connected to server');
        console.log('[WebSocket] Socket ID:', socket.id);
        console.log('[WebSocket] Transport:', socket.io.engine.transport.name);
    });

    socket.on('disconnect', function() {
        console.log('[WebSocket] ❌ Disconnected from server');
    });

    socket.on('connect_error', function(error) {
        console.error('[WebSocket] Connection error:', error);
        console.error('[WebSocket] Error type:', error.type);
        console.error('[WebSocket] Error message:', error.message);
    });
    
    socket.on('connected', function(data) {
        console.log('[WebSocket] Server confirmed:', data.message);
    });
    
    socket.on('progress', function(data) {
        console.log('[PROGRESS]', data.step, data.progress + '%', data.message);
        updateProgress(data.step, data.progress, data.message);
    });
    
    socket.on('complete', function(data) {
        console.log('[COMPLETE] Processing finished:', data);
        displayResults(data);
    });
    
    socket.on('error', function(data) {
        console.error('[ERROR]', data.message);
        showError(data.message);
    });
    
    socket.on('model_selection_request', function(data) {
        console.log('[MODEL] Selection requested:', data);
        showModelSelection(data);
    });
    
    socket.on('llm_progress', function(data) {
        console.log('[LLM]', data.message);
        updateLLMProgress(data);
    });
}

// Setup UI Event Listeners
function setupEventListeners() {
    // Upload area click
    uploadArea.addEventListener('click', function() {
        console.log('[CLICK] Upload area clicked');
        fileInput.click();
    });
    
    // Drag and drop
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function() {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });
    
    // File selection
    fileInput.addEventListener('change', handleFileSelect);
    
    // Upload button
    uploadBtn.addEventListener('click', uploadFile);
    
    // Clear cache button
    const clearCacheBtn = document.getElementById('clearCacheBtn');
    if (clearCacheBtn) {
        clearCacheBtn.addEventListener('click', function() {
            if (confirm('🗑️ Xóa toàn bộ cache và reset Web UI?')) {
                clearState();
                resetUI();
                showNotification('✅ Cache cleared!', 'success');
            }
        });
    }
    
    // Clear server button
    const clearServerBtn = document.getElementById('clearServerBtn');
    if (clearServerBtn) {
        clearServerBtn.addEventListener('click', clearServerSessions);
    }
    
    console.log('[EVENTS] All event listeners attached');
}

// Handle file selection
function handleFileSelect() {
    if (fileInput.files.length > 0) {
        const newFile = fileInput.files[0];
        console.log('[FILE] Selected:', newFile.name, newFile.size, 'bytes');
        
        // Check file size (max 500MB)
        if (newFile.size > 500 * 1024 * 1024) {
            alert('❌ File too large! Maximum size is 500MB');
            fileInput.value = '';
            return;
        }
        
        // Check file type
        const ext = newFile.name.split('.').pop().toLowerCase();
        const allowed = ['mp3', 'wav', 'm4a', 'flac', 'ogg'];
        if (!allowed.includes(ext)) {
            alert('❌ Invalid file type! Allowed: ' + allowed.join(', '));
            fileInput.value = '';
            return;
        }
        
        selectedFile = newFile;
        uploadArea.querySelector('.upload-text').textContent = `Selected: ${newFile.name}`;
        uploadBtn.disabled = false;
        uploadBtn.textContent = '🚀 Start Processing';
    }
}

// Upload file and start processing
async function uploadFile() {
    if (!selectedFile) {
        alert('❌ Please select a file first!');
        return;
    }
    
    console.log('[UPLOAD] Starting upload:', selectedFile.name);
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    // Generate session ID
    currentSessionId = `session_${Date.now()}`;
    formData.append('session_id', currentSessionId);
    
    // Disable button
    uploadBtn.disabled = true;
    uploadBtn.textContent = '⏳ Uploading...';
    
    // Show progress container
    progressContainer.classList.add('active');
    resultsContainer.classList.remove('active');
    errorMessage.classList.remove('active');
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            console.log('[UPLOAD] Success:', data);
            lastUploadedFile = selectedFile;
            uploadBtn.textContent = '⏳ Processing...';
        } else {
            throw new Error(data.error || 'Upload failed');
        }
    } catch (error) {
        console.error('[UPLOAD] Error:', error);
        showError(error.message);
        uploadBtn.disabled = false;
        uploadBtn.textContent = '🚀 Start Processing';
        progressContainer.classList.remove('active');
    }
}

// Update progress UI
function updateProgress(step, progress, message) {
    stepLabel.textContent = message;
    stepProgress.textContent = Math.round(progress) + '%';
    progressBar.style.width = progress + '%';
    progressText.textContent = Math.round(progress) + '%';
    
    // Save state
    saveState({
        status: 'processing',
        progress: { step, progress, message },
        sessionId: currentSessionId
    });
}

// Display results
function displayResults(data) {
    console.log('[RESULTS] Displaying results:', data);
    
    progressContainer.classList.remove('active');
    resultsContainer.classList.add('active');
    
    // Update stats
    document.getElementById('statDuration').textContent = data.duration.toFixed(1);
    document.getElementById('statSpeakers').textContent = data.num_speakers;
    document.getElementById('statSegments').textContent = data.num_segments;
    
    // Update transcripts
    document.getElementById('timelineTranscript').textContent = data.timeline;
    document.getElementById('enhancedTranscript').textContent = data.enhanced || data.timeline;
    
    // Setup download buttons
    setupDownloadButtons(data);
    
    // Enable re-process
    uploadBtn.disabled = false;
    uploadBtn.textContent = '🔄 Process Another File';
    
    // Save state
    saveState({
        status: 'complete',
        results: data,
        sessionId: currentSessionId
    });
}

// Setup download buttons
function setupDownloadButtons(data) {
    const downloadTimeline = document.getElementById('downloadTimeline');
    const downloadEnhanced = document.getElementById('downloadEnhanced');
    const downloadSegments = document.getElementById('downloadSegments');
    
    if (downloadTimeline) {
        downloadTimeline.href = `/download/${data.session_id}/timeline`;
    }
    if (downloadEnhanced) {
        downloadEnhanced.href = `/download/${data.session_id}/enhanced`;
    }
    if (downloadSegments && data.files.segments) {
        downloadSegments.href = `/download/${data.session_id}/segments`;
    }
}

// Show error message
function showError(message) {
    errorMessage.textContent = `❌ Error: ${message}`;
    errorMessage.classList.add('active');
    progressContainer.classList.remove('active');
    uploadBtn.disabled = false;
    uploadBtn.textContent = '🚀 Start Processing';
}

// Show notification (simple)
function showNotification(message, type) {
    console.log('[NOTIFICATION]', type, message);
    // Could add toast notification here
}

// State persistence functions
function saveState(state) {
    try {
        localStorage.setItem(STATE_KEY, JSON.stringify({
            ...state,
            timestamp: Date.now()
        }));
    } catch (e) {
        console.warn('Failed to save state:', e);
    }
}

function clearState() {
    try {
        localStorage.removeItem(STATE_KEY);
    } catch (e) {
        console.warn('Failed to clear state:', e);
    }
}

// Reset UI to initial state
function resetUI() {
    progressContainer.classList.remove('active');
    resultsContainer.classList.remove('active');
    errorMessage.classList.remove('active');
    
    selectedFile = null;
    lastUploadedFile = null;
    fileInput.value = '';
    uploadArea.querySelector('.upload-text').textContent = 'Click to upload or drag & drop audio file';
    uploadBtn.disabled = true;
    uploadBtn.textContent = '🚀 Start Processing';
}

// Clear server sessions
async function clearServerSessions() {
    if (!confirm('🗑️ Clear all sessions on server?\n\nThis will delete all processed results.')) {
        return;
    }
    
    try {
        const response = await fetch('/clear-sessions', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            showNotification(`✅ Cleared ${data.sessions_deleted} session(s)`, 'success');
        } else {
            showError(data.error);
        }
    } catch (error) {
        console.error('[CLEAR] Error:', error);
        showError(error.message);
    }
}

// Model selection dialog (placeholder)
function showModelSelection(data) {
    console.log('[MODEL] Show selection dialog:', data);
    // TODO: Implement model selection UI
}

// LLM progress update (placeholder)
function updateLLMProgress(data) {
    console.log('[LLM]', data.message);
    // TODO: Show LLM progress in UI
}

console.log('[LOAD] main.js initialization complete');
