# Frontend Architecture — AI ChatBot Assistant

> Last updated after the UX-UI refactoring series (event delegation, overlay
> manager, message model, CSS split). This is the authoritative document for
> anyone working on the chatbot frontend.

---

## 1. App Shell

```
templates/index.html          ← single HTML page (SPA-like)
static/css/app.css             ← @import hub (11 partials in css/parts/)
static/css/image-gen-v2.css    ← styles for the cloud image-gen modal
static/js/main.js              ← orchestration, boot, event bindings
static/js/mcp.js               ← MCP sidebar (independent controller)
static/js/language-switcher.js  ← i18n toggle
static/js/modules/             ← feature modules (ES modules, imported by main.js)
```

**Boot sequence** (`main.js`):
1. `DOMContentLoaded` fires.
2. `initDelegation()` installs the global `data-action` click/change router.
3. `initOverlayManager()` installs Escape + outside-click overlay closing.
4. `new ChatBotApp()` wires all modules together (ChatManager, APIService,
   UIUtils, MessageRenderer, FileHandler, …).
5. `registerOverlay(id)` is called for each overlay element.
6. `registerClickActions({…})` is called for each delegation action group.
7. `initGallery()`, `initOverlayActions()`, `initLightbox()`,
   `initAdvancedSettings()`, `initImageGenBindings()` attach feature-specific
   handlers.

**HTML structure** (simplified):
```
#app
  .sidebar           — chat list, new-chat button, storage widget
  .main-content
    .topbar          — model selector, tools dropdown, skill selector, more menu
    .chat-area
      #chatMessages  — message bubbles
      .welcome       — shown when no messages
    .input-area
      #messageInput  — composer textarea
      .staging-area  — staged file pills
      .input-actions — send / stop / file attach buttons
```

---

## 2. Module Responsibilities

### Core modules (imported by `main.js`)

| Module | Responsibility |
|---|---|
| `api-service.js` | `fetch` + SSE communication. **Single point of contact** with backend. Methods: `sendStreamMessage`, `generateTitle`, `getHistory`, `clearHistory`, etc. |
| `chat-manager.js` | localStorage persistence. Sessions CRUD, auto-cleanup on quota, pinning, reordering. |
| `message-renderer.js` | Markdown → DOM rendering. Handles code blocks, tables, thinking process, message versioning, copy buttons, image rendering. |
| `send-message-helpers.js` | Orchestrates the full send flow: `collectFormState` → `routeByIntent` → `prepareOutgoingPayload` → `runStreamingChatFlow` / `runImageRequestFlow`. |
| `ui-utils.js` | Theme, sidebar toggle, storage display, chat list rendering, accessibility. |
| `file-handler.js` | File input, drag-and-drop, staging area, OCR/image preview. |
| `event-delegation.js` | Global `data-action` router. All new click/change handlers go through `registerClickActions()` or `registerAction()`. |
| `overlay-manager.js` | Registry of overlay elements. Provides Escape-to-close (stack-based, topmost first) and outside-click-to-close. |
| `overlay-actions.js` | Image overlay buttons (download/info/save via `data-igv2-action`), lightbox zoom/pinch-to-zoom/swipe-to-close. |
| `message-model.js` | Data-first message persistence. `domToStructured()` converts live DOM to structured objects; `isStructuredSession()` detects format. |
| `gallery-manager.js` | Gallery modal — fetches images, renders grid, delegates actions. |
| `image-gen.js` | Image Generation v1 — Stable Diffusion integration (legacy). |
| `image-gen-v2.js` | Image Generation v2 — cloud providers (fal.ai, BFL, etc.). |
| `image-gen-bindings.js` | Binds image-gen UI controls (tags, categories) to the image-gen modules. |
| `video-gen.js` | Video generation (Sora 2). |
| `memory-manager.js` | AI memory CRUD via `/memory/*` routes. |
| `skill-manager.js` | Runtime skill selection and session activation via `/api/skills/*`. |
| `csv-preview.js` | CSV table preview modal with pagination, search, cell popup. |
| `split-view.js` | Side-by-side chat split view. |
| `export-handler.js` | Export chat as PDF/JSON/text. |
| `adv-settings.js` | Advanced model settings panel (temperature, top-p, etc.). |
| `performance-utils.js` | **DEAD CODE** — not imported. Kept for reference only. |

### Standalone scripts

| Script | Loads via | Purpose |
|---|---|---|
| `mcp.js` | `<script type="module">` in HTML | MCP sidebar controller. Exposes `window.mcpController`. |
| `language-switcher.js` | Imported by `main.js` | i18n toggle (vi/en). |

---

## 3. CSS Architecture

`app.css` is an `@import` hub loading 11 responsibility-based partials:

```
css/app.css                    ← @import hub
  parts/tokens.css              — CSS variables, themes (dark/light/eye-care), reset, icons
  parts/layout.css              — app shell grid, split view
  parts/sidebar.css             — sidebar nav, chat list, drag & drop
  parts/topbar.css              — top bar, model/tool selectors, brand
  parts/chat.css                — messages, bubbles, thinking, code blocks, tables
  parts/composer.css            — input area, file staging, skills badge, quote preview
  parts/overlays.css            — modals, gallery, image preview, panels, popups
  parts/components.css          — buttons, forms, badges
  parts/media.css               — MCP, memory, video, storage widget
  parts/utilities.css           — hover helpers, transitions, old-class compat
  parts/responsive.css          — @media queries (768px, 480px), reduced-motion

css/image-gen-v2.css            ← separate stylesheet for cloud image-gen modal
```

**Theme system**: 3 themes defined as `[data-theme]` attribute on `<html>`:
- `dark` (default) — defined in `:root`
- `light` — `[data-theme="light"]`
- `eye-care` — `[data-theme="eye-care"]`

**Overlay convention**: All overlays use the `.open` class to toggle visibility.
CSS in `parts/overlays.css` and `parts/utilities.css` defines `.open` rules.

---

## 4. Chat / Message Data Model

### Session structure (`chat-manager.js` → localStorage)

```js
chatSessions = {
  "session-id-1": {
    id: "session-id-1",
    title: "Chat title",
    messages: [ /* MessageRenderer DOM or structured objects */ ],
    model: "gpt-4o",
    createdAt: 1700000000000,
    updatedAt: 1700001000000,
    pinned: false,
  },
  // ...
}
```

### Message data model (`message-model.js`)

Two formats coexist:
1. **Legacy (DOM strings)**: Messages stored as `outerHTML` strings. Rendered by
   directly inserting into DOM on load.
2. **Structured (data-first)**: Messages stored as plain objects:
   ```js
   {
     role: "assistant",
     content: "Hello!",
     model: "gpt-4o",
     timestamp: 1700000000000,
     versions: [ /* version branches */ ],
     currentVersion: 0,
   }
   ```

`isStructuredSession(session)` detects which format a session uses.
`domToStructured(messages)` converts live DOM → structured objects.

**Migration note**: New sessions should use the structured format. Existing
sessions auto-convert when opened if the renderer detects DOM strings.

---

## 5. MCP Architecture

```
┌──────────────┐   HTTP    ┌────────────────┐   stdio    ┌────────────────┐
│ mcp.js       │ ────────→ │ routes/mcp.py  │ ────────→  │ mcp-server/    │
│ (frontend)   │           │ (Flask proxy)  │            │ server.py      │
│              │           │                │            │ tools/         │
│ MCPController│           │ /api/mcp/*     │            │ (FastMCP)      │
└──────────────┘           └────────────────┘            └────────────────┘
```

- `window.mcpController` exposes `getSelectedFilePaths()` for injection into
  chat requests.
- `api-service.js` and `send-message-helpers.js` read MCP context from
  `window.mcpController` when building the outgoing payload.
- MCP transport is **stdio** — no HTTP server on the MCP side.

---

## 6. Overlay State Pattern

All overlays (modals, dropdowns, panels) follow a unified pattern:

### Registration
```js
// In DOMContentLoaded block of main.js:
registerOverlay('galleryModal');
registerOverlay('imagePreviewModal');
registerOverlay('videoGenModal');
// ... 12 overlays total
```

### Opening / Closing
```js
// Open: add .open (and optionally .active for transition)
element.classList.add('active', 'open');

// Close: remove classes
element.classList.remove('active', 'open');
```

### Auto-close behavior (provided by overlay-manager.js)
- **Escape key**: Closes the topmost registered overlay (stack-based).
- **Outside click**: Closes the overlay if the click target is the backdrop.
- **Focus save/restore**: Saves the focused element before open, restores on close.

### CSS convention
```css
/* In parts/overlays.css or parts/utilities.css */
.my-overlay { display: none; }
.my-overlay.open { display: flex; /* or block */ }
```

**Important**: Some older modules still use `style.display` directly for
internal UI state (tab switching, upload previews). This is acceptable for
non-overlay elements. Only overlay show/hide must use the `.open` class.

---

## 7. Event Delegation Pattern

All new click handlers must use the delegation system instead of inline
`onclick` attributes or direct `addEventListener` on individual elements.

### HTML pattern
```html
<button data-action="gallery:close">Close</button>
<button data-action="staged:remove" data-index="0">×</button>
```

### JS registration
```js
import { registerClickActions, registerAction } from './modules/event-delegation.js';

// Click actions (most common)
registerClickActions({
    'gallery:close':   () => closeGallery(),
    'gallery:refresh': () => refreshGallery(),
});

// Other event types
registerAction('change', 'config:toggle', (e) => { /* ... */ });
```

### Naming convention
```
{domain}:{verb}      e.g. gallery:close, staged:remove, user:logout
```

---

## 8. Rules for Adding New Features

### Adding a new modal / overlay
1. Add HTML shell to `templates/index.html` with a unique `id`.
2. Add CSS in the appropriate partial (usually `parts/overlays.css`).
3. Use `.open` class for visibility (not `style.display`).
4. Call `registerOverlay('myModalId')` in the `DOMContentLoaded` block of
   `main.js` so Escape and outside-click close it.
5. Wire open/close via `data-action` delegation.

### Adding a new tool / selector button
1. Trace the full path: HTML element → JS handler → backend route → response.
2. Add `data-action="tool:my-action"` to the button.
3. Register the action via `registerClickActions()`.
4. If calling a backend route, use `api-service.js` methods.
5. Ensure payload field names match between frontend and backend.

### Adding a new CSS section
1. Put it in the appropriate `parts/*.css` file.
2. Use existing CSS variables from `parts/tokens.css` — never hardcode colors or
   spacing.
3. If it's a new category, discuss whether a new partial is warranted (rare).
4. Prefix section-specific classes with a BEM-like namespace
   (e.g. `.mcp__tool-item`, `.gallery__grid`).

### Adding a new JS module
1. Create `static/js/modules/my-feature.js`.
2. Export a class or init function.
3. Import in `main.js` and wire up in the `DOMContentLoaded` block.
4. Use `escapeHtml` from whichever parent module context is available (see
   "Known duplication" below).
5. Never add `window.X` globals unless absolutely required for cross-module
   communication. Prefer imports.

---

## 9. Migration Notes — Legacy Fallbacks

### Old-class compatibility CSS (`parts/utilities.css`)
```css
/* These map old class names to new vars so JS modules work */
.message-content { display: block; }
.message-text { display: block; word-wrap: break-word; ... }
.message-info { display: flex; ... }
.message-buttons { display: flex; gap: 4px; ... }
```
These exist because some rendered DOM (stored in localStorage) uses old class
names. Once all sessions have been migrated to structured format, these can be
removed.

### Image generation v1 (`image-gen.js`)
The v1 module handles Stable Diffusion (local server). It coexists with v2
(cloud providers). Both are active. V1 uses older patterns (`style.display`
toggling, no delegation). Migrating v1 to the new patterns is optional unless
its UI is being changed.

### Window globals
These globals remain for cross-module communication. They are consumed by
templates or modules that don't import each other directly:

| Global | Set by | Why |
|---|---|---|
| `window.chatManager` | main.js | Used by templates and ui-utils |
| `window.mcpController` | mcp.js | Used by api-service, send-message-helpers |
| `window.imageGenV2` | main.js | Used by inline onclick in image-gen-v2 results |
| `window.videoGen` | main.js | Used by inline onclick in video-gen results |
| `window.openImagePreview` | overlay-actions.js | Used by file-handler, gallery, renderer |
| `window.resetPreviewZoom` | overlay-actions.js | Used by gallery |
| `window.skillManager` | index.html | Used by send-message-helpers |

### Inline `onclick` in generated HTML
Some modules (`image-gen-v2.js`, `video-gen.js`, `image-gen-bindings.js`) still
generate HTML strings with inline `onclick="window.X()"`. This is a known
pattern that should be migrated to `data-action` delegation when those modules
are next edited.

---

## 10. Known Technical Debt

| Item | Severity | Location | Effort |
|---|---|---|---|
| `escapeHtml` duplicated 9× across modules | Medium | 9 files (see audit) | Create `html-utils.js`, import everywhere |
| `performance-utils.js` dead (595 lines) | Low | `modules/performance-utils.js` | Delete when ready |
| `style.display` toggles in `mcp.js`, `image-gen.js` | Low | ~26 instances | Migrate to `.open` when editing those modules |
| Inline `onclick` in generated HTML | Low | image-gen-v2, video-gen, bindings | Migrate to `data-igv2-action` or `data-action` |
| 3 dead exports in `message-model.js` | Low | `createVersionEntry`, `isStructuredVersion`, `isStructuredBranch` | Remove or use |
| `getCurrentLang()` dead export | Low | `language-switcher.js` | Remove or use |
| CSS `@import` adds HTTP round-trips in dev | Info | `app.css` | Use PostCSS or bundler for production |
