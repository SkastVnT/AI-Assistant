# Chat Template Partials

`index.html` is only the composition shell. Open the smallest partial or script below for focused edits.

| Feature | Template partial | Main JS/static owner |
|---|---|---|
| Head assets, CSS, CDN libs | `_head_assets.html` | `main.js`, loaded CDN scripts |
| Electron titlebar + JS debug overlay markup | `_titlebar_debug.html` | `debug-overlay.js`, `modules/electron-bridge.js` |
| Conversation sidebar | `_sidebar.html` | `main.js`, `modules/chat-manager.js`, `modules/ui-utils.js` |
| Topbar selectors and creative entry buttons | `_topbar.html` | `model-selector.js`, `thinking-mode-selector.js`, `skill-selector.js`, `topbar-tools.js` |
| Chat messages, loading, memory panel | `_chat_area.html` | `main.js`, `modules/message-renderer.js`, `modules/memory-manager.js` |
| Composer, attachments, tool buttons | `_composer.html` | `tool-state.js`, `quick-tools-glue.js`, `modules/file-handler.js` |
| MCP context panel | `_mcp_sidebar.html` | `mcp.js` |
| Image generation and SDXL modals | `_modals_image.html` | `modules/image-gen-v2.js`, `modules/image-gen.js`, `style-presets.js` |
| Video generation modal | `_modals_video.html` | `modules/video-gen.js` |
| Nano Banana, gallery, preview, Config Agent | `_modals_shared.html` | `modules/nano-banana.js`, `config-agent.js` |
| Right status panel, thinking panel, compatibility elements | `_right_sidebar.html` | `modules/right-sidebar.js`, `thinking-panel.js` |
| Script loading and Jinja-only Firebase logging | `_scripts.html`, `_firebase_logging.html` | files listed in `_scripts.html` |

Keep route and payload contracts aligned with `routes/stream.py`; the tool list still reaches the backend through `window.getActiveTools()`.
