/**
 * ThinkingPanel — manages the inline collapsible thinking block.
 *
 * The old "side panel that slides from the right" is gone.
 * The thinking block is now an inline .thinking-block element inside the
 * message. Clicking the header expands/collapses it in-place.
 *
 * Public API (unchanged for call-site compatibility):
 *   ThinkingPanel.open(block)    — expand the block
 *   ThinkingPanel.close()        — collapse the current block
 *   ThinkingPanel.toggle(block)  — toggle expand/collapse
 *   ThinkingPanel.onStep(block, stepText, isReasoningChunk, trajectoryId)
 *   ThinkingPanel.onFinalize(block, data)
 */
window.ThinkingPanel = (function () {
    var _currentBlock = null;

    // ── Helpers ────────────────────────────────────────────────
    function _esc(str) {
        var d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    // ── Expand / collapse ──────────────────────────────────────
    function toggle(block) {
        if (!block) return;
        if (block.classList.contains('thinking-block--expanded')) {
            close();
        } else {
            open(block);
        }
    }

    function open(block) {
        if (!block) return;
        // Collapse the previous block if different
        if (_currentBlock && _currentBlock !== block) {
            _currentBlock.classList.remove('thinking-block--expanded');
        }
        _currentBlock = block;
        // Populate content from stepsData if it's empty (first open)
        if (block._contentEl && block._contentEl.children.length === 0 && block._stepsData && block._stepsData.length > 0) {
            _renderContent(block);
        }
        block.classList.add('thinking-block--expanded');
    }

    function close() {
        if (!_currentBlock) return;
        _currentBlock.classList.remove('thinking-block--expanded');
        _currentBlock = null;
    }

    // ── Content rendering ──────────────────────────────────────
    function _renderContent(block) {
        var el = block._contentEl;
        if (!el) return;
        el.innerHTML = '';
        var steps = block._stepsData || [];
        steps.forEach(function (step) { _appendStep(el, step, block._finalized); });
    }

    function _appendStep(container, step, finalized) {
        if (!container) return;
        var el = document.createElement('div');
        var isDone = finalized || step.done;

        if (step.isReasoning) {
            el.className = 'tsp-reasoning' + (isDone ? '' : ' tsp-reasoning--live');
            el.dataset.tid = step.tid || '_default';

            if (isDone && step.text.trim()) {
                var tid = step.tid || '_default';
                var tidMatch = tid.match(/^p(\d+)_t(\d+)$/);
                var label = tidMatch
                    ? ('🔍 Agent ' + (parseInt(tidMatch[2]) + 1) + ' · Phase ' + (parseInt(tidMatch[1]) + 1))
                    : (tid === 'synthesis' ? '✨ Synthesis' : '🔍 Reasoning');

                el.innerHTML =
                    '<div class="tsp-reasoning__header">' +
                        '<span class="tsp-reasoning__label">' + label + '</span>' +
                        '<span class="tsp-reasoning__toggle">▶</span>' +
                    '</div>' +
                    '<div class="tsp-reasoning__body"></div>';

                var body = el.querySelector('.tsp-reasoning__body');
                if (typeof marked !== 'undefined') {
                    var rendered = marked.parse(step.text);
                    if (typeof DOMPurify !== 'undefined') {
                        body.innerHTML = DOMPurify.sanitize(rendered);
                    } else {
                        console.warn('[security] DOMPurify missing — rendering as plain text');
                        body.textContent = step.text;
                    }
                } else {
                    body.textContent = step.text;
                }

                var expanded = false;
                (function (element) {
                    element.querySelector('.tsp-reasoning__header').addEventListener('click', function () {
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
                el.innerHTML =
                    '<div class="tsp-step__title">' + _esc(boldMatch[1]) + '</div>' +
                    (boldMatch[2].trim() ? '<div class="tsp-step__desc">' + _esc(boldMatch[2].trim()) + '</div>' : '');
            } else {
                el.textContent = step.text;
            }
        }
        container.appendChild(el);
    }

    // ── Live step updates during streaming ────────────────────
    function onStep(block, stepText, isReasoningChunk, trajectoryId) {
        // Always append to _contentEl so content builds up even when collapsed.
        // The user will see accumulated steps on expand.
        if (!block || !block._contentEl) return;
        var el = block._contentEl;
        var tid = trajectoryId || '_default';

        if (isReasoningChunk) {
            var liveBlock = el.querySelector('.tsp-reasoning.tsp-reasoning--live[data-tid="' + tid + '"]');
            if (!liveBlock) {
                liveBlock = document.createElement('div');
                liveBlock.className = 'tsp-reasoning tsp-reasoning--live';
                liveBlock.dataset.tid = tid;
                el.appendChild(liveBlock);
            }
            liveBlock.textContent += stepText;
            if (block.classList.contains('thinking-block--expanded')) {
                el.scrollTop = el.scrollHeight;
            }
        } else {
            el.querySelectorAll('.tsp-step--active').forEach(function (s) {
                s.classList.remove('tsp-step--active');
                s.classList.add('tsp-step--done');
            });
            el.querySelectorAll('.tsp-reasoning--live').forEach(function (s) {
                s.classList.remove('tsp-reasoning--live');
            });
            var newStep = document.createElement('div');
            newStep.className = 'tsp-step tsp-step--active';
            var bm = stepText.match(/^\*\*(.+?)\*\*\n?([\s\S]*)$/);
            if (bm) {
                newStep.innerHTML =
                    '<div class="tsp-step__title">' + _esc(bm[1]) + '</div>' +
                    (bm[2].trim() ? '<div class="tsp-step__desc">' + _esc(bm[2].trim()) + '</div>' : '');
            } else {
                newStep.textContent = stepText;
            }
            el.appendChild(newStep);
            if (block.classList.contains('thinking-block--expanded')) {
                el.scrollTop = el.scrollHeight;
            }
        }
    }

    function onFinalize(block, data) {
        // Re-render from finalized _stepsData (all steps now marked done)
        if (block && block.classList.contains('thinking-block--expanded')) {
            _renderContent(block);
        }
    }

    // Escape key collapses the current block
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && _currentBlock) close();
    });

    return { open: open, close: close, toggle: toggle, onStep: onStep, onFinalize: onFinalize };
})();
