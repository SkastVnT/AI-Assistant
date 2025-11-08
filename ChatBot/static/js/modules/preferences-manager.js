/**
 * PreferencesManager Module
 * Manages user preferences and application state
 * Phase 5: Sidebar Toggle & Polish
 */

export class PreferencesManager {
    constructor() {
        this.storageKey = 'chatbot_preferences';
        this.preferences = this.loadPreferences();
        this.listeners = new Map();
        
        // Default preferences
        this.defaults = {
            sidebarCollapsed: false,
            theme: 'light',
            activeProjectId: null,
            searchFilters: {
                messageType: 'all',
                dateRange: 'all',
                sortBy: 'newest'
            },
            messageDisplay: {
                showTimestamps: true,
                showVersions: true,
                compactMode: false
            },
            notifications: {
                enabled: true,
                duration: 3000
            },
            accessibility: {
                reducedMotion: false,
                highContrast: false,
                fontSize: 'medium'
            }
        };
    }

    /**
     * Load preferences from localStorage
     */
    loadPreferences() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (stored) {
                const parsed = JSON.parse(stored);
                return { ...this.defaults, ...parsed };
            }
        } catch (error) {
            console.error('Failed to load preferences:', error);
        }
        return { ...this.defaults };
    }

    /**
     * Save preferences to localStorage
     */
    savePreferences() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.preferences));
            this.notifyListeners('*');
        } catch (error) {
            console.error('Failed to save preferences:', error);
        }
    }

    /**
     * Get a preference value
     * @param {string} key - Dot notation key (e.g., 'sidebar.collapsed')
     */
    get(key) {
        const keys = key.split('.');
        let value = this.preferences;
        
        for (const k of keys) {
            if (value && typeof value === 'object' && k in value) {
                value = value[k];
            } else {
                return undefined;
            }
        }
        
        return value;
    }

    /**
     * Set a preference value
     * @param {string} key - Dot notation key
     * @param {any} value - Value to set
     */
    set(key, value) {
        const keys = key.split('.');
        const lastKey = keys.pop();
        let target = this.preferences;
        
        // Navigate to nested object
        for (const k of keys) {
            if (!(k in target) || typeof target[k] !== 'object') {
                target[k] = {};
            }
            target = target[k];
        }
        
        // Set value
        target[lastKey] = value;
        this.savePreferences();
        this.notifyListeners(key);
    }

    /**
     * Toggle a boolean preference
     * @param {string} key - Preference key
     */
    toggle(key) {
        const current = this.get(key);
        if (typeof current === 'boolean') {
            this.set(key, !current);
            return !current;
        }
        return null;
    }

    /**
     * Reset preferences to defaults
     * @param {string} key - Optional specific key to reset
     */
    reset(key = null) {
        if (key) {
            const keys = key.split('.');
            const lastKey = keys.pop();
            let target = this.preferences;
            let defaultTarget = this.defaults;
            
            for (const k of keys) {
                target = target[k];
                defaultTarget = defaultTarget[k];
            }
            
            target[lastKey] = defaultTarget[lastKey];
        } else {
            this.preferences = { ...this.defaults };
        }
        
        this.savePreferences();
    }

    /**
     * Register a listener for preference changes
     * @param {string} key - Key to listen for ('*' for all changes)
     * @param {Function} callback - Callback function
     */
    on(key, callback) {
        if (!this.listeners.has(key)) {
            this.listeners.set(key, []);
        }
        this.listeners.get(key).push(callback);
    }

    /**
     * Unregister a listener
     * @param {string} key - Key
     * @param {Function} callback - Callback to remove
     */
    off(key, callback) {
        if (this.listeners.has(key)) {
            const callbacks = this.listeners.get(key);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    /**
     * Notify listeners of changes
     * @param {string} key - Changed key
     */
    notifyListeners(key) {
        // Notify specific listeners
        if (this.listeners.has(key)) {
            this.listeners.get(key).forEach(callback => {
                callback(this.get(key), key);
            });
        }
        
        // Notify wildcard listeners
        if (key !== '*' && this.listeners.has('*')) {
            this.listeners.get('*').forEach(callback => {
                callback(this.get(key), key);
            });
        }
    }

    /**
     * Export preferences as JSON
     */
    export() {
        return JSON.stringify(this.preferences, null, 2);
    }

    /**
     * Import preferences from JSON
     * @param {string} json - JSON string
     */
    import(json) {
        try {
            const imported = JSON.parse(json);
            this.preferences = { ...this.defaults, ...imported };
            this.savePreferences();
            return true;
        } catch (error) {
            console.error('Failed to import preferences:', error);
            return false;
        }
    }

    /**
     * Apply system preferences (dark mode, reduced motion, etc.)
     */
    applySystemPreferences() {
        // Dark mode
        const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
        if (this.get('theme') === 'auto') {
            this.applyTheme(darkModeQuery.matches ? 'dark' : 'light');
        }
        
        // Listen for system changes
        darkModeQuery.addEventListener('change', (e) => {
            if (this.get('theme') === 'auto') {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });
        
        // Reduced motion
        const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
        if (reducedMotionQuery.matches) {
            this.set('accessibility.reducedMotion', true);
            document.body.classList.add('reduced-motion');
        }
        
        // High contrast
        const highContrastQuery = window.matchMedia('(prefers-contrast: high)');
        if (highContrastQuery.matches) {
            this.set('accessibility.highContrast', true);
            document.body.classList.add('high-contrast');
        }
    }

    /**
     * Apply theme
     * @param {string} theme - 'light', 'dark', or 'auto'
     */
    applyTheme(theme) {
        if (theme === 'auto') {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
            theme = darkModeQuery.matches ? 'dark' : 'light';
        }
        
        if (theme === 'dark') {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
        
        this.set('theme', theme);
    }

    /**
     * Apply sidebar state
     */
    applySidebarState() {
        const collapsed = this.get('sidebarCollapsed');
        if (collapsed) {
            document.body.classList.add('sidebar-collapsed');
        } else {
            document.body.classList.remove('sidebar-collapsed');
        }
    }

    /**
     * Initialize preferences
     */
    initialize() {
        // Apply system preferences
        this.applySystemPreferences();
        
        // Apply stored preferences
        this.applyTheme(this.get('theme'));
        this.applySidebarState();
        
        // Apply accessibility settings
        if (this.get('accessibility.reducedMotion')) {
            document.body.classList.add('reduced-motion');
        }
        
        if (this.get('accessibility.highContrast')) {
            document.body.classList.add('high-contrast');
        }
        
        // Set font size
        const fontSize = this.get('accessibility.fontSize');
        document.documentElement.style.fontSize = {
            'small': '14px',
            'medium': '16px',
            'large': '18px',
            'x-large': '20px'
        }[fontSize] || '16px';
        
        console.log('Preferences initialized:', this.preferences);
    }
}

/**
 * SidebarToggle Component
 * Handles sidebar collapse/expand functionality
 */
export class SidebarToggle {
    constructor(preferencesManager) {
        this.preferences = preferencesManager;
        this.sidebar = document.querySelector('.sidebar');
        this.mainContent = document.querySelector('.main-content');
        this.toggleBtn = null;
        this.mobileOverlay = null;
        
        this.isMobile = window.matchMedia('(max-width: 768px)').matches;
        
        this.initialize();
    }

    /**
     * Create toggle button
     */
    createToggleButton() {
        // Check if button already exists
        if (this.sidebar.querySelector('.sidebar-toggle-btn')) {
            this.toggleBtn = this.sidebar.querySelector('.sidebar-toggle-btn');
            return;
        }
        
        this.toggleBtn = document.createElement('button');
        this.toggleBtn.className = 'sidebar-toggle-btn';
        this.toggleBtn.setAttribute('aria-label', 'Toggle sidebar');
        this.toggleBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M4.5 12.5l5-5-5-5v10z"/>
            </svg>
        `;
        
        this.sidebar.appendChild(this.toggleBtn);
    }

    /**
     * Create mobile overlay
     */
    createMobileOverlay() {
        if (document.querySelector('.mobile-overlay')) {
            this.mobileOverlay = document.querySelector('.mobile-overlay');
            return;
        }
        
        this.mobileOverlay = document.createElement('div');
        this.mobileOverlay.className = 'mobile-overlay';
        document.body.appendChild(this.mobileOverlay);
    }

    /**
     * Toggle sidebar
     */
    toggle() {
        if (this.isMobile) {
            this.toggleMobile();
        } else {
            this.toggleDesktop();
        }
    }

    /**
     * Toggle desktop sidebar (collapse/expand)
     */
    toggleDesktop() {
        const isCollapsed = document.body.classList.toggle('sidebar-collapsed');
        this.preferences.set('sidebarCollapsed', isCollapsed);
        
        // Update button rotation
        const svg = this.toggleBtn.querySelector('svg');
        if (isCollapsed) {
            svg.style.transform = 'rotate(180deg)';
        } else {
            svg.style.transform = 'rotate(0deg)';
        }
        
        // Dispatch event for other components
        window.dispatchEvent(new CustomEvent('sidebarToggled', {
            detail: { collapsed: isCollapsed }
        }));
    }

    /**
     * Toggle mobile sidebar (show/hide)
     */
    toggleMobile() {
        const isOpen = document.body.classList.toggle('sidebar-open');
        
        if (isOpen) {
            this.mobileOverlay.style.display = 'block';
            document.body.style.overflow = 'hidden'; // Prevent scroll
        } else {
            this.mobileOverlay.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    /**
     * Close sidebar (mobile only)
     */
    close() {
        if (this.isMobile) {
            document.body.classList.remove('sidebar-open');
            this.mobileOverlay.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Toggle button click
        this.toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });
        
        // Mobile overlay click (close sidebar)
        if (this.mobileOverlay) {
            this.mobileOverlay.addEventListener('click', () => {
                this.close();
            });
        }
        
        // Keyboard shortcut (Ctrl+B or Cmd+B)
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                e.preventDefault();
                this.toggle();
            }
        });
        
        // Handle window resize
        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                const wasMobile = this.isMobile;
                this.isMobile = window.matchMedia('(max-width: 768px)').matches;
                
                // Clean up mobile state if switching to desktop
                if (wasMobile && !this.isMobile) {
                    document.body.classList.remove('sidebar-open');
                    this.mobileOverlay.style.display = 'none';
                    document.body.style.overflow = '';
                }
            }, 250);
        });
        
        // Close sidebar when clicking chat items (mobile only)
        document.addEventListener('click', (e) => {
            if (this.isMobile && e.target.closest('.chat-item')) {
                this.close();
            }
        });
    }

    /**
     * Initialize sidebar toggle
     */
    initialize() {
        this.createToggleButton();
        this.createMobileOverlay();
        this.setupEventListeners();
        
        // Apply initial state
        const collapsed = this.preferences.get('sidebarCollapsed');
        if (collapsed && !this.isMobile) {
            document.body.classList.add('sidebar-collapsed');
            const svg = this.toggleBtn.querySelector('svg');
            svg.style.transform = 'rotate(180deg)';
        }
        
        console.log('Sidebar toggle initialized');
    }
}

/**
 * NotificationManager
 * Displays toast notifications
 */
export class NotificationManager {
    constructor(preferencesManager) {
        this.preferences = preferencesManager;
        this.queue = [];
        this.activeNotification = null;
    }

    /**
     * Show notification
     * @param {string} message - Notification message
     * @param {string} type - 'success', 'error', 'info', 'warning'
     * @param {number} duration - Display duration in ms
     */
    show(message, type = 'info', duration = null) {
        if (!this.preferences.get('notifications.enabled')) {
            return;
        }
        
        duration = duration || this.preferences.get('notifications.duration');
        
        const notification = {
            message,
            type,
            duration,
            element: this.createNotificationElement(message, type)
        };
        
        // Add to queue
        this.queue.push(notification);
        
        // Show if no active notification
        if (!this.activeNotification) {
            this.showNext();
        }
    }

    /**
     * Create notification element
     */
    createNotificationElement(message, type) {
        const div = document.createElement('div');
        div.className = `notification notification-${type}`;
        
        const icon = {
            'success': '✓',
            'error': '✕',
            'info': 'i',
            'warning': '⚠'
        }[type] || 'i';
        
        div.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 18px;">${icon}</span>
                <span>${message}</span>
            </div>
        `;
        
        return div;
    }

    /**
     * Show next notification in queue
     */
    showNext() {
        if (this.queue.length === 0) {
            this.activeNotification = null;
            return;
        }
        
        const notification = this.queue.shift();
        this.activeNotification = notification;
        
        // Add to DOM
        document.body.appendChild(notification.element);
        
        // Trigger animation
        setTimeout(() => {
            notification.element.classList.add('show');
        }, 10);
        
        // Auto-hide
        setTimeout(() => {
            this.hide(notification);
        }, notification.duration);
    }

    /**
     * Hide notification
     */
    hide(notification) {
        if (!notification || !notification.element) {
            return;
        }
        
        notification.element.classList.remove('show');
        
        setTimeout(() => {
            if (notification.element.parentNode) {
                notification.element.parentNode.removeChild(notification.element);
            }
            
            // Show next in queue
            if (this.activeNotification === notification) {
                this.showNext();
            }
        }, 300);
    }
}

// Export default
export default PreferencesManager;
