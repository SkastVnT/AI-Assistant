# AI-Assistant — Electron Desktop Wrapper

Thin Electron shell around the existing AI-Assistant chatbot. It does
**not** replace the web app, rewrite the UI, or change `/chat/stream`.
It only:

1. Spawns the existing Python backend (`services/chatbot/run.py`) in
   FastAPI mode.
2. Waits until the backend answers on `http://127.0.0.1:5000`.
3. Loads that URL inside a sandboxed `BrowserWindow`.
4. Stops the backend when the window closes.

Web mode is unaffected — `python services/chatbot/run.py` still works
exactly as before.

---

## Layout

```
desktop/electron/
  package.json
  src/
    main.js              # Electron main process
    preload.js           # Sandboxed bridge (exposes only desktopAPI)
    backend-process.js   # Spawns + supervises services/chatbot/run.py
```

---

## Requirements

- **Node.js 18+** (for Electron 31).
- **Python** with the chatbot dependencies installed in `venv-core`
  (or available on `PATH`). This wrapper does **not** install Python
  packages.
- A working `services/chatbot` setup (env files, API keys, etc.).

`backend-process.js` auto-detects `venv-core/Scripts/python.exe`
(Windows) or `venv-core/bin/python` (POSIX). Override with:

```powershell
$env:PYTHON = "C:\path\to\python.exe"
```

---

## Run web mode (unchanged)

```powershell
cd services\chatbot
python run.py
```

---

## Run desktop mode

```powershell
cd desktop\electron
npm install
npm run dev
```

What happens:

1. Electron sets `USE_FASTAPI=true`, `FLASK_PORT=5000`,
   `PYTHONIOENCODING=utf-8`, `ELECTRON_DESKTOP=true` and spawns
   `python services/chatbot/run.py`.
2. The main process polls `http://127.0.0.1:5000/health` (falls back
   to `/`) until it responds.
3. The `BrowserWindow` loads `http://127.0.0.1:5000` (the existing
   web UI — `loadFile` is intentionally **not** used).
4. On quit, the Python process tree is terminated
   (`taskkill /T /F` on Windows, `SIGTERM`→`SIGKILL` elsewhere).

---

## Scripts

| Script           | Purpose                                              |
| ---------------- | ---------------------------------------------------- |
| `npm run dev`    | Launch Electron with DevTools detached.              |
| `npm start`      | Launch Electron without DevTools.                    |
| `npm run package`| `electron-builder --dir` (unpacked build, for QA).   |
| `npm run make`   | `electron-builder` (full installer / artifact).      |

---

## Security contract

The renderer is fully sandboxed:

```js
nodeIntegration: false
contextIsolation: true
sandbox: true
webSecurity: true
preload: src/preload.js
```

`preload.js` exposes **only**:

```js
window.desktopAPI = {
  isDesktop: true,
  platform: process.platform,
}
```

Not exposed: `fs`, `child_process`, `shell`, `ipcRenderer`, `require`,
or any arbitrary file/command APIs. External links are routed to the
default browser via `shell.openExternal`; in-page navigation away from
`http://127.0.0.1:5000` is blocked.

`child_process.spawn` is used **only** in the main process
(`backend-process.js`) to launch the Python backend.

---

## What this wrapper does NOT do

- Does **not** replace, fork, or rewrite the web UI.
- Does **not** modify `/chat/stream` or any backend route.
- Does **not** touch `ComfyUI/` or `image_pipeline/`.
- Does **not** add or change Python dependencies
  (`requirements-core.txt`, `requirements-image.txt`,
  `requirements.txt` are untouched).
- Does **not** ship its own copy of `services/chatbot/templates/` or
  `static/` — everything is served by Flask/FastAPI as in web mode.

---

## Troubleshooting

- **`'electron' is not recognized`** — run `npm install` inside
  `desktop/electron/` first.
- **Window shows "Backend failed to start"** — open a terminal and run
  `cd services/chatbot && python run.py` directly to see the Python
  error. The desktop wrapper just spawns the same command.
- **Port 5000 already in use** — stop the existing chatbot process or
  set `FLASK_PORT` (and a matching `AI_ASSISTANT_HOST` if needed)
  before launching Electron.
- **Wrong Python interpreter** — set the `PYTHON` env var to the
  absolute path of the interpreter you want to use.
