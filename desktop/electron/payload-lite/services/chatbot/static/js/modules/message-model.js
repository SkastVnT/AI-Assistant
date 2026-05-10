/**
 * Structured Message Model — single source of truth for chat message data.
 *
 * Schema version history:
 *   1 — initial structured model (id, role, kind, content, html, meta, attachments, createdAt, versions)
 *
 * Legacy sessions store messages as HTML strings in session.messages[].
 * New sessions store structured objects in session.structuredMessages[].
 * The loader detects which format is present and handles both.
 */

export const MESSAGE_SCHEMA_VERSION = 1;

/**
 * Create a new structured message object.
 *
 * @param {Object} opts
 * @param {string}  opts.role         - 'user' | 'assistant' | 'system'
 * @param {string}  [opts.kind]       - 'text' | 'image' | 'file' | 'image-gen' | 'video-gen' | 'error' | 'thinking'
 * @param {string}  opts.content      - Raw content (markdown for assistant, plain text for user)
 * @param {string}  [opts.html]       - Pre-rendered HTML snapshot (cache, not source of truth)
 * @param {Object}  [opts.meta]       - Arbitrary metadata
 * @param {Array}   [opts.attachments]- File / image attachment descriptors
 * @param {string}  [opts.createdAt]  - ISO timestamp (auto-set if omitted)
 * @param {Array}   [opts.versions]   - Edit version history
 * @returns {Object} Structured message
 */
export function createMessage(opts = {}) {
    return {
        id:          opts.id || `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        role:        opts.role || 'user',
        kind:        opts.kind || 'text',
        content:     opts.content ?? '',
        html:        opts.html ?? null,
        meta:        Object.assign({
            model:      null,
            context:    null,
            thinkingMode: null,
            thinkingProcess: null,
            customPrompt: false,
            agentConfig:  null,
            feedback:     null,   // 'like' | 'dislike' | null
            imageGen:     null,   // { provider, prompt, regenCount, ... }
        }, opts.meta || {}),
        attachments: opts.attachments || [],
        createdAt:   opts.createdAt || new Date().toISOString(),
        versions:    opts.versions || [],
        _v:          MESSAGE_SCHEMA_VERSION,
    };
}

/**
 * Detect whether a session uses the structured format.
 * @param {Object} session
 * @returns {boolean}
 */
export function isStructuredSession(session) {
    return Array.isArray(session.structuredMessages) && session.structuredMessages.length > 0;
}

// ─── DOM ↔ Structured conversion helpers ─────────────────────────

/**
 * Extract a structured message from a rendered DOM element.
 * Used during save to capture data from live DOM.
 *
 * @param {HTMLElement} el - A .message div in the chat container
 * @returns {Object} Structured message
 */
export function domToStructured(el) {
    const isUser = el.classList.contains('user');
    const role   = isUser ? 'user' : (el.classList.contains('system') ? 'system' : 'assistant');

    // Extract raw text content (markdown source for assistant, plain for user)
    const textEl = el.querySelector('.message-text');
    let content = '';
    if (textEl) {
        if (role === 'user') {
            // User messages: collect text from .user-line spans or direct text
            const lines = textEl.querySelectorAll('.user-line');
            if (lines.length > 0) {
                content = Array.from(lines).map(l => l.textContent).join('\n');
            } else {
                content = textEl.textContent || '';
            }
        } else {
            // Assistant messages: store inner HTML as content since markdown source is lost
            content = textEl.innerHTML || '';
        }
    }

    // Meta from data attributes
    const meta = {
        model:      el.dataset.model || null,
        context:    el.dataset.context || null,
        thinkingMode: null,
        thinkingProcess: null,
        customPrompt: false,
        agentConfig: null,
        feedback:   el.dataset.feedback || null,
        imageGen:   null,
    };

    // Capture image-gen metadata
    if (el.dataset.igv2Provider) {
        meta.imageGen = {};
        for (const [key, val] of Object.entries(el.dataset)) {
            if (key.startsWith('igv2')) {
                meta.imageGen[key] = val;
            }
        }
    }

    // Thinking process
    const thinkingPill = el.querySelector('.thinking-pill');
    if (thinkingPill) {
        const thinkContent = thinkingPill.querySelector('.thinking-content');
        if (thinkContent) {
            meta.thinkingProcess = thinkContent.textContent || null;
        }
    }

    // Attachments — images and files
    const attachments = [];
    const fileCards = el.querySelectorAll('.file-message-card');
    fileCards.forEach(card => {
        const nameEl = card.querySelector('.file-message-name');
        const img = card.querySelector('.file-message-preview img');
        attachments.push({
            type: img ? 'image' : 'file',
            name: nameEl ? nameEl.textContent : '',
            src:  img ? img.src : null,
        });
    });

    // Inline images in assistant messages (base64 or URL)
    if (role === 'assistant' && textEl) {
        textEl.querySelectorAll('img').forEach(img => {
            if (img.closest('.file-message-card')) return; // already captured
            attachments.push({
                type: 'image',
                name: img.alt || '',
                src:  img.src,
            });
        });
    }

    // Determine kind
    let kind = 'text';
    if (attachments.length > 0 && !content.trim()) {
        kind = attachments[0].type === 'image' ? 'image' : 'file';
    } else if (meta.imageGen) {
        kind = 'image-gen';
    }

    return createMessage({
        id:          el.dataset.messageId || `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        role,
        kind,
        content,
        html:        el.outerHTML,
        meta,
        attachments,
        createdAt:   el.dataset.timestamp || new Date().toISOString(),
        versions:    [],   // Versions managed separately in session.messageVersions
    });
}

// ─── Version-history helpers ─────────────────────────────────────

/**
 * Create a structured version-history entry.
 * Centralises the shape so callers cannot accidentally omit new fields.
 *
 * @param {Object} opts
 * @param {string}  opts.userContent        - User message text (plain)
 * @param {string}  [opts.assistantContent]  - Raw API response (markdown/text) — data-first field
 * @param {string}  opts.assistantResponse   - Rendered HTML cache (for fast restore / backward compat)
 * @param {string}  [opts.timestamp]         - ISO timestamp
 * @returns {Object} Version entry
 */
export function createVersionEntry(opts = {}) {
    return {
        userContent:      opts.userContent ?? '',
        assistantContent: opts.assistantContent ?? null,   // raw API response — null for DOM-captured versions
        assistantResponse: opts.assistantResponse ?? '',   // HTML cache / legacy field
        timestamp:        opts.timestamp || new Date().toISOString(),
    };
}

/**
 * Detect whether a version entry was created with the structured format.
 * Legacy entries have no `assistantContent` property.
 */
export function isStructuredVersion(version) {
    return version != null && 'assistantContent' in version;
}

/**
 * Detect whether branch data uses the new structured format.
 * Legacy: Array of HTML strings.  New: { html: [...], structured: [...] }
 */
export function isStructuredBranch(branchData) {
    return branchData != null && !Array.isArray(branchData) && Array.isArray(branchData.html);
}

// ─── Legacy migration helpers ────────────────────────────────────

/**
 * Convert a legacy HTML string message to a structured message.
 * Used during migration when loading old sessions.
 *
 * @param {string} htmlString - Raw HTML string from legacy session.messages[]
 * @param {number} index      - Position in the message array
 * @returns {Object} Structured message (best-effort extraction)
 */
export function legacyHtmlToStructured(htmlString, index) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlString, 'text/html');
    const el = doc.body.firstElementChild;

    if (!el) {
        // Totally unparseable — wrap as raw system message
        return createMessage({
            id:      `legacy_${index}_${Date.now()}`,
            role:    'system',
            kind:    'text',
            content: htmlString,
            html:    htmlString,
        });
    }

    const msg = domToStructured(el);
    // Override ID to preserve dataset messageId if present, else generate from index
    if (!el.dataset.messageId) {
        msg.id = `legacy_${index}_${Date.now()}`;
    }
    return msg;
}
