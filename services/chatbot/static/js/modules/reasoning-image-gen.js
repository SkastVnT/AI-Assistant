/**
 * Reasoning Image Gen — UI bridge (Cycle 6).
 *
 * Self-registering button that probes /api/reasoning-image-gen/status. When
 * the route is missing (REASONING_PIPELINE=false) the button is silently
 * removed and no other UI is touched. When present, the button opens a
 * minimal prompt dialog and POSTs to /api/reasoning-image-gen/generate.
 *
 * Additive only — does NOT touch image-gen-v2.js or any existing controls.
 */
(function () {
    "use strict";

    const STATUS_URL = "/api/reasoning-image-gen/status";
    const GENERATE_URL = "/api/reasoning-image-gen/generate";
    const BTN_ID = "reasoningImageGenBtn";

    function injectButton() {
        if (document.getElementById(BTN_ID)) return;
        const btn = document.createElement("button");
        btn.id = BTN_ID;
        btn.type = "button";
        btn.title = "Reasoning Image Pipeline (local, multi-panel)";
        btn.textContent = "🧠 Reason";
        btn.style.cssText =
            "position:fixed;right:16px;bottom:120px;z-index:9999;padding:8px 12px;" +
            "border-radius:18px;border:1px solid #6a5acd;background:#1e1e2f;color:#fff;" +
            "font-size:12px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,0.3);";
        btn.addEventListener("click", openDialog);
        document.body.appendChild(btn);
    }

    function buildBody(promptText, { force } = {}) {
        const opts = (window.imageGenOptions || {});
        const sel  = window.selectedCharacter || null;
        const mp   = window.manualProfile || null;
        const body = { prompt: promptText };
        if (sel) body.selected_character = sel;
        if (mp)  body.manual_profile = mp;
        // ``force`` (Generate anyway) clears the preflight gates so the
        // pipeline runs on this attempt only — chip toggles stay set.
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

    async function runWithPrompt(promptText, { force } = {}) {
        const btn = document.getElementById(BTN_ID);
        if (btn) { btn.disabled = true; btn.textContent = "🧠 …"; }
        try {
            const data = await postGenerate(buildBody(promptText, { force }));
            handleResponse(data, promptText);
        } catch (err) {
            console.error("[reasoning-image-gen] error", err);
            showWarning({
                risk_level: "high",
                blocking_reason: "request_failed",
                suggested_next_action: err.message || "network error",
            }, promptText, { allowRetry: true });
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = "🧠 Reason"; }
        }
    }

    function handleResponse(data, promptText) {
        if (data && data.success && data.image_b64) {
            showResultImage(data.image_b64, data.comic);
            return;
        }
        if (data && data.preflight) {
            // Compact warning UI: only render the banner for medium/high.
            // For ``low`` (typical preflight-only happy path) we silently
            // do nothing — caller can re-click without preflight gating.
            const risk = (data.risk_level || "low").toLowerCase();
            if (risk === "low") {
                showLowRiskHint(promptText);
                return;
            }
            showWarning(data, promptText, { allowRetry: true });
            return;
        }
        console.warn("[reasoning-image-gen] failed", data);
        showWarning({
            risk_level: "high",
            blocking_reason: "pipeline_error",
            suggested_next_action: (data && data.error) || "unknown error",
        }, promptText, { allowRetry: false });
    }

    async function openDialog() {
        let prompt;
        try {
            prompt = (typeof window.appPrompt === "function")
                ? await window.appPrompt("Reasoning pipeline prompt (local ComfyUI):", "")
                : window.prompt("Reasoning pipeline prompt (local ComfyUI):", "");
        } catch (_) { prompt = null; }
        if (!prompt || !String(prompt).trim()) return;
        await runWithPrompt(String(prompt).trim());
    }

    // ── Compact warning banner (no big technical panel) ───────────────
    const BANNER_ID = "reasoningImageGenWarn";

    function dismissBanner() {
        const el = document.getElementById(BANNER_ID);
        if (el) el.remove();
    }

    function showLowRiskHint(promptText) {
        // Tiny non-blocking confirmation. Disappears in 3s.
        dismissBanner();
        const el = document.createElement("div");
        el.id = BANNER_ID;
        el.style.cssText =
            "position:fixed;right:16px;bottom:170px;z-index:9999;max-width:320px;" +
            "padding:8px 12px;border-radius:8px;border:1px solid #2e7d32;" +
            "background:#13241a;color:#cfe9d4;font-size:12px;box-shadow:0 2px 8px rgba(0,0,0,0.4);";
        el.textContent = "Preflight: low risk. Click Reason to generate.";
        document.body.appendChild(el);
        setTimeout(dismissBanner, 3000);
    }

    function showWarning(data, promptText, { allowRetry } = {}) {
        dismissBanner();
        const risk = (data.risk_level || "high").toLowerCase();
        const isHigh = risk === "high";
        const el = document.createElement("div");
        el.id = BANNER_ID;
        el.style.cssText =
            "position:fixed;right:16px;bottom:170px;z-index:9999;max-width:360px;" +
            "padding:10px 12px;border-radius:8px;font-size:12px;line-height:1.4;" +
            "box-shadow:0 2px 8px rgba(0,0,0,0.4);" +
            (isHigh
                ? "border:1px solid #b00020;background:#2a0f12;color:#f3c0c4;"
                : "border:1px solid #b8860b;background:#2a210a;color:#f3dfa6;");
        const ident = data.canonical_id || data.provisional_id || "";
        el.innerHTML =
            `<div style="font-weight:600;margin-bottom:4px;">` +
            `Preflight: ${escapeHTML(risk)} risk` +
            (data.character_mode ? ` <span style="opacity:.7;">(${escapeHTML(data.character_mode)})</span>` : "") +
            `</div>` +
            (data.blocking_reason
                ? `<div>Reason: ${escapeHTML(data.blocking_reason)}</div>` : "") +
            (data.suggested_next_action
                ? `<div>Next: ${escapeHTML(data.suggested_next_action)}</div>` : "") +
            (ident
                ? `<div style="opacity:.7;">id: <code>${escapeHTML(ident)}</code></div>` : "") +
            `<div style="margin-top:8px;display:flex;gap:6px;justify-content:flex-end;">` +
            (allowRetry
                ? `<button type="button" data-act="anyway" style="padding:4px 10px;border-radius:4px;border:1px solid #888;background:transparent;color:inherit;cursor:pointer;">Generate anyway</button>`
                : "") +
            `<button type="button" data-act="close" style="padding:4px 10px;border-radius:4px;border:1px solid #555;background:transparent;color:inherit;cursor:pointer;">Dismiss</button>` +
            `</div>`;
        el.addEventListener("click", (ev) => {
            const t = ev.target;
            if (!t || t.tagName !== "BUTTON") return;
            const act = t.getAttribute("data-act");
            if (act === "close") {
                dismissBanner();
            } else if (act === "anyway") {
                dismissBanner();
                runWithPrompt(promptText, { force: true });
            }
        });
        document.body.appendChild(el);
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
                `${comic.layout} — ${comic.panel_count} panel(s) — ` +
                `${comic.width}×${comic.height}`;
        }
        overlay.appendChild(img);
        overlay.appendChild(caption);
        overlay.addEventListener("click", () => overlay.remove());
        document.body.appendChild(overlay);
    }

    async function init() {
        try {
            const res = await fetch(STATUS_URL, { method: "GET" });
            if (!res.ok) return;
            const data = await res.json();
            if (data && data.enabled) injectButton();
        } catch (_err) {
            // Route absent — silent no-op.
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
