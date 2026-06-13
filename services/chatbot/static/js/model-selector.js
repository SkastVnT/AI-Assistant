    // ════════════════════════════════════════════════════════════
    // MODEL SELECTOR (dropdown)
    // ════════════════════════════════════════════════════════════
    (function() {
        const btn = document.getElementById('modelSelectorBtn');
        const dropdown = document.getElementById('modelDropdown');
        const label = document.getElementById('modelSelectorLabel');
        const hiddenSelect = document.getElementById('modelSelect');
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
                const model = item.dataset.model;
                items.forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                label.textContent = modelLabels[model] || model;
                hiddenSelect.value = model;
                hiddenSelect.dispatchEvent(new Event('change'));
                dropdown.classList.remove('open');
                btn.classList.remove('open');
            });
        });
    })();

    // ════════════════════════════════════════════════════════════
