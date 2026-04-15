# Frontend Refactoring — Final Checklist

## Completed

- [x] **DOMContentLoaded extraction** — All init code runs inside a single
      `DOMContentLoaded` handler in `main.js`.
- [x] **sendMessage extraction** — Send flow extracted to
      `send-message-helpers.js` (~50 KB). `main.js` orchestrates, helpers do
      the heavy lifting.
- [x] **MCP single source of truth** — `mcp.js` owns the MCP controller.
      Other modules read via `window.mcpController`.
- [x] **message-model.js** — Data-first persistence.
      `domToStructured()` + `isStructuredSession()` for migration.
- [x] **Version/branch data-first refactoring** — Version navigation uses
      structured objects instead of DOM scraping.
- [x] **Event delegation** — `event-delegation.js` provides `data-action`
      routing. ~30 inline handlers migrated. 21 window globals removed.
      6 CSS hover utility classes added.
- [x] **Overlay state manager** — `overlay-manager.js` with registry,
      Escape (stack-based topmost close), outside-click, focus save/restore.
      14 overlays migrated to `.open` convention.
- [x] **CSS split** — Monolithic `app.css` (5878 lines) split into 11
      responsibility-based partials under `css/parts/`. 64 duplicate lines
      removed. All braces balanced.
- [x] **Dead import cleanup** — Removed unused `openGallery`, `openOverlay`,
      `closeOverlay`, `toggleOverlay` imports from `main.js`.
- [x] **Lightbox gestures fix** — Unreachable pinch-to-zoom / swipe-to-close /
      wheel-zoom code in `overlay-actions.js` made reachable (moved `return`
      after gesture setup).
- [x] **manualCleanup fix** — Broken `window.manualCleanup()` replaced with
      `data-action="storage:cleanup"` wired to chatManager session purge.
- [x] **Dead code marked** — `performance-utils.js` (595 lines, never
      imported) marked as dead code with header comment.
- [x] **FRONTEND_ARCHITECTURE.md** — Comprehensive architecture documentation
      covering app shell, modules, data model, MCP, overlay pattern, delegation
      pattern, and rules for new features.
- [x] **Flow verification** — All 7 main flows verified intact: chat submit,
      SSE streaming, file staging, MCP, image gen, gallery, modal/dropdown
      Escape.

## Technical Debt Remaining

| # | Item | Severity | Effort |
|---|---|---|---|
| 1 | `escapeHtml` duplicated in 9 files | Medium | Create shared `html-utils.js`, update all imports |
| 2 | `performance-utils.js` still shipped (595 lines dead) | Low | Delete when team agrees |
| 3 | `style.display` toggles in `mcp.js`, `image-gen.js`, `video-gen.js` (~26 instances) | Low | Migrate to `.open` class when editing |
| 4 | Inline `onclick` in generated HTML (`image-gen-v2.js`, `video-gen.js`, `image-gen-bindings.js`) | Low | Convert to `data-action` or `data-igv2-action` |
| 5 | 3 unused exports in `message-model.js` (`createVersionEntry`, `isStructuredVersion`, `isStructuredBranch`) | Low | Use or remove |
| 6 | `getCurrentLang()` exported but never imported | Low | Use or remove |
| 7 | CSS `@import` chains add HTTP round-trips (dev only) | Info | Add PostCSS/bundler for production |
| 8 | Dual image-gen modules (v1=SD, v2=cloud) coexist with different patterns | Info | Unify if v1 UI is next edited |
| 9 | Window globals (~15 remaining) for cross-module communication | Info | Eliminate as modules are refactored to import each other |

## Suggested Next Steps

1. **`escapeHtml` consolidation** — Highest-value cleanup. Create
   `modules/html-utils.js` exporting `escapeHtml()` and `htmlAttrEsc()`.
   Replace all 9 copies with imports.

2. **image-gen v1 modernization** — If the SD UI is being changed, migrate
   `image-gen.js` to use `.open` class and delegation.

3. **Build tooling** — Add a simple PostCSS or esbuild step to:
   - Inline CSS `@import` for production (eliminates round-trips)
   - Optionally bundle JS modules for browsers without native ES module support

4. **Structured session migration** — Run `domToStructured()` on remaining
   legacy sessions at load time. Once all sessions are structured, remove
   old-class compat CSS from `parts/utilities.css`.

5. **Remove window globals** — As modules are refactored, replace
   `window.X` assignments with proper ES module imports. Priority:
   `window.imageGenV2`, `window.videoGen` (used in inline onclick).
