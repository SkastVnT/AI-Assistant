    // THINKING MODE
    // ════════════════════════════════════════════════════════════
    const _savedMode = localStorage.getItem('thinkingMode');
    let currentThinkingMode = (['instant', 'thinking', 'multi-thinking'].includes(_savedMode)) ? _savedMode : 'instant';

    function initThinkingMode() {
        const btn = document.getElementById('thinkingModeBtn');
        const dropdown = document.getElementById('thinkingModeDropdown');
        const options = document.querySelectorAll('.thinking-mode-option');

        if (!btn || !dropdown) return;

        // Toggle dropdown on click/tap
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const isOpen = !dropdown.classList.contains('hidden');
            // Close all other dropdowns first
            document.querySelectorAll('.model-dropdown.open, .tools-dropdown.open, .topbar__more-dropdown:not(.hidden)').forEach(d => {
                if (d !== dropdown) { d.classList.add('hidden'); d.classList.remove('open'); }
            });
            if (isOpen) {
                dropdown.classList.add('hidden');
                dropdown.classList.remove('open');
            } else {
                dropdown.classList.remove('hidden');
                dropdown.classList.add('open');
            }
        });

        // Close on outside click/tap
        document.addEventListener('click', (e) => {
            if (!btn.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.add('hidden');
                dropdown.classList.remove('open');
            }
        });

        options.forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                selectThinkingMode(option.dataset.mode, option.dataset.icon, option.dataset.label);
                dropdown.classList.add('hidden');
                dropdown.classList.remove('open');
            });
        });

        const saved = document.querySelector(`.thinking-mode-option[data-mode="${currentThinkingMode}"]`);
        if (saved) selectThinkingMode(currentThinkingMode, saved.dataset.icon, saved.dataset.label);
    }

    function selectThinkingMode(mode, icon, label) {
        currentThinkingMode = mode;
        localStorage.setItem('thinkingMode', mode);
        const iconEl = document.getElementById('thinkingModeIcon');
        if (iconEl) {
            iconEl.innerHTML = '<i data-lucide="' + icon + '" class="lucide"></i>';
            if (window.lucide) lucide.createIcons({nodes: [iconEl]});
        }
        const labelEl = document.getElementById('thinkingModeLabel');
        if (labelEl) labelEl.textContent = label;
        const valueEl = document.getElementById('thinkingModeValue');
        if (valueEl) valueEl.value = mode;
        document.querySelectorAll('.thinking-mode-option').forEach(o => {
            o.classList.toggle('active', o.dataset.mode === mode);
        });
        const container = document.getElementById('thinkingModeContainer');
        if (container) container.dataset.thinkingMode = mode;
    }

    window.getThinkingMode = () => currentThinkingMode;
    window.isDeepThinking = () => currentThinkingMode === 'multi-thinking';
    window.selectThinkingMode = selectThinkingMode;

    // ════════════════════════════════════════════════════════════

    // COORDINATED REASONING
    // ════════════════════════════════════════════════════════════
    window.coordinatedReasoning = {
        estimateComplexity(msg) {
            const pats = [/giải thích|explain|why|tại sao/i, /so sánh|compare/i, /phân tích|analyze/i,
                /code|programming|bug|error|lỗi/i, /math|toán|calculate/i, /step by step|từng bước/i];
            let c = 0;
            pats.forEach(p => { if (p.test(msg)) c++; });
            if (msg.length > 200) c++;
            if (msg.length > 500) c++;
            return c;
        },
        autoDecideMode(msg) {
            const mode = window.getThinkingMode ? window.getThinkingMode() : 'instant';
            return mode === 'multi-thinking';
        }
    };

    // ════════════════════════════════════════════════════════════


if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThinkingMode);
} else {
    initThinkingMode();
}
