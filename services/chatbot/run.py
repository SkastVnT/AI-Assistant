"""
Chatbot Application Entry Point

Desktop-only build: launches the Flask monolith (chatbot_main.py).
FastAPI and modular-app-factory modes were removed.
"""

import atexit
import logging
import os
import runpy
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from services.shared_env import load_shared_env

# Tracks all background sidecar processes spawned by this session so they
# can be killed when the chatbot exits (atexit handler below).
_sidecar_processes: list[subprocess.Popen] = []


def _kill_sidecars() -> None:
    """Kill all tracked sidecar processes on Python interpreter exit."""
    for proc in _sidecar_processes:
        try:
            if proc.poll() is None:
                proc.kill()
        except Exception as exc:
            logging.warning(
                "Failed to kill sidecar process pid=%s during shutdown: %s",
                getattr(proc, "pid", "unknown"),
                exc,
                exc_info=True,
            )


atexit.register(_kill_sidecars)

# Ensure stdout/stderr emit UTF-8 on Windows (default is cp1252 which garbles emoji).
# Python 3.7+ TextIOWrapper supports reconfigure(); falls back to PYTHONIOENCODING env var.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Configure logging early — before any module imports so all loggers inherit this config.
# NOTE: force=False (default) so that when uvicorn worker re-imports this module it does NOT
# wipe uvicorn's access-log handlers that were already set up by the worker bootstrap.
# The basicConfig call is effectively a no-op inside the worker (root logger already has handlers).
_log_level = logging.DEBUG if os.getenv("DEBUG", "0") == "1" else logging.INFO
if not logging.root.handlers:
    logging.basicConfig(
        level=_log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
else:
    logging.root.setLevel(_log_level)
# Reduce noise from verbose third-party loggers
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("multipart").setLevel(logging.WARNING)

# Ensure the chatbot service directory is in path
service_dir = Path(__file__).parent

# Add project root for shared configs
project_root = service_dir.parent.parent
app_root = project_root / "app"

# Guarantee priority order at the front of sys.path:
#   project_root > service_dir > app_root
# Strip any existing occurrences first (Python may have auto-inserted
# service_dir, and PYTHONPATH may have added others), then prepend together.
_priority = [str(project_root), str(service_dir), str(app_root)]
sys.path = _priority + [p for p in sys.path if p not in set(_priority)]

# Load environment variables EARLY — before any app module imports
# so that config class attributes (evaluated at import time) pick up .env values.

load_shared_env(__file__)

# Load chatbot-specific .env for vars not already set by shared env
# (e.g. FAL_API_KEY, STEPFUN_API_KEY that only exist in chatbot .env).

_chatbot_env = service_dir / ".env"
if _chatbot_env.exists():
    load_dotenv(_chatbot_env)  # no override: shared env values take priority


def _env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


def _port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_host_port(url: str, default_port: int) -> tuple[str, int]:
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or default_port
    return host, port


def _background_flags() -> int:
    flags = 0
    for attr in ("CREATE_NEW_PROCESS_GROUP", "DETACHED_PROCESS", "CREATE_NO_WINDOW"):
        flags |= getattr(subprocess, attr, 0)
    return flags


def _spawn_background_process(
    command: list[str],
    cwd: Path,
    log_name: str,
    env: dict | None = None,
) -> bool:
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / log_name
    log_handle = open(log_path, "ab")  # noqa: SIM115  # must stay open for Popen

    try:
        child = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            creationflags=_background_flags(),
            close_fds=True,
        )
        _sidecar_processes.append(child)
        print(f">> Started background process: {' '.join(command)}")
        print(f">> Logs: {log_path}")
        return True
    except Exception as exc:
        print(f"[WARN] Failed to start {' '.join(command)}: {exc}")
        return False
    finally:
        log_handle.close()


def _spawn_windows_terminal(command_line: str, cwd: Path, title: str) -> bool:
    import tempfile

    try:
        bat_lines = [
            "@echo off",
            command_line,
            "echo.",
            "echo ==================================================",
            "echo Process exited. Press any key to close this window.",
            "echo ==================================================",
            "pause",
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bat", delete=False, encoding="utf-8"
        ) as f:
            f.write("\n".join(bat_lines) + "\n")
            bat_path = Path(f.name)

        subprocess.Popen(
            f'cmd.exe /c start "{title}" cmd.exe /k "{bat_path}"',
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            close_fds=True,
        )
        print(f">> Started terminal window: {title}")
        print(f">> Working directory: {cwd}")
        return True
    except Exception as exc:
        print(f"[WARN] Failed to start terminal window '{title}': {exc}")
        return False


def _resolve_python(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def _python_has_cuda(python_exe: Path) -> bool:
    try:
        result = subprocess.run(
            [str(python_exe), "-c", "import torch; print(torch.cuda.is_available())"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip().lower() == "true"
    except Exception:
        return False


def _start_comfyui_if_needed() -> None:
    if not _env_flag("AUTO_START_COMFYUI", "true"):
        return

    comfyui_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    host, port = _parse_host_port(comfyui_url, 8188)
    if _port_is_open(host, port):
        print(f">> ComfyUI already running at {host}:{port}")
        return

    comfyui_dir_candidates = [
        project_root / "ComfyUI",
        project_root / "services" / "edit-image" / "ComfyUI",
    ]
    comfyui_dir = next(
        (path for path in comfyui_dir_candidates if (path / "main.py").exists()), None
    )
    if not comfyui_dir:
        print("[WARN] ComfyUI directory not found. Skipping ComfyUI autostart.")
        return

    # Some local checkouts do not include this folder until first manual run,
    # but ComfyUI expects it to exist during prestartup.
    (comfyui_dir / "custom_nodes").mkdir(parents=True, exist_ok=True)

    python_exe = _resolve_python(
        project_root / "venv-image" / "Scripts" / "python.exe",
        project_root / "venv-core" / "Scripts" / "python.exe",
    )
    comfyui_args = [
        "main.py",
        "--listen",
        "0.0.0.0",
        "--port",
        str(port),
    ]  # nosec B104  # ComfyUI service binding
    comfyui_cpu_mode = os.getenv("COMFYUI_CPU_MODE", "auto").lower()
    use_cpu = comfyui_cpu_mode == "1" or comfyui_cpu_mode == "true"
    if comfyui_cpu_mode == "auto" and not _python_has_cuda(python_exe):
        use_cpu = True

    if use_cpu:
        comfyui_args.append("--cpu")
        print(">> ComfyUI autostart detected CUDA unavailable, using --cpu mode")

    # On Windows with IMAGE_SERVICE_VISIBLE_WINDOWS=true (the default), open
    # ComfyUI in its own terminal window.  This avoids the forrtl/Intel-MKL
    # "program aborting due to window-CLOSE event" crash that occurs when
    # PyTorch/MKL registers a console-close handler and the background-process
    # flags (CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS) interfere with it.
    # The hidden-background path is kept for headless / CI / Electron builds
    # where IMAGE_SERVICE_VISIBLE_WINDOWS is explicitly set to false.
    if os.name == "nt" and _env_flag("IMAGE_SERVICE_VISIBLE_WINDOWS", "true"):
        comfyui_args_str = " ".join(f'"{a}"' if " " in a else a for a in comfyui_args)
        command_line = f'cd /d "{comfyui_dir}" && "{python_exe}" {comfyui_args_str}'
        _spawn_windows_terminal(command_line, comfyui_dir, f"ComfyUI {port}")
    else:
        _spawn_background_process(
            [str(python_exe), *comfyui_args],
            comfyui_dir,
            "comfyui-autostart.log",
        )


def _start_stable_diffusion_if_needed() -> None:
    if not _env_flag("AUTO_START_STABLE_DIFFUSION", "true"):
        return

    port = int(os.getenv("STABLE_DIFFUSION_PORT", "7861"))
    host = os.getenv("STABLE_DIFFUSION_HOST", "127.0.0.1")
    if _port_is_open(host, port):
        print(f">> Stable Diffusion already running at {host}:{port}")
        return

    stable_diffusion_dir = project_root / "services" / "stable-diffusion"
    custom_command = os.getenv("STABLE_DIFFUSION_START_COMMAND", "").strip()

    if custom_command:
        if os.name == "nt" and _env_flag("IMAGE_SERVICE_VISIBLE_WINDOWS", "true"):
            _spawn_windows_terminal(
                custom_command, stable_diffusion_dir, f"Stable Diffusion {port}"
            )
        else:
            _spawn_background_process(
                ["cmd.exe", "/c", custom_command],
                stable_diffusion_dir,
                "stable-diffusion-autostart.log",
            )
        return

    webui_bat = stable_diffusion_dir / "webui.bat"
    if webui_bat.exists():
        command_line = (
            f'cd /d "{stable_diffusion_dir}" && '
            f"webui.bat --port {port} --api --skip-python-version-check --skip-torch-cuda-test --no-half"
        )
        if os.name == "nt" and _env_flag("IMAGE_SERVICE_VISIBLE_WINDOWS", "true"):
            _spawn_windows_terminal(
                command_line, stable_diffusion_dir, f"Stable Diffusion {port}"
            )
        else:
            _spawn_background_process(
                [
                    "cmd.exe",
                    "/c",
                    "webui.bat",
                    "--port",
                    str(port),
                    "--api",
                    "--skip-python-version-check",
                    "--skip-torch-cuda-test",
                    "--no-half",
                ],
                stable_diffusion_dir,
                "stable-diffusion-autostart.log",
            )
        return

    print("[WARN] Stable Diffusion launcher not found in services/stable-diffusion.")
    print(
        "[WARN] Set STABLE_DIFFUSION_START_COMMAND in services/chatbot/.env if you have a custom launcher."
    )


def _autostart_image_services() -> None:
    if not _env_flag("AUTO_START_IMAGE_SERVICES", "true"):
        return

    _start_comfyui_if_needed()
    _start_stable_diffusion_if_needed()
    _start_character_select_if_needed()


def _start_character_select_if_needed() -> None:
    """Spawn the Character Select SAA Electron sidecar when configured.

    Gated by both ``CHARACTER_SELECT_ENABLED`` and
    ``CHARACTER_SELECT_AUTO_START`` so the sidecar only launches when the
    operator has explicitly opted in. Skips silently when the install
    directory is missing or the port is already in use.
    """
    if not _env_flag("CHARACTER_SELECT_ENABLED", "false"):
        return
    if not _env_flag("CHARACTER_SELECT_AUTO_START", "false"):
        return

    saa_url = os.getenv("CHARACTER_SELECT_URL", "http://localhost:51028")
    saa_port_env = os.getenv("CHARACTER_SELECT_PORT", "51028")
    try:
        saa_port = int(saa_port_env)
    except ValueError:
        saa_port = 51028
    host, port = _parse_host_port(saa_url, saa_port)
    if _port_is_open(host, port):
        print(f">> Character Select SAA already running at {host}:{port}")
        return

    saa_path_str = os.getenv(
        "CHARACTER_SELECT_PATH",
        str(app_root / "character_select_stand_alone_app-main"),
    )
    saa_path = Path(saa_path_str)
    if not saa_path.is_absolute():
        saa_path = (project_root / saa_path).resolve()
    if not (saa_path / "package.json").exists():
        print(
            f"[WARN] Character Select SAA not found at {saa_path}. Skipping autostart."
        )
        return

    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

    # 2026-04-28: guard against silent FileNotFoundError when npm is not
    # on PATH. Previously we'd spawn `npm.cmd` blindly and the user
    # would only see a vague background failure in the log file. Skip
    # cleanly with an actionable message instead.
    import shutil

    if shutil.which(npm_cmd) is None:
        print(
            f"[WARN] Character Select SAA autostart skipped: '{npm_cmd}' not found on PATH. "
            f"Install Node.js (https://nodejs.org/) or set CHARACTER_SELECT_AUTO_START=false."
        )
        return

    # First-run install: SAA ships a package.json but no node_modules; without
    # Electron installed, `npm start` immediately fails with
    # "'electron' is not recognized". Install once on first launch.
    needs_install = not (saa_path / "node_modules" / "electron").exists()
    install_clause = f"{npm_cmd} install && " if needs_install else ""

    # Build env for SAA process — inherit current env and add SHOW_ELECTRON_SAA.
    # Default false: SAA runs as a headless webserver (no Electron window) unless
    # the operator explicitly sets SHOW_ELECTRON_SAA=true.
    saa_env = dict(os.environ)
    saa_env["SHOW_ELECTRON_SAA"] = os.getenv("SHOW_ELECTRON_SAA", "false")

    if (
        os.name == "nt"
        and _env_flag("IMAGE_SERVICE_VISIBLE_WINDOWS", "true")
        and _env_flag("SHOW_ELECTRON_SAA", "false")
    ):
        command_line = f'cd /d "{saa_path}" && {install_clause}{npm_cmd} start'
        _spawn_windows_terminal(command_line, saa_path, f"Character Select {port}")
    elif needs_install:
        # Headless: chain install → start in one shell so the spawned
        # process tree stays attached to the same log file.
        shell_cmd = f"{npm_cmd} install && {npm_cmd} start"
        if os.name == "nt":
            _spawn_background_process(
                ["cmd.exe", "/c", shell_cmd],
                saa_path,
                "character-select-autostart.log",
                env=saa_env,
            )
        else:
            _spawn_background_process(
                ["sh", "-c", shell_cmd],
                saa_path,
                "character-select-autostart.log",
                env=saa_env,
            )
    else:
        _spawn_background_process(
            [npm_cmd, "start"],
            saa_path,
            "character-select-autostart.log",
            env=saa_env,
        )


def _should_autostart_services() -> bool:
    if os.getenv("WERKZEUG_RUN_MAIN") == "true":
        return False
    return os.getenv("RUN_MAIN") != "true"


USE_FASTAPI = False
USE_NEW_STRUCTURE = False

# -- Flask monolith (only supported mode) --
if __name__ == "__main__":
    if _should_autostart_services():
        _autostart_image_services()

    app_py_path = service_dir / "chatbot_main.py"
    runpy.run_path(str(app_py_path), run_name="__main__")
