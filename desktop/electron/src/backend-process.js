// desktop/electron/src/backend-process.js
//
// Spawns the existing Python chatbot backend (services/chatbot/run.py)
// in FastAPI mode and exposes helpers for readiness polling and clean
// shutdown. This file is the ONLY place where child_process is used.
//
// Contract:
//   - Runs `python run.py` from services/chatbot/.
//   - Sets USE_FASTAPI=true, FLASK_PORT=5000, PYTHONIOENCODING=utf-8,
//     ELECTRON_DESKTOP=true in the spawned env.
//   - Inherits the parent process env so the user's existing API keys,
//     PATH, and venv activation continue to work.
//   - Does NOT modify Python deps. Does NOT touch ComfyUI / image_pipeline.

'use strict';

const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

// Workspace layout: <repo>/desktop/electron/src/backend-process.js
//                    -> repoRoot = ../../..
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const CHATBOT_DIR = path.join(REPO_ROOT, 'services', 'chatbot');
const RUN_PY = path.join(CHATBOT_DIR, 'run.py');

const DEFAULT_PORT = 5000;
const DEFAULT_HOST = '127.0.0.1';

function resolvePython() {
  // Honor explicit override first.
  if (process.env.PYTHON) return process.env.PYTHON;

  // Prefer the project's venv-core if present.
  const isWin = process.platform === 'win32';
  const venvPython = isWin
    ? path.join(REPO_ROOT, 'venv-core', 'Scripts', 'python.exe')
    : path.join(REPO_ROOT, 'venv-core', 'bin', 'python');

  try {
    // Avoid pulling in fs at top-level; require lazily.
    const fs = require('fs');
    if (fs.existsSync(venvPython)) return venvPython;
  } catch (_) {
    // fall through
  }

  return isWin ? 'python' : 'python3';
}

function buildBackendEnv() {
  // Start from the current process env so PATH, HOME, USERPROFILE,
  // shared API keys, etc. propagate into the spawned Python process.
  const env = Object.assign({}, process.env);

  // Required by the task contract:
  env.USE_FASTAPI = 'true';
  env.FLASK_PORT = String(DEFAULT_PORT);
  env.PYTHONIOENCODING = 'utf-8';
  env.ELECTRON_DESKTOP = 'true';

  // Avoid Python output buffering so logs surface promptly in dev.
  env.PYTHONUNBUFFERED = env.PYTHONUNBUFFERED || '1';

  return env;
}

/**
 * Start the Python backend. Returns the spawned ChildProcess.
 * Callers should attach 'exit' / 'error' listeners and call stop() to terminate.
 */
function startBackend({ onStdout, onStderr } = {}) {
  const python = resolvePython();
  const env = buildBackendEnv();

  const child = spawn(python, [RUN_PY], {
    cwd: CHATBOT_DIR,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: false,
    // Detached=false so the child stays in our process group and we can
    // signal it on quit. On Windows we kill via taskkill /T below.
    detached: false,
  });

  if (child.stdout && onStdout) {
    child.stdout.setEncoding('utf-8');
    child.stdout.on('data', onStdout);
  }
  if (child.stderr && onStderr) {
    child.stderr.setEncoding('utf-8');
    child.stderr.on('data', onStderr);
  }

  return child;
}

/**
 * Stop the backend cleanly. On Windows uses taskkill /T to kill the
 * whole tree (uvicorn workers, autostarted sidecars spawned by run.py).
 */
function stopBackend(child) {
  if (!child || child.killed || typeof child.pid !== 'number') return;

  try {
    if (process.platform === 'win32') {
      // /F = force, /T = tree. taskkill is the only reliable way to
      // terminate uvicorn + child workers on Windows.
      spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], {
        stdio: 'ignore',
        windowsHide: true,
      });
    } else {
      try { child.kill('SIGTERM'); } catch (_) { /* ignore */ }
      // Escalate after a short grace period.
      setTimeout(() => {
        try { if (!child.killed) child.kill('SIGKILL'); } catch (_) { /* ignore */ }
      }, 3000).unref();
    }
  } catch (_) {
    // best-effort
  }
}

/**
 * HEAD/GET probe for backend readiness.
 * Tries /health first; if it returns any HTTP status (including 404),
 * the server is up. Falls back to a plain GET / .
 */
function probeOnce(host, port, pathName, timeoutMs) {
  return new Promise((resolve) => {
    const req = http.get(
      { host, port, path: pathName, timeout: timeoutMs },
      (res) => {
        // Drain to free the socket.
        res.resume();
        resolve(true);
      },
    );
    req.on('timeout', () => { req.destroy(); resolve(false); });
    req.on('error', () => resolve(false));
  });
}

/**
 * Poll until the backend responds or the deadline elapses.
 * Resolves to the URL that should be loaded by the BrowserWindow.
 */
async function waitForBackend({
  host = DEFAULT_HOST,
  port = DEFAULT_PORT,
  timeoutMs = 60000,
  intervalMs = 400,
} = {}) {
  const deadline = Date.now() + timeoutMs;
  const baseUrl = `http://${host}:${port}`;
  // Prefer /health, but accept root-level response too.
  while (Date.now() < deadline) {
    if (await probeOnce(host, port, '/health', 1500)) return baseUrl;
    if (await probeOnce(host, port, '/', 1500)) return baseUrl;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`Backend did not become ready at ${baseUrl} within ${timeoutMs}ms`);
}

module.exports = {
  startBackend,
  stopBackend,
  waitForBackend,
  DEFAULT_HOST,
  DEFAULT_PORT,
  REPO_ROOT,
  CHATBOT_DIR,
};
