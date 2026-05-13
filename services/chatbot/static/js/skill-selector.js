    // SKILL SELECTOR
    // ════════════════════════════════════════════════════════════
    let skillManager = null;

    async function initSkillSelector() {
        try {
            const { SkillManager } = await import(window.__CHAT_ASSET_URLS?.skillManager || '/static/js/modules/skill-manager.js');
            skillManager = new SkillManager();
            await skillManager.init();
            window.skillManager = skillManager;
            window.getActiveSkillId = () => skillManager.getActiveSkillId();
        } catch (err) {
            console.warn('[SkillSelector] Init failed:', err.message);
        }
    }

    // ════════════════════════════════════════════════════════════


if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSkillSelector);
} else {
    initSkillSelector();
}
