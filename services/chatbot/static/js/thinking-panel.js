window.ThinkingPanel = (function() {
    var _panel = null, _panelBody = null, _panelTitle = null, _currentPill = null;

    function _init() {
        _panel = document.getElementById('thinkingSidePanel');
        _panelBody = document.getElementById('thinkingPanelBody');
        _panelTitle = document.getElementById('thinkingPanelTitle');
        var closeBtn = document.getElementById('thinkingPanelClose');
        if (closeBtn) closeBtn.addEventListener('click', close);
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && _panel && _panel.classList.contains('thinking-side-panel--open')) close();
        });
    }

    function open(pill) {
        if (!_panel) _init();
        if (!_panel) return;
        _currentPill = pill;
        _renderContent(pill);
        _panel.classList.add('thinking-side-panel--open');
        _panel.removeAttribute('aria-hidden');
        var closeBtn = document.getElementById('thinkingPanelClose');
        if (closeBtn) { closeBtn.removeAttribute('tabindex'); closeBtn.removeAttribute('aria-hidden'); }
        document.querySelectorAll('.thinking-pill--panel-open').forEach(function(p) { p.classList.remove('thinking-pill--panel-open'); });
        pill.classList.add('thinking-pill--panel-open');
    }

    function close() {
        if (!_panel) return;
        _panel.classList.remove('thinking-side-panel--open');
        _panel.setAttribute('aria-hidden', 'true');
        var closeBtn = document.getElementById('thinkingPanelClose');
        if (closeBtn) { closeBtn.setAttribute('tabindex', '-1'); closeBtn.setAttribute('aria-hidden', 'true'); }
        if (_currentPill) {
            _currentPill.classList.remove('thinking-pill--panel-open');
            _currentPill = null;
        }
    }

    function _esc(str) {
        var d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    function _renderContent(pill) {
        if (!_panelBody) return;
        _panelBody.innerHTML = '';
        var steps = pill._stepsData || [];
        var dur = pill._durationMs ? (pill._durationMs / 1000).toFixed(1) + 's' : '';
        if (_panelTitle) {
            _panelTitle.textContent = pill._finalized
                ? (pill._summary || ('Thought. ' + dur))
                : 'Thinking...';
        }
        steps.forEach(function(step) { _appendStep(step, pill._finalized); });
    }

    function _appendStep(step, finalized) {
        if (!_panelBody) return;
        var el = document.createElement('div');
        var isDone = finalized || step.done;
        if (step.isReasoning) {
            el.className = 'tsp-reasoning' + (isDone ? '' : ' tsp-reasoning--live');
            el.dataset.tid = step.tid || '_default';
            if (isDone && step.text.trim()) {
                var tid = step.tid || '_default';
                var tidMatch = tid.match(/^r(\d+)_t(\d+)$/);
                var label = tidMatch
                    ? ('🔍 Direction ' + (parseInt(tidMatch[2]) + 1) + ' (round ' + (parseInt(tidMatch[1]) + 1) + ')')
                    : '🔍 Reasoning';
                el.innerHTML = '<div class="tsp-reasoning__header"><span class="tsp-reasoning__label">' + label + '</span><span class="tsp-reasoning__toggle">▶</span></div><div class="tsp-reasoning__body"></div>';
                var body = el.querySelector('.tsp-reasoning__body');
                if (typeof marked !== 'undefined') {
                    var rendered = marked.parse(step.text);
                    // SECURITY: refuse to inject un-sanitized HTML. Plain-text
                    // fallback if DOMPurify did not load.
                    if (typeof DOMPurify !== 'undefined') {
                        body.innerHTML = DOMPurify.sanitize(rendered);
                    } else {
                        console.warn('[security] DOMPurify missing — rendering reasoning step as plain text');
                        body.textContent = step.text;
                    }
                } else {
                    body.textContent = step.text;
                }
                var expanded = false;
                (function(element) {
                    element.querySelector('.tsp-reasoning__header').addEventListener('click', function() {
                        expanded = !expanded;
                        element.classList.toggle('tsp-reasoning--expanded', expanded);
                        element.querySelector('.tsp-reasoning__toggle').textContent = expanded ? '▼' : '▶';
                    });
                })(el);
            } else {
                el.textContent = step.text;
            }
        } else {
            el.className = 'tsp-step' + (isDone ? ' tsp-step--done' : ' tsp-step--active');
            var boldMatch = step.text.match(/^\*\*(.+?)\*\*\n?([\s\S]*)$/);
            if (boldMatch) {
                el.innerHTML = '<div class="tsp-step__title">' + _esc(boldMatch[1]) + '</div>' +
                    (boldMatch[2].trim() ? '<div class="tsp-step__desc">' + _esc(boldMatch[2].trim()) + '</div>' : '');
            } else {
                el.textContent = step.text;
            }
        }
        _panelBody.appendChild(el);
    }

    function onStep(pill, stepText, isReasoningChunk, trajectoryId) {
        if (_currentPill !== pill || !_panelBody) return;
        var tid = trajectoryId || '_default';
        if (isReasoningChunk) {
            var block = _panelBody.querySelector('.tsp-reasoning.tsp-reasoning--live[data-tid="' + tid + '"]');
            if (!block) {
                block = document.createElement('div');
                block.className = 'tsp-reasoning tsp-reasoning--live';
                block.dataset.tid = tid;
                _panelBody.appendChild(block);
            }
            block.textContent += stepText;
        } else {
            _panelBody.querySelectorAll('.tsp-step--active').forEach(function(el) {
                el.classList.remove('tsp-step--active');
                el.classList.add('tsp-step--done');
            });
            _panelBody.querySelectorAll('.tsp-reasoning--live').forEach(function(el) {
                el.classList.remove('tsp-reasoning--live');
            });
            var el2 = document.createElement('div');
            el2.className = 'tsp-step tsp-step--active';
            var bm = stepText.match(/^\*\*(.+?)\*\*\n?([\s\S]*)$/);
            if (bm) {
                el2.innerHTML = '<div class="tsp-step__title">' + _esc(bm[1]) + '</div>' +
                    (bm[2].trim() ? '<div class="tsp-step__desc">' + _esc(bm[2].trim()) + '</div>' : '');
            } else {
                el2.textContent = stepText;
            }
            _panelBody.appendChild(el2);
        }
    }

    function onFinalize(pill, data) {
        if (_currentPill !== pill || !_panelBody) return;
        var dur = data.duration_ms ? (data.duration_ms / 1000).toFixed(1) + 's' : '';
        if (_panelTitle) _panelTitle.textContent = data.summary || ('Thought. ' + dur);
        _renderContent(pill);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }

    return { open: open, close: close, onStep: onStep, onFinalize: onFinalize };
})();
