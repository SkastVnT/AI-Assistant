// LoRA Training WebUI - Main JavaScript
// Socket.IO connection and real-time updates

// Initialize Socket.IO
const socket = io();

// Charts
let lossChart, lrChart;
const lossData = [];
const lrData = [];
const maxDataPoints = 100;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    loadDatasets();
    loadModels();
    setupSocketListeners();
    
    // Load initial status
    fetchStatus();
});

// Socket.IO Event Listeners
function setupSocketListeners() {
    socket.on('connect', function() {
        console.log('Connected to server');
        updateConnectionStatus(true);
    });

    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateConnectionStatus(false);
    });

    socket.on('training_update', function(data) {
        updateTrainingUI(data);
    });

    socket.on('log', function(data) {
        addLog(data.message);
    });

    socket.on('connected', function(data) {
        console.log(data.status);
    });
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    
    if (connected) {
        dot.style.backgroundColor = '#4CAF50';
        if (!isTraining()) {
            text.textContent = 'Connected - Idle';
        }
    } else {
        dot.style.backgroundColor = '#f44336';
        text.textContent = 'Disconnected';
    }
}

// Initialize Charts
function initializeCharts() {
    const lossCtx = document.getElementById('lossChart').getContext('2d');
    const lrCtx = document.getElementById('lrChart').getContext('2d');

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { display: true, title: { display: true, text: 'Step' } },
            y: { display: true, beginAtZero: true }
        },
        plugins: {
            legend: { display: true, position: 'top' }
        }
    };

    lossChart = new Chart(lossCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Loss',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                tension: 0.4
            }]
        },
        options: chartOptions
    });

    lrChart = new Chart(lrCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Learning Rate',
                data: [],
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                tension: 0.4
            }]
        },
        options: chartOptions
    });
}

// Load datasets
async function loadDatasets() {
    try {
        const response = await fetch('/api/datasets');
        const datasets = await response.json();
        
        const select = document.getElementById('datasetSelect');
        select.innerHTML = '<option value="">Select dataset...</option>';
        
        datasets.forEach(dataset => {
            const option = document.createElement('option');
            option.value = dataset.path;
            option.textContent = `${dataset.name} (${dataset.image_count} images)`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading datasets:', error);
    }
}

// Load models
async function loadModels() {
    try {
        const response = await fetch('/api/models');
        const models = await response.json();
        
        const select = document.getElementById('baseModel');
        select.innerHTML = '';
        
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.path;
            option.textContent = model.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading models:', error);
    }
}

// Fetch current status
async function fetchStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();
        updateTrainingUI(status);
    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

// Update Training UI
function updateTrainingUI(data) {
    // Status
    const statusText = document.getElementById('statusText');
    const statusDot = document.getElementById('statusDot');
    statusText.textContent = data.status;
    
    if (data.is_training) {
        statusDot.style.backgroundColor = '#FF9800'; // Orange for training
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;
    } else {
        statusDot.style.backgroundColor = '#4CAF50'; // Green for idle
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
    }

    // Progress
    document.getElementById('currentEpoch').textContent = data.current_epoch;
    document.getElementById('totalEpochs').textContent = data.total_epochs;
    document.getElementById('currentStep').textContent = data.current_step;
    document.getElementById('totalSteps').textContent = data.total_steps;
    
    const progress = data.progress || 0;
    document.getElementById('progressBar').style.width = progress + '%';
    document.getElementById('progressPercent').textContent = progress.toFixed(1) + '%';

    // Metrics
    document.getElementById('lossValue').textContent = data.loss.toFixed(4);
    document.getElementById('lrValue').textContent = data.lr.toExponential(2);
    document.getElementById('etaValue').textContent = data.eta;

    // Update charts
    if (data.is_training && data.current_step > 0) {
        updateCharts(data.current_step, data.loss, data.lr);
    }
}

// Update Charts
function updateCharts(step, loss, lr) {
    // Add data
    lossData.push({ x: step, y: loss });
    lrData.push({ x: step, y: lr });

    // Limit data points
    if (lossData.length > maxDataPoints) {
        lossData.shift();
        lrData.shift();
    }

    // Update loss chart
    lossChart.data.labels = lossData.map(d => d.x);
    lossChart.data.datasets[0].data = lossData.map(d => d.y);
    lossChart.update('none'); // No animation for performance

    // Update LR chart
    lrChart.data.labels = lrData.map(d => d.x);
    lrChart.data.datasets[0].data = lrData.map(d => d.y);
    lrChart.update('none');
}

// Add log entry
function addLog(message) {
    const container = document.getElementById('logsContainer');
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.textContent = message;
    container.appendChild(logEntry);

    // Auto-scroll if enabled
    if (document.getElementById('autoScroll').checked) {
        container.scrollTop = container.scrollHeight;
    }

    // Limit log entries
    while (container.children.length > 1000) {
        container.removeChild(container.firstChild);
    }
}

// Clear logs
function clearLogs() {
    document.getElementById('logsContainer').innerHTML = '';
}

// Download logs
function downloadLogs() {
    const logs = Array.from(document.getElementById('logsContainer').children)
        .map(el => el.textContent)
        .join('\n');
    
    const blob = new Blob([logs], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `training_logs_${new Date().toISOString().slice(0,10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

// Start Training
async function startTraining() {
    const config = buildConfig();
    
    try {
        const response = await fetch('/api/start_training', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await response.json();
        
        if (response.ok) {
            addLog('✓ Training started');
            // Clear previous data
            lossData.length = 0;
            lrData.length = 0;
        } else {
            addLog(`✗ Error: ${result.error}`);
            alert(`Error: ${result.error}`);
        }
    } catch (error) {
        console.error('Error starting training:', error);
        addLog(`✗ Error: ${error.message}`);
        alert('Failed to start training');
    }
}

// Stop Training
async function stopTraining() {
    try {
        const response = await fetch('/api/stop_training', {
            method: 'POST'
        });

        const result = await response.json();
        addLog('⏹ Stop requested');
    } catch (error) {
        console.error('Error stopping training:', error);
    }
}

// Build config from form
function buildConfig() {
    return {
        model: {
            pretrained_model_name_or_path: document.getElementById('baseModel').value
        },
        lora: {
            rank: parseInt(document.getElementById('loraRank').value),
            alpha: parseInt(document.getElementById('loraAlpha').value)
        },
        training: {
            train_data_dir: document.getElementById('datasetSelect').value,
            num_train_epochs: parseInt(document.getElementById('epochs').value),
            train_batch_size: parseInt(document.getElementById('batchSize').value),
            learning_rate: parseFloat(document.getElementById('learningRate').value),
            optimizer: document.getElementById('optimizer').value,
            use_loraplus: document.getElementById('useLoraPlus').checked,
            use_min_snr: document.getElementById('useMinSNR').checked,
            use_ema: document.getElementById('useEMA').checked,
            loss_type: document.getElementById('lossType').value,
            noise_offset: parseFloat(document.getElementById('noiseOffset').value)
        }
    };
}

// Tab switching
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // Set button active
    event.target.classList.add('active');
}

// Tag dataset with WD14
async function tagDataset() {
    const datasetPath = document.getElementById('datasetSelect').value;
    
    if (!datasetPath) {
        alert('Please select a dataset first');
        return;
    }

    const threshold = prompt('Enter confidence threshold (0.0-1.0):', '0.35');
    if (!threshold) return;

    try {
        const response = await fetch('/api/tag_dataset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                dataset_path: datasetPath,
                threshold: parseFloat(threshold)
            })
        });

        const result = await response.json();
        addLog('🏷️ WD14 tagging started...');
    } catch (error) {
        console.error('Error tagging dataset:', error);
        alert('Failed to start tagging');
    }
}

// Analyze dataset
async function analyzeDataset() {
    const datasetPath = document.getElementById('datasetSelect').value;
    
    if (!datasetPath) {
        alert('Please select a dataset first');
        return;
    }

    try {
        addLog('📊 Analyzing dataset...');
        
        const response = await fetch('/api/analyze_dataset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_path: datasetPath })
        });

        const stats = await response.json();
        
        // Show analysis results
        const info = document.getElementById('datasetInfo');
        info.innerHTML = `
            <strong>Dataset Analysis:</strong><br>
            Images: ${stats.total_images}<br>
            Avg Resolution: ${stats.avg_resolution}<br>
            Has Captions: ${stats.captioned_images}/${stats.total_images}<br>
            Quality Score: ${stats.quality_score}/10
        `;
        
        addLog(`✓ Analysis complete: ${stats.total_images} images, quality ${stats.quality_score}/10`);
    } catch (error) {
        console.error('Error analyzing dataset:', error);
        alert('Failed to analyze dataset');
    }
}

// Get AI-powered config recommendations from Gemini
async function getAIRecommendations() {
    const datasetPath = document.getElementById('datasetSelect').value;
    const trainingGoal = document.getElementById('trainingGoal').value;
    
    if (!datasetPath) {
        alert('Please select a dataset first');
        return;
    }

    try {
        addLog('🤖 Getting AI recommendations from Gemini...');
        addLog('⚠️ Privacy-safe: Only metadata sent, not your NSFW images!');
        
        const response = await fetch('/api/recommend_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                dataset_path: datasetPath,
                training_goal: trainingGoal
            })
        });

        const result = await response.json();
        
        if (result.error) {
            addLog(`❌ Error: ${result.error}`);
            alert(`Failed to get recommendations: ${result.error}`);
            return;
        }
        
        const config = result.config;
        
        // Apply recommendations to UI
        document.getElementById('learningRate').value = config.learning_rate;
        document.getElementById('batchSize').value = config.batch_size;
        document.getElementById('epochs').value = config.epochs;
        document.getElementById('networkDim').value = config.network_dim;
        document.getElementById('networkAlpha').value = config.network_alpha;
        document.getElementById('optimizer').value = config.optimizer;
        document.getElementById('lrScheduler').value = config.lr_scheduler;
        
        if (config.min_snr_gamma !== undefined) {
            document.getElementById('minSnrGamma').value = config.min_snr_gamma;
        }
        
        if (config.use_lora_plus !== undefined) {
            document.getElementById('useLoraPlus').checked = config.use_lora_plus;
            if (config.lora_plus_lr_ratio) {
                document.getElementById('loraPlusLrRatio').value = config.lora_plus_lr_ratio;
            }
        }
        
        // Show reasoning in logs
        addLog('✅ AI recommendations applied!');
        addLog('');
        addLog('📝 Reasoning:');
        addLog(config.reasoning);
        addLog('');
        
        if (config.warnings && config.warnings.length > 0) {
            addLog('⚠️ Warnings:');
            config.warnings.forEach(warning => addLog(`  - ${warning}`));
            addLog('');
        }
        
        addLog(`⏱️ Estimated training time: ${config.estimated_time || 'Unknown'}`);
        addLog(`💾 Estimated VRAM: ${config.estimated_vram || 'Unknown'}`);
        
        // Highlight applied settings
        alert(`AI recommendations applied!\n\nLR: ${config.learning_rate}\nBatch: ${config.batch_size}\nEpochs: ${config.epochs}\nDim: ${config.network_dim}\n\nCheck logs for detailed reasoning.`);
        
    } catch (error) {
        console.error('Error getting AI recommendations:', error);
        addLog(`❌ Error: ${error.message}`);
        alert('Failed to get AI recommendations. Check logs for details.');
    }
}

// Load config
async function loadConfig() {
    try {
        const response = await fetch('/api/configs');
        const configs = await response.json();
        
        // Show selection dialog
        const configName = prompt('Available configs:\n' + 
            configs.map(c => c.name).join('\n') + 
            '\n\nEnter config name:');
        
        if (!configName) return;

        const configResponse = await fetch(`/api/config/${configName}`);
        const config = await configResponse.json();
        
        // Populate form with config values
        populateFormFromConfig(config);
        addLog(`✓ Loaded config: ${configName}`);
    } catch (error) {
        console.error('Error loading config:', error);
        alert('Failed to load config');
    }
}

// Dataset Tools Functions

async function resizeDataset() {
    const datasetPath = document.getElementById('datasetSelect').value;
    const targetWidth = parseInt(document.getElementById('resizeWidth').value);
    const targetHeight = parseInt(document.getElementById('resizeHeight').value);
    const keepAspect = document.getElementById('keepAspectRatio').checked;
    const quality = parseInt(document.getElementById('resizeQuality').value);
    
    if (!datasetPath) {
        alert('Please select a dataset first');
        return;
    }
    
    if (!confirm(`Resize all images to ${targetWidth}x${targetHeight}?\nOriginals will be backed up to _backup_original folder.`)) {
        return;
    }
    
    try {
        addLog(`🖼️ Starting resize to ${targetWidth}x${targetHeight}...`);
        
        const response = await fetch('/api/resize_dataset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                dataset_path: datasetPath,
                target_width: targetWidth,
                target_height: targetHeight,
                keep_aspect_ratio: keepAspect,
                quality: quality
            })
        });
        
        const result = await response.json();
        if (result.success) {
            addLog('✅ Resize started! Check logs below for progress...');
        } else {
            addLog(`❌ Error: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        addLog(`❌ Error: ${error.message}`);
    }
}

async function convertFormat() {
    const datasetPath = document.getElementById('datasetSelect').value;
    const targetFormat = document.getElementById('targetFormat').value;
    const quality = parseInt(document.getElementById('convertQuality').value);
    const deleteOriginal = document.getElementById('deleteOriginal').checked;
    
    if (!datasetPath) {
        alert('Please select a dataset first');
        return;
    }
    
    const warningMsg = deleteOriginal 
        ? `Convert all images to ${targetFormat.toUpperCase()}?\n⚠️ ORIGINAL FILES WILL BE DELETED!`
        : `Convert all images to ${targetFormat.toUpperCase()}?`;
    
    if (!confirm(warningMsg)) {
        return;
    }
    
    try {
        addLog(`🔄 Converting to ${targetFormat.toUpperCase()}...`);
        
        const response = await fetch('/api/convert_format', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                dataset_path: datasetPath,
                target_format: targetFormat,
                quality: quality,
                delete_original: deleteOriginal
            })
        });
        
        const result = await response.json();
        if (result.success) {
            addLog('✅ Conversion started! Check logs below for progress...');
        } else {
            addLog(`❌ Error: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        addLog(`❌ Error: ${error.message}`);
    }
}

async function deduplicateDataset() {
    const datasetPath = document.getElementById('datasetSelect').value;
    const keepStrategy = document.getElementById('keepStrategy').value;
    
    if (!datasetPath) {
        alert('Please select a dataset first');
        return;
    }
    
    if (!confirm('Remove duplicate images?\n⚠️ This will DELETE files permanently!')) {
        return;
    }
    
    try {
        addLog('🔍 Scanning for duplicates...');
        
        const response = await fetch('/api/deduplicate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                dataset_path: datasetPath,
                keep: keepStrategy
            })
        });
        
        const result = await response.json();
        if (result.success) {
            addLog('✅ Deduplication started! Check logs below for progress...');
        } else {
            addLog(`❌ Error: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        addLog(`❌ Error: ${error.message}`);
    }
}

async function organizeDataset() {
    const datasetPath = document.getElementById('datasetSelect').value;
    
    if (!datasetPath) {
        alert('Please select a dataset first');
        return;
    }
    
    if (!confirm('Organize images into subfolders by resolution?\n(e.g., 512x512/, 768x1024/, etc.)')) {
        return;
    }
    
    try {
        addLog('📁 Organizing dataset...');
        
        const response = await fetch('/api/organize_dataset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_path: datasetPath })
        });
        
        const result = await response.json();
        if (result.success) {
            addLog('✅ Organization started! Check logs below for progress...');
        } else {
            addLog(`❌ Error: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        addLog(`❌ Error: ${error.message}`);
    }
}

async function validateDataset() {
    const datasetPath = document.getElementById('datasetSelect').value;
    
    if (!datasetPath) {
        alert('Please select a dataset first');
        return;
    }
    
    try {
        addLog('✅ Validating dataset...');
        
        const response = await fetch('/api/validate_dataset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_path: datasetPath })
        });
        
        const result = await response.json();
        if (result.success) {
            addLog('✅ Validation started! Check logs below for results...');
        } else {
            addLog(`❌ Error: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        addLog(`❌ Error: ${error.message}`);
    }
}

// Save config
async function saveConfig() {
    const configName = prompt('Enter config name:');
    if (!configName) return;

    const config = buildConfig();

    try {
        const response = await fetch(`/api/config/${configName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        const result = await response.json();
        addLog(`✓ Saved config: ${configName}`);
    } catch (error) {
        console.error('Error saving config:', error);
        alert('Failed to save config');
    }
}

// Populate form from config
function populateFormFromConfig(config) {
    if (config.model) {
        document.getElementById('baseModel').value = config.model.pretrained_model_name_or_path || '';
    }
    
    if (config.lora) {
        document.getElementById('loraRank').value = config.lora.rank || 32;
        document.getElementById('loraAlpha').value = config.lora.alpha || 64;
    }
    
    if (config.training) {
        document.getElementById('learningRate').value = config.training.learning_rate || '1e-4';
        document.getElementById('epochs').value = config.training.num_train_epochs || 10;
        document.getElementById('batchSize').value = config.training.train_batch_size || 2;
        document.getElementById('optimizer').value = config.training.optimizer || 'adamw';
        document.getElementById('useLoraPlus').checked = config.training.use_loraplus || false;
        document.getElementById('useMinSNR').checked = config.training.use_min_snr || false;
        document.getElementById('useEMA').checked = config.training.use_ema || false;
        document.getElementById('lossType').value = config.training.loss_type || 'mse';
        document.getElementById('noiseOffset').value = config.training.noise_offset || 0.1;
    }
}

// Helper function
function isTraining() {
    return !document.getElementById('startBtn').disabled;
}

// Request updates periodically
setInterval(() => {
    socket.emit('request_update');
}, 5000); // Every 5 seconds
