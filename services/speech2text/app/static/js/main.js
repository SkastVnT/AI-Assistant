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
let timingChart = null;

// State persistence
const STATE_KEY = 'vistral_s2t_state';

// DOM Elements (will be initialized in DOMContentLoaded)
let uploadArea, fileInput, uploadBtn, stopBtn;
let progressSection, resultsSection, chartsSection;
let progressBar, progressPercent, currentStep;
let logsContainer, autoScroll;
let fileInfo, fileName, fileSize;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DOM] Content loaded, initializing...');
    
    // Get DOM elements
    uploadArea = document.getElementById('uploadArea');
    fileInput = document.getElementById('fileInput');
    uploadBtn = document.getElementById('uploadBtn');
    stopBtn = document.getElementById('stopBtn');
    progressSection = document.getElementById('progressSection');
    resultsSection = document.getElementById('resultsSection');
    chartsSection = document.getElementById('chartsSection');
    progressBar = document.getElementById('progressBar');
    progressPercent = document.getElementById('progressPercent');
    currentStep = document.getElementById('currentStep');
    logsContainer = document.getElementById('logsContainer');
    autoScroll = document.getElementById('autoScroll');
    fileInfo = document.getElementById('fileInfo');
    fileName = document.getElementById('fileName');
    fileSize = document.getElementById('fileSize');
    
    // Check if elements exist
    console.log('[DOM] Elements found:', {
        uploadArea: !!uploadArea,
        fileInput: !!fileInput,
        uploadBtn: !!uploadBtn
    });
    
    if (!uploadArea || !fileInput || !uploadBtn) {
        console.error('[FATAL] Required elements not found!');
        addLog('❌ ERROR: UI elements not found! Please refresh the page.', 'error');
        return;
    }
    
    // Initialize charts
    initializeCharts();
    
    // Setup event listeners
    setupEventListeners();
    setupSocketListeners();
    
    // Clear cache on load
    clearState();
    addLog('✅ VistralS2T WebUI initialized', 'success');
    
    console.log('[INIT] Initialization complete');
});

// Setup Socket.IO Event Listeners
function setupSocketListeners() {
    socket.on('connect', function() {
        console.log('[WebSocket] ✅ Connected to server');
        console.log('[WebSocket] Socket ID:', socket.id);
        console.log('[WebSocket] Transport:', socket.io.engine.transport.name);
        updateConnectionStatus(true);
    });

    socket.on('disconnect', function() {
        console.log('[WebSocket] ❌ Disconnected from server');
        updateConnectionStatus(false);
    });

    socket.on('connect_error', function(error) {
        console.error('[WebSocket] Connection error:', error);
        console.error('[WebSocket] Error type:', error.type);
        console.error('[WebSocket] Error message:', error.message);
        addLog('❌ Connection error: ' + error.message, 'error');
    });
    
    socket.on('connected', function(data) {
        console.log('[WebSocket] Server confirmed:', data.message);
        addLog('✅ ' + data.message, 'success');
    });
    
    socket.on('progress', function(data) {
        console.log('[PROGRESS]', data.step, data.progress + '%', data.message);
        updateProgress(data.step, data.progress, data.message);
        addLog(data.message, 'info');
    });
    
    socket.on('complete', function(data) {
        console.log('[COMPLETE] Processing finished:', data);
        displayResults(data);
        addLog('✅ Processing complete!', 'success');
    });
    
    socket.on('error', function(data) {
        console.error('[ERROR]', data.message);
        showError(data.message);
        addLog('❌ Error: ' + data.message, 'error');
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
        
        // Update UI
        uploadArea.querySelector('.upload-text').textContent = '✅ File selected';
        fileInfo.style.display = 'block';
        fileName.textContent = newFile.name;
        fileSize.textContent = formatBytes(newFile.size);
        uploadBtn.disabled = false;
        
        addLog('📁 File selected: ' + newFile.name, 'info');
    }
}

// Format bytes to human readable
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Upload file and start processing
async function uploadFile() {
    if (!selectedFile) {
        alert('❌ Please select a file first!');
        return;
    }
    
    console.log('[UPLOAD] Starting upload:', selectedFile.name);
    addLog('⬆️ Uploading file...', 'info');
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    // Generate session ID
    currentSessionId = `session_${Date.now()}`;
    formData.append('session_id', currentSessionId);
    
    // Disable button
    uploadBtn.disabled = true;
    uploadBtn.textContent = '⏳ Uploading...';
    stopBtn.disabled = false;
    
    // Show progress
    progressSection.style.display = 'block';
    resultsSection.style.display = 'none';
    
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
            addLog('✅ Upload successful, processing started', 'success');
            
            // Update status
            document.getElementById('statusText').textContent = 'Processing...';
        } else {
            throw new Error(data.error || 'Upload failed');
        }
    } catch (error) {
        console.error('[UPLOAD] Error:', error);
        showError(error.message);
        uploadBtn.disabled = false;
        uploadBtn.textContent = '🚀 Start Processing';
        stopBtn.disabled = true;
        progressSection.style.display = 'none';
    }
}

// Update progress UI
function updateProgress(step, progress, message) {
    currentStep.textContent = message;
    progressPercent.textContent = Math.round(progress) + '%';
    progressBar.style.width = progress + '%';
    
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
    
    progressSection.style.display = 'none';
    resultsSection.style.display = 'block';
    
    // Update metrics
    document.getElementById('metricDuration').textContent = data.duration?.toFixed(1) + 's' || '-';
    document.getElementById('metricSpeakers').textContent = data.num_speakers || '-';
    document.getElementById('metricSegments').textContent = data.num_segments || '-';
    document.getElementById('metricProcessTime').textContent = data.processingTime?.toFixed(1) + 's' || '-';
    
    // Update transcripts
    document.getElementById('timelineTranscript').textContent = data.timeline || '';
    document.getElementById('enhancedTranscript').textContent = data.enhanced || data.timeline || '';
    
    // Update chart
    if (data.timings) {
        updateChart(data.timings);
    }
    
    // Setup download buttons
    setupDownloadButtons(data);
    
    // Reset buttons
    uploadBtn.disabled = false;
    uploadBtn.textContent = '🚀 Start Processing';
    stopBtn.disabled = true;
    document.getElementById('statusText').textContent = 'Ready';
    
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
        downloadTimeline.onclick = function(e) {
            if (!data.session_id) {
                e.preventDefault();
                alert('No session available for download');
            }
        };
    }
    if (downloadEnhanced) {
        downloadEnhanced.href = `/download/${data.session_id}/enhanced`;
        downloadEnhanced.onclick = function(e) {
            if (!data.session_id) {
                e.preventDefault();
                alert('No session available for download');
            }
        };
    }
    if (downloadSegments) {
        if (data.files && data.files.segments) {
            downloadSegments.href = `/download/${data.session_id}/segments`;
            downloadSegments.style.display = 'inline-flex';
        } else {
            downloadSegments.style.display = 'none';
        }
        downloadSegments.onclick = function(e) {
            if (!data.session_id || !data.files || !data.files.segments) {
                e.preventDefault();
                alert('No segments file available for download');
            }
        };
    }
    
    console.log('[DOWNLOAD] Buttons configured for session:', data.session_id);
}

// Show error message
function showError(message) {
    addLog('❌ Error: ' + message, 'error');
    progressSection.style.display = 'none';
    uploadBtn.disabled = false;
    uploadBtn.textContent = '🚀 Start Processing';
    stopBtn.disabled = true;
    document.getElementById('statusText').textContent = 'Error';
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
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    chartsSection.style.display = 'none';
    
    selectedFile = null;
    lastUploadedFile = null;
    fileInput.value = '';
    uploadArea.querySelector('.upload-text').textContent = 'Click to upload or drag & drop audio file';
    fileInfo.style.display = 'none';
    uploadBtn.disabled = true;
    uploadBtn.textContent = '🚀 Start Processing';
    document.getElementById('statusText').textContent = 'Ready';
    
    addLog('🔄 UI reset', 'info');
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

// Model selection dialog
function showModelSelection(data) {
    console.log('[MODEL] Model selection requested:', data);
    addLog('🤖 Please select AI model for enhancement', 'info');
    
    // Get selected model from dropdown
    const modelSelect = document.getElementById('modelSelect');
    const selectedModel = modelSelect ? modelSelect.value : 'gemini';
    
    console.log('[MODEL] Auto-selecting:', selectedModel);
    
    // Send selection to server
    socket.emit('model_selected', {
        session_id: data.session_id,
        model: selectedModel
    });
    
    addLog(`✅ Selected model: ${selectedModel.toUpperCase()}`, 'success');
}

// LLM progress update (placeholder)
function updateLLMProgress(data) {
    console.log('[LLM]', data.message);
    addLog(data.message, data.error ? 'error' : 'info');
}

// Initialize charts
function initializeCharts() {
    const ctx = document.getElementById('timingChart');
    if (!ctx) return;
    
    timingChart = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['Preprocessing', 'Diarization', 'Whisper', 'PhoWhisper', 'AI Enhancement'],
            datasets: [{
                label: 'Processing Time (seconds)',
                data: [0, 0, 0, 0, 0],
                backgroundColor: [
                    'rgba(74, 158, 255, 0.8)',
                    'rgba(167, 139, 250, 0.8)',
                    'rgba(74, 222, 128, 0.8)',
                    'rgba(251, 146, 60, 0.8)',
                    'rgba(248, 113, 113, 0.8)'
                ],
                borderColor: [
                    'rgb(74, 158, 255)',
                    'rgb(167, 139, 250)',
                    'rgb(74, 222, 128)',
                    'rgb(251, 146, 60)',
                    'rgb(248, 113, 113)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { 
                    beginAtZero: true,
                    ticks: { color: '#a0a0ab' },
                    grid: { color: '#333346' }
                },
                x: {
                    ticks: { color: '#a0a0ab' },
                    grid: { color: '#333346' }
                }
            },
            plugins: {
                legend: { 
                    display: true,
                    labels: { color: '#e4e4e7' }
                }
            }
        }
    });
    console.log('[CHARTS] Timing chart initialized');
}

// Update chart with timing data
function updateChart(timings) {
    if (!timingChart) return;
    
    const data = [
        timings.preprocessing || 0,
        timings.diarization || 0,
        timings.whisper || 0,
        timings.phowhisper || 0,
        timings.gemini || timings.openai || timings.deepseek || 0
    ];
    
    timingChart.data.datasets[0].data = data;
    timingChart.update();
    
    chartsSection.style.display = 'block';
}

// Add log entry
function addLog(message, type = 'info') {
    if (!logsContainer) return;
    
    const timestamp = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${timestamp}] ${message}`;
    
    logsContainer.appendChild(entry);
    
    // Auto-scroll if enabled
    if (autoScroll && autoScroll.checked) {
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }
    
    // Keep last 100 logs
    while (logsContainer.children.length > 100) {
        logsContainer.removeChild(logsContainer.firstChild);
    }
}

// Clear logs
function clearLogs() {
    if (logsContainer) {
        logsContainer.innerHTML = '';
        addLog('Logs cleared', 'info');
    }
}

// Switch result tabs
function switchResultTab(tabName) {
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => tab.classList.remove('active'));
    contents.forEach(content => content.classList.remove('active'));
    
    const activeTab = event.target;
    const activeContent = document.getElementById(tabName + '-tab');
    
    if (activeTab) activeTab.classList.add('active');
    if (activeContent) activeContent.classList.add('active');
}

// Update connection status
function updateConnectionStatus(connected) {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    
    if (!statusDot || !statusText) return;
    
    if (connected) {
        statusDot.style.backgroundColor = '#4ade80';
        statusText.textContent = 'Connected';
        addLog('✅ Connected to server', 'success');
    } else {
        statusDot.style.backgroundColor = '#f87171';
        statusText.textContent = 'Disconnected';
        addLog('❌ Disconnected from server', 'error');
    }
}

console.log('[LOAD] main.js initialization complete');
