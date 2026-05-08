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
 *   panel    — floating tool window, no backdrop, draggable+resizable,
 *              outside-click closes, state preserved (DOM stays mounted)
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
            } else if (entry.type === 'dropdown' || entry.type === 'panel') {
                // For dropdowns / floating panels: close on outside click.
                // The .modal-overlay--panel CSS makes the overlay click-through
                // (pointer-events: none) so any click outside the panel content
                // hits the document and ends up here.
                if (!el.contains(e.target)) {
                    closeOverlay(id);
                }
            }
            // drawers: no auto-close on outside click by default
        }
    });
}

// ── Floating panel mode (drag + resize + persist) ──────────────────

const PANEL_LS_PREFIX = 'panel-mode:';

/**
 * Promote a registered overlay to floating-panel mode.
 * - Adds `.modal-overlay--panel` class for CSS positioning.
 * - Wires drag-by-header and persists position+size in localStorage.
 * - Safe to call multiple times (idempotent).
 *
 * @param {string} id          Overlay element id
 * @param {Object} [opts]
 * @param {string} [opts.handleSelector]  Selector for drag handle inside the panel
 *                                        (default: '.modal-panel__header')
 * @param {string} [opts.contentSelector] Selector for the panel content element
 *                                        (default: first child of overlay)
 */
export function enablePanelMode(id, opts = {}) {
    const overlay = document.getElementById(id);
    if (!overlay) {
        // Element not yet in DOM (lazy-built panels like characterPickerModal,
        // jobQueuePanel). Watch for it once via MutationObserver — runs at most
        // once per registered id.
        if (opts._waiting) return;
        const obs = new MutationObserver(() => {
            if (document.getElementById(id)) {
                obs.disconnect();
                enablePanelMode(id, { ...opts, _waiting: false });
            }
        });
        obs.observe(document.body, { childList: true, subtree: true });
        return;
    }
    if (overlay.dataset.panelMode === '1') return;
    overlay.dataset.panelMode = '1';
    overlay.classList.add('modal-overlay--panel');

    const handleSel = opts.handleSelector || '.modal-panel__header, .character-picker-header, #jobQueueHeader, .jq-header';
    const contentSel = opts.contentSelector || ':scope > .modal-panel, :scope > #jobQueueWindow, :scope > .character-picker-content';

    // If the element itself IS the panel (no overlay wrapper, e.g. jobQueuePanel),
    // mark it standalone so CSS treats it directly as the resizable surface.
    const hasInnerPanel = overlay.querySelector(contentSel);
    if (!hasInnerPanel) {
        overlay.classList.add('is-standalone-panel');
    }

    const findContent = () => overlay.querySelector(contentSel) || overlay;
    const findHandle = () => overlay.querySelector(handleSel);

    // Restore persisted geometry
    const saved = _loadPanelState(id);
    const applyState = () => {
        const content = findContent();
        if (!content) return;
        if (saved) {
            content.style.setProperty('--panel-top', saved.top + 'px');
            content.style.setProperty('--panel-left', saved.left + 'px');
            content.style.setProperty('--panel-tx', '0px'); // clear centering transform
            if (saved.w) content.style.setProperty('--panel-w', saved.w + 'px');
            if (saved.h) content.style.setProperty('--panel-h', saved.h + 'px');
        }
    };
    applyState();

    // Persist size on resize (CSS resize handle)
    const observeSize = () => {
        const content = findContent();
        if (!content) return;
        const ro = new ResizeObserver(() => {
            const rect = content.getBoundingClientRect();
            _savePanelState(id, { ...(_loadPanelState(id) || {}), w: Math.round(rect.width), h: Math.round(rect.height) });
        });
        ro.observe(content);
    };
    observeSize();

    // Drag-by-header
    let dragging = false;
    let startX = 0, startY = 0, startTop = 0, startLeft = 0;
    let dragHandle = null;
    let dragContent = null;

    overlay.addEventListener('pointerdown', (e) => {
        const handle = e.target.closest(handleSel);
        if (!handle || !overlay.contains(handle)) return;
        // Don't start a drag from clicks on close button / form controls inside the header
        if (e.target.closest('button, input, select, textarea, a')) return;
        const content = findContent();
        if (!content) return;
        dragging = true;
        dragHandle = handle;
        dragContent = content;
        const rect = content.getBoundingClientRect();
        startX = e.clientX;
        startY = e.clientY;
        startTop = rect.top;
        startLeft = rect.left;
        // Anchor the panel at its actual screen position before dragging
        // (removes the default -50% centering transform).
        content.style.setProperty('--panel-top', startTop + 'px');
        content.style.setProperty('--panel-left', startLeft + 'px');
        content.style.setProperty('--panel-tx', '0px');
        handle.classList.add('is-dragging');
        try { handle.setPointerCapture(e.pointerId); } catch (_) {}
        e.preventDefault();
    });

    overlay.addEventListener('pointermove', (e) => {
        if (!dragging || !dragContent) return;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        const top = Math.max(0, startTop + dy);
        const left = Math.max(0, startLeft + dx);
        dragContent.style.setProperty('--panel-top', top + 'px');
        dragContent.style.setProperty('--panel-left', left + 'px');
        dragContent.style.setProperty('--panel-tx', '0px');
    });

    const endDrag = (e) => {
        if (!dragging) return;
        dragging = false;
        if (dragHandle) {
            dragHandle.classList.remove('is-dragging');
            try { dragHandle.releasePointerCapture(e.pointerId); } catch (_) {}
        }
        if (dragContent) {
            const rect = dragContent.getBoundingClientRect();
            _savePanelState(id, { ...(_loadPanelState(id) || {}), top: Math.round(rect.top), left: Math.round(rect.left) });
        }
        dragHandle = null;
        dragContent = null;
    };
    overlay.addEventListener('pointerup', endDrag);
    overlay.addEventListener('pointercancel', endDrag);
}

function _savePanelState(id, state) {
    try { localStorage.setItem(PANEL_LS_PREFIX + id, JSON.stringify(state)); } catch (_) {}
}
function _loadPanelState(id) {
    try {
        const raw = localStorage.getItem(PANEL_LS_PREFIX + id);
        return raw ? JSON.parse(raw) : null;
    } catch (_) { return null; }
}
