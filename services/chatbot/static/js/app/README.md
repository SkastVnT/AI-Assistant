# Stable UI Shell — `static/js/app/`

Active frontend for `templates/index.html`. Keep this small, stable, and dependency-free.

## Boot order
`index.js` is the only entry. It:
1. Calls `initDom()` to cache and verify required element ids (loud failure on missing).
2. Calls `initDebugPanel()` first so global error hooks are installed before anything else can throw.
3. Restores theme from `localStorage["ui2:theme"]` (`dark` | `eye-comfort`).
4. Wires top bar, then `initTools/initComposer/initSidebar/initGallery`.
5. Loads conversation list, then resolves initial conversation from `/c/<id>` URL or `ui2:lastActiveChatId`.

## Modules

| File | Role |
|---|---|
| `dom.js` | Cached `getElementById`. Throws on missing required ids. |
| `state.js` | Single `appState` object + `setStatus()`. Statuses: `idle` `composing` `uploading` `streaming` `stopping` `error`. Writes `body[data-state="…"]`. Emits `appstatechange`. |
| `api.js` | REST + SSE wrappers. Backend contract unchanged. `setFetchHook()` lets debug panel observe every request. |
| `chat-store.js` | Mongo-first repository. localStorage cache under `ui2:` keys. Caps at 200 messages. Strips base64 before persist. |
| `chat-renderer.js` | Pure DOM renderers. Tiny markdown (code fences + line breaks). Never reads from state. |
| `stream-controller.js` | Owns one in-flight stream. Generates a fresh `streamId`, drops frames whose stream/conv id doesn't match the current context. Always returns to `idle` and refocuses the input. |
| `composer-controller.js` | Input box, attach, Enter sends / Shift+Enter newline, send/stop button gating. |
| `sidebar-controller.js` | Conversation list, new chat, refresh, single delete. **No bulk delete, no drag, no quota, no payment, no profile, no admin.** |
| `tools-controller.js` | Two toggles only: `web-search` (→ `google-search`) and `deep-research`. |
| `gallery-controller.js` | Right-panel gallery; rebuilds from `appState.messages.flatMap(images)`. Click → lightbox. |
| `toast.js` | `toast.info / success / warn / error`. Click to dismiss. |
| `debug-panel.js` | Captures `window.error`, `unhandledrejection`, fetch failures. Live state pane. Toggle: `Ctrl+Shift+D` or top-bar ⚙ button. |
| `index.js` | Boot. |

## Hard rules

- **Mongo is the source of truth.** localStorage is a fallback cache only.
- **Never store rendered HTML.** Only structured `{id, role, content, parts, images, createdAt, status}`.
- **Never persist base64.** `chat-store.js` strips before write.
- **Never bypass the state machine.** All UI gating reads `appState.status`.
- **Drop late stream frames.** `streamId` and `conversation_id` must match the current context or the frame is ignored.
- **No new dependencies.** Plain ES modules, no bundler, no React.
- **Backend contract unchanged.** `POST /chat/stream`, `GET/DELETE /conversations`, `POST /conversations/new`, `POST /conversations/<id>/switch`.

## Restoring the legacy UI

The previous monolithic UI is intact at `templates/index_legacy.html` plus the old assets in `private/old_ALL_templates/`. To temporarily serve it, swap the template name in `routes/main.py` (`render_template('index_legacy.html')`) — no other change required.
