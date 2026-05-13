# Chat CSS Map

`../app.css` is the public entrypoint. It is now a manifest that imports these files in cascade order. Keep that import order stable unless you are intentionally changing visual precedence.

| Feature | CSS file | Template partial | JS owner |
|---|---|---|---|
| Theme tokens, icon sizing | `00-tokens.css` | `_head_assets.html` | `modules/ui-utils.js` |
| Base reset and scrollbars | `01-base.css` | all partials | browser/runtime |
| App frame | `02-layout.css` | `index.html` shell | `main.js`, `modules/split-view.js` |
| Conversation sidebar | `03-sidebar.css` | `_sidebar.html` | `modules/ui-utils.js`, `modules/chat-manager.js` |
| Topbar, model menu, chips | `04-topbar.css` | `_topbar.html` | `model-selector.js`, `topbar-tools.js`, `skill-selector.js` |
| Right status sidebar | `05-right-sidebar.css` | `_right_sidebar.html` | `modules/right-sidebar.js` |
| Chat area and welcome screen | `06-chat-area.css` | `_chat_area.html` | `welcome-suggestions.js` |
| Messages and markdown | `07-messages-markdown.css` | generated messages | `modules/message-renderer.js` |
| Thinking UI and loading | `08-thinking.css` | `_right_sidebar.html`, generated messages | `thinking-panel.js`, `modules/message-renderer.js` |
| Composer and advanced settings | `09-composer.css` | `_composer.html` | `main.js`, `modules/file-handler.js` |
| Tools and skill state | `10-tools-skill.css` | `_topbar.html`, `_composer.html` | `tool-state.js`, `skill-selector.js` |
| Shared modals, buttons, MCP, memory | `11-modals-shared.css` | modal/MCP partials | `mcp.js`, `modules/overlay-manager.js` |
| Gallery, image preview, video jobs | `12-gallery-media.css` | `_modals_shared.html`, `_modals_video.html` | `modules/gallery-manager.js`, `modules/video-gen.js` |
| Main responsive rules | `90-responsive.css` | all partials | viewport/browser |
| Utilities and compatibility | `13-utilities-compat.css` | all partials | multiple modules |
| Message actions and suggestions | `14-message-actions.css` | generated messages | `modules/message-renderer.js` |
| File, text, CSV, and storage previews | `15-file-table-preview.css` | `_composer.html`, generated modals | `modules/file-handler.js`, `modules/csv-preview.js` |
| Inline image generation UX | `16-inline-image-gen.css` | generated messages | `modules/image-gen-v2.js`, `modules/send-message-helpers.js` |
| Inline and enhanced tables | `17-table-markdown.css` | generated messages | `modules/message-renderer.js`, `modules/csv-preview.js` |
| Reduced motion and late typography overrides | `99-utilities-overrides.css` | generated messages | browser/runtime |

Critical JS-controlled classes: `.active`, `.hidden`, `.open`, `.collapsed`, `.light-mode`, `.eye-care-mode`, `.streaming-cursor`. Do not rename or remove them without updating the owning JS.
