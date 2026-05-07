/* main.js — Electron entry point.
 *
 * Lifecycle:
 *   1. App ready  → create BrowserWindow showing loading.html.
 *   2. Spawn the Python backend (services/chatbot/run.py) via backend-process.js.
 *   3. When the backend's /health responds, swap the window to loadURL('http://127.0.0.1:5000').
 *   4. On window-all-closed (or before-quit), kill the backend child.
 *
 * Hard rules per repo policy:
 *   - loadURL only (never loadFile of repo HTML); the chatbot is the canonical web app.
 *   - webPreferences sandboxed: nodeIntegration:false, contextIsolation:true, sandbox:true.
 *   - No file:// access to repo internals from renderer.
 */
const { app, BrowserWindow, shell } = require('electron');
const path = require('path');
const { startBackend } = require('./backend-process');

let mainWindow = null;
let backendChild = null;
let recentLog = '';

function rememberLog(stream, text) {
    recentLog += '[' + stream + '] ' + text;
    if (recentLog.length > 8000) recentLog = recentLog.slice(-8000);
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 820,
        minWidth: 960,
        minHeight: 640,
        backgroundColor: '#0f1115',
        title: 'AI-Assistant',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true,
            webSecurity: true
        }
    });

    // External links open in the user's default browser, not a new Electron window.
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        if (url && (url.startsWith('http://127.0.0.1') || url.startsWith('http://localhost'))) {
            return { action: 'allow' };
        }
        shell.openExternal(url);
        return { action: 'deny' };
    });

    mainWindow.loadFile(path.join(__dirname, 'loading.html'));
    mainWindow.on('closed', () => { mainWindow = null; });
}

async function bootBackendAndLoad() {
    try {
        const { child, baseUrl } = await startBackend({ onLog: rememberLog });
        backendChild = child;
        if (!mainWindow) return;
        await mainWindow.loadURL(baseUrl);
    } catch (err) {
        const msg = err && err.message ? err.message : String(err);
        process.stderr.write('[electron] backend boot failed: ' + msg + '\n');
        if (mainWindow && !mainWindow.isDestroyed()) {
            // Re-display loading.html (already loaded) and post the error to it.
            mainWindow.webContents.executeJavaScript(
                'window.postMessage(' + JSON.stringify({ type: 'error', message: msg, log: recentLog }) + ', "*");'
            ).catch(() => {});
        }
    }
}

function killBackend() {
    if (backendChild && !backendChild.killed) {
        try { backendChild.kill(); } catch (_) {}
    }
    backendChild = null;
}

app.whenReady().then(() => {
    createWindow();
    bootBackendAndLoad();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('before-quit', killBackend);
app.on('window-all-closed', () => {
    killBackend();
    if (process.platform !== 'darwin') app.quit();
});
