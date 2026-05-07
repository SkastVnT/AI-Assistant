// desktop/electron/src/main.js
//
// Electron main process for the AI-Assistant desktop wrapper.
//
// Responsibilities:
//   1. Spawn the existing Python backend (services/chatbot/run.py) via
//      backend-process.js — this is the ONLY place a backend is started.
//   2. Wait for the backend to become reachable on http://127.0.0.1:5000.
//   3. Open a sandboxed BrowserWindow that loads that URL (NOT loadFile).
//   4. Tear the backend down on quit.
//
// This file does NOT replace the web UI, modify routes, or change
// /chat/stream. It is purely a desktop shell around the existing app.

'use strict';

const { app, BrowserWindow, shell } = require('electron');
const path = require('path');

const {
  startBackend,
  stopBackend,
  waitForBackend,
  DEFAULT_HOST,
  DEFAULT_PORT,
} = require('./backend-process');

const BACKEND_HOST = process.env.AI_ASSISTANT_HOST || DEFAULT_HOST;
const BACKEND_PORT = parseInt(process.env.FLASK_PORT || String(DEFAULT_PORT), 10);
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;

let mainWindow = null;
let backendProcess = null;
let backendExitedEarly = false;
let isQuitting = false;

function logBackendChunk(prefix, chunk) {
  // Keep desktop logs minimal — just mirror to stdout so `npm run dev`
  // shows them. Avoid writing to disk to keep this wrapper stateless.
  const text = String(chunk).replace(/\s+$/, '');
  if (text) process.stdout.write(`[backend ${prefix}] ${text}\n`);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 900,
    minHeight: 600,
    show: false,
    title: 'AI Assistant',
    backgroundColor: '#0f1115',
    webPreferences: {
      // Security contract — locked per task requirements.
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // Open external links in the user's default browser instead of a new
  // Electron window (which would otherwise inherit our security context).
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    try {
      const u = new URL(url);
      if (u.origin !== BACKEND_URL) {
        shell.openExternal(url);
        return { action: 'deny' };
      }
    } catch (_) { /* fall through */ }
    return { action: 'allow' };
  });

  // Block in-page navigation away from the backend origin.
  mainWindow.webContents.on('will-navigate', (event, url) => {
    try {
      const u = new URL(url);
      if (u.origin !== BACKEND_URL) {
        event.preventDefault();
        shell.openExternal(url);
      }
    } catch (_) {
      event.preventDefault();
    }
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    if (process.env.ELECTRON_DEV === 'true') {
      mainWindow.webContents.openDevTools({ mode: 'detach' });
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

async function loadBackendIntoWindow() {
  try {
    await waitForBackend({
      host: BACKEND_HOST,
      port: BACKEND_PORT,
      timeoutMs: 90000,
    });
  } catch (err) {
    process.stderr.write(`[desktop] Backend never became ready: ${err.message}\n`);
    if (mainWindow) {
      const html =
        '<html><body style="font-family:sans-serif;background:#0f1115;color:#eee;padding:2em">' +
        '<h2>Backend failed to start</h2>' +
        `<p>Tried <code>${BACKEND_URL}</code>.</p>` +
        '<p>Check the terminal output for Python errors. You can also run ' +
        '<code>cd services/chatbot &amp;&amp; python run.py</code> manually to diagnose.</p>' +
        '</body></html>';
      await mainWindow.loadURL(
        'data:text/html;charset=utf-8,' + encodeURIComponent(html),
      );
    }
    return;
  }

  if (mainWindow) {
    await mainWindow.loadURL(BACKEND_URL);
  }
}

function startBackendAndWatch() {
  backendProcess = startBackend({
    onStdout: (chunk) => logBackendChunk('out', chunk),
    onStderr: (chunk) => logBackendChunk('err', chunk),
  });

  backendProcess.on('error', (err) => {
    process.stderr.write(`[desktop] Failed to spawn backend: ${err.message}\n`);
  });

  backendProcess.on('exit', (code, signal) => {
    backendExitedEarly = !isQuitting;
    process.stdout.write(
      `[desktop] Backend exited (code=${code}, signal=${signal})\n`,
    );
    if (backendExitedEarly && mainWindow) {
      // Surface a minimal in-window notice so the renderer doesn't just
      // sit on a blank/error page silently.
      const html =
        '<html><body style="font-family:sans-serif;background:#0f1115;color:#eee;padding:2em">' +
        '<h2>Backend stopped</h2>' +
        `<p>The Python backend exited unexpectedly (code=${code}). ` +
        'Close this window and restart the app to try again.</p>' +
        '</body></html>';
      mainWindow.loadURL(
        'data:text/html;charset=utf-8,' + encodeURIComponent(html),
      ).catch(() => { /* ignore */ });
    }
  });
}

// Single-instance lock: a second launch should focus the existing window
// instead of spawning a second backend on the same port.
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    startBackendAndWatch();
    createWindow();
    await loadBackendIntoWindow();
  });

  app.on('window-all-closed', () => {
    // Quit on all platforms — desktop wrapper has no menu-bar-only mode.
    if (process.platform !== 'darwin') {
      app.quit();
    } else {
      app.quit();
    }
  });

  app.on('before-quit', () => {
    isQuitting = true;
    stopBackend(backendProcess);
  });

  app.on('will-quit', () => {
    stopBackend(backendProcess);
  });
}
