/* main.js — Electron entry point.
 *
 * Lifecycle:
 *   1. App ready  → create frameless BrowserWindow showing loading.html.
 *   2. Spawn the Python backend (services/chatbot/run.py) via backend-process.js.
 *   3. When the backend's /health responds, swap the window to loadURL('http://127.0.0.1:5000').
 *   4. On window close → minimise to tray. Tray Quit actually exits.
 *
 * Phase 4 additions:
 *   - frameless window + custom titlebar (renderer side)
 *   - tray icon with Show/Hide/Quit menu + active-job badge
 *   - global shortcut Ctrl+Shift+A toggles window
 *   - single-instance lock
 *   - IPC handlers: window:* + tray:setBadge + notify:show
 *
 * Hard rules per repo policy:
 *   - loadURL only (never loadFile of repo HTML); the chatbot is the canonical web app.
 *   - webPreferences sandboxed: nodeIntegration:false, contextIsolation:true, sandbox:true.
 *   - No file:// access to repo internals from renderer.
 */
const {
    app, BrowserWindow, Menu, Tray, nativeImage,
    ipcMain, globalShortcut, shell, Notification
} = require('electron');
const path = require('path');
const fs = require('fs');
const { startBackend, REPO_ROOT } = require('./backend-process');
const { startComfyUI, stopComfyUI } = require('./comfyui-process');

// Auto-updater is optional: only loaded if installed (production builds).
let autoUpdater = null;
try { autoUpdater = require('electron-updater').autoUpdater; } catch (_) { /* dev mode */ }

// ── Single-instance lock ──────────────────────────────────────────
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
    app.quit();
}

let mainWindow = null;
let tray = null;
let backendChild = null;
let comfyuiChild = null;
let comfyuiStatus = 'stopped'; // 'stopped' | 'starting' | 'running' | 'failed'
let recentLog = '';
let activeJobs = 0;
let isQuitting = false;

// ── Persistent settings ──────────────────────────────────────────
let settings = { quitOnClose: false };
function loadSettings() {
    try {
        const data = fs.readFileSync(path.join(app.getPath('userData'), 'ai-assistant-settings.json'), 'utf8');
        settings = Object.assign({ quitOnClose: false }, JSON.parse(data));
    } catch (_) {}
}
function saveSettings() {
    try {
        fs.writeFileSync(
            path.join(app.getPath('userData'), 'ai-assistant-settings.json'),
            JSON.stringify(settings, null, 2)
        );
    } catch (_) {}
}

function rememberLog(stream, text) {
    recentLog += '[' + stream + '] ' + text;
    if (recentLog.length > 8000) recentLog = recentLog.slice(-8000);
    // Push to loading screen (if it is still displayed).
    if (mainWindow && !mainWindow.isDestroyed()) {
        const safe = JSON.stringify({ stream, text });
        mainWindow.webContents.executeJavaScript(
            '(function(){var m=' + safe + ';if(typeof window.__appendLog==="function")window.__appendLog(m.stream,m.text);})()'
        ).catch(() => {});
    }
}

// 1×1 transparent PNG fallback used when no tray-icon.png is shipped.
// Replace by dropping `app/electron/src/tray-icon.png` (16/24/32px square).
const TRAY_FALLBACK_PNG = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAQAAAC1+jfqAAAAEklEQVR42mNk+M9QzwAEjDAGADJ/AwlnHfXhAAAAAElFTkSuQmCC',
    'base64'
);

function loadTrayIcon() {
    const iconPath = path.join(__dirname, 'tray-icon.png');
    try {
        const fromFile = nativeImage.createFromPath(iconPath);
        if (!fromFile.isEmpty()) return fromFile;
    } catch (_) { /* fall through to fallback */ }
    return nativeImage.createFromBuffer(TRAY_FALLBACK_PNG);
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 820,
        minWidth: 960,
        minHeight: 640,
        frame: false,
        titleBarStyle: 'hidden',
        backgroundColor: '#0f1115',
        title: 'AI-Assistant',
        icon: path.join(__dirname, 'tray-icon.png'),
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

    // Dev / navigation keyboard shortcuts.
    mainWindow.webContents.on('before-input-event', (event, input) => {
        if (input.type !== 'keyDown') return;

        // F12 → toggle DevTools
        if (input.key === 'F12') {
            if (mainWindow.webContents.isDevToolsOpened()) {
                mainWindow.webContents.closeDevTools();
            } else {
                mainWindow.webContents.openDevTools();
            }
            event.preventDefault();
            return;
        }

        // F5 → reload renderer (like browser refresh)
        if (input.key === 'F5' && !input.control && !input.shift && !input.alt && !input.meta) {
            mainWindow.reload();
            event.preventDefault();
            return;
        }

        // Ctrl+Shift+R → kill & restart the Python backend
        if (input.key === 'R' && input.control && input.shift && !input.alt) {
            killBackend();
            mainWindow.loadFile(path.join(__dirname, 'loading.html'))
                .then(() => bootBackendAndLoad())
                .catch(() => {});
            event.preventDefault();
            return;
        }
    });

    mainWindow.loadFile(path.join(__dirname, 'loading.html'));

    // Closing the window minimises to tray instead of quitting.
    // When 'quitOnClose' preference is set, it exits completely instead.
    mainWindow.on('close', (e) => {
        if (!isQuitting) {
            if (settings.quitOnClose) {
                isQuitting = true; // let the close proceed → triggers before-quit
            } else {
                e.preventDefault();
                mainWindow.hide();
                refreshTray();
            }
        }
    });
    mainWindow.on('closed', () => { mainWindow = null; });

    // Push max/unmax state to renderer so the titlebar icon can swap.
    const pushMaxState = () => {
        if (!mainWindow || mainWindow.isDestroyed()) return;
        try {
            mainWindow.webContents.send('window:maximized-changed', mainWindow.isMaximized());
        } catch (_) {}
    };
    mainWindow.on('maximize', pushMaxState);
    mainWindow.on('unmaximize', pushMaxState);

    // Watch the loading splash for the "__retry_backend__" sentinel and re-run boot.
    mainWindow.webContents.on('page-title-updated', (e, title) => {
        if (title === '__retry_backend__') {
            e.preventDefault();
            killBackend();
            mainWindow.webContents.executeJavaScript(
                'window.postMessage({ type: "retrying" }, "*"); document.title = "AI-Assistant — Starting…";'
            ).catch(() => {});
            bootBackendAndLoad();
        }
    });
}

function buildTrayMenu() {
    const comfyuiUrl = 'http://127.0.0.1:' + (process.env.COMFYUI_PORT || '8188');
    return Menu.buildFromTemplate([
        {
            label: mainWindow && mainWindow.isVisible() ? 'Hide window' : 'Show window',
            click: () => toggleWindow()
        },
        { label: 'Active jobs: ' + activeJobs, enabled: false },
        { label: 'ComfyUI: ' + comfyuiStatus, enabled: false },
        { type: 'separator' },
        {
            label: 'Open ComfyUI',
            click: () => shell.openExternal(comfyuiUrl)
        },
        { type: 'separator' },
        {
            label: 'Restart backend',
            click: () => {
                killBackend();
                if (mainWindow) {
                    mainWindow.loadFile(path.join(__dirname, 'loading.html'))
                        .then(() => bootBackendAndLoad())
                        .catch(() => {});
                }
            }
        },
        { type: 'separator' },
        {
            label: 'Quit on close',
            type: 'checkbox',
            checked: settings.quitOnClose,
            click: (item) => {
                settings.quitOnClose = item.checked;
                saveSettings();
                refreshTray();
            }
        },
        { label: 'Quit', click: () => { isQuitting = true; app.quit(); } }
    ]);
}

function refreshTray() {
    if (!tray) return;
    try {
        tray.setToolTip('AI-Assistant — ' + (activeJobs > 0 ? activeJobs + ' active job(s)' : 'idle'));
        tray.setContextMenu(buildTrayMenu());
    } catch (_) {}
}

function createTray() {
    if (tray) return;
    try {
        tray = new Tray(loadTrayIcon());
        tray.setToolTip('AI-Assistant');
        refreshTray();
        tray.on('click', () => toggleWindow());
        tray.on('double-click', () => showWindow());
    } catch (err) {
        process.stderr.write('[electron] tray init failed: ' + err.message + '\n');
    }
}

function showWindow() {
    if (!mainWindow) { createWindow(); return; }
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
    refreshTray();
}

function toggleWindow() {
    if (!mainWindow) { createWindow(); return; }
    if (mainWindow.isVisible() && mainWindow.isFocused()) {
        mainWindow.hide();
    } else {
        showWindow();
    }
    refreshTray();
}

async function bootBackendAndLoad() {
    try {
        const { child, baseUrl } = await startBackend({ onLog: rememberLog });
        backendChild = child;
        if (!mainWindow) return;
        await mainWindow.loadURL(baseUrl);

        // Fire-and-forget ComfyUI: failure must NOT block the chatbot UI.
        bootComfyUI();
    } catch (err) {
        const msg = err && err.message ? err.message : String(err);
        process.stderr.write('[electron] backend boot failed: ' + msg + '\n');
        if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.executeJavaScript(
                'window.postMessage(' + JSON.stringify({ type: 'error', message: msg, log: recentLog }) + ', "*");'
            ).catch(() => {});
        }
    }
}

async function bootComfyUI() {
    comfyuiStatus = 'starting';
    refreshTray();
    try {
        const { child } = await startComfyUI({ payloadRoot: REPO_ROOT, onLog: rememberLog });
        comfyuiChild = child;
        comfyuiStatus = 'running';
    } catch (err) {
        comfyuiStatus = 'failed';
        process.stderr.write('[electron] ComfyUI boot failed: ' + (err && err.message ? err.message : err) + '\n');
    } finally {
        refreshTray();
    }
}

function killBackend() {
    if (backendChild && !backendChild.killed) {
        try { backendChild.kill(); } catch (_) {}
    }
    backendChild = null;
}

function killComfyUI() {
    stopComfyUI(comfyuiChild);
    comfyuiChild = null;
    comfyuiStatus = 'stopped';
}

function setupAutoUpdater() {
    if (!autoUpdater || !app.isPackaged) return;
    autoUpdater.autoDownload = true;
    autoUpdater.on('error', (err) => {
        process.stderr.write('[updater] ' + (err && err.message ? err.message : err) + '\n');
    });
    autoUpdater.on('update-downloaded', (info) => {
        try {
            const n = new Notification({
                title: 'AI-Assistant update ready',
                body: 'Version ' + (info && info.version) + ' will be installed on quit.',
            });
            n.show();
        } catch (_) {}
    });
    // Delay first check so the user gets a responsive UI immediately.
    setTimeout(() => {
        try { autoUpdater.checkForUpdates(); } catch (_) {}
    }, 30_000);
}

// ── IPC bridge for renderer-driven window/tray controls ───────────
function registerIpc() {
    ipcMain.handle('window:minimize', () => { if (mainWindow) mainWindow.minimize(); });
    ipcMain.handle('window:maximize', () => {
        if (!mainWindow) return false;
        if (mainWindow.isMaximized()) mainWindow.unmaximize();
        else mainWindow.maximize();
        return mainWindow.isMaximized();
    });
    ipcMain.handle('window:close', () => { if (mainWindow) mainWindow.close(); });
    ipcMain.handle('window:isMaximized', () => mainWindow ? mainWindow.isMaximized() : false);

    ipcMain.handle('tray:setBadge', (_e, count) => {
        const n = Number.isFinite(+count) ? Math.max(0, Math.floor(+count)) : 0;
        activeJobs = n;
        // Windows taskbar overlay (best-effort)
        try {
            if (mainWindow && process.platform === 'win32') {
                if (n > 0) {
                    mainWindow.setOverlayIcon(loadTrayIcon(), String(n) + ' active');
                } else {
                    mainWindow.setOverlayIcon(null, '');
                }
            }
        } catch (_) {}
        refreshTray();
        return activeJobs;
    });

    ipcMain.handle('notify:show', (_e, payload) => {
        try {
            if (!Notification.isSupported()) return false;
            const n = new Notification({
                title: (payload && payload.title) || 'AI-Assistant',
                body:  (payload && payload.body)  || '',
                silent: !!(payload && payload.silent)
            });
            n.on('click', () => showWindow());
            n.show();
            return true;
        } catch (_) { return false; }
    });
}

// Single-instance: focus existing window when a 2nd launch occurs.
app.on('second-instance', () => { showWindow(); });

app.whenReady().then(() => {
    loadSettings();
    Menu.setApplicationMenu(null); // frameless: no app menu
    registerIpc();
    createWindow();
    createTray();
    bootBackendAndLoad();
    setupAutoUpdater();

    try { globalShortcut.register('CommandOrControl+Shift+A', toggleWindow); } catch (_) {}

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
        else showWindow();
    });
});

app.on('before-quit', () => { isQuitting = true; killBackend(); killComfyUI(); });
app.on('will-quit', () => { try { globalShortcut.unregisterAll(); } catch (_) {} });
app.on('window-all-closed', () => {
    // Frameless + tray app: stay alive when the window is hidden.
    // Only quit if the user explicitly chose Quit (sets isQuitting).
    if (isQuitting && process.platform !== 'darwin') app.quit();
});
