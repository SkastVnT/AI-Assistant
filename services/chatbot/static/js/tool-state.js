    // TOOLS MENU
    // ════════════════════════════════════════════════════════════
    // ── Persistent tool state ────────────────────────────────────
    // Default: google-search is ON. User can toggle from the "+ Tools" menu.
    const ACTIVE_TOOLS_KEY = 'activeTools';
    function loadActiveTools() {
        try {
            const saved = JSON.parse(localStorage.getItem(ACTIVE_TOOLS_KEY));
            if (Array.isArray(saved)) return new Set(saved);
        } catch (_) {}
        return new Set(['google-search']); // first-run default
    }
    function saveActiveTools() {
        localStorage.setItem(ACTIVE_TOOLS_KEY, JSON.stringify([...activeTools]));
    }
    let activeTools = loadActiveTools();
    let _thinkingModeBeforeDeepResearch = null;

    // Map tool name → button element ID (shared by setupToolItemClicks + removeTool)
    // NOTE: 'reverse-image' is a virtual UI slug that toggles BOTH
    // serpapi-reverse-image (Google Lens) and saucenao at once.
    const toolBtnMap = {
        'image-generation':    'imageGenToolBtn',
        'img2img':             'img2imgToolBtn',
        'google-search':       'googleSearchBtn',
        'github':              'githubBtn',
        'deep-research':       'deepResearchToolBtn',
        'serpapi-images':      'serpapiImagesBtn',
        'last30days-research': 'last30daysBtn',
        'reverse-image':       'reverseImageBtn',
    };
    // Virtual → real tool slug expansion (sent to backend in `tools` array)
    const toolExpansionMap = {
        'reverse-image': ['serpapi-reverse-image', 'saucenao'],
    };

    function initToolsMenu() {
        const btn = document.getElementById('toolsMenuBtn');
        const dropdown = document.getElementById('toolsMenuDropdown');
        if (!btn || !dropdown) return;

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('open');
        });

        document.addEventListener('click', () => dropdown.classList.remove('open'));
        dropdown.addEventListener('click', (e) => e.stopPropagation());

        setupToolItemClicks();
        // Sync button active classes with restored tool state
        activeTools.forEach(tool => {
            const btnId = toolBtnMap[tool];
            if (btnId) {
                const el = document.getElementById(btnId);
                if (el) el.classList.add('active');
            }
        });
        updateActiveToolsDisplay();
    }

    function setupToolItemClicks() {
        const configBtn = document.getElementById('configAgentBtn');
        if (configBtn) configBtn.addEventListener('click', () => { closeToolsMenu(); openConfigAgentModal(); });

        let _thinkingModeBeforeDeepResearch = null;

        // All toggle-able tools — derived from toolBtnMap for DRY
        Object.entries(toolBtnMap).forEach(([tool, id]) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('click', () => {
                toggleToolActive(tool, el);
                // Deep Research: also enable web search + switch to multi-thinking
                if (tool === 'deep-research') {
                    if (activeTools.has('deep-research')) {
                        // Activating — save current mode then switch to multi-thinking
                        _thinkingModeBeforeDeepResearch = window.getThinkingMode ? window.getThinkingMode() : 'instant';
                        const gsBtn = document.getElementById('googleSearchBtn');
                        if (gsBtn && !activeTools.has('google-search')) {
                            activeTools.add('google-search');
                            gsBtn.classList.add('active');
                        }
                        if (typeof selectThinkingMode === 'function') {
                            selectThinkingMode('multi-thinking', 'layers', '4-Agents');
                        }
                    } else {
                        // Deactivating — restore previous mode
                        const _restore = _thinkingModeBeforeDeepResearch || 'instant';
                        _thinkingModeBeforeDeepResearch = null;
                        const _modeMap = {
                            'instant':        ['zap',    'Instant'],
                            'thinking':       ['brain',  'Think'],
                            'multi-thinking': ['layers', '4-Agents'],
                        };
                        const [_icon, _label] = _modeMap[_restore] || _modeMap.instant;
                        if (typeof selectThinkingMode === 'function') selectThinkingMode(_restore, _icon, _label);
                    }
                }
            });
        });

        const br = document.getElementById('branchConversationBtn');
        if (br) br.addEventListener('click', () => { closeToolsMenu(); createBranchConversation(); });
    }

    function toggleToolActive(name, btn) {
        if (activeTools.has(name)) {
            activeTools.delete(name);
            btn.classList.remove('active');
        } else {
            activeTools.add(name);
            btn.classList.add('active');
        }
        saveActiveTools();
        updateActiveToolsDisplay();
    }

    function updateActiveToolsDisplay() {
        const display = document.getElementById('activeToolsDisplay');
        if (!display) return;
        display.innerHTML = '';
        if (activeTools.size === 0) return;
        const icons = {
            'image-generation': '🎨', 'img2img': '🖼️',
            'google-search': '🔍', 'github': '📦', 'deep-research': '🔬',
            'serpapi-images': '🖼️', 'reverse-image': '📸',
            'last30days-research': '📊'
        };
        const labels = {
            'image-generation': 'Image Gen', 'img2img': 'Img2Img',
            'google-search': 'Web', 'github': 'GitHub', 'deep-research': 'Deep Research',
            'serpapi-images': 'Images', 'reverse-image': 'Reverse Image',
            'last30days-research': 'Social',
        };
        // Tools that run silently in the background — don't show a badge
        const hiddenTools = new Set(['google-search', 'serpapi-images', 'last30days-research', 'github']);
        activeTools.forEach(tool => {
            if (hiddenTools.has(tool)) return;
            const badge = document.createElement('span');
            badge.className = 'active-tool-badge';
            badge.innerHTML = `${icons[tool] || '🔧'} ${labels[tool] || tool} <button onclick="removeTool('${tool}')">&times;</button>`;
            display.appendChild(badge);
        });
    }

    window.removeTool = function(name) {
        activeTools.delete(name);
        // Sync the dropdown button state so it no longer appears active
        const btnId = toolBtnMap[name];
        if (btnId) {
            const btn = document.getElementById(btnId);
            if (btn) btn.classList.remove('active');
        }
        saveActiveTools();
        updateActiveToolsDisplay();
    };
    // Expand virtual tools (e.g. 'reverse-image' → ['serpapi-reverse-image','saucenao'])
    // before sending to the backend, so existing dispatchers keep working.
    window.getActiveTools = () => {
        const out = [];
        activeTools.forEach(t => {
            if (toolExpansionMap[t]) {
                out.push(...toolExpansionMap[t]);
            } else {
                out.push(t);
            }
        });
        return out;
    };

    function closeToolsMenu() {
        const d = document.getElementById('toolsMenuDropdown');
        if (d) d.classList.remove('open');
    }

    // ════════════════════════════════════════════════════════════
    // TOOL STATUS BAR — shows what tools are running during SSE
    // ════════════════════════════════════════════════════════════
    const toolStatusMessages = {
        'google-search': '🔍 Đang tìm trên web…',
        'serpapi-bing': '🔍 Searching Bing…',
        'serpapi-baidu': '🔍 Searching Baidu…',
        'serpapi-images': '🖼️ Đang tìm ảnh…',
        'serpapi-reverse-image': '📸 Reverse image (Lens)…',
        'saucenao': '🔎 Reverse image (SauceNAO)…',
        'reverse-image': '📸 Reverse image (Lens + SauceNAO song song)…',
        'github': '📦 Đang tìm GitHub…',
        'image-generation': '🎨 Generating image…',
        'img2img': '🖼️ Running Img2Img…',
        'deep-research': '🔬 Deep research in progress…',
        'last30days-research': '📊 Social media research…',
    };

    window.showToolStatus = function() {
        const bar = document.getElementById('toolStatusBar');
        if (!bar) return;
        // Use the user-facing activeTools (not expanded) so combined slugs
        // like 'reverse-image' show a single status line instead of two.
        const active = Array.from(activeTools);
        if (active.length === 0) { bar.style.display = 'none'; return; }
        const msgs = active.map(t => toolStatusMessages[t]).filter(Boolean);
        if (msgs.length === 0) { bar.style.display = 'none'; return; }
        bar.innerHTML = msgs.map(m => `<span class="tool-status-item">${m}</span>`).join('');
        bar.style.display = 'flex';
    };

    window.hideToolStatus = function() {
        const bar = document.getElementById('toolStatusBar');
        if (bar) { bar.innerHTML = ''; bar.style.display = 'none'; }
    };

    // ════════════════════════════════════════════════════════════

    // BRANCH CONVERSATION
    // ════════════════════════════════════════════════════════════
    function createBranchConversation() {
        if (!window.chatManager) return;
        const cur = window.chatManager.getCurrentSession();
        if (!cur || !cur.messages || cur.messages.length === 0) return;

        const branchId = 'branch_' + Date.now();
        const title = `🌿 ${(cur.title || 'Chat').substring(0, 20)}…`;
        window.chatManager.chatSessions[branchId] = {
            id: branchId, title: title, messages: [...cur.messages],
            parentId: cur.id, branchPoint: cur.messages.length, createdAt: Date.now(),
            attachedFiles: cur.attachedFiles ? [...cur.attachedFiles] : []
        };
        window.chatManager.saveSessions();
        window.chatManager.currentChatId = branchId;
        window.dispatchEvent(new Event('chatListNeedsUpdate'));
        if (window.chatApp) window.chatApp.loadCurrentChat();
    }

    // ════════════════════════════════════════════════════════════


if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initToolsMenu);
} else {
    initToolsMenu();
}
