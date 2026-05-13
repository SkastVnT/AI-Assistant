    // Topbar Tools dropdown + character picker / job queue / local-img / anime
    // bindings. Buttons use real IDs (imageGenV2Btn, animePipelineBtn,
    // characterPickerBtn, jobQueueBtn, videoGenBtn) so existing JS listeners
    // (main.js video-gen modal, image-gen-v2 init, character-chip glue) keep
    // working without changes.
    (function () {
        // ── Tools dropdown toggle ─────────────────────────────────────
        const toolsBtn = document.getElementById('topbarToolsBtn');
        const toolsDropdown = document.getElementById('topbarToolsDropdown');
        if (toolsBtn && toolsDropdown) {
            toolsBtn.addEventListener('click', (ev) => {
                ev.stopPropagation();
                const open = !toolsDropdown.classList.contains('hidden');
                if (open) {
                    toolsDropdown.classList.add('hidden');
                    toolsBtn.setAttribute('aria-expanded', 'false');
                } else {
                    toolsDropdown.classList.remove('hidden');
                    toolsBtn.setAttribute('aria-expanded', 'true');
                }
            });
            // Close-on-outside-click + on item click.
            document.addEventListener('click', (ev) => {
                if (!toolsDropdown.classList.contains('hidden')
                    && !toolsDropdown.contains(ev.target)
                    && ev.target !== toolsBtn
                    && !toolsBtn.contains(ev.target)) {
                    toolsDropdown.classList.add('hidden');
                    toolsBtn.setAttribute('aria-expanded', 'false');
                }
            });
            toolsDropdown.addEventListener('click', (ev) => {
                if (ev.target.closest('.topbar__more-item')) {
                    toolsDropdown.classList.add('hidden');
                    toolsBtn.setAttribute('aria-expanded', 'false');
                }
            });
        }

        // ── Character picker entry-point.
        // NOTE: character-chip.js wires the SAME #characterPickerBtn for the
        // inline picker + preview enrichment. We only register a fallback
        // here so a click still works if character-chip.js is missing or
        // the inline flow is unavailable. character-chip.js's listener is
        // registered first and stops propagation when it succeeds.
        const localImgBtn = document.getElementById('localImageGenBtn');
        if (localImgBtn) {
            localImgBtn.addEventListener('click', () => {
                if (typeof window.openLocalImageGen !== 'function') {
                    console.warn('[local-image-gen] module not loaded');
                    return;
                }
                window.openLocalImageGen();
            });
        }
        const queueBtn = document.getElementById('jobQueueBtn');
        if (queueBtn) {
            queueBtn.addEventListener('click', () => {
                if (typeof window.openJobQueuePanel !== 'function') {
                    console.warn('[job-queue] module not loaded');
                    return;
                }
                window.openJobQueuePanel();
            });
        }
        // Anime Pipeline topbar entry — kicks off the inline chat flow so
        // the user sees the same reasoning pill + layer gallery as when the
        // pipeline auto-triggers from a chat message.
        const apBtn = document.getElementById('animePipelineBtn');
        if (apBtn) {
            apBtn.addEventListener('click', () => {
                const ap = window.chatApp?.animePipeline;
                if (!ap) {
                    console.warn('[anime-pipeline] AnimePipeline not initialized yet');
                    return;
                }
                const inputEl = document.getElementById('messageInput');
                const prefill = (inputEl?.value || '').trim();
                if (prefill && typeof ap.openModalWithPrompt === 'function') {
                    ap.openModalWithPrompt(prefill);
                    if (inputEl) inputEl.value = '';
                } else if (typeof ap.openModal === 'function') {
                    ap.openModal();
                } else {
                    console.warn('[anime-pipeline] no openModal entry-point found');
                }
            });
        }
        // Listen for character:selected to refresh icons
        document.addEventListener('character:selected', () => {
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        });
    })();
