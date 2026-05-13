(function () {
    // 1) Toggle "More…" sections inside the tools dropdown.
    document.addEventListener('click', function (e) {
        var t = e.target.closest && e.target.closest('.tools-list__more-toggle');
        if (!t) return;
        e.preventDefault();
        e.stopPropagation();
        var list = t.parentElement;
        var more = list && list.querySelector('.tools-list__more');
        if (!more) return;
        var open = !more.hasAttribute('hidden');
        if (open) {
            more.setAttribute('hidden', '');
            t.textContent = 'More\u2026';
        } else {
            more.removeAttribute('hidden');
            t.textContent = 'Less';
        }
    });

    // 2) Inline quick-tool delegates clicks to the underlying dropdown button.
    document.addEventListener('click', function (e) {
        var q = e.target.closest && e.target.closest('.quick-tool');
        if (!q) return;
        var id = q.dataset && q.dataset.target;
        var target = id && document.getElementById(id);
        if (!target) return;
        e.preventDefault();
        e.stopPropagation();
        target.click();
    });

    // 2b) Proxy buttons inside the tools dropdown delegate to the real wired button
    //     elsewhere in the DOM (topbar/sidebar). Existing main.js bindings stay intact.
    document.addEventListener('click', function (e) {
        var p = e.target.closest && e.target.closest('.tools-list__item.is-proxy[data-proxy]');
        if (!p) return;
        var id = p.dataset && p.dataset.proxy;
        var target = id && document.getElementById(id);
        if (!target) return;
        e.preventDefault();
        e.stopPropagation();
        target.click();
    });

    // 3) Mirror `.active` class from the underlying button onto the quick-tool.
    function syncQuickActive() {
        document.querySelectorAll('.quick-tool').forEach(function (q) {
            var target = document.getElementById(q.dataset.target);
            if (!target) return;
            q.classList.toggle('active', target.classList.contains('active'));
        });
    }
    function wireMirroring() {
        var observer = new MutationObserver(syncQuickActive);
        document.querySelectorAll('.quick-tool').forEach(function (q) {
            var target = document.getElementById(q.dataset.target);
            if (target) observer.observe(target, { attributes: true, attributeFilter: ['class'] });
        });
        syncQuickActive();
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wireMirroring);
    } else {
        wireMirroring();
    }
})();
