/**
 * Version Navigator Module
 * Handles message version history navigation with < 2/2 > controls
 * Allows users to view and navigate through message edit history
 */

export default class VersionNavigator {
    constructor(chatManager, messageRenderer) {
        this.chatManager = chatManager;
        this.messageRenderer = messageRenderer;
        this.versionStates = new Map(); // messageId -> { currentIndex, versions[] }
        this.initialized = false;
    }

    /**
     * Initialize version navigator
     */
    async init() {
        console.log('🔄 Initializing Version Navigator...');
        
        // Setup event delegation for version controls
        this.setupEventListeners();
        
        // Load version data from storage
        await this.loadVersionData();
        
        this.initialized = true;
        console.log('✅ Version Navigator initialized');
    }

    /**
     * Setup event listeners for version controls
     */
    setupEventListeners() {
        // Use event delegation on message container
        const messagesContainer = document.getElementById('messagesContainer');
        if (!messagesContainer) {
            console.warn('Messages container not found');
            return;
        }

        messagesContainer.addEventListener('click', (e) => {
            const prevBtn = e.target.closest('.version-prev');
            const nextBtn = e.target.closest('.version-next');
            const versionInfo = e.target.closest('.version-info');

            if (prevBtn) {
                const messageId = prevBtn.dataset.messageId;
                this.navigateToPrevious(messageId);
            } else if (nextBtn) {
                const messageId = nextBtn.dataset.messageId;
                this.navigateToNext(messageId);
            } else if (versionInfo) {
                const messageId = versionInfo.dataset.messageId;
                this.showVersionHistory(messageId);
            }
        });

        // Keyboard shortcuts for version navigation
        document.addEventListener('keydown', (e) => {
            // Alt + Left Arrow: Previous version
            if (e.altKey && e.key === 'ArrowLeft') {
                e.preventDefault();
                this.navigateActiveMessageVersion('prev');
            }
            // Alt + Right Arrow: Next version
            else if (e.altKey && e.key === 'ArrowRight') {
                e.preventDefault();
                this.navigateActiveMessageVersion('next');
            }
        });
    }

    /**
     * Add a new version to a message
     * @param {string} messageId - Message identifier
     * @param {object} versionData - Version content and metadata
     */
    addVersion(messageId, versionData) {
        if (!this.versionStates.has(messageId)) {
            this.versionStates.set(messageId, {
                currentIndex: 0,
                versions: []
            });
        }

        const state = this.versionStates.get(messageId);
        const version = {
            id: this.generateVersionId(),
            content: versionData.content,
            timestamp: versionData.timestamp || Date.now(),
            model: versionData.model || null,
            editReason: versionData.editReason || null,
            metadata: versionData.metadata || {}
        };

        state.versions.push(version);
        state.currentIndex = state.versions.length - 1;

        // Save to storage
        this.saveVersionData();

        // Update UI if message is visible
        this.updateVersionControls(messageId);

        console.log(`Added version ${state.versions.length} for message ${messageId}`);
    }

    /**
     * Navigate to previous version
     * @param {string} messageId - Message identifier
     */
    navigateToPrevious(messageId) {
        const state = this.versionStates.get(messageId);
        if (!state || state.currentIndex === 0) {
            console.log('Already at oldest version');
            return;
        }

        state.currentIndex--;
        this.updateMessageDisplay(messageId);
        this.saveVersionData();

        console.log(`Navigated to version ${state.currentIndex + 1}/${state.versions.length}`);
    }

    /**
     * Navigate to next version
     * @param {string} messageId - Message identifier
     */
    navigateToNext(messageId) {
        const state = this.versionStates.get(messageId);
        if (!state || state.currentIndex === state.versions.length - 1) {
            console.log('Already at newest version');
            return;
        }

        state.currentIndex++;
        this.updateMessageDisplay(messageId);
        this.saveVersionData();

        console.log(`Navigated to version ${state.currentIndex + 1}/${state.versions.length}`);
    }

    /**
     * Navigate to specific version
     * @param {string} messageId - Message identifier
     * @param {number} versionIndex - Version index to navigate to
     */
    navigateToVersion(messageId, versionIndex) {
        const state = this.versionStates.get(messageId);
        if (!state || versionIndex < 0 || versionIndex >= state.versions.length) {
            console.error('Invalid version index');
            return;
        }

        state.currentIndex = versionIndex;
        this.updateMessageDisplay(messageId);
        this.saveVersionData();
    }

    /**
     * Navigate version for currently selected/active message
     * @param {string} direction - 'prev' or 'next'
     */
    navigateActiveMessageVersion(direction) {
        const activeMessage = document.querySelector('.message-bubble.active');
        if (!activeMessage) {
            console.log('No active message');
            return;
        }

        const messageId = activeMessage.dataset.messageId;
        if (direction === 'prev') {
            this.navigateToPrevious(messageId);
        } else if (direction === 'next') {
            this.navigateToNext(messageId);
        }
    }

    /**
     * Update message display with current version
     * @param {string} messageId - Message identifier
     */
    updateMessageDisplay(messageId) {
        const state = this.versionStates.get(messageId);
        if (!state) return;

        const currentVersion = state.versions[state.currentIndex];
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        
        if (!messageElement) return;

        // Update message content
        const contentElement = messageElement.querySelector('.message-content');
        if (contentElement) {
            // Render content (may include markdown, code, etc.)
            contentElement.innerHTML = this.messageRenderer.renderContent(currentVersion.content);
        }

        // Update version controls
        this.updateVersionControls(messageId);

        // Add visual feedback
        this.animateVersionChange(messageElement);
    }

    /**
     * Update version navigation controls
     * @param {string} messageId - Message identifier
     */
    updateVersionControls(messageId) {
        const state = this.versionStates.get(messageId);
        if (!state || state.versions.length <= 1) {
            // Hide controls if only one version
            this.hideVersionControls(messageId);
            return;
        }

        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageElement) return;

        // Find or create controls container
        let controlsContainer = messageElement.querySelector('.version-controls');
        if (!controlsContainer) {
            controlsContainer = this.createVersionControls(messageId);
            
            // Insert after message content
            const contentElement = messageElement.querySelector('.message-content');
            if (contentElement) {
                contentElement.after(controlsContainer);
            }
        }

        // Update button states and version info
        const prevBtn = controlsContainer.querySelector('.version-prev');
        const nextBtn = controlsContainer.querySelector('.version-next');
        const versionInfo = controlsContainer.querySelector('.version-info');

        if (prevBtn) {
            prevBtn.disabled = state.currentIndex === 0;
            prevBtn.classList.toggle('disabled', state.currentIndex === 0);
        }

        if (nextBtn) {
            nextBtn.disabled = state.currentIndex === state.versions.length - 1;
            nextBtn.classList.toggle('disabled', state.currentIndex === state.versions.length - 1);
        }

        if (versionInfo) {
            versionInfo.textContent = `${state.currentIndex + 1} / ${state.versions.length}`;
        }

        // Show controls
        controlsContainer.style.display = 'flex';
    }

    /**
     * Create version navigation controls
     * @param {string} messageId - Message identifier
     * @returns {HTMLElement} Controls container
     */
    createVersionControls(messageId) {
        const state = this.versionStates.get(messageId);
        
        const container = document.createElement('div');
        container.className = 'version-controls';
        
        container.innerHTML = `
            <button class="version-prev" data-message-id="${messageId}" title="Previous version (Alt+←)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
            </button>
            <span class="version-info" data-message-id="${messageId}" title="Click to see version history">
                ${state.currentIndex + 1} / ${state.versions.length}
            </span>
            <button class="version-next" data-message-id="${messageId}" title="Next version (Alt+→)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
            </button>
        `;

        return container;
    }

    /**
     * Hide version controls for a message
     * @param {string} messageId - Message identifier
     */
    hideVersionControls(messageId) {
        const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
        if (!messageElement) return;

        const controls = messageElement.querySelector('.version-controls');
        if (controls) {
            controls.style.display = 'none';
        }
    }

    /**
     * Show version history modal
     * @param {string} messageId - Message identifier
     */
    showVersionHistory(messageId) {
        const state = this.versionStates.get(messageId);
        if (!state) return;

        const modal = this.createVersionHistoryModal(messageId, state);
        document.body.appendChild(modal);

        // Animate in
        setTimeout(() => modal.classList.add('show'), 10);

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeVersionHistoryModal(modal);
            }
        });
    }

    /**
     * Create version history modal
     * @param {string} messageId - Message identifier
     * @param {object} state - Version state
     * @returns {HTMLElement} Modal element
     */
    createVersionHistoryModal(messageId, state) {
        const modal = document.createElement('div');
        modal.className = 'version-history-modal';
        
        const versionsHtml = state.versions.map((version, index) => {
            const isActive = index === state.currentIndex;
            const date = new Date(version.timestamp);
            const formattedDate = this.formatVersionDate(date);
            
            return `
                <div class="version-history-item ${isActive ? 'active' : ''}" data-version-index="${index}">
                    <div class="version-history-header">
                        <span class="version-number">Version ${index + 1}</span>
                        <span class="version-date">${formattedDate}</span>
                    </div>
                    ${version.model ? `<div class="version-model">Model: ${version.model}</div>` : ''}
                    ${version.editReason ? `<div class="version-reason">${version.editReason}</div>` : ''}
                    <div class="version-preview">${this.truncateText(version.content, 150)}</div>
                    <button class="version-view-btn" data-version-index="${index}">
                        ${isActive ? 'Current Version' : 'View This Version'}
                    </button>
                </div>
            `;
        }).join('');

        modal.innerHTML = `
            <div class="version-history-content">
                <div class="version-history-header-main">
                    <h3>Message Version History</h3>
                    <button class="version-history-close">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="version-history-list">
                    ${versionsHtml}
                </div>
            </div>
        `;

        // Setup event listeners
        modal.querySelector('.version-history-close').addEventListener('click', () => {
            this.closeVersionHistoryModal(modal);
        });

        modal.querySelectorAll('.version-view-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const versionIndex = parseInt(btn.dataset.versionIndex);
                this.navigateToVersion(messageId, versionIndex);
                this.closeVersionHistoryModal(modal);
            });
        });

        return modal;
    }

    /**
     * Close version history modal
     * @param {HTMLElement} modal - Modal element
     */
    closeVersionHistoryModal(modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }

    /**
     * Animate version change
     * @param {HTMLElement} messageElement - Message element
     */
    animateVersionChange(messageElement) {
        messageElement.classList.add('version-changing');
        setTimeout(() => {
            messageElement.classList.remove('version-changing');
        }, 300);
    }

    /**
     * Get current version for a message
     * @param {string} messageId - Message identifier
     * @returns {object|null} Current version data
     */
    getCurrentVersion(messageId) {
        const state = this.versionStates.get(messageId);
        if (!state) return null;
        return state.versions[state.currentIndex];
    }

    /**
     * Get all versions for a message
     * @param {string} messageId - Message identifier
     * @returns {array} All versions
     */
    getAllVersions(messageId) {
        const state = this.versionStates.get(messageId);
        return state ? state.versions : [];
    }

    /**
     * Check if message has multiple versions
     * @param {string} messageId - Message identifier
     * @returns {boolean} Has multiple versions
     */
    hasMultipleVersions(messageId) {
        const state = this.versionStates.get(messageId);
        return state && state.versions.length > 1;
    }

    /**
     * Delete a specific version
     * @param {string} messageId - Message identifier
     * @param {number} versionIndex - Version index to delete
     */
    deleteVersion(messageId, versionIndex) {
        const state = this.versionStates.get(messageId);
        if (!state || state.versions.length <= 1) {
            console.error('Cannot delete only version');
            return;
        }

        if (versionIndex < 0 || versionIndex >= state.versions.length) {
            console.error('Invalid version index');
            return;
        }

        // Remove version
        state.versions.splice(versionIndex, 1);

        // Adjust current index if needed
        if (state.currentIndex >= state.versions.length) {
            state.currentIndex = state.versions.length - 1;
        }

        this.updateMessageDisplay(messageId);
        this.saveVersionData();

        console.log(`Deleted version ${versionIndex + 1} from message ${messageId}`);
    }

    /**
     * Clear all versions for a message (keep only current)
     * @param {string} messageId - Message identifier
     */
    clearVersionHistory(messageId) {
        const state = this.versionStates.get(messageId);
        if (!state) return;

        const currentVersion = state.versions[state.currentIndex];
        state.versions = [currentVersion];
        state.currentIndex = 0;

        this.hideVersionControls(messageId);
        this.saveVersionData();

        console.log(`Cleared version history for message ${messageId}`);
    }

    /**
     * Save version data to storage
     */
    async saveVersionData() {
        try {
            const data = {
                versions: Array.from(this.versionStates.entries()).map(([messageId, state]) => ({
                    messageId,
                    currentIndex: state.currentIndex,
                    versions: state.versions
                }))
            };

            localStorage.setItem('message_versions', JSON.stringify(data));
        } catch (error) {
            console.error('Failed to save version data:', error);
        }
    }

    /**
     * Load version data from storage
     */
    async loadVersionData() {
        try {
            const data = localStorage.getItem('message_versions');
            if (!data) return;

            const parsed = JSON.parse(data);
            if (parsed.versions) {
                parsed.versions.forEach(item => {
                    this.versionStates.set(item.messageId, {
                        currentIndex: item.currentIndex,
                        versions: item.versions
                    });
                });
            }

            console.log(`Loaded ${this.versionStates.size} message version histories`);
        } catch (error) {
            console.error('Failed to load version data:', error);
        }
    }

    /**
     * Generate unique version ID
     * @returns {string} Version ID
     */
    generateVersionId() {
        return `v_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Format version date
     * @param {Date} date - Date object
     * @returns {string} Formatted date
     */
    formatVersionDate(date) {
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;

        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
        });
    }

    /**
     * Truncate text with ellipsis
     * @param {string} text - Text to truncate
     * @param {number} maxLength - Maximum length
     * @returns {string} Truncated text
     */
    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    /**
     * Export version history
     * @param {string} messageId - Message identifier
     * @returns {object} Version history data
     */
    exportVersionHistory(messageId) {
        const state = this.versionStates.get(messageId);
        if (!state) return null;

        return {
            messageId,
            currentIndex: state.currentIndex,
            totalVersions: state.versions.length,
            versions: state.versions.map((v, index) => ({
                index,
                id: v.id,
                content: v.content,
                timestamp: v.timestamp,
                date: new Date(v.timestamp).toISOString(),
                model: v.model,
                editReason: v.editReason,
                metadata: v.metadata
            }))
        };
    }

    /**
     * Import version history
     * @param {object} data - Version history data
     */
    importVersionHistory(data) {
        if (!data || !data.messageId || !data.versions) {
            console.error('Invalid import data');
            return;
        }

        this.versionStates.set(data.messageId, {
            currentIndex: data.currentIndex || 0,
            versions: data.versions
        });

        this.saveVersionData();
        console.log(`Imported version history for message ${data.messageId}`);
    }

    /**
     * Get statistics about version usage
     * @returns {object} Statistics
     */
    getStatistics() {
        let totalVersions = 0;
        let messagesWithVersions = 0;
        let maxVersions = 0;

        this.versionStates.forEach((state) => {
            const versionCount = state.versions.length;
            totalVersions += versionCount;
            if (versionCount > 1) messagesWithVersions++;
            if (versionCount > maxVersions) maxVersions = versionCount;
        });

        return {
            totalMessages: this.versionStates.size,
            messagesWithVersions,
            totalVersions,
            averageVersionsPerMessage: totalVersions / Math.max(this.versionStates.size, 1),
            maxVersionsForSingleMessage: maxVersions
        };
    }
}
