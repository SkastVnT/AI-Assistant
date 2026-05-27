# PACKAGING — Building the AI-Assistant Windows installer

This document covers the **one-time** build-machine setup and the recurring
build/release workflow. The output is a single offline `.exe` installer that
bundles Python, ComfyUI, models, LORAs, and the chatbot. End users double-click
it once → get a Desktop shortcut → click it → app starts.

> Output location is `<repo-root>\private\install\` per project requirement.
> To change, edit `directories.output` in `electron-builder.yml` and the
> `$Output` var in `scripts/build-installer.ps1`.

---

## 1. Build-machine prerequisites

Install once on the machine that will produce the installer:

| Tool | Version | Notes |
|---|---|---|
| Windows | 10 or 11 x64 | NSIS targets Windows only |
| Node.js | ≥ 20 LTS | for `electron-builder` |
| Python | 3.11.x | system Python — used to download wheels |
| Disk | ≥ 120 GB free | payload + wheel cache + installer |

```powershell
cd app\electron
npm install
```

---

## 2. One-time payload assets

Two big things are NOT in git and must be staged manually under
`app/electron/payload/` before the first build.

### 2.1 Bundled Python 3.11 runtime → `payload/python311/`

End users won't have Python; we ship our own. Use **python-build-standalone**
(NOT the embeddable zip — that one omits the `venv` module).

```powershell
$dst = "app\electron\payload"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$url = "https://github.com/astral-sh/python-build-standalone/releases/download/20250115/cpython-3.11.11+20250115-x86_64-pc-windows-msvc-install_only.tar.gz"
$tgz = "$env:TEMP\py311-standalone.tar.gz"
Invoke-WebRequest $url -OutFile $tgz
tar -xzf $tgz -C $dst                # extracts to $dst\python\
Rename-Item "$dst\python" "python311"
```

Verify: `app\electron\payload\python311\python.exe -c "import venv, pip, ssl; print('ok')"`

### 2.2 Wheel caches → `payload/wheels/core` + `payload/wheels/image`

Used by the postinstall script to build venvs **offline** on the user's machine.

The build script can do this for you:

```powershell
cd app\electron
powershell -ExecutionPolicy Bypass -File scripts\build-installer.ps1 -BuildWheels -SkipPayload -DirOnly
```

Or manually:

```powershell
python -m pip download -r ..\..\app\requirements\profile_core_services.txt `
    -d payload\wheels\core --only-binary=:all: --platform win_amd64 --python-version 3.11

python -m pip download -r ..\..\app\requirements\profile_image_ai_services.txt `
    -d payload\wheels\image --only-binary=:all: --platform win_amd64 --python-version 3.11
```

> CUDA target: this assumes torch wheels for the default CUDA your
> `requirements-image.txt` pins. If you need a specific CUDA, add the index
> URL: `--extra-index-url https://download.pytorch.org/whl/cu121`.

---

## 3. Build the installer

Recurring command for every release:

```powershell
cd app\electron
powershell -ExecutionPolicy Bypass -File scripts\build-installer.ps1
```

What happens:
1. `npm install` (idempotent)
2. `prepare-payload.js` rsync-copies `services/`, `ComfyUI/`, `LORA/`,
   `app/config/.env.example`, etc. into `payload/` (skipping real `.env` files,
   keys, certs, `__pycache__`, venvs, logs).
3. `electron-builder --win nsis` produces:
   `<repo-root>\private\install\AI-Assistant-Setup-<version>.exe`

For a fast sanity check without compressing, use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-installer.ps1 -DirOnly
```

That writes `<repo-root>\private\install\win-unpacked\` you can `cd` into and
run `AI-Assistant.exe` directly.

---

## 4. Code signing (optional)

Without a signing cert, Windows SmartScreen will warn first-time users
("Don't run / More info → Run anyway"). For internal distribution that's
usually acceptable.

To sign:

```powershell
$env:CSC_LINK          = 'C:\path\to\codesign.pfx'
$env:CSC_KEY_PASSWORD  = '<pfx password>'
```

Then run the build. Uncomment `certificateFile` in `electron-builder.yml` if
you prefer the file-based path.

---

## 5. Auto-updates

`electron-updater` is wired in `main.js` and reads the `publish` block in
`electron-builder.yml`. Default points to `http://updates.local/ai-assistant/`.

To enable updates:
1. Bump `version` in `app/electron/package.json` (e.g. `0.1.0` → `0.1.1`).
2. Build the installer.
3. Upload `AI-Assistant-Setup-<ver>.exe` **and** `latest.yml` (auto-generated
   alongside it) to your HTTP server under the `publish.url` path.
4. Existing installs poll every launch; users get a tray notification when an
   update is downloaded and applies it on quit.

To disable updates entirely, delete the `publish` block in `electron-builder.yml`.

---

## 6. End-user installation

Hand the user the `.exe`. They double-click → choose install dir
(default `C:\Program Files\AI-Assistant`) → installer copies files →
postinstall runs `setup_venvs.py` (5–15 minutes, progress in NSIS dialog) →
Desktop + Start Menu shortcuts are created.

Click the **AI-Assistant** Desktop shortcut → Electron window opens →
Python backend (port 5000) and ComfyUI (port 8188) auto-spawn → chat UI ready.

Logs:
- Backend / ComfyUI stdout: visible in Electron console (Ctrl+Shift+I in dev)
- `setup_venvs.py` log: `<install dir>\resources\app-payload\logs\setup_venvs.log`

Uninstall via **Settings → Apps** removes the install dir, including venvs and
ComfyUI output (per `installer.nsh` `customUnInstall` macro).

---

## 7. What's bundled vs. excluded

Bundled (see `prepare-payload.js`):
- `services/` (chatbot + MCP + stable-diffusion + edit-image)
- `app/config/` (includes `.env.example`; real `.env` files are excluded)
- `app/src/`, `app/scripts/`, `app/requirements/`
- `ComfyUI/` (minus `output/`, `temp/`, `user/`)
- `app/image_pipeline/`, `app/configs_vps/`, `app/rag/`
- Curated `app/storage/` (character DBs, prompts, references)
- `LORA/` (minus `old/`, `new_1/`, `new_2/`, `*.zip`)
- `python311/` portable runtime
- `wheels/core/` + `wheels/image/` offline pip mirror

Excluded:
- `venv-core/`, `venv-image/` (rebuilt on user's machine)
- `__pycache__/`, `*.pyc`, `*.log`, `node_modules/`
- `private/`, `app/character_select_stand_alone_app-main/` (sidecars, opt-in)
- `tests/`, `.git/`, `.github/`, `.vscode/`

To change the bundle list, edit `COPY_ITEMS` / `EXCLUDE_*` in
`scripts/prepare-payload.js`.


---

## LITE installer (no models, no bundled Python)

A second build target produces a tiny installer (a few hundred MB instead of
~50 GB). It ships **only** source code + `app/config/.env.example` + bootstrap scripts.
On first install it:

1. Detects/installs **Python 3.11**, **Node.js LTS**, and **Git** per-user
   (no admin needed) via `winget` first, then direct download fallback.
2. Creates `venv-core` and `venv-image` ONLINE from PyPI (+ PyTorch CU128
   index for the image venv).
3. Creates `app/config/.env` from `.env.example` if missing, then patches install-location keys.

### Build it

```powershell
cd app\electron
powershell -ExecutionPolicy Bypass -File scripts\build-lite-installer.ps1
# or:
npm run build:installer-lite
```

Output: `<repo-root>\private\pre-installer\AI-Assistant-Lite-Setup-<version>.exe`

### Files involved

| File | Purpose |
|---|---|
| `electron-builder-lite.yml`              | NSIS config, `perMachine: false`, output `private/pre-installer/` |
| `scripts/prepare-payload-lite.js`        | Stages `payload-lite/` — excludes models, weights, wheels, bundled Python |
| `scripts/bootstrap_prereqs.ps1`          | Auto-installs Python 3.11 / Node / Git per-user |
| `scripts/setup_lite.py`                  | Builds venvs ONLINE from PyPI |
| `build/installer-lite.nsh`               | NSIS hooks: bootstrap → setup → done |

### What user must provide on the target machine

- Internet connection during install (for pip + PyTorch download — ~5 GB).
- Models — drop `.safetensors` / LORAs into `<INSTDIR>\resources\app-payload\ComfyUI\models\` and `<INSTDIR>\resources\app-payload\LORA\` after install.
- Optional NVIDIA GPU + driver supporting CUDA 12.8 for image generation.

### Admin / UAC behaviour

- Installer itself runs `asInvoker` (no UAC prompt).
- Per-user install dir defaults to `%LOCALAPPDATA%\Programs\AI-Assistant-Lite`
  (user can change on the wizard page).
- Python / Node installed via `winget --scope user` or per-user MSI/EXE
  (`InstallAllUsers=0`, `ALLUSERS=""`).
- Git uses PortableGit fallback (zero-touch, no installer at all).
- Only edge cases (missing winget + missing internet) require manual install.
