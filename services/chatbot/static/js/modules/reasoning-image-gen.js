/**
 * Reasoning Image Gen — UI bridge.
 *
 * Probes /api/reasoning-image-gen/status. When the route is missing
 * (REASONING_PIPELINE=false) nothing is rendered. When present:
 *   • A "Reasoning Pipeline" item is appended to the topbar More menu
 *     (#moreMenuDropdown) — matches existing topbar__more-item style.
 *   • Clicking opens a styled modal (textarea + Generate button) that
 *     POSTs to /api/reasoning-image-gen/generate.
 *   • Warnings render inline inside the modal; results render in a
 *     full-screen overlay.
 *
 * Additive only — does NOT touch image-gen-v2.js or any existing controls.
 */
(function () {
    "use strict";

    const STATUS_URL = "/api/reasoning-image-gen/status";
    const GENERATE_URL = "/api/reasoning-image-gen/generate";
    const MENU_ITEM_ID = "reasoningImageGenMenuItem";
    const MODAL_ID = "reasoningImageGenModal";

    // ── Menu wiring ───────────────────────────────────────────────────

    function injectMenuItem() {
        if (document.getElementById(MENU_ITEM_ID)) return;
        const menu = document.getElementById("moreMenuDropdown");
        if (!menu) return;
        const item = document.createElement("button");
        item.id = MENU_ITEM_ID;
        item.type = "button";
        item.className = "topbar__more-item";
        item.title = "Reasoning Image Pipeline (local, multi-panel)";
        item.innerHTML =
            '<i data-lucide="brain-circuit" class="lucide"></i> ' +
            "<span>Reasoning Pipeline</span>";
        item.addEventListener("click", () => {
            const dropdown = document.getElementById("moreMenuDropdown");
            if (dropdown) dropdown.classList.add("hidden");
            openModal();
        });
        menu.appendChild(item);
        if (window.lucide && typeof window.lucide.createIcons === "function") {
            try { window.lucide.createIcons(); } catch (_e) { /* noop */ }
        }
    }

    // ── Modal ─────────────────────────────────────────────────────────

    function ensureModal() {
        let overlay = document.getElementById(MODAL_ID);
        if (overlay) return overlay;

        overlay = document.createElement("div");
        overlay.id = MODAL_ID;
        overlay.className = "modal-overlay";
        overlay.innerHTML =
            '<div class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="reasoningImageGenTitle" style="max-width:560px;width:90vw;">' +
                '<div class="modal-panel__header">' +
                    '<h3 class="modal-panel__title" id="reasoningImageGenTitle">Reasoning Image Pipeline</h3>' +
                    '<button type="button" class="modal-panel__close" data-act="close" aria-label="Close">&times;</button>' +
                '</div>' +
                '<div class="modal-panel__body">' +
                    '<p style="margin:0 0 8px;font-size:13px;color:var(--text-secondary, #888);">' +
                        'Local multi-panel pipeline (ComfyUI). Describe the scene; the planner will split it into panels and run preflight checks.' +
                    '</p>' +
                    '<textarea id="reasoningImageGenPrompt" rows="5" placeholder="e.g. A two-panel comic: hero entering a forest; closeup of their face under moonlight." ' +
                        'style="width:100%;box-sizing:border-box;padding:10px 12px;border-radius:8px;border:1px solid var(--border, #444);' +
                        'background:var(--bg-secondary, #1a1a24);color:var(--text-primary, #eee);font:inherit;resize:vertical;"></textarea>' +
                    '<div id="reasoningImageGenInlineMsg" style="margin-top:10px;font-size:12px;line-height:1.4;"></div>' +
                '</div>' +
                '<div class="modal-panel__footer">' +
                    '<button type="button" class="btn btn--ghost" data-act="close">Cancel</button>' +
                    '<button type="button" class="btn btn--primary" data-act="generate" id="reasoningImageGenSubmit">Generate</button>' +
                '</div>' +
            '</div>';

        overlay.addEventListener("click", (ev) => {
            const t = ev.target;
            if (!(t instanceof HTMLElement)) return;
            const act = t.getAttribute("data-act");
            if (t === overlay || act === "close") {
                closeModal();
            } else if (act === "generate") {
                submitPrompt();
            }
        });

        document.body.appendChild(overlay);
        return overlay;
    }

    function openModal(prefill) {
        const overlay = ensureModal();
        const ta = overlay.querySelector("#reasoningImageGenPrompt");
        if (ta && typeof prefill === "string") ta.value = prefill;
        clearInlineMsg();
        overlay.classList.add("open");
        setTimeout(() => { if (ta) ta.focus(); }, 50);
    }

    function closeModal() {
        const overlay = document.getElementById(MODAL_ID);
        if (overlay) overlay.classList.remove("open");
    }

    function setInlineMsg(html, kind) {
        const el = document.querySelector("#reasoningImageGenInlineMsg");
        if (!el) return;
        const palette = {
            warn: "color:#f3dfa6;border:1px solid #b8860b;background:#2a210a;",
            err:  "color:#f3c0c4;border:1px solid #b00020;background:#2a0f12;",
            ok:   "color:#cfe9d4;border:1px solid #2e7d32;background:#13241a;",
        };
        const style = palette[kind] || palette.warn;
        el.style.cssText = "padding:8px 10px;border-radius:6px;" + style;
        el.innerHTML = html;
    }

    function clearInlineMsg() {
        const el = document.querySelector("#reasoningImageGenInlineMsg");
        if (el) { el.textContent = ""; el.removeAttribute("style"); }
    }

    function setSubmitBusy(busy) {
        const btn = document.querySelector("#reasoningImageGenSubmit");
        if (!btn) return;
        btn.disabled = !!busy;
        btn.textContent = busy ? "Generating…" : "Generate";
    }

    // ── Request flow ──────────────────────────────────────────────────

    function buildBody(promptText, { force } = {}) {
        const opts = (window.imageGenOptions || {});
        const sel  = window.selectedCharacter || null;
        const mp   = window.manualProfile || null;
        const body = { prompt: promptText };
        if (sel) body.selected_character = sel;
        if (mp)  body.manual_profile = mp;
        if (!force && opts.preflightOnly) body.preflight_only = true;
        if (!force && opts.requirePreflightPass) body.require_preflight_pass = true;
        if (opts.budgetMode === "fast") body.budget_mode = "fast";
        if (opts.maxCostLevel) body.max_cost_level = opts.maxCostLevel;
        return body;
    }

    async function postGenerate(body) {
        const res = await fetch(GENERATE_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        return res.json();
    }

    async function submitPrompt({ force } = {}) {
        const ta = document.querySelector("#reasoningImageGenPrompt");
        const promptText = ta ? ta.value.trim() : "";
        if (!promptText) {
            setInlineMsg("Please enter a prompt.", "warn");
            return;
        }
        setSubmitBusy(true);
        clearInlineMsg();
        try {
            const data = await postGenerate(buildBody(promptText, { force }));
            handleResponse(data, promptText);
        } catch (err) {
            console.error("[reasoning-image-gen] error", err);
            setInlineMsg(
                "Request failed: " + escapeHTML(err && err.message || String(err)),
                "err"
            );
        } finally {
            setSubmitBusy(false);
        }
    }

    function handleResponse(data, promptText) {
        if (data && data.success && data.image_b64) {
            closeModal();
            showResultImage(data.image_b64, data.comic);
            return;
        }
        if (data && data.preflight) {
            const risk = (data.risk_level || "low").toLowerCase();
            if (risk === "low") {
                setInlineMsg("Preflight: low risk. Click Generate again to run.", "ok");
                return;
            }
            renderWarning(data, promptText);
            return;
        }
        setInlineMsg(
            "Pipeline error: " + escapeHTML((data && data.error) || "unknown"),
            "err"
        );
    }

    function renderWarning(data, _promptText) {
        const risk = (data.risk_level || "high").toLowerCase();
        const ident = data.canonical_id || data.provisional_id || "";
        const html =
            '<div style="font-weight:600;margin-bottom:4px;">Preflight: ' +
                escapeHTML(risk) + " risk" +
                (data.character_mode
                    ? ' <span style="opacity:.7;">(' + escapeHTML(data.character_mode) + ')</span>'
                    : "") +
            "</div>" +
            (data.blocking_reason ? "<div>Reason: " + escapeHTML(data.blocking_reason) + "</div>" : "") +
            (data.suggested_next_action ? "<div>Next: " + escapeHTML(data.suggested_next_action) + "</div>" : "") +
            (ident ? '<div style="opacity:.7;">id: <code>' + escapeHTML(ident) + "</code></div>" : "") +
            '<div style="margin-top:8px;display:flex;gap:6px;justify-content:flex-end;">' +
                '<button type="button" id="reasoningImageGenForceBtn" ' +
                    'style="padding:4px 10px;border-radius:4px;border:1px solid currentColor;background:transparent;color:inherit;cursor:pointer;">' +
                    "Generate anyway</button>" +
            "</div>";
        setInlineMsg(html, risk === "high" ? "err" : "warn");
        const forceBtn = document.querySelector("#reasoningImageGenForceBtn");
        if (forceBtn) forceBtn.addEventListener("click", () => submitPrompt({ force: true }));
    }

    function escapeHTML(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function showResultImage(b64, comic) {
        const overlay = document.createElement("div");
        overlay.style.cssText =
            "position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:99999;" +
            "display:flex;align-items:center;justify-content:center;padding:24px;cursor:pointer;";
        overlay.title = "Click to close";
        const img = new Image();
        img.src = "data:image/png;base64," + b64;
        img.style.cssText = "max-width:90vw;max-height:85vh;border-radius:8px;";
        const caption = document.createElement("div");
        caption.style.cssText =
            "position:absolute;bottom:8px;left:8px;color:#bbb;font-size:11px;" +
            "background:rgba(0,0,0,0.6);padding:4px 8px;border-radius:4px;";
        if (comic) {
            caption.textContent =
                comic.layout + " — " + comic.panel_count + " panel(s) — " +
                comic.width + "×" + comic.height;
        }
        overlay.appendChild(img);
        overlay.appendChild(caption);
        overlay.addEventListener("click", () => overlay.remove());
        document.body.appendChild(overlay);
    }

    // ── Init ──────────────────────────────────────────────────────────

    async function init() {
        try {
            const res = await fetch(STATUS_URL, { method: "GET" });
            if (!res.ok) return;
            const data = await res.json();
            if (data && data.enabled) injectMenuItem();
        } catch (_err) {
            // Route absent — silent no-op.
        }
    }

    // Public API for other modules / hotkeys.
    window.openReasoningImageGen = openModal;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
