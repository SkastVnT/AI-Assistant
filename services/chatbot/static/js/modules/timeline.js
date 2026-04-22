/**
 * Conversation timeline helpers — pure data, no DOM access.
 *
 * Goal: provide a single structured-first builder for the conversation
 * history that the chatbot sends to the backend. This is the incremental
 * step toward a fully event-sourced chat model. The functions here:
 *
 *   - prefer structured messages from session state over DOM scraping
 *   - merge generated-image asset records into the same timeline so the
 *     LLM sees them in chronological order with text turns
 *   - degrade gracefully when only legacy HTML messages exist
 *   - never emit unbounded payloads — caller-supplied caps are respected
 *
 * The timeline event shape is intentionally minimal so it can grow
 * without breaking older sessions:
 *
 *   {
 *     role:    'user' | 'assistant' | 'system',
 *     kind:    'text' | 'image-gen' | 'system-notice',
 *     content: string,                  // already truncated
 *     ts:      number | null,           // ms epoch
 *     meta:    { ... } | undefined      // optional, kind-specific
 *   }
 *
 * History (what we send to the LLM) keeps the legacy {role, content}
 * shape so the existing backend contract is unchanged. The richer
 * timeline is exposed for future code (UI, analytics) without forcing
 * a wire-protocol change today.
 */

const DEFAULT_MAX_MESSAGES = 30;
const DEFAULT_MAX_CHARS = 4000;

/**
 * Strip HTML tags and collapse whitespace. Used when the structured
 * message stored its content as HTML (assistant messages historically did).
 */
function stripHtml(input) {
    if (input == null) return '';
    const s = String(input);
    if (s.indexOf('<') === -1) return s;
    return s
        .replace(/<style[\s\S]*?<\/style>/gi, ' ')
        .replace(/<script[\s\S]*?<\/script>/gi, ' ')
        .replace(/<[^>]+>/g, ' ')
        .replace(/&nbsp;/g, ' ')
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/\s+/g, ' ')
        .trim();
}

function truncate(text, maxChars) {
    if (text == null) return '';
    const s = String(text);
    if (s.length <= maxChars) return s;
    return s.slice(0, maxChars) + '\n…(truncated)';
}

function tsToMs(value) {
    if (value == null) return null;
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'string') {
        const parsed = Date.parse(value);
        if (!Number.isNaN(parsed)) return parsed;
    }
    return null;
}

/**
 * Project a structured message (from message-model.js) into a
 * timeline event. Returns null when the message has no usable content.
 */
function structuredToEvent(msg, maxChars) {
    if (!msg || typeof msg !== 'object') return null;
    const role = msg.role === 'user' || msg.role === 'system' ? msg.role : 'assistant';

    let raw = msg.content;
    // Assistant messages historically stored inner HTML in `content`;
    // strip tags so the LLM doesn't see markup it can't reason about.
    if (role !== 'user') {
        raw = stripHtml(raw);
    } else if (raw == null && msg.html) {
        // User message somehow lost its content but kept html — recover.
        raw = stripHtml(msg.html);
    }
    raw = (raw || '').trim();
    if (!raw) return null;

    return {
        role,
        kind: msg.kind && msg.kind === 'image-gen' ? 'image-gen' : 'text',
        content: truncate(raw, maxChars),
        ts: tsToMs(msg.createdAt),
        meta: msg.meta && msg.meta.model ? { model: msg.meta.model } : undefined,
    };
}

/**
 * Project a generated-image asset record into a timeline event so the
 * LLM sees it interleaved with text turns instead of as an unrelated
 * appendix. Mirrors the asset_memory schema on the backend.
 */
function imageRecordToEvent(rec, maxChars) {
    if (!rec || typeof rec !== 'object') return null;
    const promptText = rec.prompt ? String(rec.prompt) : '';
    const url = rec.url ? String(rec.url) : '';
    if (!promptText && !url && !rec.job_id) return null;

    const bits = [];
    if (rec.job_id) bits.push(`job=${rec.job_id}`);
    if (rec.provider || rec.model) bits.push(`by ${rec.provider || '?'}/${rec.model || '?'}`);
    if (rec.preset) bits.push(`preset=${rec.preset}`);
    if (rec.character_key) bits.push(`character=${rec.character_key}`);
    const head = bits.length ? `[generated image] ${bits.join(' | ')}` : '[generated image]';
    const lines = [head];
    if (promptText) lines.push(`prompt: ${promptText}`);
    if (url) lines.push(`url: ${url}`);

    return {
        role: 'system',
        kind: 'image-gen',
        content: truncate(lines.join('\n'), maxChars),
        ts: tsToMs(rec.timestamp),
        meta: { jobId: rec.job_id || null },
    };
}

/**
 * Build the merged, time-ordered timeline of conversation events.
 *
 * @param {Object} session         - Chat session (may have structuredMessages, messages, generatedImages)
 * @param {Object} [opts]
 * @param {number} [opts.maxMessages=30]
 * @param {number} [opts.maxChars=4000]
 * @param {Function} [opts.legacyMigrator] - Optional: fn(htmlString, index) → structured.
 *                   Provided so the browser can plug in DOMParser-based migration
 *                   from message-model.js; tests can omit it.
 * @returns {Array<Event>} Time-ordered timeline events (capped to maxMessages).
 */
export function buildTimeline(session, opts = {}) {
    const maxMessages = Number.isFinite(opts.maxMessages) ? opts.maxMessages : DEFAULT_MAX_MESSAGES;
    const maxChars = Number.isFinite(opts.maxChars) ? opts.maxChars : DEFAULT_MAX_CHARS;
    if (!session || typeof session !== 'object') return [];

    let structured = Array.isArray(session.structuredMessages) ? session.structuredMessages : [];

    // Legacy fallback: if no structured messages exist but we have raw HTML
    // strings AND a migrator was supplied, lazily project them. The browser
    // path passes legacyHtmlToStructured here; pure-data tests skip it.
    if (structured.length === 0
            && Array.isArray(session.messages)
            && session.messages.length > 0
            && typeof opts.legacyMigrator === 'function') {
        try {
            structured = session.messages.map((html, i) => opts.legacyMigrator(html, i));
        } catch (_) {
            structured = [];
        }
    }

    const events = [];
    for (const msg of structured) {
        const ev = structuredToEvent(msg, maxChars);
        if (ev) events.push(ev);
    }

    const images = Array.isArray(session.generatedImages) ? session.generatedImages : [];
    for (const rec of images) {
        const ev = imageRecordToEvent(rec, maxChars);
        if (ev) events.push(ev);
    }

    // Stable sort: events with no ts keep insertion order relative to dated events.
    // Use a fallback monotonic sequence so equal/missing ts do not shuffle.
    events.forEach((ev, idx) => { ev._seq = idx; });
    events.sort((a, b) => {
        const at = a.ts == null ? 0 : a.ts;
        const bt = b.ts == null ? 0 : b.ts;
        if (at !== bt) return at - bt;
        return a._seq - b._seq;
    });
    events.forEach((ev) => { delete ev._seq; });

    // Keep only the most recent N events.
    return events.length > maxMessages ? events.slice(-maxMessages) : events;
}

/**
 * Build the wire-format conversation history the backend expects.
 * This is the structured-first replacement for buildConversationHistory()
 * that scraped the DOM. The shape of each item — {role, content} — is
 * preserved so the backend contract does not change.
 *
 * Image-gen events are included as role='system' so the LLM can see them
 * but they don't get attributed to the user or assistant.
 */
export function buildHistoryFromTimeline(session, opts = {}) {
    const timeline = buildTimeline(session, opts);
    return timeline.map((ev) => ({
        role: ev.role,
        content: ev.content,
    }));
}

// Exports for test introspection — not part of the public API.
export const __test__ = { stripHtml, truncate, tsToMs, structuredToEvent, imageRecordToEvent };
