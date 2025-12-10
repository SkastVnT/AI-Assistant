# Changelog

All notable changes to ChatBot AI Assistant will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2025-11-04

### 🎉 Major Release - Complete UX Overhaul

### Added
- **Auto-File Analysis**: Upload files and get instant AI analysis without typing
  - Support for code files (.py, .js, .html, .css, .json)
  - Document processing (.pdf, .doc, .docx, .txt)
  - Image recognition
  - Automatic prompt generation with detailed requirements
  
- **Stop Generation Feature**: Interrupt AI mid-response
  - Stop button in loading indicator
  - AbortController integration for fetch cancellation
  - Partial response preservation with "stopped" indicator
  - Graceful error handling for aborted requests
  
- **Message History Versioning**: Track multiple response versions
  - Version tracking per message ID
  - Support for regeneration with version increment
  - Future: UI for browsing versions
  
- **Fancy Storage Display**: Visual progress bar with status indicators
  - 💚 Green (0-50%): Good status
  - 🟡 Yellow (50-80%): Warning
  - 🔴 Red (80-100%): Full
  - One-click cleanup button
  - Keeps 5 most recent chats
  
- **File Messages in Chat**: Files display as message bubbles
  - Grid layout with file cards
  - Image previews for photos
  - File type icons (🖼️ 📕 🐍 📜 etc.)
  - Size and metadata display
  - Hover effects and animations

### Changed
- **Full-Screen Layout**: ChatGPT-like interface
  - Body: 100vh height, no overflow
  - Chat container: flex: 1, full viewport utilization
  - Messages: 85% max-width (increased from 70%)
  - Removed unnecessary padding and margins
  
- **Enhanced Chat Items**: Better visibility in sidebar
  - Solid borders and shadows
  - Active state: solid blue (#667eea) with white indicator
  - Icons: 💬 (normal chat) vs ✨ (special chat)
  - Removed transform animations
  
- **Centered Header**: Title and subtitle centered
  - Flexbox layout with space-between
  - GitHub badge on the right
  - Responsive design
  
- **Timestamp Logic**: Fixed "pop-up" animation issue
  - Timestamps only update on new messages
  - Not updated when switching chats
  - Prevents chat items from jumping

### Fixed
- Chat items no longer animate/jump when switching conversations
- File upload input properly clears after selection
- Storage display accurately reflects usage
- Loading indicator properly shows/hides
- Dark mode consistency across all components

### Technical
- **Module Refactoring**: ES6 module architecture
  - main.js: Main app controller
  - chat-manager.js: Session management
  - api-service.js: API communications with AbortSignal support
  - ui-utils.js: UI utilities
  - message-renderer.js: Message rendering + file messages
  - file-handler.js: File processing and management
  - memory-manager.js: Memory features
  - image-gen.js: Image generation
  - export-handler.js: PDF export

- **Storage Optimization**:
  - Image compression to 60% quality
  - Max thumbnail size: 800x800px
  - Text content truncation for large files
  - Automatic cleanup on quota exceeded
  
- **Performance Improvements**:
  - Debounced textarea resizing
  - Lazy file content loading
  - Virtual scrolling in chat container
  - Optimized CSS with GPU acceleration

---

## [1.8.0] - 2024-10-15

### Added
- Image-to-Image (img2img) generation support
- LoRA model integration
- VAE model selection
- Feature extraction from images (DeepDanbooru, CLIP, WD14)
- Multi-model ensemble tagging
- Prompt history and templates

### Changed
- Improved image generation UI with tabs
- Enhanced model selection interface
- Better error handling for SD API

### Fixed
- SD API connection stability
- Image generation progress tracking
- Model loading timeout issues

---

## [1.5.0] - 2024-08-20

### Added
- Local Qwen 1.5-1.8B model support
- Conversation memory system
- Message editing and regeneration
- PDF export functionality
- Dark mode toggle
- Sidebar for chat history

### Changed
- Migrated to modular JavaScript architecture
- Improved responsive design
- Enhanced markdown rendering

### Fixed
- Memory leak in chat history
- Image loading performance
- Mobile viewport issues

---

## [1.0.0] - 2024-06-01

### Added
- Initial release
- Multi-model support (GPT-4, Gemini)
- Basic text-to-image generation
- Simple chat interface
- Message history storage

---

## Future Roadmap

### Planned for v2.1.0
- [ ] Message version browsing UI
- [ ] Drag & drop file upload
- [ ] File preview modal
- [ ] Batch file operations
- [ ] Conversation search

### Planned for v2.5.0
- [ ] Voice input/output
- [ ] Real-time collaboration
- [ ] Cloud sync
- [ ] Mobile app (PWA)

### Planned for v3.0.0
- [ ] TypeScript migration
- [ ] Unit test coverage
- [ ] E2E testing suite
- [ ] Performance profiling
- [ ] Accessibility (WCAG 2.1 AA)

---

## Legend

- **Added**: New features
- **Changed**: Changes to existing features
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
- **Technical**: Internal/developer-facing changes

---

**Maintained by:** @SkastVnT
**Repository:** [AI-Assistant/ChatBot](https://github.com/SkastVnT/AI-Assistant/tree/master/ChatBot)
