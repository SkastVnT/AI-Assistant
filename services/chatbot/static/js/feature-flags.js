try {
    if (window.innerWidth > 768 && !localStorage.getItem('sidebarFixApplied_v1')) {
        localStorage.removeItem('sidebarCollapsed');
        localStorage.setItem('sidebarFixApplied_v1', '1');
    }
} catch(e) {}

// Runtime feature flags (override via localStorage or window.__CHAT_FEATURES)
try {
    const storedFlags = JSON.parse(localStorage.getItem('chatFeatureFlags') || '{}');
    window.__CHAT_FEATURES = {
        tokenGauge: true,
        collapsibleThinking: false,
        suggestionChips: true,
        selectAndReply: true,
        codeCopy: true,
        ...storedFlags,
        ...(window.__CHAT_FEATURES || {}),
        collapsibleThinking: false,
    };
} catch (e) {
    window.__CHAT_FEATURES = {
        tokenGauge: true,
        collapsibleThinking: false,
        suggestionChips: true,
        selectAndReply: true,
        codeCopy: true,
    };
}
