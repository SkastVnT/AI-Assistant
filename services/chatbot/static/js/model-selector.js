    // ════════════════════════════════════════════════════════════
    // MODEL SELECTOR (dropdown)
    // ════════════════════════════════════════════════════════════
    (function() {
        const btn = document.getElementById('modelSelectorBtn');
        const dropdown = document.getElementById('modelDropdown');
        const label = document.getElementById('modelSelectorLabel');
        const hiddenSelect = document.getElementById('modelSelect');
        if (!btn || !dropdown) return;
        const items = dropdown.querySelectorAll('.model-dropdown__item');

        const modelLabels = {
            'grok': 'Grok-3 Mini',
            'deepseek-reasoner': 'DeepSeek R1',
            'openai': 'GPT-4o-mini',
            'deepseek': 'DeepSeek Chat',
            'gemini': 'Gemini 2.5 Flash',
            'step-flash': 'Step-3.5 Flash',
            'laguna': 'Laguna XS.2',
            'r1-free': 'DeepSeek R1 (Free)',
            'hermes3': 'Hermes 3 405B',
            'lyria': 'Lyria 3 Pro',
            'nemotron-super': 'Nemotron 3 Super 120B',
            'owl-alpha': 'Owl Alpha',
            'stepfun': 'StepFun Direct'
        };

        // Best value ranking (quality × 1/cost, June 2025)
        const MODEL_PRIORITY = [
            'grok',             // Grok-3 Mini — default pick
            'gemini',           // Gemini 2.5 Flash — $0.15/1M, top tier speed+quality
            'deepseek',         // DeepSeek Chat — very cheap, strong multilingual
            'openai',           // GPT-4o-mini — reliable, cheap
            'step-flash',       // Step-3.5 Flash — fast + free
            'r1-free',          // DeepSeek R1 Free — free but rate-limited
            'deepseek-reasoner',// DeepSeek R1 — pricier reasoning
        ];

        const STORAGE_KEY = 'ai_selected_model';

        function applyModel(modelId, saveToStorage = true) {
            const name = modelLabels[modelId] || modelId;
            label.textContent = name;
            hiddenSelect.value = modelId;
            hiddenSelect.dispatchEvent(new Event('change'));
            items.forEach(i => {
                i.classList.toggle('active', i.dataset.model === modelId);
            });
            if (saveToStorage) {
                try { localStorage.setItem(STORAGE_KEY, modelId); } catch (_) {}
            }
        }

        // Auto-select on load: restore saved preference or pick best-value
        (function autoSelect() {
            let saved = null;
            try { saved = localStorage.getItem(STORAGE_KEY); } catch (_) {}

            const availableIds = new Set([...items].map(i => i.dataset.model));

            if (saved && availableIds.has(saved)) {
                applyModel(saved, false);
                return;
            }

            const best = MODEL_PRIORITY.find(id => availableIds.has(id));
            if (best) applyModel(best, true);
        })();

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('open');
            btn.classList.toggle('open');
        });

        document.addEventListener('click', () => {
            dropdown.classList.remove('open');
            btn.classList.remove('open');
        });

        items.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                applyModel(item.dataset.model, true);
                dropdown.classList.remove('open');
                btn.classList.remove('open');
            });
        });
    })();

    // ════════════════════════════════════════════════════════════
