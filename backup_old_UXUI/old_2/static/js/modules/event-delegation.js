/**
 * Event Delegation Module
 * Central document-level delegation for click, change, and input events.
 * Replaces inline onclick/onchange/oninput handlers with data-action attributes.
 *
 * Usage:
 *   HTML:  <button data-action="gallery:close">×</button>
 *   JS:    registerAction('click', 'gallery:close', (e, el) => { ... });
 *
 * Special attributes:
 *   data-action-stop   — Prevents ancestor data-action from firing when click
 *                         originates inside this element (replaces event.stopPropagation()).
 *   data-mirror-to     — On input events, mirrors element value to target selector.
 *                         <input data-mirror-to="#tempValue" oninput>
 */

const _registry = {
    click:  {},
    change: {},
    input:  {},
};

/**
 * Register a handler for a data-action value.
 * @param {'click'|'change'|'input'} type  Event type
 * @param {string}                   action  data-action value
 * @param {(e: Event, el: HTMLElement) => void} handler
 */
export function registerAction(type, action, handler) {
    if (!_registry[type]) {
        console.warn(`[Delegation] Unknown event type: ${type}`);
        return;
    }
    _registry[type][action] = handler;
}

/**
 * Register multiple click actions at once.
 * @param {Record<string, (e: Event, el: HTMLElement) => void>} map
 */
export function registerClickActions(map) {
    for (const [action, handler] of Object.entries(map)) {
        _registry.click[action] = handler;
    }
}

/**
 * Initialize document-level event delegation.
 * Call once from DOMContentLoaded.
 */
export function initDelegation() {
    // ── Click delegation ──
    document.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;

        // If click originated inside a [data-action-stop] descendant of this
        // action element, suppress the outer action (but not inner ones).
        const stopper = e.target.closest('[data-action-stop]');
        if (stopper && target.contains(stopper) && stopper !== target) return;

        const action = target.dataset.action;
        const handler = _registry.click[action];
        if (handler) {
            handler(e, target);
        }
    });

    // ── Change delegation ──
    document.addEventListener('change', (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;
        const action = target.dataset.action;
        const handler = _registry.change[action];
        if (handler) {
            handler(e, target);
        }
    });

    // ── Input delegation (data-mirror-to) ──
    document.addEventListener('input', (e) => {
        // Mirror value to target element
        const mirrorTo = e.target.dataset.mirrorTo;
        if (mirrorTo) {
            const dest = document.getElementById(mirrorTo);
            if (dest) dest.textContent = e.target.value;
        }

        // Custom action handler
        const target = e.target.closest('[data-action]');
        if (!target) return;
        const action = target.dataset.action;
        const handler = _registry.input[action];
        if (handler) {
            handler(e, target);
        }
    });
}
