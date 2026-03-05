/**
 * Language Switcher (Minimal stub)
 * Full implementation available in old_UI/static/js/language-switcher.js
 */

let currentLang = localStorage.getItem('lang') || 'vi';

const translations = {
    vi: {},
    en: {}
};

export function initLanguage() {
    currentLang = localStorage.getItem('lang') || 'vi';
    applyLanguage();
    
    const langBtn = document.getElementById('langBtn');
    if (langBtn) {
        // Lucide icon is set in HTML, just add click handler
        langBtn.addEventListener('click', () => {
            currentLang = currentLang === 'vi' ? 'en' : 'vi';
            localStorage.setItem('lang', currentLang);
            applyLanguage();
        });
    }
}

function applyLanguage() {
    // data-lang-key elements can be extended later
    document.querySelectorAll('[data-lang-key]').forEach(el => {
        // Keep current text as-is (bilingual support is optional)
    });
}

export function getCurrentLang() {
    return currentLang;
}
