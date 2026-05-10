/**
 * CSV / TSV Table Preview Module
 * Vanilla JS — ported logic from webui_csv React app
 * Shows an interactive paginated table when a CSV/TSV file is clicked.
 */

const ROWS_PER_PAGE = 50;
const CELL_MAX_LEN = 80;

// ── Helpers ──────────────────────────────────────────────────

function escHtml(str) {
    if (str === null || str === undefined) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
}

function detectType(value) {
    if (value === null || value === undefined) return 'empty';
    const s = String(value).trim();
    if (!s) return 'empty';
    if (!isNaN(s) && s !== '') return 'number';
    try {
        if ((s.startsWith('{') && s.endsWith('}')) || (s.startsWith('[') && s.endsWith(']'))) {
            JSON.parse(s);
            return 'json';
        }
    } catch (_) { /* not json */ }
    return 'text';
}

// ── CSV / TSV Parser ─────────────────────────────────────────

function parseDelimited(text, delimiter) {
    const lines = text.split(/\r?\n/);
    const nonEmpty = lines.filter(l => l.trim() !== '');
    if (nonEmpty.length === 0) return { headers: [], rows: [] };

    const parseLine = (line) => {
        const result = [];
        let current = '';
        let inQuotes = false;
        for (let i = 0; i < line.length; i++) {
            const ch = line[i];
            if (ch === '"') {
                if (inQuotes && line[i + 1] === '"') { current += '"'; i++; }
                else { inQuotes = !inQuotes; }
            } else if (ch === delimiter && !inQuotes) {
                result.push(current.trim());
                current = '';
            } else {
                current += ch;
            }
        }
        result.push(current.trim());
        return result;
    };

    const headers = parseLine(nonEmpty[0]);
    const rows = nonEmpty.slice(1).map(line => {
        const vals = parseLine(line);
        const row = {};
        headers.forEach((h, i) => { row[h] = vals[i] !== undefined ? vals[i] : ''; });
        return row;
    });

    return { headers, rows };
}

// ── Main Class ───────────────────────────────────────────────

export class CsvPreview {
    constructor() {
        this._modal = null;
        this._data = { headers: [], rows: [] };
        this._filename = '';
        this._page = 1;
        this._search = '';
        this._sortCol = null;
        this._sortDir = 'asc';
    }

    /**
     * Parse text to structured table data
     * @param {string} text   Raw file content
     * @param {string} filename  Used to detect delimiter (csv vs tsv)
     * @returns {{ headers: string[], rows: object[] }}
     */
    parse(text, filename) {
        const ext = (filename || '').split('.').pop().toLowerCase();
        const delimiter = ext === 'tsv' ? '\t' : ',';
        return parseDelimited(text, delimiter);
    }

    /**
     * Show the full-screen table viewer modal
     * @param {{ headers: string[], rows: object[] }} parsedData
     * @param {string} filename
     */
    show(parsedData, filename) {
        this._data = parsedData;
        this._filename = filename || 'Bảng dữ liệu';
        this._page = 1;
        this._search = '';
        this._sortCol = null;
        this._sortDir = 'asc';

        if (!this._modal) this._build();

        // Sync search input
        this._modal.querySelector('.csv-preview-search').value = '';

        this._update();
        this._modal.classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    close() {
        if (this._modal) this._modal.classList.remove('open');
        document.body.style.overflow = '';
        // Hide cell popup if open
        const popup = this._modal?.querySelector('.csv-cell-popup');
        if (popup) popup.style.display = 'none';
    }

    // ── DOM Construction (runs once) ─────────────────────────

    _build() {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay csv-preview-overlay';
        overlay.innerHTML = `
            <div class="csv-preview-panel">
                <div class="csv-preview-header">
                    <div class="csv-preview-title-row">
                        <svg class="lucide" viewBox="0 0 24 24">
                            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>
                        </svg>
                        <span class="csv-preview-filename"></span>
                        <span class="csv-preview-stats"></span>
                    </div>
                    <div class="csv-preview-toolbar">
                        <div class="csv-preview-search-wrap">
                            <svg class="lucide lucide-sm" viewBox="0 0 24 24">
                                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                            </svg>
                            <input class="csv-preview-search" type="text" placeholder="Tìm kiếm trong bảng...">
                        </div>
                        <button class="csv-preview-close" title="Đóng (Esc)">
                            <svg class="lucide" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>
                        </button>
                    </div>
                </div>
                <div class="csv-preview-body">
                    <div class="csv-preview-table-wrap">
                        <table class="csv-preview-table">
                            <thead class="csv-preview-thead"></thead>
                            <tbody class="csv-preview-tbody"></tbody>
                        </table>
                    </div>
                </div>
                <div class="csv-preview-footer">
                    <span class="csv-preview-page-info"></span>
                    <div class="csv-preview-pagination"></div>
                </div>
            </div>
            <div class="csv-cell-popup" style="display:none;"></div>
        `;

        this._modal = overlay;

        // Close on backdrop click
        overlay.addEventListener('click', e => {
            if (e.target === overlay) this.close();
        });

        // Close button
        overlay.querySelector('.csv-preview-close').addEventListener('click', () => this.close());

        // Escape key
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && overlay.classList.contains('open')) this.close();
        });

        // Search input
        const searchInput = overlay.querySelector('.csv-preview-search');
        searchInput.addEventListener('input', () => {
            this._search = searchInput.value;
            this._page = 1;
            this._updateTable();
            this._updatePagination();
            this._updateStats();
        });

        // Hide cell popup on body click
        document.addEventListener('click', () => {
            const popup = this._modal?.querySelector('.csv-cell-popup');
            if (popup) popup.style.display = 'none';
        });

        document.body.appendChild(overlay);
    }

    // ── Data helpers ─────────────────────────────────────────

    _filteredRows() {
        if (!this._search.trim()) return this._data.rows;
        const q = this._search.toLowerCase();
        return this._data.rows.filter(row =>
            Object.values(row).some(v => String(v ?? '').toLowerCase().includes(q))
        );
    }

    _sortedRows(rows) {
        if (!this._sortCol) return rows;
        const col = this._sortCol;
        return [...rows].sort((a, b) => {
            const av = String(a[col] ?? '');
            const bv = String(b[col] ?? '');
            const na = parseFloat(av), nb = parseFloat(bv);
            const bothNum = !isNaN(na) && !isNaN(nb);
            const cmp = bothNum ? na - nb : av.localeCompare(bv, undefined, { sensitivity: 'base' });
            return this._sortDir === 'asc' ? cmp : -cmp;
        });
    }

    // ── Render helpers ────────────────────────────────────────

    _update() {
        this._modal.querySelector('.csv-preview-filename').textContent = this._filename;
        this._updateTable();
        this._updatePagination();
        this._updateStats();
    }

    _updateStats() {
        const filtered = this._filteredRows();
        const total = this._data.rows.length;
        const cols = this._data.headers.length;
        const filterNote = this._search ? ` (lọc từ ${total})` : '';
        this._modal.querySelector('.csv-preview-stats').textContent =
            `${filtered.length} hàng${filterNote} · ${cols} cột`;

        const totalPages = Math.ceil(filtered.length / ROWS_PER_PAGE);
        const pageInfo = this._modal.querySelector('.csv-preview-page-info');
        if (totalPages > 1) {
            pageInfo.textContent = `Trang ${this._page} / ${totalPages}`;
        } else {
            pageInfo.textContent = '';
        }
    }

    _updateTable() {
        const { headers } = this._data;
        const filtered = this._filteredRows();
        const sorted = this._sortedRows(filtered);
        const start = (this._page - 1) * ROWS_PER_PAGE;
        const pageRows = sorted.slice(start, start + ROWS_PER_PAGE);

        // ── Head ──
        const thead = this._modal.querySelector('.csv-preview-thead');
        thead.innerHTML = `
            <tr>
                <th class="csv-th csv-th-row">#</th>
                ${headers.map(h => `
                    <th class="csv-th ${this._sortCol === h ? 'csv-th-sorted' : ''}" data-col="${escHtml(h)}">
                        <span class="csv-th-label">${escHtml(h)}</span>
                        <span class="csv-sort-icon">${this._sortCol === h ? (this._sortDir === 'asc' ? '↑' : '↓') : ''}</span>
                    </th>
                `).join('')}
            </tr>
        `;

        thead.querySelectorAll('.csv-th[data-col]').forEach(th => {
            th.addEventListener('click', () => {
                const col = th.dataset.col;
                if (this._sortCol === col) {
                    this._sortDir = this._sortDir === 'asc' ? 'desc' : 'asc';
                } else {
                    this._sortCol = col;
                    this._sortDir = 'asc';
                }
                this._updateTable();
            });
        });

        // ── Body ──
        const tbody = this._modal.querySelector('.csv-preview-tbody');

        if (pageRows.length === 0) {
            tbody.innerHTML = `
                <tr><td colspan="${headers.length + 1}" class="csv-empty-state">
                    Không có dữ liệu phù hợp
                </td></tr>
            `;
            return;
        }

        tbody.innerHTML = pageRows.map((row, ri) => {
            const actualIdx = start + ri;
            return `
                <tr class="csv-tr ${actualIdx % 2 === 0 ? 'csv-tr-even' : 'csv-tr-odd'}">
                    <td class="csv-td csv-td-row">${actualIdx + 1}</td>
                    ${headers.map(h => {
                        const val = row[h] ?? '';
                        const str = String(val);
                        const type = detectType(val);

                        if (type === 'empty') {
                            return `<td class="csv-td"><span class="csv-empty">—</span></td>`;
                        }

                        const truncated = str.length > CELL_MAX_LEN;
                        const display = truncated ? str.substring(0, CELL_MAX_LEN) + '…' : str;
                        const typeClass = type === 'json' ? ' csv-cell-json'
                                        : type === 'number' ? ' csv-cell-num' : '';

                        return `<td class="csv-td">
                            <span class="csv-cell${typeClass}"
                                  data-full="${escHtml(str)}"
                                  data-col="${escHtml(h)}">
                                ${escHtml(display)}${truncated
                                    ? `<span class="csv-cell-more">+${str.length - CELL_MAX_LEN}</span>`
                                    : ''}
                            </span>
                        </td>`;
                    }).join('')}
                </tr>
            `;
        }).join('');

        // Cell click → popup
        tbody.querySelectorAll('.csv-cell').forEach(cell => {
            cell.addEventListener('click', e => {
                e.stopPropagation();
                this._showCellPopup(e, cell);
            });
        });
    }

    _updatePagination() {
        const filtered = this._filteredRows();
        const totalPages = Math.ceil(filtered.length / ROWS_PER_PAGE);
        const pag = this._modal.querySelector('.csv-preview-pagination');

        if (totalPages <= 1) { pag.innerHTML = ''; return; }

        const cur = this._page;
        const pages = [];

        // Always show first
        pages.push(1);
        if (cur - 2 > 2) pages.push('…');
        for (let p = Math.max(2, cur - 2); p <= Math.min(totalPages - 1, cur + 2); p++) pages.push(p);
        if (cur + 2 < totalPages - 1) pages.push('…');
        if (totalPages > 1) pages.push(totalPages);

        // Deduplicate
        const unique = pages.filter((p, i) => pages.indexOf(p) === i);

        pag.innerHTML = `
            <button class="csv-page-btn" data-page="${cur - 1}" ${cur === 1 ? 'disabled' : ''}>‹ Trước</button>
            ${unique.map(p => p === '…'
                ? `<span class="csv-page-dot">…</span>`
                : `<button class="csv-page-btn ${p === cur ? 'csv-page-active' : ''}" data-page="${p}">${p}</button>`
            ).join('')}
            <button class="csv-page-btn" data-page="${cur + 1}" ${cur === totalPages ? 'disabled' : ''}>Sau ›</button>
        `;

        pag.querySelectorAll('.csv-page-btn:not([disabled])').forEach(btn => {
            btn.addEventListener('click', () => {
                this._page = parseInt(btn.dataset.page);
                this._updateTable();
                this._updatePagination();
                this._updateStats();
                // Scroll table to top
                const wrap = this._modal.querySelector('.csv-preview-table-wrap');
                if (wrap) wrap.scrollTop = 0;
            });
        });
    }

    _showCellPopup(e, cell) {
        const full = cell.dataset.full || '';
        const col = cell.dataset.col || '';
        const popup = this._modal.querySelector('.csv-cell-popup');

        popup.style.display = 'block';
        popup.innerHTML = `
            <div class="csv-popup-header">
                <span class="csv-popup-col">${escHtml(col)}</span>
                <button class="csv-popup-close">✕</button>
            </div>
            <pre class="csv-popup-content">${escHtml(full)}</pre>
            <button class="csv-popup-copy">Sao chép</button>
        `;

        popup.querySelector('.csv-popup-close').addEventListener('click', e => {
            e.stopPropagation();
            popup.style.display = 'none';
        });

        popup.querySelector('.csv-popup-copy').addEventListener('click', async e => {
            e.stopPropagation();
            try { await navigator.clipboard.writeText(full); } catch (_) {}
            const btn = popup.querySelector('.csv-popup-copy');
            btn.textContent = '✓ Đã sao chép';
            setTimeout(() => { btn.textContent = 'Sao chép'; }, 1500);
        });

        // Position popup: below the cell, clipped to panel bounds
        const panel = this._modal.querySelector('.csv-preview-panel');
        const cellRect = cell.getBoundingClientRect();
        const panelRect = panel.getBoundingClientRect();

        const top = cellRect.bottom - panelRect.top + 4;
        const left = Math.min(
            cellRect.left - panelRect.left,
            panelRect.width - 300
        );

        popup.style.top = `${top}px`;
        popup.style.left = `${Math.max(8, left)}px`;
    }
}

/** Singleton instance — import and call csvPreview.show() */
export const csvPreview = new CsvPreview();
