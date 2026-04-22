/**
 * Focused tests for modules/timeline.js — the structured-first history
 * builder. Pure JS, no DOM, executable directly via `node test_timeline.mjs`.
 *
 * Each test is self-contained; the runner exits non-zero on the first
 * failure so the pytest wrapper can surface the assertion. We avoid any
 * test framework so this works in venv-core without npm packages.
 */
import { buildTimeline, buildHistoryFromTimeline } from '../static/js/modules/timeline.js';

let ok = 0;
let failed = 0;
const failures = [];

function check(name, cond, detail) {
    if (cond) {
        ok++;
        console.log(`PASS ${name}`);
    } else {
        failed++;
        failures.push({ name, detail });
        console.log(`FAIL ${name}${detail ? ' :: ' + detail : ''}`);
    }
}

function eq(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
}

// ─── 1. Structured-first preferred over legacy HTML ──────────────────────
{
    const session = {
        structuredMessages: [
            { role: 'user', kind: 'text', content: 'Hello', createdAt: '2026-04-01T10:00:00Z' },
            { role: 'assistant', kind: 'text', content: 'Hi there', createdAt: '2026-04-01T10:00:01Z' },
        ],
        // Legacy HTML present too — must be ignored when structured exists.
        messages: ['<div class="message user"><div class="message-text">SHOULD-NOT-APPEAR</div></div>'],
        generatedImages: [],
    };
    const history = buildHistoryFromTimeline(session);
    check('structured preferred over legacy HTML', eq(history, [
        { role: 'user', content: 'Hello' },
        { role: 'assistant', content: 'Hi there' },
    ]));
}

// ─── 2. Legacy migration runs only when migrator supplied ────────────────
{
    const session = {
        structuredMessages: [],
        messages: ['<div class="message user"><div class="message-text">Legacy hi</div></div>'],
        generatedImages: [],
    };
    // Without migrator: legacy ignored, history empty.
    const noMigrate = buildHistoryFromTimeline(session);
    check('legacy ignored without migrator', noMigrate.length === 0,
        `got ${JSON.stringify(noMigrate)}`);

    // With a fake migrator that returns a structured object.
    const fakeMigrator = (html, i) => ({
        role: 'user',
        kind: 'text',
        content: 'migrated-' + i,
        createdAt: '2026-04-01T09:00:00Z',
    });
    const migrated = buildHistoryFromTimeline(session, { legacyMigrator: fakeMigrator });
    check('legacy migrator invoked when supplied', eq(migrated, [
        { role: 'user', content: 'migrated-0' },
    ]));
}

// ─── 3. Generated images merged as system events in order ────────────────
{
    const session = {
        structuredMessages: [
            { role: 'user', kind: 'text', content: 'draw a cat', createdAt: '2026-04-01T10:00:00Z' },
            { role: 'assistant', kind: 'text', content: 'sure', createdAt: '2026-04-01T10:00:05Z' },
            { role: 'user', kind: 'text', content: 'now bigger', createdAt: '2026-04-01T10:01:00Z' },
        ],
        generatedImages: [
            {
                job_id: 'job_42',
                url: 'https://cdn/cat.png',
                prompt: 'cat',
                provider: 'local',
                model: 'anime_xl',
                preset: 'anime_quality',
                timestamp: Date.parse('2026-04-01T10:00:30Z'),
            },
        ],
    };
    const timeline = buildTimeline(session);
    check('image event interleaved between turns',
        timeline.length === 4
        && timeline[0].role === 'user'
        && timeline[1].role === 'assistant'
        && timeline[2].role === 'system' && timeline[2].kind === 'image-gen'
        && timeline[3].role === 'user',
        `got ${JSON.stringify(timeline.map(e => `${e.role}/${e.kind}`))}`);

    const imageEv = timeline[2];
    check('image event includes prompt + url + meta',
        imageEv.content.includes('cat')
        && imageEv.content.includes('cdn/cat.png')
        && imageEv.content.includes('job=job_42')
        && imageEv.content.includes('preset=anime_quality')
        && imageEv.meta && imageEv.meta.jobId === 'job_42',
        imageEv.content);

    // History view exposes them as system messages.
    const history = buildHistoryFromTimeline(session);
    check('history exposes image event as system role',
        history.length === 4 && history[2].role === 'system'
        && history[2].content.includes('[generated image]'),
        JSON.stringify(history));
}

// ─── 4. Cap and truncation respected ─────────────────────────────────────
{
    const structured = [];
    for (let i = 0; i < 50; i++) {
        structured.push({
            role: i % 2 === 0 ? 'user' : 'assistant',
            kind: 'text',
            content: 'msg-' + i,
            createdAt: new Date(Date.UTC(2026, 0, 1, 0, 0, i)).toISOString(),
        });
    }
    const session = { structuredMessages: structured, generatedImages: [] };
    const history = buildHistoryFromTimeline(session, { maxMessages: 5 });
    check('history capped to maxMessages', history.length === 5,
        `got length ${history.length}`);
    check('history keeps the most recent turns',
        history[0].content === 'msg-45' && history[4].content === 'msg-49',
        `got ${history.map(h => h.content).join(',')}`);

    // Per-message truncation
    const long = 'x'.repeat(10_000);
    const longSession = {
        structuredMessages: [{ role: 'user', kind: 'text', content: long, createdAt: '2026-04-01T00:00:00Z' }],
        generatedImages: [],
    };
    const longHist = buildHistoryFromTimeline(longSession, { maxChars: 100 });
    check('per-message content truncated',
        longHist[0].content.length <= 100 + 20  // +20 for the truncation marker
        && longHist[0].content.endsWith('(truncated)'),
        `length=${longHist[0].content.length}`);
}

// ─── 5. Safe missing/malformed input handling ────────────────────────────
{
    check('null session yields empty', eq(buildTimeline(null), []));
    check('undefined session yields empty', eq(buildTimeline(undefined), []));
    check('empty session yields empty', eq(buildHistoryFromTimeline({}), []));

    const messy = {
        structuredMessages: [
            null,
            'string-not-object',
            { role: 'user', kind: 'text', content: '   ' },         // empty after trim
            { role: 'user', kind: 'text', content: 'real' },
        ],
        generatedImages: [
            null,
            { foo: 'bar' },                                          // no usable fields
            { url: 'https://x/a.png', prompt: 'p', timestamp: 1 },
        ],
    };
    const history = buildHistoryFromTimeline(messy);
    check('messy input keeps only usable items',
        history.length === 2
        && history.some(h => h.content === 'real')
        && history.some(h => h.role === 'system' && h.content.includes('https://x/a.png')),
        JSON.stringify(history));
}

// ─── 6. Assistant HTML content gets stripped ─────────────────────────────
{
    const session = {
        structuredMessages: [
            { role: 'assistant', kind: 'text',
              content: '<p>Hello <strong>world</strong></p><script>alert(1)</script>',
              createdAt: '2026-04-01T10:00:00Z' },
        ],
        generatedImages: [],
    };
    const history = buildHistoryFromTimeline(session);
    check('assistant HTML content stripped',
        history.length === 1
        && history[0].content === 'Hello world'
        && !history[0].content.includes('<')
        && !history[0].content.toLowerCase().includes('alert'),
        JSON.stringify(history));
}

// ─── Result ──────────────────────────────────────────────────────────────
console.log(`\n${ok} passed, ${failed} failed`);
if (failed > 0) {
    console.log('FAILURES:');
    for (const f of failures) console.log(' -', f.name, f.detail || '');
    process.exit(1);
}
process.exit(0);
