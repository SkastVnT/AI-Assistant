/**
 * RAG Services - Main JavaScript
 * Phase 2: Web UI
 */

const API_BASE = '';

// Current mode: 'search' or 'rag'
let currentMode = 'search';
let ragAvailable = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 RAG Services UI Initialized');
    
    // Setup event listeners
    setupUploadArea();
    setupFileInput();
    
    // Load initial data
    loadSystemInfo();
    refreshDocuments();
    checkRAGStatus();
    
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
 * Check if RAG is available
 */
async function checkRAGStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/rag/status`);
        const data = await response.json();
        
        ragAvailable = data.available;
        
        if (!ragAvailable) {
            // Disable RAG mode button
            document.getElementById('ragModeBtn').disabled = true;
            document.getElementById('ragModeBtn').classList.add('opacity-50', 'cursor-not-allowed');
            document.getElementById('ragModeBtn').title = 'Configure GEMINI_API_KEY to enable';
        }
    } catch (error) {
        console.error('Failed to check RAG status:', error);
        ragAvailable = false;
    }
}

/**
 * Switch between search and RAG mode
 */
function switchMode(mode) {
    currentMode = mode;
    
    const searchBtn = document.getElementById('searchModeBtn');
    const ragBtn = document.getElementById('ragModeBtn');
    const ragBadge = document.getElementById('ragStatusBadge');
    
    if (mode === 'search') {
        searchBtn.classList.remove('bg-gray-200', 'text-gray-700');
        searchBtn.classList.add('bg-blue-500', 'text-white');
        ragBtn.classList.remove('bg-purple-500', 'text-white');
        ragBtn.classList.add('bg-gray-200', 'text-gray-700');
        ragBadge.classList.add('hidden');
    } else {
        ragBtn.classList.remove('bg-gray-200', 'text-gray-700');
        ragBtn.classList.add('bg-purple-500', 'text-white');
        searchBtn.classList.remove('bg-blue-500', 'text-white');
        searchBtn.classList.add('bg-gray-200', 'text-gray-700');
        ragBadge.classList.remove('hidden');
    }
}

/**
 * Handle query based on current mode
 */
function handleQuery() {
    if (currentMode === 'rag') {
        performRAG();
    } else {
        performSearch();
    }
}

/**
 * Perform RAG query
 */
async function performRAG() {
    const query = document.getElementById('searchInput').value.trim();
    
    if (!query) {
        showToast('warning', '⚠️ Please enter a question');
        return;
    }
    
    if (!ragAvailable) {
        showToast('error', '❌ RAG not available. Configure GEMINI_API_KEY.');
        return;
    }
    
    const topK = parseInt(document.getElementById('topKSelect').value);
    
    // Show searching status
    document.getElementById('searchStatus').classList.remove('hidden');
    document.getElementById('welcomeMessage').classList.add('hidden');
    document.getElementById('resultsContainer').classList.add('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/api/rag/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                query, 
                top_k: topK,
                language: 'auto'
            })
        });
        
        const data = await response.json();
        
        // Hide searching status
        document.getElementById('searchStatus').classList.add('hidden');
        
        if (data.answer) {
            displayRAGResult(data, query);
        } else {
            showNoResults();
        }
        
    } catch (error) {
        console.error('RAG query error:', error);
        document.getElementById('searchStatus').classList.add('hidden');
        showToast('error', '❌ RAG query failed: ' + error.message);
    }
}

/**
 * Display RAG result
 */
function displayRAGResult(data, query) {
    const resultsContainer = document.getElementById('resultsContainer');
    const resultsTitle = document.getElementById('resultsTitle');
    const resultsIcon = document.getElementById('resultsIcon');
    const resultCount = document.getElementById('resultCount');
    const ragAnswer = document.getElementById('ragAnswer');
    const ragAnswerText = document.getElementById('ragAnswerText');
    const ragSources = document.getElementById('ragSources');
    const resultsDiv = document.getElementById('results');
    
    // Update header
    resultsContainer.classList.remove('hidden');
    resultsTitle.textContent = 'AI Answer';
    resultsIcon.className = 'fas fa-robot text-purple-500 mr-2';
    resultCount.textContent = `Based on ${data.retrieved_chunks} relevant chunk(s)`;
    
    // Show RAG answer
    ragAnswer.classList.remove('hidden');
    
    // Format answer (support markdown)
    ragAnswerText.innerHTML = formatMarkdown(data.answer);
    
    // Display sources
    if (data.sources && data.sources.length > 0) {
        ragSources.innerHTML = `
            <div class="text-sm font-semibold text-gray-700 mb-2">📚 Sources:</div>
            <div class="space-y-1">
                ${data.sources.map(source => {
                    const relevance = Math.round(source.relevance * 100);
                    return `
                        <div class="flex items-center justify-between text-sm">
                            <span class="text-gray-600">
                                <i class="fas fa-file-alt text-purple-400 mr-2"></i>
                                ${source.name}
                            </span>
                            <span class="text-purple-600 font-semibold">${relevance}%</span>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }
    
    // Show search results below (collapsible)
    if (data.search_results && data.search_results.length > 0) {
        resultsDiv.innerHTML = `
            <div class="mt-4 pt-4 border-t border-gray-200">
                <button onclick="toggleSearchResults()" class="text-sm text-blue-500 hover:text-blue-600 mb-3">
                    <i class="fas fa-chevron-down mr-1"></i>
                    Show source chunks (${data.search_results.length})
                </button>
                <div id="searchResultsDetails" class="hidden space-y-4">
                    ${data.search_results.map((result, index) => createSearchResultCard(result, index, query)).join('')}
                </div>
            </div>
        `;
    }
    
    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Toggle search results details
 */
function toggleSearchResults() {
    const details = document.getElementById('searchResultsDetails');
    details.classList.toggle('hidden');
}

/**
 * Format markdown text
 */
function formatMarkdown(text) {
    if (!text) return '';
    
    // Simple markdown formatting
    let html = text
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Code
        .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 rounded">$1</code>')
        // Line breaks
        .replace(/\n/g, '<br>')
        // Bullet points
        .replace(/^- (.+)$/gm, '• $1')
        .replace(/^\d+\. (.+)$/gm, '<strong>$&</strong>');
    
    return html;
}

/**
 * Create search result card
 */
function createSearchResultCard(result, index, query) {
    const scorePercent = Math.round(result.score * 100);
    const scoreColor = scorePercent >= 80 ? 'green' : scorePercent >= 60 ? 'yellow' : 'orange';
    
    // Highlight query terms
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
    const resultsTitle = document.getElementById('resultsTitle');
    const resultsIcon = document.getElementById('resultsIcon');
    const resultCount = document.getElementById('resultCount');
    const ragAnswer = document.getElementById('ragAnswer');
    
    // Hide RAG answer (search mode)
    ragAnswer.classList.add('hidden');
    
    // Update header
    resultsContainer.classList.remove('hidden');
    resultsTitle.textContent = 'Search Results';
    resultsIcon.className = 'fas fa-list-ul text-purple-500 mr-2';
    resultCount.textContent = `Found ${results.length} relevant result(s)`;
    
    resultsDiv.innerHTML = results.map((result, index) => 
        createSearchResultCard(result, index, query)
    ).join('');
    
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

// ==================== PHASE 4: ADVANCED FEATURES ====================

// Global state for Phase 4
let currentSessionId = null;
let currentFilters = {
    documents: [],
    fileTypes: [],
    minScore: 0.7
};
let trendsChart = null;

/**
 * Show/hide main tabs
 */
function showTab(tab) {
    const searchSection = document.querySelector('#welcomeMessage').parentElement;
    const analyticsSection = document.getElementById('analyticsSection');
    const searchTabBtn = document.getElementById('searchTabBtn');
    const analyticsTabBtn = document.getElementById('analyticsTabBtn');
    
    if (tab === 'search') {
        searchSection.classList.remove('hidden');
        analyticsSection.classList.add('hidden');
        searchTabBtn.classList.add('bg-white', 'bg-opacity-20');
        searchTabBtn.classList.remove('hover:bg-white', 'hover:bg-opacity-10');
        analyticsTabBtn.classList.remove('bg-white', 'bg-opacity-20');
        analyticsTabBtn.classList.add('hover:bg-white', 'hover:bg-opacity-10');
    } else if (tab === 'analytics') {
        searchSection.classList.add('hidden');
        analyticsSection.classList.remove('hidden');
        analyticsTabBtn.classList.add('bg-white', 'bg-opacity-20');
        analyticsTabBtn.classList.remove('hover:bg-white', 'hover:bg-opacity-10');
        searchTabBtn.classList.remove('bg-white', 'bg-opacity-20');
        searchTabBtn.classList.add('hover:bg-white', 'hover:bg-opacity-10');
        
        // Load analytics data
        loadAnalyticsDashboard();
    }
}

// ==================== CHAT HISTORY FUNCTIONS ====================

/**
 * Start new chat session
 */
async function startNewChat() {
    try {
        const response = await fetch(`${API_BASE}/api/chat/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentSessionId = data.session_id;
            document.getElementById('currentSessionInfo').classList.remove('hidden');
            document.getElementById('sessionNameInput').value = '';
            document.getElementById('sessionMessageCount').textContent = '0 messages';
            showToast('success', '✨ New chat started!');
            await loadChatSessions();
        }
    } catch (error) {
        console.error('Error starting chat:', error);
        showToast('error', 'Failed to start new chat');
    }
}

/**
 * Save current session
 */
async function saveCurrentSession() {
    if (!currentSessionId) {
        showToast('warning', 'No active session');
        return;
    }
    
    const sessionName = document.getElementById('sessionNameInput').value.trim();
    
    try {
        const response = await fetch(`${API_BASE}/api/chat/session/${currentSessionId}/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_name: sessionName })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('success', '💾 Session saved!');
            await loadChatSessions();
        }
    } catch (error) {
        console.error('Error saving session:', error);
        showToast('error', 'Failed to save session');
    }
}

/**
 * Load all chat sessions
 */
async function loadChatSessions() {
    try {
        const response = await fetch(`${API_BASE}/api/chat/sessions`);
        const data = await response.json();
        
        const sessionsList = document.getElementById('sessionsList');
        
        if (data.sessions && data.sessions.length > 0) {
            sessionsList.innerHTML = data.sessions.map(session => `
                <div class="session-item p-3 border border-gray-200 rounded-lg cursor-pointer">
                    <div class="flex items-start justify-between">
                        <div class="flex-1" onclick="loadChatSession('${session.session_id}')">
                            <h4 class="font-semibold text-sm text-gray-800 mb-1">
                                ${session.session_name || 'Untitled Session'}
                            </h4>
                            <p class="text-xs text-gray-500">
                                ${session.message_count} messages • ${new Date(session.updated_at).toLocaleDateString()}
                            </p>
                        </div>
                        <div class="flex space-x-1">
                            <button onclick="exportChatSession('${session.session_id}', 'txt'); event.stopPropagation();" 
                                    class="text-gray-400 hover:text-blue-500 text-xs p-1"
                                    title="Export as TXT">
                                <i class="fas fa-download"></i>
                            </button>
                            <button onclick="deleteChatSession('${session.session_id}'); event.stopPropagation();" 
                                    class="text-gray-400 hover:text-red-500 text-xs p-1"
                                    title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            sessionsList.innerHTML = `
                <div class="text-center text-gray-400 py-4 text-sm">
                    <i class="fas fa-comments text-2xl mb-2"></i>
                    <p>No saved sessions</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

/**
 * Load specific chat session
 */
async function loadChatSession(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/api/chat/session/${sessionId}`);
        const data = await response.json();
        
        currentSessionId = sessionId;
        document.getElementById('currentSessionInfo').classList.remove('hidden');
        document.getElementById('sessionNameInput').value = data.session_name || '';
        document.getElementById('sessionMessageCount').textContent = `${data.message_count} messages`;
        
        showToast('success', `📂 Loaded: ${data.session_name || 'Session'}`);
    } catch (error) {
        console.error('Error loading session:', error);
        showToast('error', 'Failed to load session');
    }
}

/**
 * Delete chat session
 */
async function deleteChatSession(sessionId) {
    if (!confirm('Are you sure you want to delete this session?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/chat/session/${sessionId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (currentSessionId === sessionId) {
                currentSessionId = null;
                document.getElementById('currentSessionInfo').classList.add('hidden');
            }
            showToast('success', '🗑️ Session deleted');
            await loadChatSessions();
        }
    } catch (error) {
        console.error('Error deleting session:', error);
        showToast('error', 'Failed to delete session');
    }
}

/**
 * Export chat session
 */
async function exportChatSession(sessionId, format = 'txt') {
    try {
        const url = `${API_BASE}/api/chat/session/${sessionId}/export?format=${format}`;
        window.open(url, '_blank');
        showToast('success', '📥 Downloading session...');
    } catch (error) {
        console.error('Error exporting session:', error);
        showToast('error', 'Failed to export session');
    }
}

// ==================== FILTER FUNCTIONS ====================

/**
 * Load available filters
 */
async function loadAvailableFilters() {
    try {
        const response = await fetch(`${API_BASE}/api/filters/available`);
        const data = await response.json();
        
        // Populate documents filter
        const documentsFilter = document.getElementById('documentsFilter');
        documentsFilter.innerHTML = '<option value="">All documents</option>' +
            data.documents.map(doc => `<option value="${doc}">${doc}</option>`).join('');
        
        // Populate file type filters
        const fileTypeFilters = document.getElementById('fileTypeFilters');
        if (data.file_types && data.file_types.length > 0) {
            fileTypeFilters.innerHTML = data.file_types.map(type => `
                <label class="flex items-center text-sm cursor-pointer hover:bg-gray-50 p-1 rounded">
                    <input type="checkbox" value="${type}" class="mr-2 file-type-checkbox">
                    <i class="fas ${getFileIcon(type.substring(1))} mr-1 text-gray-500"></i>
                    <span>${type.toUpperCase()}</span>
                </label>
            `).join('');
        } else {
            fileTypeFilters.innerHTML = '<p class="text-xs text-gray-400">No file types available</p>';
        }
    } catch (error) {
        console.error('Error loading filters:', error);
    }
}

/**
 * Apply filters to search
 */
function applyFilters() {
    // Get selected documents
    const documentsFilter = document.getElementById('documentsFilter');
    const selectedDocs = Array.from(documentsFilter.selectedOptions)
        .map(opt => opt.value)
        .filter(val => val);
    
    // Get selected file types
    const fileTypeCheckboxes = document.querySelectorAll('.file-type-checkbox:checked');
    const selectedTypes = Array.from(fileTypeCheckboxes).map(cb => cb.value);
    
    // Get min score
    const minScore = document.getElementById('minScoreSlider').value / 100;
    
    currentFilters = {
        documents: selectedDocs,
        fileTypes: selectedTypes,
        minScore: minScore
    };
    
    // Update active filters display
    updateActiveFilters();
    
    // Re-run current search if any
    const searchInput = document.getElementById('searchInput');
    if (searchInput.value.trim()) {
        handleQuery();
    }
    
    showToast('success', '✅ Filters applied');
}

/**
 * Update active filters display
 */
function updateActiveFilters() {
    const activeFiltersDiv = document.getElementById('activeFilters');
    const filters = [];
    
    if (currentFilters.documents.length > 0) {
        currentFilters.documents.forEach(doc => {
            filters.push(`
                <span class="filter-badge inline-flex items-center px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs">
                    <i class="fas fa-file mr-1"></i> ${doc}
                    <button onclick="removeDocumentFilter('${doc}')" class="ml-1 hover:text-blue-900">
                        <i class="fas fa-times text-xs"></i>
                    </button>
                </span>
            `);
        });
    }
    
    if (currentFilters.fileTypes.length > 0) {
        currentFilters.fileTypes.forEach(type => {
            filters.push(`
                <span class="filter-badge inline-flex items-center px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs">
                    <i class="fas fa-file mr-1"></i> ${type}
                    <button onclick="removeFileTypeFilter('${type}')" class="ml-1 hover:text-green-900">
                        <i class="fas fa-times text-xs"></i>
                    </button>
                </span>
            `);
        });
    }
    
    if (currentFilters.minScore > 0.7) {
        filters.push(`
            <span class="filter-badge inline-flex items-center px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs">
                <i class="fas fa-sliders-h mr-1"></i> Score ≥ ${currentFilters.minScore.toFixed(2)}
            </span>
        `);
    }
    
    if (filters.length > 0) {
        activeFiltersDiv.innerHTML = filters.join('');
        activeFiltersDiv.classList.remove('hidden');
    } else {
        activeFiltersDiv.classList.add('hidden');
    }
}

/**
 * Remove specific document filter
 */
function removeDocumentFilter(doc) {
    currentFilters.documents = currentFilters.documents.filter(d => d !== doc);
    const documentsFilter = document.getElementById('documentsFilter');
    Array.from(documentsFilter.options).forEach(opt => {
        if (opt.value === doc) opt.selected = false;
    });
    updateActiveFilters();
    applyFilters();
}

/**
 * Remove specific file type filter
 */
function removeFileTypeFilter(type) {
    currentFilters.fileTypes = currentFilters.fileTypes.filter(t => t !== type);
    const checkbox = document.querySelector(`.file-type-checkbox[value="${type}"]`);
    if (checkbox) checkbox.checked = false;
    updateActiveFilters();
    applyFilters();
}

/**
 * Clear all filters
 */
function clearFilters() {
    currentFilters = {
        documents: [],
        fileTypes: [],
        minScore: 0.7
    };
    
    document.getElementById('documentsFilter').selectedIndex = 0;
    document.querySelectorAll('.file-type-checkbox').forEach(cb => cb.checked = false);
    document.getElementById('minScoreSlider').value = 70;
    document.getElementById('minScoreValue').textContent = '0.70';
    
    updateActiveFilters();
    showToast('info', '🧹 Filters cleared');
}

// ==================== ANALYTICS FUNCTIONS ====================

/**
 * Load complete analytics dashboard
 */
async function loadAnalyticsDashboard() {
    try {
        const response = await fetch(`${API_BASE}/api/analytics/dashboard`);
        const data = await response.json();
        
        // Update performance metrics
        document.getElementById('metricTotalQueries').textContent = data.performance.total_queries || 0;
        document.getElementById('metricSuccessRate').textContent = 
            ((data.success_rate.rate * 100) || 0).toFixed(1) + '%';
        document.getElementById('metricSuccessful').textContent = data.success_rate.successful || 0;
        document.getElementById('metricFailed').textContent = data.success_rate.failed || 0;
        document.getElementById('metricAvgResponse').textContent = 
            (data.performance.avg_response_time || 0).toFixed(2) + 's';
        document.getElementById('metricRAGQueries').textContent = data.query_by_mode.rag || 0;
        document.getElementById('metricSearchQueries').textContent = data.query_by_mode.search || 0;
        
        // Load popular queries
        loadPopularQueries(data.popular_queries || []);
        
        // Load popular documents
        loadPopularDocuments(data.popular_documents || []);
        
        // Load recent activity
        loadRecentActivity(data.recent_queries || []);
        
        // Load trends chart
        loadTrendsChart(data.trends || {});
        
    } catch (error) {
        console.error('Error loading analytics:', error);
        showToast('error', 'Failed to load analytics');
    }
}

/**
 * Load popular queries list
 */
function loadPopularQueries(queries) {
    const container = document.getElementById('popularQueries');
    
    if (queries.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-400 py-4 text-sm">
                <i class="fas fa-inbox text-2xl mb-2"></i>
                <p>No queries yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = queries.map((item, index) => `
        <div class="flex items-center justify-between p-2 hover:bg-gray-50 rounded">
            <div class="flex items-center flex-1">
                <span class="text-lg font-bold text-gray-400 mr-3">${index + 1}</span>
                <span class="text-sm text-gray-700">${item.query}</span>
            </div>
            <span class="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded-full">
                ${item.count}×
            </span>
        </div>
    `).join('');
}

/**
 * Load popular documents list
 */
function loadPopularDocuments(documents) {
    const container = document.getElementById('popularDocuments');
    
    if (documents.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-400 py-4 text-sm">
                <i class="fas fa-inbox text-2xl mb-2"></i>
                <p>No documents used yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = documents.map((doc, index) => `
        <div class="flex items-center justify-between p-2 hover:bg-gray-50 rounded">
            <div class="flex items-center flex-1">
                <span class="text-lg font-bold text-gray-400 mr-3">${index + 1}</span>
                <span class="text-sm text-gray-700">${doc.name}</span>
            </div>
            <span class="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full">
                ${doc.queries} queries
            </span>
        </div>
    `).join('');
}

/**
 * Load recent activity
 */
function loadRecentActivity(queries) {
    const container = document.getElementById('recentActivity');
    
    if (queries.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-400 py-4 text-sm">
                <i class="fas fa-inbox text-2xl mb-2"></i>
                <p>No recent activity</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = queries.map(q => {
        const success = q.success !== false;
        const mode = q.mode === 'rag' ? 'RAG' : 'Search';
        const icon = q.mode === 'rag' ? 'fa-robot' : 'fa-search';
        const color = success ? 'green' : 'red';
        
        return `
            <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                <div class="flex-shrink-0 w-8 h-8 bg-${color}-100 rounded-lg flex items-center justify-center">
                    <i class="fas ${icon} text-${color}-600 text-sm"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm text-gray-800 truncate">${q.query}</p>
                    <div class="flex items-center space-x-2 mt-1 text-xs text-gray-500">
                        <span>${mode}</span>
                        <span>•</span>
                        <span>${q.results_count} results</span>
                        <span>•</span>
                        <span>${q.response_time?.toFixed(2) || 0}s</span>
                    </div>
                </div>
                <div class="flex-shrink-0">
                    <i class="fas fa-${success ? 'check-circle text-green-500' : 'times-circle text-red-500'}"></i>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Load trends chart
 */
async function loadTrends(period = 'day') {
    try {
        const response = await fetch(`${API_BASE}/api/analytics/trends?period=${period}`);
        const data = await response.json();
        
        loadTrendsChart(data.trends || {});
    } catch (error) {
        console.error('Error loading trends:', error);
    }
}

/**
 * Render trends chart
 */
function loadTrendsChart(trends) {
    const ctx = document.getElementById('trendsChart');
    
    if (!ctx) return;
    
    // Destroy existing chart
    if (trendsChart) {
        trendsChart.destroy();
    }
    
    const labels = Object.keys(trends);
    const searchData = labels.map(key => trends[key].search || 0);
    const ragData = labels.map(key => trends[key].rag || 0);
    
    trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Search',
                    data: searchData,
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'RAG',
                    data: ragData,
                    borderColor: 'rgb(168, 85, 247)',
                    backgroundColor: 'rgba(168, 85, 247, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

/**
 * Refresh analytics
 */
function refreshAnalytics() {
    loadAnalyticsDashboard();
    showToast('success', '🔄 Analytics refreshed');
}

// ==================== UPDATE EXISTING FUNCTIONS ====================

// Override performSearch to include filters
const originalPerformSearch = window.performSearch;
window.performSearch = async function() {
    const query = document.getElementById('searchInput').value.trim();
    
    if (!query) {
        showToast('warning', 'Please enter a search query');
        return;
    }
    
    const topK = parseInt(document.getElementById('topKSelect').value);
    
    // Show loading
    document.getElementById('searchStatus').classList.remove('hidden');
    document.getElementById('resultsContainer').classList.add('hidden');
    document.getElementById('welcomeMessage').classList.add('hidden');
    
    try {
        const requestBody = {
            query: query,
            top_k: topK
        };
        
        // Add filters if any
        if (currentFilters.documents.length > 0 || 
            currentFilters.fileTypes.length > 0 || 
            currentFilters.minScore > 0.7) {
            requestBody.filters = currentFilters;
        }
        
        const response = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Hide search status
        document.getElementById('searchStatus').classList.add('hidden');
        
        // Display results
        displayResults(data.results, query, data.stats);
        
    } catch (error) {
        console.error('Search error:', error);
        document.getElementById('searchStatus').classList.add('hidden');
        showToast('error', `Search failed: ${error.message}`);
    }
};

// Override performRAG to include session
const originalPerformRAG = window.performRAG;
window.performRAG = async function() {
    const query = document.getElementById('searchInput').value.trim();
    
    if (!query) {
        showToast('warning', 'Please enter a question');
        return;
    }
    
    const topK = parseInt(document.getElementById('topKSelect').value);
    const useHistory = document.getElementById('useHistoryToggle')?.checked || false;
    
    // Show loading
    document.getElementById('searchStatus').classList.remove('hidden');
    document.getElementById('resultsContainer').classList.add('hidden');
    document.getElementById('welcomeMessage').classList.add('hidden');
    
    try {
        const requestBody = {
            query: query,
            top_k: topK,
            language: 'auto',
            use_history: useHistory && currentSessionId !== null,
            session_id: currentSessionId
        };
        
        const response = await fetch(`${API_BASE}/api/rag/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Hide search status
        document.getElementById('searchStatus').classList.add('hidden');
        
        // Update session message count if active
        if (currentSessionId) {
            const countElem = document.getElementById('sessionMessageCount');
            const currentCount = parseInt(countElem.textContent) || 0;
            countElem.textContent = `${currentCount + 2} messages`;
        }
        
        // Display RAG answer
        displayRAGResult(data, query);
        
    } catch (error) {
        console.error('RAG error:', error);
        document.getElementById('searchStatus').classList.add('hidden');
        showToast('error', `RAG query failed: ${error.message}`);
    }
};

// Update displayResults to show filter stats
const originalDisplayResults = window.displayResults;
window.displayResults = function(results, query, stats) {
    originalDisplayResults(results, query);
    
    // Add filter stats if available
    if (stats && stats.total_results) {
        const resultCount = document.getElementById('resultCount');
        resultCount.innerHTML = `
            ${stats.total_results} results 
            ${stats.unique_documents ? `from ${stats.unique_documents} documents` : ''}
            ${stats.avg_score ? `(avg: ${(stats.avg_score * 100).toFixed(0)}%)` : ''}
        `;
    }
};

// Initialize Phase 4 on load
document.addEventListener('DOMContentLoaded', function() {
    // Load chat sessions
    loadChatSessions();
    
    // Load available filters
    loadAvailableFilters();
    
    // Auto-refresh sessions every 60 seconds
    setInterval(loadChatSessions, 60000);
});
