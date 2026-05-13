(function() {
    var entries = [];
    function append(text) {
        entries.push(text);
        if (entries.length > 50) entries.shift();
        var m = document.getElementById('__jsDebugMsg');
        if (m) m.textContent = entries.join('\n');
    }
    function show() {
        var d = document.getElementById('__jsDebugOverlay');
        if (d) d.hidden = false;
    }
    function toggle() {
        var d = document.getElementById('__jsDebugOverlay');
        if (!d) return;
        d.hidden = !d.hidden;
    }
    function isAbortError(err, input, init) {
        var signal = init && init.signal;
        if (!signal && input && typeof input === 'object') signal = input.signal;
        return (signal && signal.aborted) ||
            (err && err.name === 'AbortError') ||
            (err && typeof err.message === 'string' && err.message.indexOf('signal is aborted') !== -1);
    }
    window.addEventListener('error', function(e) {
        append('ERR: ' + (e.message || '') + ' @ ' + (e.filename || '') + ':' + (e.lineno || 0));
        show();
    });
    window.addEventListener('unhandledrejection', function(e) {
        if (isAbortError(e.reason)) return;
        var msg = e.reason && e.reason.message ? e.reason.message : String(e.reason);
        append('REJECT: ' + msg);
        show();
    });
    // Wrap fetch to surface network failures and >=500 responses to the debug panel.
    // Deferred via requestIdleCallback to keep it off the critical paint path.
    var _wrapFetch = function() {
        if (typeof window.fetch === 'function') {
            var _origFetch = window.fetch.bind(window);
            window.fetch = function(input, init) {
                var url = (typeof input === 'string') ? input : (input && input.url) || '';
                return _origFetch(input, init).then(function(res) {
                    if (res && res.status >= 500) {
                        append('HTTP ' + res.status + ' ' + (res.statusText || '') + ' ' + url);
                        show();
                    }
                    return res;
                }).catch(function(err) {
                    if (isAbortError(err, input, init)) {
                        throw err;
                    }
                    append('FETCH ERR: ' + (err && err.message ? err.message : String(err)) + ' ' + url);
                    show();
                    throw err;
                });
            };
        }
    };
    (window.requestIdleCallback || function(cb) { setTimeout(cb, 200); })(_wrapFetch);
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.shiftKey && (e.key === 'D' || e.key === 'd')) {
            e.preventDefault();
            toggle();
        }
    });
    document.addEventListener('click', function(e) {
        if (e.target && e.target.id === '__jsDebugClose') {
            var d = document.getElementById('__jsDebugOverlay');
            if (d) d.hidden = true;
        }
    });
})();
