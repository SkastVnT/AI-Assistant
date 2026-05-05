/**
 * composer-chips.js — Render an "active character" chip in the composer.
 *
 * Listens for `character:state-changed` (dispatched by character-chip.js
 * after `/api/characters/preview` enrichment) and renders a small chip
 * with thumbnail + name + clear button into #activeCharacterChip.
 *
 * Public API (read-only): none. Side-effects only.
 */
(function () {
    'use strict';

    const CHIP_ID = 'activeCharacterChip';

    function escapeHTML(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function thumbForKey(key) {
        return key
            ? '/api/characters/' + encodeURIComponent(key) + '/thumbnail'
            : null;
    }

    function render(character) {
        const el = document.getElementById(CHIP_ID);
        if (!el) return;
        if (!character || (!character.display_name && !character.canonical_id)) {
            el.style.display = 'none';
            el.innerHTML = '';
            return;
        }
        const name = character.display_name || character.canonical_id || 'character';
        const series = character.series_name || '';
        const thumb = character.preview_url || thumbForKey(character.key);
        const flagsBits = [];
        if (character.safe_to_attach_lora === false) flagsBits.push('LoRA off');
        if (character.needs_review) flagsBits.push('needs review');
        const flags = flagsBits.length
            ? '<span class="chip__flag">' + flagsBits.map(escapeHTML).join(' · ') + '</span>'
            : '';
        const thumbHtml = thumb
            ? '<img class="chip__thumb" src="' + escapeHTML(thumb) + '" alt="" loading="lazy" />'
            : '<span class="chip__thumb chip__thumb--placeholder">?</span>';
        el.innerHTML =
            thumbHtml +
            '<div class="chip__body">' +
                '<span class="chip__name">' + escapeHTML(name) + '</span>' +
                (series
                    ? '<span class="chip__series">' + escapeHTML(series) + '</span>'
                    : '') +
                flags +
            '</div>' +
            '<button type="button" class="chip__clear" aria-label="Bỏ chọn">×</button>';
        el.style.display = '';
        const clearBtn = el.querySelector('.chip__clear');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                window.selectedCharacter = null;
                document.body.removeAttribute('data-character-key');
                document.body.removeAttribute('data-series-key');
                document.dispatchEvent(new CustomEvent('character:state-changed', {
                    detail: { character: null },
                }));
            });
        }
    }

    document.addEventListener('character:state-changed', (ev) => {
        const ch = ev && ev.detail ? ev.detail.character : null;
        render(ch);
    });

    // Initial paint in case state was set before this module loaded.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => render(window.selectedCharacter));
    } else {
        render(window.selectedCharacter);
    }
})();
