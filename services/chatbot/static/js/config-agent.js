    // CONFIG AGENT
    // ════════════════════════════════════════════════════════════
    const defaultAgentConfig = {
        enabled: false, systemPrompt: '', injectionPrompt: '', contextPrompt: '',
        temperature: 0.7, topP: 0.9, tokenLimit: 4096, thinkingBudget: 'off'
    };

    function loadAgentConfig() {
        const storedAgentConfig = localStorage.getItem('agentConfig');
        if (!storedAgentConfig) return {...defaultAgentConfig};

        try {
            return JSON.parse(storedAgentConfig) || {...defaultAgentConfig};
        } catch (error) {
            return {...defaultAgentConfig};
        }
    }

    let agentConfig = loadAgentConfig();
    window.getAgentConfig = () => (!agentConfig || !agentConfig.enabled) ? null : agentConfig;
    window.agentConfig = agentConfig;

    function openConfigAgentModal() {
        const m = document.getElementById('configAgentModal');
        document.getElementById('configAgentEnabled').checked = agentConfig.enabled;
        document.getElementById('configSystemPrompt').value = agentConfig.systemPrompt || '';
        document.getElementById('configInjectionPrompt').value = agentConfig.injectionPrompt || '';
        document.getElementById('configContextPrompt').value = agentConfig.contextPrompt || '';
        document.getElementById('configTemperature').value = agentConfig.temperature;
        document.getElementById('tempValue').textContent = agentConfig.temperature;
        document.getElementById('configTopP').value = agentConfig.topP;
        document.getElementById('topPValue').textContent = agentConfig.topP;
        document.getElementById('configTokenLimit').value = agentConfig.tokenLimit;
        document.getElementById('tokenLimitValue').textContent = agentConfig.tokenLimit;
        document.querySelectorAll('input[name="thinkingBudget"]').forEach(r => r.checked = r.value === agentConfig.thinkingBudget);
        toggleConfigAgent();
        m.classList.add('open');
    }

    function closeConfigAgentModal() {
        document.getElementById('configAgentModal').classList.remove('open');
    }

    function toggleConfigAgent() {
        const enabled = document.getElementById('configAgentEnabled').checked;
        const fields = document.getElementById('configAgentFields');
        fields.style.opacity = enabled ? '1' : '0.5';
        fields.style.pointerEvents = enabled ? 'auto' : 'none';
        agentConfig.enabled = enabled;
        window.agentConfig = agentConfig;
        localStorage.setItem('agentConfig', JSON.stringify(agentConfig));
    }

    function saveConfigAgent() {
        agentConfig = {
            enabled: document.getElementById('configAgentEnabled').checked,
            systemPrompt: document.getElementById('configSystemPrompt').value.trim(),
            injectionPrompt: document.getElementById('configInjectionPrompt').value.trim(),
            contextPrompt: document.getElementById('configContextPrompt').value.trim(),
            temperature: parseFloat(document.getElementById('configTemperature').value),
            topP: parseFloat(document.getElementById('configTopP').value),
            tokenLimit: parseInt(document.getElementById('configTokenLimit').value),
            thinkingBudget: document.querySelector('input[name="thinkingBudget"]:checked')?.value || 'off'
        };
        localStorage.setItem('agentConfig', JSON.stringify(agentConfig));
        window.agentConfig = agentConfig;
        closeConfigAgentModal();
    }

    function resetConfigAgent() {
        if (!confirm('Reset?')) return;
        agentConfig = {...defaultAgentConfig};
        localStorage.removeItem('agentConfig');
        window.agentConfig = agentConfig;
        openConfigAgentModal();
    }

    // ════════════════════════════════════════════════════════════


window.openConfigAgentModal = openConfigAgentModal;
window.closeConfigAgentModal = closeConfigAgentModal;
window.toggleConfigAgent = toggleConfigAgent;
window.saveConfigAgent = saveConfigAgent;
window.resetConfigAgent = resetConfigAgent;

function initThinkingBudgetRadios() {
    document.querySelectorAll('input[name="thinkingBudget"]').forEach(radio => {
        radio.addEventListener('change', () => {
            radio.closest('[style*="grid"]')?.querySelectorAll('label').forEach(l => {
                l.style.borderColor = l.querySelector('input:checked') ? 'var(--accent)' : 'transparent';
            });
        });
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThinkingBudgetRadios);
} else {
    initThinkingBudgetRadios();
}
