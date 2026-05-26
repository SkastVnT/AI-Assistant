"""setup_venvs.py — postinstall hook for AI-Assistant Windows installer.

Invoked by NSIS (`installer.nsh`) right after files are copied:

    python311\\python.exe scripts\\setup_venvs.py <payload_root>

Responsibilities
----------------
1. Build `<payload_root>\\venv-core` from `wheels\\core` (chatbot + MCP deps).
2. Build `<payload_root>\\venv-image` from `wheels\\image` (ComfyUI + image deps).
3. Persist absolute install dir into `app/config/.env` (best-effort) so paths
   that depend on install location resolve correctly.
4. Log everything to `<payload_root>\\logs\\setup_venvs.log`.

Designed to be idempotent: re-running cleans the venv dir and rebuilds.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from datetime import datetime


def log(msg: str, fh) -> None:
    line = "[" + datetime.now().strftime("%H:%M:%S") + "] " + msg
    print(line, flush=True)
    fh.write(line + "\n")
    fh.flush()


def build_venv(venv_dir: Path, wheel_dir: Path, requirements: Path, fh) -> None:
    if venv_dir.exists():
        log("removing existing venv: " + str(venv_dir), fh)
        shutil.rmtree(venv_dir, ignore_errors=True)

    log("creating venv (--copies): " + str(venv_dir), fh)
    builder = venv.EnvBuilder(
        system_site_packages=False,
        clear=True,
        symlinks=False,
        with_pip=True,
        upgrade_deps=False,
    )
    # Use copies so the venv survives if the bundled python311 is moved.
    builder.create(str(venv_dir))

    py = venv_dir / "Scripts" / "python.exe"
    if not py.exists():
        raise RuntimeError("venv python missing after create: " + str(py))

    log("upgrading pip in " + venv_dir.name, fh)
    subprocess.check_call(
        [
            str(py),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheel_dir),
            "--upgrade",
            "pip",
        ],
        stdout=fh,
        stderr=subprocess.STDOUT,
    )

    if not requirements.exists():
        log("WARN: requirements file missing: " + str(requirements), fh)
        return

    # We download the wheel cache with `--no-deps` (the requirements file is a
    # frozen pip-list snapshot — every transitive dep is already pinned and
    # present), so install with `--no-deps` to mirror that behaviour and skip
    # pip's resolver entirely. This avoids resolution-impossible errors on
    # legit-but-conflicting pinned trees (e.g. paddlepaddle vs google-* protobuf).
    log("installing requirements offline from " + str(wheel_dir), fh)
    subprocess.check_call(
        [
            str(py),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--find-links",
            str(wheel_dir),
            "-r",
            str(requirements),
        ],
        stdout=fh,
        stderr=subprocess.STDOUT,
    )

    # For venv-image: requirements-image.txt does NOT pin the CUDA-built
    # torch trio (they live in payload/wheels/image as separate +cu128 wheels).
    # Install them explicitly here so ComfyUI gets a working CUDA torch.
    if venv_dir.name == "venv-image":
        torch_whls = (
            sorted(wheel_dir.glob("torch-*+cu*.whl"))
            + sorted(wheel_dir.glob("torchvision-*+cu*.whl"))
            + sorted(wheel_dir.glob("torchaudio-*+cu*.whl"))
        )
        if torch_whls:
            log(
                "installing CUDA torch wheels: "
                + ", ".join(w.name for w in torch_whls),
                fh,
            )
            subprocess.check_call(
                [
                    str(py),
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--no-deps",
                    *[str(w) for w in torch_whls],
                ],
                stdout=fh,
                stderr=subprocess.STDOUT,
            )
        else:
            log("WARN: no torch +cu*.whl found in " + str(wheel_dir), fh)

    log("verifying critical imports for " + venv_dir.name, fh)
    if venv_dir.name == "venv-core":
        check = "import flask, requests; print('core ok')"
    else:
        check = "import sys; print('image ok python', sys.version)"
    subprocess.check_call([str(py), "-c", check], stdout=fh, stderr=subprocess.STDOUT)


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

    install_marker = "# === INSTALL-LOCATION (set by setup_venvs.py) ==="
    text = env_path.read_text(encoding="utf-8", errors="replace")

    lines = []
    skipping = False
    for ln in text.splitlines():
        if ln.strip() == install_marker:
            skipping = True
            continue
        if skipping:
            if ln.strip().startswith("# === END INSTALL-LOCATION ==="):
                skipping = False
            continue
        lines.append(ln)

    pl = str(payload_root).replace("\\", "/")
    inject = [
        install_marker,
        "AI_ASSISTANT_INSTALL_DIR=" + pl,
        "COMFYUI_OUTPUT_DIR=" + pl + "/ComfyUI/output",
        "REASONING_PIPELINE_COMFY_URL=http://127.0.0.1:8188",
        "COMFYUI_URL=http://127.0.0.1:8188",
        "# === END INSTALL-LOCATION ===",
    ]

    new_text = "\n".join(lines).rstrip() + "\n\n" + "\n".join(inject) + "\n"
    env_path.write_text(new_text, encoding="utf-8")
    log("patched " + str(env_path) + " with install-location keys", fh)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: setup_venvs.py <payload_root>", file=sys.stderr)
        return 2

    payload_root = Path(sys.argv[1]).resolve()
    if not payload_root.exists():
        print("payload root does not exist: " + str(payload_root), file=sys.stderr)
        return 2

    log_dir = payload_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "setup_venvs.log"

    with open(log_file, "a", encoding="utf-8") as fh:
        log("=" * 70, fh)
        log("setup_venvs.py starting at " + datetime.now().isoformat(), fh)
        log("payload root: " + str(payload_root), fh)
        log("python      : " + sys.executable, fh)
        log("python ver  : " + sys.version, fh)

        # Ensure ComfyUI/output exists so the chatbot's local-image-gen polling
        # never trips on a missing dir at first run.
        (payload_root / "ComfyUI" / "output").mkdir(parents=True, exist_ok=True)
        (payload_root / "logs").mkdir(parents=True, exist_ok=True)
        (payload_root / "tmp").mkdir(parents=True, exist_ok=True)

        try:
            build_venv(
                venv_dir=payload_root / "venv-core",
                wheel_dir=payload_root / "wheels" / "core",
                requirements=payload_root / "requirements-core.txt",
                fh=fh,
            )
            build_venv(
                venv_dir=payload_root / "venv-image",
                wheel_dir=payload_root / "wheels" / "image",
                requirements=payload_root / "requirements-image.txt",
                fh=fh,
            )
            patch_env_file(payload_root, fh)
            log("setup_venvs.py completed successfully", fh)
            return 0
        except subprocess.CalledProcessError as e:
            log("subprocess failed (exit " + str(e.returncode) + "): " + str(e.cmd), fh)
            return 1
        except Exception as e:  # noqa: BLE001 — top-level installer hook, surface any failure
            log("FATAL: " + type(e).__name__ + ": " + str(e), fh)
            return 1


if __name__ == "__main__":
    sys.exit(main())
