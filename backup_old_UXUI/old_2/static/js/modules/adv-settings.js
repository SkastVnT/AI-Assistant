/**
 * Advanced Model Settings Module
 * Temperature, top-P, max tokens panel with localStorage persistence.
 *
 * Extracted from main.js — no behavior change.
 */

const ADV_STORAGE_KEY = 'adv_model_params';
const DEFAULTS = { temperature: 0.7, temperatureDeep: 0.5, maxTokensDeep: 4096, topP: null };

function loadAdv() {
    try { return Object.assign({}, DEFAULTS, JSON.parse(localStorage.getItem(ADV_STORAGE_KEY) || '{}')); }
    catch { return Object.assign({}, DEFAULTS); }
}

function saveAdv(vals) {
    localStorage.setItem(ADV_STORAGE_KEY, JSON.stringify(vals));
}

function fmt(key, val) {
    if (key === 'topP') return val >= 1 ? 'default' : String(val);
    if (key === 'maxTokensDeep') return String(val);
    return Number(val).toFixed(2);
}

/**
 * Initialize the advanced model settings panel, wire sliders,
 * and expose window.getAdvancedModelParams.
 * Call from DOMContentLoaded.
 */
export function initAdvancedSettings() {
    const panel   = document.getElementById('advSettingsPanel');
    const togBtn  = document.getElementById('advSettingsBtn');
    const resetBtn = document.getElementById('advSettingsReset');

    const sliders = {
        temperature:     document.getElementById('advTemperature'),
        temperatureDeep: document.getElementById('advTemperatureDeep'),
        maxTokensDeep:   document.getElementById('advMaxTokensDeep'),
        topP:            document.getElementById('advTopP'),
    };
    const valueEls = {
        temperature:     document.getElementById('advTemperatureVal'),
        temperatureDeep: document.getElementById('advTemperatureDeepVal'),
        maxTokensDeep:   document.getElementById('advMaxTokensDeepVal'),
        topP:            document.getElementById('advTopPVal'),
    };

    function applyToUI(vals) {
        for (const key of Object.keys(sliders)) {
            const s = sliders[key];
            const e = valueEls[key];
            if (!s || !e) continue;
            const v = (vals[key] != null) ? vals[key] : (key === 'topP' ? 1 : DEFAULTS[key]);
            s.value = v;
            e.textContent = fmt(key, v);
        }
    }

    // Init from storage
    const current = loadAdv();
    applyToUI(current);

    // Wire sliders
    for (const [key, slider] of Object.entries(sliders)) {
        if (!slider) continue;
        slider.addEventListener('input', () => {
            const val = parseFloat(slider.value);
            valueEls[key].textContent = fmt(key, val);
            const saved = loadAdv();
            saved[key] = (key === 'topP' && val >= 1) ? null : val;
            saveAdv(saved);
        });
    }

    // Toggle panel
    if (togBtn && panel) {
        togBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const open = panel.classList.toggle('adv-settings--open');
            panel.setAttribute('aria-hidden', open ? 'false' : 'true');
            togBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
            togBtn.classList.toggle('active', open);
        });
        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!panel.contains(e.target) && e.target !== togBtn) {
                panel.classList.remove('adv-settings--open');
                panel.setAttribute('aria-hidden', 'true');
                togBtn.setAttribute('aria-expanded', 'false');
                togBtn.classList.remove('active');
            }
        });
    }

    // Reset
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            saveAdv(DEFAULTS);
            applyToUI(DEFAULTS);
        });
    }

    // Global getter for sendStreamMessage
    window.getAdvancedModelParams = () => {
        const v = loadAdv();
        return {
            temperature:     v.temperature,
            temperatureDeep: v.temperatureDeep,
            maxTokensDeep:   v.maxTokensDeep,
            topP:            v.topP, // null means "don't send"
        };
    };
}
