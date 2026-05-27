"""setup_lite.py — postinstall hook for AI-Assistant LITE installer.

Invoked by NSIS (`installer-lite.nsh`) after `bootstrap_prereqs.ps1` has
installed/located Python 3.11:

    <python.exe> scripts\\setup_lite.py <payload_root>

Differs from setup_venvs.py: NO offline wheel cache. Everything is
pip-installed online from PyPI + PyTorch's CUDA 12.8 index.

Steps
-----
1. Build `<payload>\\venv-core` and `pip install -r requirements-core.txt`.
2. Build `<payload>\\venv-image` and `pip install -r requirements-image.txt`
   plus CUDA torch from `https://download.pytorch.org/whl/cu128`.
3. Patch `app/config/.env` with install-location keys.
4. Log everything to `<payload>\\logs\\setup_lite.log`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from datetime import datetime


PYTORCH_CUDA_INDEX = "https://download.pytorch.org/whl/cu128"
TORCH_PACKAGES = [
    "torch==2.11.0+cu128",
    "torchvision==0.26.0+cu128",
    "torchaudio==2.11.0+cu128",
]


def log(msg: str, fh) -> None:
    line = "[" + datetime.now().strftime("%H:%M:%S") + "] " + msg
    print(line, flush=True)
    fh.write(line + "\n")
    fh.flush()


def run(cmd: list[str], fh) -> None:
    log("$ " + " ".join(cmd), fh)
    subprocess.check_call(cmd, stdout=fh, stderr=subprocess.STDOUT)


def build_venv_online(
    venv_dir: Path, requirements: Path, fh, *, with_cuda_torch: bool
) -> None:
    if venv_dir.exists():
        log("removing existing venv: " + str(venv_dir), fh)
        shutil.rmtree(venv_dir, ignore_errors=True)

    log("creating venv: " + str(venv_dir), fh)
    venv.EnvBuilder(
        system_site_packages=False,
        clear=True,
        symlinks=False,
        with_pip=True,
        upgrade_deps=False,
    ).create(str(venv_dir))

    py = venv_dir / "Scripts" / "python.exe"
    if not py.exists():
        raise RuntimeError("venv python missing: " + str(py))

    # Upgrade pip / wheel / setuptools online.
    run(
        [str(py), "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"], fh
    )

    if requirements.exists():
        log("installing requirements ONLINE from " + str(requirements), fh)
        # --no-deps mirrors the offline behaviour: requirements files are frozen
        # pip-list snapshots, so transitive deps are pinned. Avoids the resolver
        # blowing up on intentionally-conflicting pins.
        cmd = [str(py), "-m", "pip", "install", "--no-deps", "-r", str(requirements)]
        if with_cuda_torch:
            cmd += ["--extra-index-url", PYTORCH_CUDA_INDEX]
        run(cmd, fh)
    else:
        log("WARN: requirements file missing: " + str(requirements), fh)

    if with_cuda_torch:
        log("installing CUDA torch trio from " + PYTORCH_CUDA_INDEX, fh)
        run(
            [
                str(py),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--index-url",
                PYTORCH_CUDA_INDEX,
                *TORCH_PACKAGES,
            ],
            fh,
        )

    check = (
        "import flask, requests; print('core ok')"
        if venv_dir.name == "venv-core"
        else "import sys; print('image ok python', sys.version)"
    )
    log("verifying critical imports for " + venv_dir.name, fh)
    run([str(py), "-c", check], fh)


def patch_env_file(payload_root: Path, fh) -> None:
    env_path = payload_root / "app" / "config" / ".env"
    if not env_path.exists():
        example_path = env_path.with_name(".env.example")
        if example_path.exists():
            env_path.write_text(
                example_path.read_text(encoding="utf-8", errors="replace"),
                encoding="utf-8",
            )
            log("created app/config/.env from .env.example", fh)
        else:
            log("no app/config/.env or .env.example present - skipping path patch", fh)
            return

    marker = "# === INSTALL-LOCATION (set by setup_lite.py) ==="
    end_marker = "# === END INSTALL-LOCATION ==="
    text = env_path.read_text(encoding="utf-8", errors="replace")

    lines, skipping = [], False
    for ln in text.splitlines():
        if ln.strip() == marker:
            skipping = True
            continue
        if skipping:
            if ln.strip() == end_marker:
                skipping = False
            continue
        lines.append(ln)

    pl = str(payload_root).replace("\\", "/")
    inject = [
        marker,
        "AI_ASSISTANT_INSTALL_DIR=" + pl,
        "COMFYUI_OUTPUT_DIR=" + pl + "/ComfyUI/output",
        "REASONING_PIPELINE_COMFY_URL=http://127.0.0.1:8188",
        "COMFYUI_URL=http://127.0.0.1:8188",
        end_marker,
    ]
    new_text = "\n".join(lines).rstrip() + "\n\n" + "\n".join(inject) + "\n"
    env_path.write_text(new_text, encoding="utf-8")
    log("patched " + str(env_path), fh)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: setup_lite.py <payload_root>", file=sys.stderr)
        return 2

    payload_root = Path(sys.argv[1]).resolve()
    if not payload_root.exists():
        print("payload root missing: " + str(payload_root), file=sys.stderr)
        return 2

    log_dir = payload_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "setup_lite.log"

    with open(log_file, "a", encoding="utf-8") as fh:
        log("=" * 70, fh)
        log("setup_lite.py starting at " + datetime.now().isoformat(), fh)
        log("payload     : " + str(payload_root), fh)
        log("python      : " + sys.executable, fh)
        log("python ver  : " + sys.version, fh)

        for sub in ("ComfyUI/output", "logs", "tmp"):
            (payload_root / sub).mkdir(parents=True, exist_ok=True)

        try:
            build_venv_online(
                venv_dir=payload_root / "venv-core",
                requirements=payload_root / "requirements-core.txt",
                fh=fh,
                with_cuda_torch=False,
            )
            build_venv_online(
                venv_dir=payload_root / "venv-image",
                requirements=payload_root / "requirements-image.txt",
                fh=fh,
                with_cuda_torch=True,
            )
            patch_env_file(payload_root, fh)
            log("setup_lite.py finished OK", fh)
            return 0
        except subprocess.CalledProcessError as e:
            log("subprocess failed (exit " + str(e.returncode) + "): " + str(e.cmd), fh)
            return 1
        except Exception as e:  # noqa: BLE001
            log("FATAL: " + type(e).__name__ + ": " + str(e), fh)
            return 1


if __name__ == "__main__":
    sys.exit(main())
