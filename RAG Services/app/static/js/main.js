/**
 * RAG Services - Main JavaScript
 * Phase 2: Web UI
 */

const API_BASE = '';

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 RAG Services UI Initialized');
    
    // Setup event listeners
    setupUploadArea();
    setupFileInput();
    
    // Load initial data
    loadSystemInfo();
    refreshDocuments();
    
    // Auto-refresh documents every 30 seconds
    setInterval(refreshDocuments, 30000);
});

/**
 * Setup drag & drop upload area
 */
function setupUploadArea() {
    const uploadArea = document.getElementById('uploadArea');
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragging');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragging');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragging');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFiles(files);
        }
    });
}

/**
 * Setup file input change handler
 */
function setupFileInput() {
    const fileInput = document.getElementById('fileInput');
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFiles(e.target.files);
        }
    });
}

/**
 * Handle file uploads
 */
async function handleFiles(files) {
    const fileArray = Array.from(files);
    
    // Show loading
    showLoading(`Uploading ${fileArray.length} file(s)...`);
    
    let successCount = 0;
    let errorCount = 0;
    
    for (const file of fileArray) {
        try {
            await uploadFile(file);
            successCount++;
        } catch (error) {
            errorCount++;
            console.error(`Failed to upload ${file.name}:`, error);
        }
    }
    
    hideLoading();
    
    // Show result
    if (successCount > 0) {
        showToast('success', `✅ Uploaded ${successCount} file(s) successfully!`);
        refreshDocuments();
    }
    
    if (errorCount > 0) {
        showToast('error', `❌ Failed to upload ${errorCount} file(s)`);
    }
    
    // Clear file input
    document.getElementById('fileInput').value = '';
}

/**
 * Upload single file
 */
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Upload failed');
    }
    
    return await response.json();
}

/**
 * Perform semantic search
 */
async function performSearch() {
    const query = document.getElementById('searchInput').value.trim();
    
    if (!query) {
        showToast('warning', '⚠️ Please enter a search query');
        return;
    }
    
    const topK = parseInt(document.getElementById('topKSelect').value);
    
    // Show searching status
    document.getElementById('searchStatus').classList.remove('hidden');
    document.getElementById('welcomeMessage').classList.add('hidden');
    document.getElementById('resultsContainer').classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query, top_k: topK })
        });
        
        const data = await response.json();
        
        // Hide searching status
        document.getElementById('searchStatus').classList.add('hidden');
        
        if (data.results && data.results.length > 0) {
            displayResults(data.results, query);
        } else {
            showNoResults();
        }
        
    } catch (error) {
        console.error('Search error:', error);
        document.getElementById('searchStatus').classList.add('hidden');
        showToast('error', '❌ Search failed: ' + error.message);
    }
}

/**
 * Display search results
 */
function displayResults(results, query) {
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsDiv = document.getElementById('results');
    const resultCount = document.getElementById('resultCount');
    
    resultsContainer.classList.remove('hidden');
    resultCount.textContent = `Found ${results.length} relevant result(s)`;
    
    resultsDiv.innerHTML = results.map((result, index) => {
        const scorePercent = Math.round(result.score * 100);
        const scoreColor = scorePercent >= 80 ? 'green' : scorePercent >= 60 ? 'yellow' : 'orange';
        
        // Highlight query terms in text (simple implementation)
        let highlightedText = result.text;
        const queryWords = query.toLowerCase().split(' ');
        queryWords.forEach(word => {
            if (word.length > 3) {
                const regex = new RegExp(`(${word})`, 'gi');
                highlightedText = highlightedText.replace(regex, '<mark class="bg-yellow-200">$1</mark>');
            }
        });
        
        return `
            <div class="search-result bg-white border-2 border-gray-200 rounded-lg p-5 fade-in">
                <div class="flex items-start justify-between mb-3">
                    <div class="flex items-center space-x-3">
                        <div class="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg flex items-center justify-center text-white font-bold">
                            ${index + 1}
                        </div>
                        <div>
                            <div class="flex items-center space-x-2">
                                <i class="fas fa-file-alt text-gray-400"></i>
                                <span class="font-semibold text-gray-800">${result.metadata.source}</span>
                            </div>
                            <div class="text-xs text-gray-500 mt-1">
                                Chunk ${result.metadata.chunk_id + 1} of ${result.metadata.total_chunks}
                            </div>
                        </div>
                    </div>
                    
                    <div class="text-right">
                        <div class="text-2xl font-bold text-${scoreColor}-600">${scorePercent}%</div>
                        <div class="text-xs text-gray-500">relevance</div>
                    </div>
                </div>
                
                <div class="w-full bg-gray-200 rounded-full h-2 mb-3">
                    <div class="score-bar bg-gradient-to-r from-${scoreColor}-400 to-${scoreColor}-600 h-2 rounded-full" 
                         style="width: ${scorePercent}%"></div>
                </div>
                
                <div class="text-gray-700 leading-relaxed">
                    ${highlightedText.substring(0, 500)}${highlightedText.length > 500 ? '...' : ''}
                </div>
                
                <div class="mt-3 flex items-center space-x-4 text-sm text-gray-500">
                    <span><i class="fas fa-tag mr-1"></i> ${result.metadata.file_type}</span>
                    <button onclick="copyText(\`${result.text.replace(/`/g, '\\`')}\`)" 
                            class="hover:text-blue-500 transition">
                        <i class="fas fa-copy mr-1"></i> Copy
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Show no results message
 */
function showNoResults() {
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsDiv = document.getElementById('results');
    const resultCount = document.getElementById('resultCount');
    
    resultsContainer.classList.remove('hidden');
    resultCount.textContent = 'No results found';
    
    resultsDiv.innerHTML = `
        <div class="text-center py-12">
            <i class="fas fa-search text-6xl text-gray-300 mb-4"></i>
            <h3 class="text-xl font-semibold text-gray-600 mb-2">No matching documents found</h3>
            <p class="text-gray-500">Try different keywords or upload more documents</p>
        </div>
    `;
}

/**
 * Load system information
 */
async function loadSystemInfo() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        const data = await response.json();
        
        if (data.status === 'healthy') {
            document.getElementById('embeddingModel').textContent = 
                data.models.embedding.name.split('/').pop().substring(0, 15) + '...';
            
            updateStats(data.stats);
        }
    } catch (error) {
        console.error('Failed to load system info:', error);
        document.getElementById('systemStatus').innerHTML = 
            '<i class="fas fa-circle text-xs"></i> Offline';
    }
}

/**
 * Refresh documents list
 */
async function refreshDocuments() {
    try {
        const response = await fetch(`${API_BASE}/api/documents`);
        const data = await response.json();
        
        const documentsList = document.getElementById('documentsList');
        
        if (data.documents.length === 0) {
            documentsList.innerHTML = `
                <div class="text-center text-gray-400 py-8">
                    <i class="fas fa-inbox text-4xl mb-2"></i>
                    <p>No documents yet</p>
                </div>
            `;
        } else {
            documentsList.innerHTML = data.documents.map(doc => {
                const ext = doc.split('.').pop().toLowerCase();
                const icon = getFileIcon(ext);
                
                return `
                    <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                        <div class="flex items-center space-x-3 flex-1 min-w-0">
                            <i class="fas ${icon} text-blue-500"></i>
                            <span class="text-sm text-gray-700 truncate" title="${doc}">${doc}</span>
                        </div>
                        <button onclick="deleteDocument('${doc}')" 
                                class="text-red-500 hover:text-red-600 transition ml-2">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                `;
            }).join('');
        }
        
        // Update stats
        updateStats({
            total_documents: data.total_documents,
            total_chunks: data.total_chunks
        });
        
    } catch (error) {
        console.error('Failed to refresh documents:', error);
    }
}

/**
 * Delete document
 */
async function deleteDocument(filename) {
    if (!confirm(`Delete "${filename}"?`)) {
        return;
    }
    
    showLoading('Deleting document...');
    
    try {
        const response = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('success', '🗑️ Document deleted successfully');
            refreshDocuments();
        } else {
            throw new Error('Delete failed');
        }
    } catch (error) {
        showToast('error', '❌ Failed to delete document');
    } finally {
        hideLoading();
    }
}

/**
 * Update statistics display
 */
function updateStats(stats) {
    document.getElementById('docCount').textContent = stats.total_documents || 0;
}

/**
 * Set search query (from suggestion buttons)
 */
function setQuery(query) {
    document.getElementById('searchInput').value = query;
    performSearch();
}

/**
 * Copy text to clipboard
 */
function copyText(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('success', '📋 Copied to clipboard!');
    });
}

/**
 * Get icon for file type
 */
function getFileIcon(ext) {
    const icons = {
        'pdf': 'fa-file-pdf',
        'docx': 'fa-file-word',
        'doc': 'fa-file-word',
        'pptx': 'fa-file-powerpoint',
        'xlsx': 'fa-file-excel',
        'txt': 'fa-file-alt',
        'md': 'fa-file-code',
        'html': 'fa-file-code'
    };
    return icons[ext] || 'fa-file';
}

/**
 * Show toast notification
 */
function showToast(type, message) {
    const toast = document.getElementById('toast');
    const icon = document.getElementById('toastIcon');
    const msg = document.getElementById('toastMessage');
    
    const icons = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    
    icon.className = `fas ${icons[type] || icons.info}`;
    msg.textContent = message;
    
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

/**
 * Show loading modal
 */
function showLoading(message = 'Processing...') {
    document.getElementById('loadingMessage').textContent = message;
    document.getElementById('loadingModal').classList.remove('hidden');
    document.getElementById('loadingModal').classList.add('flex');
}

/**
 * Hide loading modal
 */
function hideLoading() {
    document.getElementById('loadingModal').classList.add('hidden');
    document.getElementById('loadingModal').classList.remove('flex');
}
