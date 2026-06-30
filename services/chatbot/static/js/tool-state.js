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
        return new Set([]); // google-search is always-on; no default active tools
    }
    function saveActiveTools() {
        localStorage.setItem(ACTIVE_TOOLS_KEY, JSON.stringify([...activeTools]));
    }
    let activeTools = loadActiveTools();
    let _thinkingModeBeforeDeepResearch = null;
    let _menuIsOpen = false;

    // Map tool name → button element ID (shared by setupToolItemClicks + removeTool)
    // NOTE: 'reverse-image' is a virtual UI slug that toggles BOTH
    // serpapi-reverse-image (Google Lens) and saucenao at once.
    const toolBtnMap = {
        'image-generation':    'imageGenToolBtn',
        'img2img':             'img2imgToolBtn',
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

        // GSAP takes ownership of visibility/opacity/transform
        if (window.gsap) {
            gsap.set(dropdown, { autoAlpha: 0, y: 10, scale: 0.96, transformOrigin: 'bottom left' });
        }

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            _menuIsOpen ? closeToolsMenu() : _openToolsMenu(dropdown);
        });

        document.addEventListener('click', () => { if (_menuIsOpen) closeToolsMenu(); });
        dropdown.addEventListener('click', (e) => e.stopPropagation());

        setupToolItemClicks();
        activeTools.forEach(tool => {
            const btnId = toolBtnMap[tool];
            if (btnId) {
                const el = document.getElementById(btnId);
                if (el) el.classList.add('active');
            }
        });
        updateActiveToolsDisplay();

        // Stagger-in quick-tools on load
        if (window.gsap) {
            gsap.from('.quick-tool', { opacity: 0, y: 5, stagger: 0.07, duration: 0.32, ease: 'power2.out', delay: 0.25 });
            // Hover microinteractions
            document.querySelectorAll('.quick-tool').forEach(el => {
                el.addEventListener('mouseenter', () => gsap.to(el, { scale: 1.12, duration: 0.13, ease: 'power2.out' }));
                el.addEventListener('mouseleave', () => gsap.to(el, { scale: 1, duration: 0.11, ease: 'power2.in' }));
            });
            // + button pulse when opened (handled by rotation), but add subtle scale-in on hover
            const menuBtn = document.getElementById('toolsMenuBtn');
            if (menuBtn) {
                menuBtn.addEventListener('mouseenter', () => { if (!_menuIsOpen) gsap.to(menuBtn, { scale: 1.05, duration: 0.13, ease: 'power2.out' }); });
                menuBtn.addEventListener('mouseleave', () => gsap.to(menuBtn, { scale: 1, duration: 0.11, ease: 'power2.in' }));
            }
        }
    }

    function _openToolsMenu(dropdown) {
        if (_menuIsOpen) return;
        _menuIsOpen = true;
        if (!window.gsap) { dropdown.classList.add('open'); return; }
        const items = dropdown.querySelectorAll('.tools-list__item');
        gsap.to(dropdown, { autoAlpha: 1, y: 0, scale: 1, duration: 0.22, ease: 'power3.out' });
        gsap.from(items, { opacity: 0, y: 7, stagger: 0.028, duration: 0.17, ease: 'power2.out', delay: 0.05 });
        gsap.to('#toolsMenuBtn svg', { rotation: 45, duration: 0.2, ease: 'back.out(2)' });
    }

    function setupToolItemClicks() {
        const configBtn = document.getElementById('configAgentBtn');
        if (configBtn) configBtn.addEventListener('click', () => { closeToolsMenu(); openConfigAgentModal(); });

        _thinkingModeBeforeDeepResearch = null;

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
            if (window.gsap) gsap.fromTo(btn, { scale: 0.9 }, { scale: 1, duration: 0.18, ease: 'back.out(2)' });
        } else {
            activeTools.add(name);
            btn.classList.add('active');
            if (window.gsap) gsap.fromTo(btn, { scale: 1.1 }, { scale: 1, duration: 0.22, ease: 'elastic.out(1.2, 0.5)' });
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
        const hiddenTools = new Set(['serpapi-images', 'last30days-research', 'github']);
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
        const out = ['google-search']; // always-on
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
        if (!_menuIsOpen) return;
        _menuIsOpen = false;
        const d = document.getElementById('toolsMenuDropdown');
        if (!d) return;
        if (!window.gsap) { d.classList.remove('open'); return; }
        gsap.to(d, { autoAlpha: 0, y: 10, scale: 0.96, duration: 0.16, ease: 'power3.in' });
        gsap.to('#toolsMenuBtn svg', { rotation: 0, duration: 0.14, ease: 'power2.out' });
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
