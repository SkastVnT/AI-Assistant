# AI-Assistant — Electron desktop wrapper

This is a **wrapper only**. It does not replace the web deployment. The web app
remains the canonical surface; Electron just spawns the existing
`services/chatbot/run.py` and points a sandboxed `BrowserWindow` at
`http://127.0.0.1:5000`.

## What it does

1. Boots a **frameless** `BrowserWindow` showing `src/loading.html` (dark splash).
2. Spawns `python services/chatbot/run.py` with `cwd = repo root`.
   - On Windows, prefers `venv-core/Scripts/python.exe`.
   - On macOS / Linux, prefers `venv-core/bin/python`.
3. Polls `GET /health` (and falls back to `/`) until it gets a `< 500` response.
4. Calls `mainWindow.loadURL('http://127.0.0.1:5000')`.
5. Holds a single-instance lock (a 2nd launch focuses the existing window).
6. Installs a **system tray icon** with Show/Hide/Restart-backend/Quit menu.
7. Polls `/api/jobs/stats` every 5 s from the renderer and mirrors the running
   job count to the tray tooltip + Windows taskbar overlay.
8. Registers global shortcut `Ctrl+Shift+A` to toggle window visibility.
9. On window close → hides to tray (does NOT quit). Tray → Quit actually exits.
10. Quitting kills the backend child process.

## What it does NOT do

- It does **not** call `loadFile` for any chatbot HTML. Renderer always talks
  to the local HTTP server.
- It does **not** enable `nodeIntegration`, disable `contextIsolation`, or
  disable `sandbox`. These are locked off per repo policy.
- It does **not** ship a Python runtime, ComfyUI, or the LoRA assets. You are
  responsible for installing them via the existing `venv-core` instructions.
- It does **not** auto-update.

## Renderer bridge

`preload.js` exposes a frozen object:

```js
window.desktopAPI = {
  isDesktop: true,
  platform: 'win32' | 'darwin' | 'linux',
  window: { minimize, maximize, close, isMaximized, onMaximizedChanged },
  tray:   { setBadge },
  notify: { show({ title, body, silent }) }
};
```

No `fs`, no `shell`, no arbitrary `ipc`. The chatbot frontend uses this from
`services/chatbot/static/js/modules/electron-bridge.js` to wire the custom
titlebar buttons and the tray-badge poller.

## Setup

```powershell
cd app/electron
npm install
npm run dev
```

`npm run dev` is just `electron . --dev`. There is no bundler.

## Packaging

```powershell
npm run package   # creates an unpackaged build under app/electron/out
npm run make      # builds installers (Squirrel on Windows, zip elsewhere)
```

Packaging the desktop wrapper does NOT bundle Python. The packaged app still
expects `venv-core` to exist next to it (or `python` on PATH). For a true
self-contained installer, see `../docs/STORAGE_CURATION_ROADMAP.md` — that work
is deferred.

## Tray icon asset

The tray defaults to a 1×1 transparent PNG fallback shipped inline. Drop a
proper square PNG (16 / 24 / 32 px) at `app/electron/src/tray-icon.png`
and it will be picked up automatically.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `AI_ASSISTANT_PORT` | `5000` | Port to probe and to set as `FLASK_PORT` for the spawned backend. |
| `ELECTRON_DESKTOP` | `true` | Set automatically. Backend code may opt into desktop-only behaviour. |

## Troubleshooting

- **"Backend did not become ready…"** — `services/chatbot/run.py` failed to
  start. The splash screen will display the last ~4 KB of stderr/stdout.
  Inspect the terminal that launched Electron for the full log.
- **Port already in use** — set `AI_ASSISTANT_PORT=5001` (or any free port)
  before launching: `set AI_ASSISTANT_PORT=5001 && npm run dev`.
- **Wrong Python** — activate `venv-core` before `npm run dev`, or symlink
  `python` to a 3.11 interpreter on PATH.
