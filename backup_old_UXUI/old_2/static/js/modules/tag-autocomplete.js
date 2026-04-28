/**
 * tag-autocomplete.js — danbooru/e621 prompt tag autocomplete dropdown.
 *
 * Attaches to the chat `messageInput` textarea and, while typing, shows a
 * small dropdown of popular booru tags that match the current word. The
 * datasource is `/api/tags/autocomplete` backed by the Character Select
 * SAA database (221k+ tags sorted by post_count).
 *
 * Activation:
 *   - Only triggers when the textarea value looks like an image-gen prompt
 *     (starts with "tạo ảnh", "vẽ", "draw", or contains booru separators
 *     `,` / `;`). Plain chat messages never see the dropdown.
 *   - Minimum 2 characters before a lookup fires.
 *   - Keyboard: ↑/↓ to highlight, Tab or Enter to accept, Esc to dismiss.
 *   - Mouse: hover + click.
 *
 * Public API:
 *   attachTagAutocomplete(textarea) – idempotent, safe to call once on boot.
 */

const IMAGE_PROMPT_RE = /^\s*(t[aạ]o\s?[aả]nh|v[ẽe]|draw|generate|make\s+(a\s+)?(picture|image)|create\s+(an?\s+)?image)/i;
const BOORU_SEPARATORS = /[,;]/;
const DEBOUNCE_MS = 120;
const MIN_CHARS = 2;
const MAX_RESULTS = 12;

const CATEGORY_LABELS = {
    0: 'gen', 1: 'art', 3: 'copy', 4: 'char', 5: 'meta',
};
const CATEGORY_COLORS = {
    0: '#8ab4ff', 1: '#ff6b6b', 3: '#b794f4', 4: '#68d391', 5: '#f6e05e',
};

let styleInjected = false;

function injectStyles() {
    if (styleInjected) return;
    styleInjected = true;
    const css = `
.tag-autocomplete-dropdown {
  position: absolute; z-index: 9999;
  min-width: 320px; max-width: 480px; max-height: 280px;
  overflow-y: auto;
  background: var(--bg-secondary, #1e1e2e);
  border: 1px solid var(--border, #333);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  font-size: 13px;
  padding: 4px 0;
}
.tag-autocomplete-dropdown[hidden] { display: none; }
.tac-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 10px; cursor: pointer; color: var(--text, #eee);
  gap: 8px; line-height: 1.3;
}
.tac-item:hover, .tac-item.active { background: rgba(138,180,255,0.15); }
.tac-tag { font-family: ui-monospace, monospace; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tac-cat { font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 3px; color: #000; }
.tac-count { color: var(--text-muted, #888); font-size: 11px; font-variant-numeric: tabular-nums; }
.tac-empty { padding: 8px 10px; color: var(--text-muted, #888); font-style: italic; }
.tac-hint { padding: 4px 10px; border-top: 1px solid var(--border, #333); color: var(--text-muted, #888); font-size: 11px; }
`;
    const el = document.createElement('style');
    el.textContent = css;
    document.head.appendChild(el);
}

function shouldActivate(value, cursor) {
    if (!value) return false;
    if (IMAGE_PROMPT_RE.test(value)) return true;
    // Commas strongly indicate booru-style tag lists.
    if (BOORU_SEPARATORS.test(value)) return true;
    return false;
}

function currentWord(value, cursor) {
    // Word is bounded by comma / newline / start.
    let start = cursor;
    while (start > 0 && !/[,;\n]/.test(value[start - 1])) start--;
    while (start < cursor && /\s/.test(value[start])) start++;
    const word = value.slice(start, cursor);
    return { word, start, end: cursor };
}

async function fetchSuggestions(prefix) {
    const url = `/api/tags/autocomplete?q=${encodeURIComponent(prefix)}&limit=${MAX_RESULTS}`;
    try {
        const res = await fetch(url, { credentials: 'same-origin' });
        if (!res.ok) return [];
        const data = await res.json();
        return Array.isArray(data.tags) ? data.tags : [];
    } catch (e) {
        return [];
    }
}

function formatCount(n) {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'k';
    return String(n);
}

export function attachTagAutocomplete(textarea) {
    if (!textarea || textarea.dataset.tacAttached === '1') return;
    textarea.dataset.tacAttached = '1';
    injectStyles();

    const dropdown = document.createElement('div');
    dropdown.className = 'tag-autocomplete-dropdown';
    dropdown.hidden = true;
    dropdown.setAttribute('role', 'listbox');
    document.body.appendChild(dropdown);

    let items = [];
    let highlight = -1;
    let activeRange = null;
    let debounceTimer = null;
    let lastQuery = '';

    function hide() {
        dropdown.hidden = true;
        items = []; highlight = -1; activeRange = null; lastQuery = '';
    }

    function positionDropdown() {
        const rect = textarea.getBoundingClientRect();
        dropdown.style.left = `${window.scrollX + rect.left}px`;
        dropdown.style.top = `${window.scrollY + rect.bottom + 4}px`;
        dropdown.style.maxWidth = `${Math.max(320, rect.width)}px`;
    }

    function render() {
        if (!items.length) {
            dropdown.innerHTML = `<div class="tac-empty">Không có gợi ý</div>`;
            return;
        }
        const rows = items.map((t, i) => {
            const cat = CATEGORY_LABELS[t.category] || 'tag';
            const col = CATEGORY_COLORS[t.category] || '#8ab4ff';
            const active = i === highlight ? 'active' : '';
            return `<div class="tac-item ${active}" data-idx="${i}" role="option">
                <span class="tac-cat" style="background:${col};">${cat}</span>
                <span class="tac-tag">${t.tag}</span>
                <span class="tac-count">${formatCount(t.post_count || 0)}</span>
            </div>`;
        }).join('');
        dropdown.innerHTML = rows
            + `<div class="tac-hint">Tab/Enter = chọn · Esc = đóng · SAA DB</div>`;
    }

    function accept(idx) {
        if (idx < 0 || idx >= items.length || !activeRange) return;
        const t = items[idx];
        const value = textarea.value;
        const { start, end } = activeRange;
        const before = value.slice(0, start);
        const after = value.slice(end);
        // Insert tag (space form, not underscore — SDXL-friendly)
        const insert = t.tag.replace(/_/g, ' ');
        // If next char isn't a separator, append ", " for convenience
        const needsSep = !/^[\s,;]/.test(after);
        const tail = needsSep ? ', ' : '';
        textarea.value = before + insert + tail + after;
        const caret = (before + insert + tail).length;
        textarea.setSelectionRange(caret, caret);
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        hide();
    }

    async function refresh() {
        const cursor = textarea.selectionStart;
        const value = textarea.value;
        if (!shouldActivate(value, cursor)) { hide(); return; }
        const { word, start, end } = currentWord(value, cursor);
        const prefix = word.trim();
        if (prefix.length < MIN_CHARS) { hide(); return; }
        if (prefix === lastQuery) { return; }
        lastQuery = prefix;
        activeRange = { start: start + (word.length - word.trimStart().length), end };
        const hits = await fetchSuggestions(prefix);
        if (prefix !== lastQuery) return; // race — a newer query replaced us
        items = hits;
        highlight = items.length ? 0 : -1;
        if (!items.length) { hide(); return; }
        positionDropdown();
        render();
        dropdown.hidden = false;
    }

    textarea.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(refresh, DEBOUNCE_MS);
    });

    textarea.addEventListener('keydown', (e) => {
        if (dropdown.hidden) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            highlight = (highlight + 1) % items.length;
            render();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            highlight = (highlight - 1 + items.length) % items.length;
            render();
        } else if (e.key === 'Tab' || (e.key === 'Enter' && highlight >= 0 && items.length)) {
            // Only intercept Enter when a suggestion is highlighted — otherwise let
            // the normal "send message" handler run.
            if (e.key === 'Enter' && items.length === 0) return;
            e.preventDefault();
            e.stopPropagation();
            accept(highlight);
        } else if (e.key === 'Escape') {
            hide();
        }
    }, true);

    textarea.addEventListener('blur', () => {
        // Small delay so click on dropdown still registers.
        setTimeout(hide, 120);
    });

    dropdown.addEventListener('mousedown', (e) => {
        const item = e.target.closest('.tac-item');
        if (!item) return;
        e.preventDefault();
        const idx = parseInt(item.dataset.idx, 10);
        accept(idx);
    });

    window.addEventListener('resize', () => {
        if (!dropdown.hidden) positionDropdown();
    });
}

// Auto-bind on DOMContentLoaded for easy inclusion as a <script type="module">.
if (typeof document !== 'undefined') {
    const boot = () => {
        const el = document.getElementById('messageInput');
        if (el) attachTagAutocomplete(el);
    };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
}

export default { attachTagAutocomplete };
