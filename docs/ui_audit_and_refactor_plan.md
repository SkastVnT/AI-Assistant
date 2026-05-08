# Chat UI Audit & Refactor Plan

## 1. Current State

### Files
| File | Lines | Role |
|------|-------|------|
| `templates/index.html` | ~2800 | Main chat UI — tools grid (790-860), inline scripts (1650-2800) |
| `static/css/app.css` | ~3100 | All styles including `.tools-grid`, `.tools-dropdown`, responsive |
| `static/js/main.js` | ~1500 | ChatBotApp class, sendMessage flow, SSE callbacks |
| `static/js/modules/api-service.js` | ~370 | `sendStreamMessage()` → `POST /chat/stream` |
| `static/js/modules/ui-utils.js` | ~300 | Cached DOM refs, showLoading/hideLoading |

### Tool Buttons (13 buttons, ungrouped in 4-column grid)
| ID | Label | Tool string | Category |
|----|-------|-------------|----------|
| imageGenToolBtn | Image Gen | `image-generation` | **Image** |
| img2imgToolBtn | Img2Img | `img2img` | **Image** |
| googleSearchBtn | Web Search | `google-search` | **Search** |
| deepResearchToolBtn | Research | `deep-research` | **Reasoning** |
| githubBtn | GitHub | `github` | **Search** |
| saucenaoBtn | SauceNAO | `saucenao` | **Image** |
| googleLensBtn | Lens | `serpapi-reverse-image` | **Image** |
| serpapiBingBtn | Bing | `serpapi-bing` | **Search** |
| serpapiBaiduBtn | Baidu | `serpapi-baidu` | **Search** |
| serpapiImagesBtn | Img Search | `serpapi-images` | **Search** |
| last30daysBtn | Social Research | `last30days-research` | **Agent** |
| configAgentBtn | Agent | *(opens modal)* | **Agent** |
| uploadFilesBtn | Upload | *(triggers file input)* | **Utility** |

### Identified Problems
1. **No tool categories** — 13 buttons in a flat 4-column grid is overwhelming
2. **No tool-running status** — only a generic "Thinking..." dot animation; no indication of *what* is running
3. **Missing `uploadFilesBtn` binding** — not in `toolBindings` array (it's handled separately but inconsistently)
4. **`last30days-research` missing from icons map** in `updateActiveToolsDisplay()`
5. **CSS responsive gap** — breakpoints at 768px and 480px but nothing at 600px; tools dropdown jumps from 4-col to 3-col abruptly
6. **Duplicate CSS selectors** — `.model-dropdown__group-label` (2x), `.topbar__btn` (3 variants)

---

## 2. Refactor Plan

### 2a. Group Tools into Categories (HTML + CSS)
Replace the flat `.tools-grid` with grouped sections using `<details>` elements with category headers.

**Categories:**
| Category | Icon | Tools |
|----------|------|-------|
| 🔍 Search | `search` | Web Search, Bing, Baidu, GitHub, Img Search |
| 🎨 Image | `image` | Image Gen, Img2Img, Lens, SauceNAO |
| 🧠 Reasoning | `brain` | Research (deep-research) |
| 🤖 Agent | `bot` | Social Research (last30days), Config Agent |
| 📎 Utility | `paperclip` | Upload Files, Branch Conversation |

**Approach:**
- Wrap each category in a `<div class="tools-category">` with a label
- Keep all existing button IDs unchanged
- Keep the `.tools-grid` class but scope to 3 columns within each category
- Categories are always expanded (no accordion — too slow for quick tool access)

### 2b. Tool-Running Status UI
Add a status indicator that shows what tools are actively running during SSE streaming.

**Approach:**
- Add a `<div id="toolStatusBar">` inside the loading indicator area
- Hook into `onMetadata` SSE event to detect tool activation
- Show status like "🔍 Searching web...", "🎨 Generating image...", "📊 Researching social media..."
- Map active tools to status messages
- Auto-clear on `onComplete` or `onError`

### 2c. Fix `updateActiveToolsDisplay()` Icons
Add missing icon for `last30days-research`.

### 2d. CSS Cleanup
- Add 600px breakpoint for smoother responsive transition
- Fix tools grid to 2-col on ≤480px
- No structural CSS changes to modals, sidebar, or topbar

---

## 3. Safety Constraints
- ✅ All existing element IDs preserved
- ✅ `toolBindings` array unchanged (same tool strings sent to backend)
- ✅ No backend API changes
- ✅ SSE event contract unchanged
- ✅ `window.getActiveTools()` returns same array
- ✅ Config Agent modal still opens via same flow
- ✅ Branch conversation still works via same button

---

## 4. Files Changed
| File | Change |
|------|--------|
| `templates/index.html` | Reorganize tools grid into categories, add tool status bar markup |
| `static/css/app.css` | Add `.tools-category` styles, status bar styles, 600px breakpoint |
| `templates/index.html` (inline script) | Update `updateActiveToolsDisplay()` icons, add `updateToolStatus()` function |

---

## 5. Manual Test Checklist
- [ ] Tools dropdown opens/closes on plus button click
- [ ] Each tool button toggles active state (accent highlight + dot indicator)
- [ ] Active tools show as badges above input area
- [ ] Tool categories display with labels
- [ ] Deep Research auto-enables Web Search + switches to multi-thinking
- [ ] Config Agent button opens modal (not a toggle)
- [ ] Upload button triggers file input
- [ ] Branch conversation works
- [ ] SSE streaming works: thinking → chunks → complete
- [ ] Tool status shows during generation (e.g., "Searching web..." when google-search is active)
- [ ] Tool status clears on completion
- [ ] Mobile (≤768px): dropdown full-width, 3-col grid
- [ ] Mobile (≤480px): 2-col grid
- [ ] Dark mode: all category labels and status bar readable
- [ ] Image generation inline loading placeholder still works
- [ ] Stop generation button still works

---


## 5. 2026-05 Stable Shell Refresh

**Goal:** Replace the unstable inline-script monolith with a small, modular,
backend-faithful UI shell. **No** React/Vite migration. **No** new AI features.
**No** changes to `/chat/stream` or any backend route.

### What changed
| Path | Change |
|---|---|
| `private/old_ALL_templates/` | Backup of previous UI (templates + 5 CSS + 36 JS files + manifest) |
| `services/chatbot/templates/index_legacy.html` | Verbatim rename of original `index.html`. **Not currently routed.** |
| `services/chatbot/templates/index.html` | New ~85-line shell. Loads 10 modular CSS files + `js/app/index.js`. |
| `services/chatbot/static/css/{tokens,layout,sidebar,topbar,chat,composer,tools,gallery,modals,debug}.css` | New modular stylesheets. Two themes: `dark` (default) + `eye-comfort`. |
| `services/chatbot/static/js/app/*.js` | 13 ES modules. See `js/app/README.md` for the architecture. |
| `services/chatbot/static/js/modules/README.md` | Marked as legacy. |

### Hard rules locked in
- Mongo is the source of truth; localStorage (`ui2:` namespace) is fallback only.
- No rendered HTML or base64 images are persisted.
- Finite state machine: `idle | composing | uploading | streaming | stopping | error`. UI gating reads `body[data-state]` only.
- Single in-flight stream. Each send gets a fresh `streamId`; late frames whose `streamId`/`conversation_id` mismatch the active context are dropped.
- Hidden in this shell by design: auth/login, quota, payment, profile, admin panel, bulk delete, drag reorder, storage gauge.
- Only two tool toggles: `web-search` (sends backend `google-search`) and `deep-research`.
- Debug panel (`Ctrl+Shift+D` or top-bar ⚙) captures `window.error`, `unhandledrejection`, and non-2xx fetches; surfaces them via toast.

### Backend untouched
`routes/main.py` still does `render_template('index.html')`. Because we replaced the file in place, no Flask change is required. Old behavior can be restored at any time by serving `index_legacy.html` instead — assets are intact in `private/old_ALL_templates/`.

### Verification
- `python run.py` (no env flags) → Flask legacy monolith mode → `GET /` renders the new shell.
- Boot order: dom verify → debug panel registers global hooks → controllers wire → conversation list loads → optional initial conversation from `/c/<id>` URL.
- Failure mode: any missing required DOM id surfaces a red error block; backend down surfaces a warn toast and falls back to cached conversations.

### Out of scope (deferred)
- Advanced markdown/syntax highlighting in messages.
- Thinking modes / reasoning visualization (events are received but not yet rendered).
- Image-generation tools, MCP tools, multi-agent council UI.
- Skill picker, character picker, job queue panel.

These can be added one at a time inside `js/app/` without disturbing the state machine or stream contract.
