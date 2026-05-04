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

    async function openDialog() {
        const prompt = window.prompt(
            "Reasoning pipeline prompt (local ComfyUI):",
            ""
        );
        if (!prompt || !prompt.trim()) return;
        const btn = document.getElementById(BTN_ID);
        if (btn) { btn.disabled = true; btn.textContent = "🧠 …"; }
        try {
            // Pull optional UI state set by character-chip.js. Both globals
            // are intentionally additive — when the chip module is absent
            // (or the user has not interacted with it) the payload contains
            // no extra fields and the route behaves exactly as before.
            const opts = (window.imageGenOptions || {});
            const sel  = window.selectedCharacter || null;
            const mp   = window.manualProfile || null;
            const body = { prompt: prompt.trim() };
            if (sel) body.selected_character = sel;
            if (mp)  body.manual_profile = mp;
            if (opts.preflightOnly) body.preflight_only = true;
            if (opts.requirePreflightPass) body.require_preflight_pass = true;
            if (opts.budgetMode === "fast") body.budget_mode = "fast";
            if (opts.maxCostLevel) body.max_cost_level = opts.maxCostLevel;
            const res = await fetch(GENERATE_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            const data = await res.json();
            if (data && data.success && data.image_b64) {
                showResultImage(data.image_b64, data.comic);
            } else if (data && data.preflight) {
                // Preflight-only or preflight-blocked response — surface a
                // compact summary instead of crying "failed".
                const lines = [
                    `Risk: ${data.risk_level || "?"}`,
                    data.blocking_reason ? `Reason: ${data.blocking_reason}` : "",
                    data.suggested_next_action ? `Next: ${data.suggested_next_action}` : "",
                ].filter(Boolean);
                window.alert("Preflight result:\n" + lines.join("\n"));
            } else {
                console.warn("[reasoning-image-gen] failed", data);
                window.alert(
                    "Reasoning pipeline failed: " +
                    (data && data.error ? data.error : "unknown error")
                );
            }
        } catch (err) {
            console.error("[reasoning-image-gen] error", err);
            window.alert("Reasoning pipeline error: " + err.message);
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = "🧠 Reason"; }
        }
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
