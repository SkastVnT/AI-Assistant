/* backend-process.js — spawn services/chatbot/run.py and wait for /health.
 *
 * Pure helper. No Electron imports. Returns a Promise<{ child, baseUrl }>.
 *
 * Health probe order:
 *   1. GET http://127.0.0.1:PORT/health   (Flask + FastAPI both expose this)
 *   2. GET http://127.0.0.1:PORT/         (final fallback)
 *
 * Resolves once any probe returns < 500. Rejects on spawn error or timeout.
 */
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');

const HOST = '127.0.0.1';
const PORT = parseInt(process.env.AI_ASSISTANT_PORT || process.env.FLASK_PORT || '5000', 10);
const STARTUP_TIMEOUT_MS = 90_000;
const PROBE_INTERVAL_MS = 500;

// Resolve the repo / payload root.
//   - In dev (`npm run dev`)            -> three levels up (repo checkout)
//   - In a packaged installer build      -> <resources>/app-payload/  (see electron-builder.yml)
//   - In a local packaged build          -> traverse up from exe until services/chatbot/run.py found
// `process.resourcesPath` is provided by Electron only in packaged builds.
function resolveRepoRoot() {
    const fs = require('fs');
    const MARKER = path.join('services', 'chatbot', 'run.py');

    // 1. Installer build: app-payload bundled inside resources.
    if (process.resourcesPath) {
        const packagedPayload = path.join(process.resourcesPath, 'app-payload');
        try {
            fs.accessSync(path.join(packagedPayload, MARKER));
            return packagedPayload;
        } catch (_) { /* not installer build */ }
    }

    // 2. Local packaged build: .exe lives somewhere inside the repo tree.
    //    Walk up from the exe's directory until we find services/chatbot/run.py.
    if (process.resourcesPath) {
        let probe = path.dirname(process.execPath);
        for (let i = 0; i < 6; i++) {
            probe = path.dirname(probe);
            try {
                fs.accessSync(path.join(probe, MARKER));
                return probe;
            } catch (_) { /* keep climbing */ }
        }
    }

    // 3. Dev (npm run dev): __dirname = app/electron/src, three levels up = repo root.
    return path.resolve(__dirname, '..', '..', '..');
}

const REPO_ROOT = resolveRepoRoot();

function probeOnce(pathName) {
    return new Promise((resolve) => {
        const req = http.get({ host: HOST, port: PORT, path: pathName, timeout: 1500 }, (res) => {
            res.resume();
            resolve(res.statusCode != null && res.statusCode < 500);
        });
        req.on('error', () => resolve(false));
        req.on('timeout', () => { req.destroy(); resolve(false); });
    });
}

async function waitForReady() {
    const deadline = Date.now() + STARTUP_TIMEOUT_MS;
    while (Date.now() < deadline) {
        if (await probeOnce('/health')) return true;
        if (await probeOnce('/'))       return true;
        await new Promise((r) => setTimeout(r, PROBE_INTERVAL_MS));
    }
    return false;
}

function pickPython() {
    // Prefer venv-core if it exists, else fall back to whatever 'python' is on PATH.
    const fs = require('fs');
    const candidate = process.platform === 'win32'
        ? path.join(REPO_ROOT, 'venv-core', 'Scripts', 'python.exe')
        : path.join(REPO_ROOT, 'venv-core', 'bin', 'python');
    if (fs.existsSync(candidate)) return candidate;
    return process.platform === 'win32' ? 'python' : 'python3';
}

function startBackend({ onLog } = {}) {
    return new Promise(async (resolve, reject) => {
        // If something is already listening on the target port, skip spawning.
        // This lets developers run `python run.py` manually and just open Electron on top.
        const alreadyUp = await probeOnce('/health') || await probeOnce('/');
        if (alreadyUp) {
            process.stdout.write('[backend] port ' + PORT + ' already open — skipping spawn, reusing existing backend.\n');
            return resolve({ child: null, baseUrl: 'http://' + HOST + ':' + PORT });
        }

        const py = pickPython();
        const args = [path.join('services', 'chatbot', 'run.py')];
        const env = Object.assign({}, process.env, {
            FLASK_PORT: String(PORT),
            PYTHONIOENCODING: 'utf-8',
            ELECTRON_DESKTOP: 'true'
        });

        let child;
        try {
            child = spawn(py, args, { cwd: REPO_ROOT, env, windowsHide: true });
        } catch (err) {
            return reject(new Error('Failed to spawn python: ' + err.message));
        }

        const log = (stream, chunk) => {
            const text = chunk.toString();
            // Mirror to Electron main process console for visibility.
            process.stdout.write('[backend ' + stream + '] ' + text);
            if (typeof onLog === 'function') {
                try { onLog(stream, text); } catch (_) {}
            }
        };
        child.stdout.on('data', (c) => log('out', c));
        child.stderr.on('data', (c) => log('err', c));

        child.on('exit', (code, signal) => {
            process.stdout.write('[backend] exited code=' + code + ' signal=' + signal + '\n');
        });
        child.on('error', (err) => reject(err));

        const ready = await waitForReady();
        if (!ready) {
            try { child.kill(); } catch (_) {}
            return reject(new Error('Backend did not become ready on http://' + HOST + ':' + PORT + ' within ' + STARTUP_TIMEOUT_MS + 'ms.'));
        }
        resolve({ child, baseUrl: 'http://' + HOST + ':' + PORT });
    });
}

module.exports = { startBackend, HOST, PORT, REPO_ROOT };
