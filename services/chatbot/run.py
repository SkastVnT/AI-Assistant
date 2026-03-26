"""
Chatbot Application Entry Point

Modes (set via environment variables):
  USE_FASTAPI=true        -> FastAPI + Uvicorn  (recommended, native async)
  USE_NEW_STRUCTURE=true  -> Flask modular app factory
  (default)               -> Legacy Flask monolith (chatbot_main.py)
"""

import os
import runpy
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

# Ensure the chatbot service directory is in path
service_dir = Path(__file__).parent
sys.path.insert(0, str(service_dir))

# Add project root for shared configs
project_root = service_dir.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables EARLY — before any app module imports
# so that config class attributes (evaluated at import time) pick up .env values.
from services.shared_env import load_shared_env
load_shared_env(__file__)

# Load chatbot-specific .env for vars not already set by shared env
# (e.g. FAL_API_KEY, STEPFUN_API_KEY that only exist in chatbot .env).
from dotenv import load_dotenv
_chatbot_env = service_dir / '.env'
if _chatbot_env.exists():
    load_dotenv(_chatbot_env)  # no override: shared env values take priority


def _env_flag(name: str, default: str = 'false') -> bool:
    return os.getenv(name, default).lower() in {'1', 'true', 'yes', 'on'}


def _port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_host_port(url: str, default_port: int) -> tuple[str, int]:
    parsed = urlparse(url)
    host = parsed.hostname or '127.0.0.1'
    port = parsed.port or default_port
    return host, port


def _background_flags() -> int:
    flags = 0
    for attr in ('CREATE_NEW_PROCESS_GROUP', 'DETACHED_PROCESS', 'CREATE_NO_WINDOW'):
        flags |= getattr(subprocess, attr, 0)
    return flags


def _spawn_background_process(command: list[str], cwd: Path, log_name: str) -> bool:
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / log_name
    log_handle = open(log_path, 'ab')

    try:
        subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=_background_flags(),
            close_fds=True,
        )
        print(f">> Started background process: {' '.join(command)}")
        print(f">> Logs: {log_path}")
        return True
    except Exception as exc:
        print(f"[WARN] Failed to start {' '.join(command)}: {exc}")
        return False
    finally:
        log_handle.close()


def _spawn_windows_terminal(command_line: str, cwd: Path, title: str) -> bool:
    try:
        wrapped_command = (
            f'{command_line} '
            '& echo. '
            '& echo ================================================== '
            '& echo Process exited. Press any key to close this window. '
            '& echo ================================================== '
            '& pause'
        )
        subprocess.Popen(
            ['cmd.exe', '/c', 'start', title, 'cmd.exe', '/k', wrapped_command],
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0),
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
            [str(python_exe), '-c', 'import torch; print(torch.cuda.is_available())'],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip().lower() == 'true'
    except Exception:
        return False


def _start_comfyui_if_needed() -> None:
    if not _env_flag('AUTO_START_COMFYUI', 'true'):
        return

    comfyui_url = os.getenv('COMFYUI_URL', 'http://127.0.0.1:8188')
    host, port = _parse_host_port(comfyui_url, 8188)
    if _port_is_open(host, port):
        print(f">> ComfyUI already running at {host}:{port}")
        return

    comfyui_dir_candidates = [
        project_root / 'ComfyUI',
        project_root / 'services' / 'edit-image' / 'ComfyUI',
    ]
    comfyui_dir = next((path for path in comfyui_dir_candidates if (path / 'main.py').exists()), None)
    if not comfyui_dir:
        print('[WARN] ComfyUI directory not found. Skipping ComfyUI autostart.')
        return

    # Some local checkouts do not include this folder until first manual run,
    # but ComfyUI expects it to exist during prestartup.
    (comfyui_dir / 'custom_nodes').mkdir(parents=True, exist_ok=True)

    python_exe = _resolve_python(
        project_root / 'venv-image' / 'Scripts' / 'python.exe',
        project_root / 'venv-core' / 'Scripts' / 'python.exe',
    )
    comfyui_args = ['main.py', '--listen', '0.0.0.0', '--port', str(port)]
    comfyui_cpu_mode = os.getenv('COMFYUI_CPU_MODE', 'auto').lower()
    use_cpu = comfyui_cpu_mode == '1' or comfyui_cpu_mode == 'true'
    if comfyui_cpu_mode == 'auto' and not _python_has_cuda(python_exe):
        use_cpu = True

    if use_cpu:
        comfyui_args.append('--cpu')
        print('>> ComfyUI autostart detected CUDA unavailable, using --cpu mode')

    if os.name == 'nt' and _env_flag('IMAGE_SERVICE_VISIBLE_WINDOWS', 'true'):
        comfyui_args_str = ' '.join(comfyui_args)
        command_line = f'cd /d "{comfyui_dir}" && "{python_exe}" {comfyui_args_str}'
        _spawn_windows_terminal(command_line, comfyui_dir, f'ComfyUI {port}')
    else:
        _spawn_background_process(
            [str(python_exe), *comfyui_args],
            comfyui_dir,
            'comfyui-autostart.log',
        )


def _start_stable_diffusion_if_needed() -> None:
    if not _env_flag('AUTO_START_STABLE_DIFFUSION', 'true'):
        return

    port = int(os.getenv('STABLE_DIFFUSION_PORT', '7861'))
    host = os.getenv('STABLE_DIFFUSION_HOST', '127.0.0.1')
    if _port_is_open(host, port):
        print(f">> Stable Diffusion already running at {host}:{port}")
        return

    stable_diffusion_dir = project_root / 'services' / 'stable-diffusion'
    custom_command = os.getenv('STABLE_DIFFUSION_START_COMMAND', '').strip()

    if custom_command:
        if os.name == 'nt' and _env_flag('IMAGE_SERVICE_VISIBLE_WINDOWS', 'true'):
            _spawn_windows_terminal(custom_command, stable_diffusion_dir, f'Stable Diffusion {port}')
        else:
            _spawn_background_process(
                ['cmd.exe', '/c', custom_command],
                stable_diffusion_dir,
                'stable-diffusion-autostart.log',
            )
        return

    webui_bat = stable_diffusion_dir / 'webui.bat'
    if webui_bat.exists():
        command_line = (
            f'cd /d "{stable_diffusion_dir}" && '
            f'webui.bat --port {port} --api --skip-python-version-check --skip-torch-cuda-test --no-half'
        )
        if os.name == 'nt' and _env_flag('IMAGE_SERVICE_VISIBLE_WINDOWS', 'true'):
            _spawn_windows_terminal(command_line, stable_diffusion_dir, f'Stable Diffusion {port}')
        else:
            _spawn_background_process(
                [
                    'cmd.exe', '/c', 'webui.bat',
                    '--port', str(port), '--api',
                    '--skip-python-version-check', '--skip-torch-cuda-test', '--no-half',
                ],
                stable_diffusion_dir,
                'stable-diffusion-autostart.log',
            )
        return

    print('[WARN] Stable Diffusion launcher not found in services/stable-diffusion.')
    print('[WARN] Set STABLE_DIFFUSION_START_COMMAND in services/chatbot/.env if you have a custom launcher.')


def _autostart_image_services() -> None:
    if not _env_flag('AUTO_START_IMAGE_SERVICES', 'true'):
        return

    _start_comfyui_if_needed()
    _start_stable_diffusion_if_needed()


def _should_autostart_services() -> bool:
    if os.getenv('WERKZEUG_RUN_MAIN') == 'true':
        return False
    if os.getenv('RUN_MAIN') == 'true':
        return False
    return True

USE_FASTAPI = os.getenv('USE_FASTAPI', 'false').lower() == 'true'
USE_NEW_STRUCTURE = os.getenv('USE_NEW_STRUCTURE', 'false').lower() == 'true'

if USE_FASTAPI:
    # -- FastAPI mode (recommended) --
    from fastapi_app import create_app as _create_fastapi_app

    app = _create_fastapi_app()

    if __name__ == '__main__':
        import uvicorn

        if _should_autostart_services():
            _autostart_image_services()

        port = int(os.getenv('FLASK_PORT', 5000))
        reload = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'

        print(f">> Starting Chatbot (FastAPI) on port {port}")
        uvicorn.run(
            "run:app",
            host=os.getenv('HOST', '0.0.0.0'),  # noqa: S104
            port=port,
            reload=reload,
            log_level='info',
        )

elif USE_NEW_STRUCTURE:
    # -- Flask modular app factory --
    import importlib.util

    app_init_path = service_dir / 'app' / '__init__.py'
    spec = importlib.util.spec_from_file_location("chatbot_app", app_init_path,
                                                    submodule_search_locations=[str(service_dir / 'app')])
    chatbot_app_module = importlib.util.module_from_spec(spec)
    sys.modules["chatbot_app"] = chatbot_app_module
    spec.loader.exec_module(chatbot_app_module)

    create_app = chatbot_app_module.create_app
    app = create_app(os.getenv('FLASK_ENV', 'development'))

    if __name__ == '__main__':
        if _should_autostart_services():
            _autostart_image_services()

        port = int(os.getenv('FLASK_PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'

        print(f">> Starting Chatbot (Flask New Structure) on port {port}")
        app.run(host=os.getenv('HOST', '0.0.0.0'), port=port, debug=debug)  # noqa: S104

else:
    # -- Legacy Flask monolith --
    print("[i] Using legacy application structure")
    print("[*] Set USE_FASTAPI=true for async FastAPI mode")

    if __name__ == '__main__':
        if _should_autostart_services():
            _autostart_image_services()

        app_py_path = service_dir / 'chatbot_main.py'
        runpy.run_path(str(app_py_path), run_name='__main__')
