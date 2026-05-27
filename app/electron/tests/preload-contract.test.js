/**
 * preload-contract.test.js
 *
 * Verifies the desktopAPI surface contract and Electron security settings
 * by inspecting the source files without loading Electron.
 *
 * Run with: node tests/preload-contract.test.js
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const preloadSrc = fs.readFileSync(path.join(__dirname, '..', 'src', 'preload.js'), 'utf8');
const mainSrc    = fs.readFileSync(path.join(__dirname, '..', 'src', 'main.js'),    'utf8');

// ─── desktopAPI surface ────────────────────────────────────────────────────

const EXPECTED_SURFACE = [
    'isDesktop',
    'platform',
    'window',
    'window.minimize',
    'window.maximize',
    'window.close',
    'window.isMaximized',
    'window.onMaximizedChanged',
    'tray',
    'tray.setBadge',
    'notify',
    'notify.show',
];

for (const key of EXPECTED_SURFACE) {
    const leaf = key.split('.').pop();
    assert.ok(
        preloadSrc.includes(leaf + ':') || preloadSrc.includes(leaf + '('),
        `preload.js must expose desktopAPI.${key}`
    );
}

// ─── contextBridge.exposeInMainWorld ──────────────────────────────────────

assert.ok(
    preloadSrc.includes("contextBridge.exposeInMainWorld('desktopAPI'"),
    "preload.js must expose 'desktopAPI' via contextBridge"
);

// ─── Security: no direct ipcRenderer.send (only invoke) ──────────────────

const dangerousAPIs = ['ipcRenderer.send', 'ipcRenderer.sendSync', 'remote.'];
for (const api of dangerousAPIs) {
    assert.ok(
        !preloadSrc.includes(api),
        `preload.js must not use dangerous API: ${api}`
    );
}

// ─── Security: webPreferences in main.js ─────────────────────────────────

assert.ok(
    mainSrc.includes('nodeIntegration: false'),
    'main.js must set nodeIntegration: false'
);
assert.ok(
    mainSrc.includes('contextIsolation: true'),
    'main.js must set contextIsolation: true'
);
assert.ok(
    mainSrc.includes('sandbox: true'),
    'main.js must set sandbox: true'
);

// ─── isDesktop is a literal true, not runtime-evaluable ──────────────────

assert.ok(
    preloadSrc.includes('isDesktop: true'),
    'preload.js must hardcode isDesktop: true (not a function call)'
);

// ─── Object.freeze on API root and sub-objects ───────────────────────────

const freezeCount = (preloadSrc.match(/Object\.freeze/g) || []).length;
assert.ok(
    freezeCount >= 3,
    `preload.js must call Object.freeze on api root + sub-objects (found ${freezeCount}, need >= 3)`
);

console.log('preload contract tests passed');
