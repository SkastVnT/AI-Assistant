/**
 * Overlay Manager Module
 * Unified state management for all overlays: modals, dropdowns, drawers.
 *
 * Convention: every overlay uses a single `.open` CSS class for visibility.
 * CSS handles transitions via opacity/visibility/pointer-events (modals)
 * or display/transform (drawers). No inline style.display toggling.
 *
 * Overlay types:
 *   modal    — centered, has backdrop, Escape closes, click-backdrop closes
 *   dropdown — positioned, no backdrop, Escape closes, outside-click closes
 *   drawer   — side panel, no backdrop, Escape closes (optional)
 *
 * Usage:
 *   registerOverlay('galleryModal', { type: 'modal' });
 *   registerOverlay('modelDropdown', { type: 'dropdown', escClose: true });
 *   openOverlay('galleryModal');
 *   closeOverlay('galleryModal');
 *   toggleOverlay('modelDropdown');
 */

// ── Registry ────────────────────────────────────────────────────────

/** @type {Map<string, OverlayEntry>} */
const _overlays = new Map();

/** Stack of open modal/drawer IDs (most recent on top) for Escape ordering */
const _stack = [];

/**
 * @typedef {Object} OverlayEntry
 * @property {string}   id           Element ID
 * @property {'modal'|'dropdown'|'drawer'} type
 * @property {boolean}  escClose     Close on Escape (default true)
 * @property {boolean}  outsideClose Close on outside click (default: true for modal/dropdown)
 * @property {Function} [onOpen]     Callback after opening
 * @property {Function} [onClose]    Callback after closing
 * @property {Element}  [savedFocus] Element that had focus before opening
 */

/**
 * Register an overlay for unified management.
 * @param {string} id  DOM element id
 * @param {Partial<OverlayEntry>} opts
 */
export function registerOverlay(id, opts = {}) {
    const type = opts.type || 'modal';
    _overlays.set(id, {
        id,
        type,
        escClose:     opts.escClose     !== undefined ? opts.escClose     : true,
        outsideClose: opts.outsideClose !== undefined ? opts.outsideClose : (type !== 'drawer'),
        onOpen:       opts.onOpen  || null,
        onClose:      opts.onClose || null,
        savedFocus:   null,
    });
}

// ── Open / Close / Toggle ───────────────────────────────────────────

/**
 * Open an overlay by id. Adds `.open` class, saves focus, pushes to stack.
 * @param {string} id
 * @param {Object} [extra]  Extra data passed to onOpen callback
 */
export function openOverlay(id, extra) {
    const entry = _overlays.get(id);
    const el = document.getElementById(id);
    if (!el) return;

    // Save focus for restoration
    if (entry) entry.savedFocus = document.activeElement;

    el.classList.add('open');

    // Push onto stack (remove first to avoid duplicates)
    const idx = _stack.indexOf(id);
    if (idx !== -1) _stack.splice(idx, 1);
    _stack.push(id);

    if (entry && entry.onOpen) entry.onOpen(el, extra);
}

/**
 * Close an overlay by id. Removes `.open` class, restores focus, pops stack.
 * @param {string} id
 */
export function closeOverlay(id) {
    const entry = _overlays.get(id);
    const el = document.getElementById(id);
    if (!el) return;

    el.classList.remove('open');

    // Remove from stack
    const idx = _stack.indexOf(id);
    if (idx !== -1) _stack.splice(idx, 1);

    // Restore focus
    if (entry && entry.savedFocus && typeof entry.savedFocus.focus === 'function') {
        entry.savedFocus.focus();
        entry.savedFocus = null;
    }

    if (entry && entry.onClose) entry.onClose(el);
}

/**
 * Toggle an overlay.
 * @param {string} id
 * @param {Object} [extra]
 */
export function toggleOverlay(id, extra) {
    if (isOpen(id)) {
        closeOverlay(id);
    } else {
        openOverlay(id, extra);
    }
}

/**
 * Check if an overlay is currently open.
 * @param {string} id
 * @returns {boolean}
 */
export function isOpen(id) {
    const el = document.getElementById(id);
    return el ? el.classList.contains('open') : false;
}

/**
 * Close the topmost overlay on the stack that has escClose enabled.
 * Called by the global Escape listener.
 * @returns {boolean} true if an overlay was closed
 */
export function closeTopmost() {
    for (let i = _stack.length - 1; i >= 0; i--) {
        const id = _stack[i];
        const entry = _overlays.get(id);
        if (entry && entry.escClose) {
            closeOverlay(id);
            return true;
        }
    }
    return false;
}

// ── Global Listeners ────────────────────────────────────────────────

let _initialized = false;

/**
 * Initialize global Escape and outside-click listeners.
 * Call once from DOMContentLoaded.
 */
export function initOverlayManager() {
    if (_initialized) return;
    _initialized = true;

    // ── Escape key ──
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (closeTopmost()) {
                e.preventDefault();
                e.stopPropagation();
            }
        }
    });

    // ── Outside click (backdrop click for modals, outside for dropdowns) ──
    document.addEventListener('click', (e) => {
        // Process a copy because closing modifies _stack
        const stackCopy = [..._stack];
        for (let i = stackCopy.length - 1; i >= 0; i--) {
            const id = stackCopy[i];
            const entry = _overlays.get(id);
            if (!entry || !entry.outsideClose) continue;

            const el = document.getElementById(id);
            if (!el) continue;

            if (entry.type === 'modal') {
                // For modals: close when clicking the overlay backdrop itself
                if (e.target === el) {
                    closeOverlay(id);
                }
            } else if (entry.type === 'dropdown') {
                // For dropdowns: close when clicking outside the element
                if (!el.contains(e.target)) {
                    closeOverlay(id);
                }
            }
            // drawers: no auto-close on outside click by default
        }
    });
}
