/**
 * Search Handler Module
 * Handles chat search functionality with filtering and highlighting
 */

export class SearchHandler {
    constructor(chatManager) {
        this.chatManager = chatManager;
        this.searchInput = null;
        this.searchResults = [];
        this.isSearching = false;
        this.searchDebounceTimer = null;
    }

    /**
     * Initialize search handler
     */
    init() {
        this.searchInput = document.getElementById('searchInput');
        
        if (!this.searchInput) {
            console.warn('[SearchHandler] Search input not found');
            return;
        }

        this.setupEventListeners();
        console.log('[SearchHandler] Initialized');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Search input with debounce
        this.searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            
            // Clear previous timer
            if (this.searchDebounceTimer) {
                clearTimeout(this.searchDebounceTimer);
            }

            // Debounce search (300ms)
            this.searchDebounceTimer = setTimeout(() => {
                this.performSearch(query);
            }, 300);
        });

        // Clear on ESC
        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.clearSearch();
            }
        });

        // Focus search with Ctrl+F
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                this.focusSearch();
            }
        });
    }

    /**
     * Perform search across all chats
     */
    performSearch(query) {
        if (!query) {
            this.clearSearch();
            return;
        }

        this.isSearching = true;
        console.log(`[SearchHandler] Searching for: "${query}"`);

        const results = this.searchChats(query);
        this.displayResults(results, query);
    }

    /**
     * Search through all chat sessions
     */
    searchChats(query) {
        const sessions = this.chatManager.chatSessions;
        const results = [];
        const lowerQuery = query.toLowerCase();

        for (const [id, session] of Object.entries(sessions)) {
            let matchType = null;
            let matchCount = 0;
            let snippet = '';

            // Search in title
            if (session.title.toLowerCase().includes(lowerQuery)) {
                matchType = 'title';
                matchCount++;
            }

            // Search in messages
            for (const messageHtml of session.messages) {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = messageHtml;
                const textContent = tempDiv.textContent.toLowerCase();

                if (textContent.includes(lowerQuery)) {
                    matchType = matchType || 'content';
                    matchCount++;

                    // Extract snippet around match
                    if (!snippet) {
                        const index = textContent.indexOf(lowerQuery);
                        const start = Math.max(0, index - 50);
                        const end = Math.min(textContent.length, index + query.length + 50);
                        snippet = tempDiv.textContent.substring(start, end);
                        
                        if (start > 0) snippet = '...' + snippet;
                        if (end < textContent.length) snippet = snippet + '...';
                    }
                }
            }

            // Add to results if match found
            if (matchType) {
                results.push({
                    id,
                    session,
                    matchType,
                    matchCount,
                    snippet,
                    score: this.calculateScore(matchType, matchCount, session.title, lowerQuery)
                });
            }
        }

        // Sort by relevance score
        results.sort((a, b) => b.score - a.score);

        console.log(`[SearchHandler] Found ${results.length} results`);
        return results;
    }

    /**
     * Calculate relevance score
     */
    calculateScore(matchType, matchCount, title, query) {
        let score = matchCount;

        // Boost title matches
        if (matchType === 'title') {
            score += 10;
        }

        // Boost exact matches
        if (title.toLowerCase() === query) {
            score += 20;
        }

        // Boost if query is at start of title
        if (title.toLowerCase().startsWith(query)) {
            score += 5;
        }

        return score;
    }

    /**
     * Display search results
     */
    displayResults(results, query) {
        const chatList = document.getElementById('chatList');
        
        if (!chatList) {
            console.warn('[SearchHandler] Chat list not found');
            return;
        }

        // Clear current list
        chatList.innerHTML = '';

        if (results.length === 0) {
            // Show "no results" message
            chatList.innerHTML = `
                <div class="search-no-results">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="m21 21-4.35-4.35"/>
                    </svg>
                    <p>No chats found</p>
                    <p class="search-hint">Try different keywords</p>
                </div>
            `;
            return;
        }

        // Show results header
        const header = document.createElement('div');
        header.className = 'search-results-header';
        header.innerHTML = `
            <span class="search-results-count">${results.length} result${results.length > 1 ? 's' : ''}</span>
            <button class="search-clear-btn" onclick="window.chatBotApp.searchHandler.clearSearch()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
            </button>
        `;
        chatList.appendChild(header);

        // Create results section
        const resultsSection = document.createElement('div');
        resultsSection.className = 'chat-section';

        for (const result of results) {
            const chatItem = this.createSearchResultItem(result, query);
            resultsSection.appendChild(chatItem);
        }

        chatList.appendChild(resultsSection);
    }

    /**
     * Create search result item
     */
    createSearchResultItem(result, query) {
        const { id, session, matchType, matchCount, snippet } = result;
        
        const item = document.createElement('div');
        item.className = 'chat-item';
        if (id === this.chatManager.currentChatId) {
            item.classList.add('active');
        }

        // Highlight query in title
        const highlightedTitle = this.highlightText(session.title, query);

        item.innerHTML = `
            <div class="chat-item-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
            </div>
            <div class="chat-item-content">
                <div class="chat-item-title">${highlightedTitle}</div>
                ${snippet ? `<div class="chat-item-snippet">${this.highlightText(snippet, query)}</div>` : ''}
                <div class="chat-item-meta">
                    <span class="match-badge ${matchType}">${matchType === 'title' ? 'Title' : 'Content'}</span>
                    ${matchCount > 1 ? `<span class="match-count">${matchCount} matches</span>` : ''}
                    <span class="chat-item-date">${this.formatDate(session.updatedAt)}</span>
                </div>
            </div>
        `;

        // Click to switch chat
        item.addEventListener('click', () => {
            this.chatManager.switchChat(id);
            // Re-render with active state
            this.displayResults([...this.searchResults], query);
        });

        return item;
    }

    /**
     * Highlight query text in string
     */
    highlightText(text, query) {
        if (!query) return text;

        const regex = new RegExp(`(${this.escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    /**
     * Escape regex special characters
     */
    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Format date for display
     */
    formatDate(date) {
        if (!(date instanceof Date)) {
            date = new Date(date);
        }

        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString();
    }

    /**
     * Clear search
     */
    clearSearch() {
        if (this.searchInput) {
            this.searchInput.value = '';
        }

        this.isSearching = false;
        this.searchResults = [];

        // Restore normal chat list
        if (this.chatManager.renderChatList) {
            this.chatManager.renderChatList();
        }

        console.log('[SearchHandler] Search cleared');
    }

    /**
     * Focus search input
     */
    focusSearch() {
        if (this.searchInput) {
            this.searchInput.focus();
            this.searchInput.select();
        }
    }

    /**
     * Advanced search with filters
     */
    advancedSearch(query, filters = {}) {
        const {
            model = null,
            dateFrom = null,
            dateTo = null,
            minLength = 0,
            maxLength = Infinity
        } = filters;

        let results = this.searchChats(query);

        // Apply filters
        if (model) {
            results = results.filter(r => {
                // Check if any message in session used this model
                return r.session.messages.some(msg => 
                    msg.includes(`"model":"${model}"`) || 
                    msg.includes(`>${model}<`)
                );
            });
        }

        if (dateFrom) {
            results = results.filter(r => 
                new Date(r.session.updatedAt) >= new Date(dateFrom)
            );
        }

        if (dateTo) {
            results = results.filter(r => 
                new Date(r.session.updatedAt) <= new Date(dateTo)
            );
        }

        if (minLength > 0 || maxLength < Infinity) {
            results = results.filter(r => {
                const length = r.session.messages.length;
                return length >= minLength && length <= maxLength;
            });
        }

        return results;
    }

    /**
     * Get search statistics
     */
    getSearchStats() {
        return {
            isSearching: this.isSearching,
            resultCount: this.searchResults.length,
            currentQuery: this.searchInput ? this.searchInput.value : ''
        };
    }
}
