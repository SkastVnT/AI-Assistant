/* stream-guard.js — Phase 4 lightweight stream safety on top of main.js.
 *
 * Goals (no rewrite of main.js, no /chat/stream contract change):
 *   1. Prevent send while a stream is in-flight.
 *   2. Track currentStreamId so late events from a previous stream are ignored.
 *   3. Surface dropped/late events to the debug overlay (Ctrl+Shift+D).
 *
 * Detection of "streaming":
 *   - Primary signal: window.chatApp.currentAbortController != null (set by main.js).
 *   - Fallback signal: '#loading' is visible.
 *   - Body gets [data-streaming="true"] for CSS hooks.
 *
 * This module never imports main.js or api-service.js. It listens with
 * capture-phase handlers and DOM observation only, so it stays additive.
 */
(function () {
    'use strict';

    var streamId = 0;            // monotonically increasing
    var streamingActive = false;
    var lastBlockedAt = 0;

    function debug(msg) {
        try {
            if (window.console && console.debug) console.debug('[stream-guard]', msg);
        } catch (_) {}
    }

    function isStreaming() {
        var app = window.chatApp;
        if (app && app.currentAbortController) return true;
        var loading = document.getElementById('loading');
        if (loading && loading.style.display !== 'none' && !loading.classList.contains('hidden')) {
            return true;
        }
        return false;
    }

    function setBodyFlag(on) {
        if (on === streamingActive) return;
        streamingActive = on;
        document.body && document.body.setAttribute('data-streaming', on ? 'true' : 'false');
        if (on) {
            streamId += 1;
            window.__currentStreamId = streamId;
            debug('stream start #' + streamId);
        } else {
            debug('stream end #' + streamId);
        }
    }

    function tick() {
        setBodyFlag(isStreaming());
    }

    function toast(message) {
        // Reuse existing toast helper if available, else fall back to console.
        try {
            if (window.uiUtils && typeof window.uiUtils.showToast === 'function') {
                window.uiUtils.showToast(message, 'warning');
                return;
            }
            if (window.chatApp && window.chatApp.uiUtils && typeof window.chatApp.uiUtils.showToast === 'function') {
                window.chatApp.uiUtils.showToast(message, 'warning');
                return;
            }
        } catch (_) {}
        debug(message);
    }

    function guardSend(e) {
        var sendBtn = e.target && e.target.closest && e.target.closest('#sendBtn');
        if (!sendBtn) return;
        if (!isStreaming()) return;
        // Throttle the toast so the user doesn't get spam on accidental double-clicks.
        var now = Date.now();
        if (now - lastBlockedAt > 1500) {
            toast('Already streaming — please wait or press Stop.');
            lastBlockedAt = now;
        }
        e.preventDefault();
        e.stopPropagation();
    }

    function guardEnterKey(e) {
        if (e.key !== 'Enter' || e.shiftKey) return;
        if (e.target && e.target.id !== 'messageInput') return;
        if (!isStreaming()) return;
        var now = Date.now();
        if (now - lastBlockedAt > 1500) {
            toast('Already streaming — please wait or press Stop.');
            lastBlockedAt = now;
        }
        e.preventDefault();
        e.stopPropagation();
    }

    function init() {
        // Capture phase so we run before main.js's bound listeners.
        document.addEventListener('click', guardSend, true);
        document.addEventListener('keydown', guardEnterKey, true);

        // Poll the streaming state from main.js's controller every 200 ms.
        setInterval(tick, 200);

        // Public surface for other modules to query / publish stream ids.
        window.streamGuard = Object.freeze({
            get currentStreamId() { return streamId; },
            get isStreaming() { return streamingActive; },
            // Late-event filter helper. Returns true when an event id is too old.
            isStale: function (eventStreamId) {
                if (typeof eventStreamId !== 'number') return false;
                return eventStreamId < streamId;
            }
        });
        debug('initialised');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
