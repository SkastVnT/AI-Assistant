/* comfyui-process.js — spawn ComfyUI/main.py against venv-image.
 *
 * Mirrors backend-process.js but for the local image stack.
 *
 * Health probe:  GET http://127.0.0.1:8188/  (ComfyUI returns 200 once ready)
 *
 * Exposes:
 *   startComfyUI({ payloadRoot, onLog }) -> Promise<{ child, baseUrl }>
 *   stopComfyUI(child)
 *
 * Failures are non-fatal for the chatbot — caller should log and continue.
 */
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');

const HOST = '127.0.0.1';
const PORT = parseInt(process.env.COMFYUI_PORT || '8188', 10);
const STARTUP_TIMEOUT_MS = 180_000; // ComfyUI cold-load can take a while
const PROBE_INTERVAL_MS = 1000;

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
        if (await probeOnce('/')) return true;
        await new Promise((r) => setTimeout(r, PROBE_INTERVAL_MS));
    }
    return false;
}

function startComfyUI({ payloadRoot, onLog } = {}) {
    return new Promise(async (resolve, reject) => {
        if (!payloadRoot) {
            return reject(new Error('startComfyUI: payloadRoot is required'));
        }
        const baseUrl = 'http://' + HOST + ':' + PORT;

        // If ComfyUI is already running on the port, reuse it.
        if (await probeOnce('/')) {
            process.stdout.write('[comfyui] port ' + PORT + ' already open — reusing existing instance.\n');
            return resolve({ child: null, baseUrl });
        }

        const py = path.join(payloadRoot, 'venv-image', 'Scripts', 'python.exe');
        const main = path.join(payloadRoot, 'ComfyUI', 'main.py');
        if (!fs.existsSync(py)) {
            return reject(new Error('venv-image python not found at ' + py));
        }
        if (!fs.existsSync(main)) {
            return reject(new Error('ComfyUI/main.py not found at ' + main));
        }

        const args = [main, '--port', String(PORT), '--listen', HOST, '--disable-auto-launch'];
        const env = Object.assign({}, process.env, {
            PYTHONIOENCODING: 'utf-8',
            ELECTRON_DESKTOP: 'true',
        });

        let child;
        try {
            child = spawn(py, args, {
                cwd: path.join(payloadRoot, 'ComfyUI'),
                env,
                windowsHide: true,
            });
        } catch (err) {
            return reject(new Error('Failed to spawn ComfyUI: ' + err.message));
        }

        const log = (stream, chunk) => {
            const text = chunk.toString();
            if (typeof onLog === 'function') {
                try { onLog(stream, text); } catch (_) {}
            }
        };
        child.stdout.on('data', (c) => log('out', c));
        child.stderr.on('data', (c) => log('err', c));
        child.on('exit', (code, signal) => {
            process.stdout.write('[comfyui] exited code=' + code + ' signal=' + signal + '\n');
        });
        child.on('error', (err) => reject(err));

        const ready = await waitForReady();
        if (!ready) {
            try { child.kill(); } catch (_) {}
            return reject(new Error('ComfyUI did not become ready on ' + baseUrl + ' within ' + STARTUP_TIMEOUT_MS + 'ms.'));
        }
        resolve({ child, baseUrl });
    });
}

function stopComfyUI(child) {
    if (child && !child.killed) {
        try { child.kill(); } catch (_) {}
    }
}

module.exports = { startComfyUI, stopComfyUI, HOST, PORT };
