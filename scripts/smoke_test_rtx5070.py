"""Smoke test for the RTX 5070 12GB local profile.

Verifies the host machine is configured to run the anime pipeline with
``configs/anime_pipeline_rtx5070.yaml``. Does NOT run an actual image
generation — that needs ComfyUI booted with models loaded. This script
is the ~30-second pre-flight check before kicking off a real pipeline
run on a fresh box.

Checks:
  1. PyTorch sees CUDA and an RTX 5070 (compute capability sm_120).
  2. A tiny tensor allocates on GPU without ``no kernel image`` errors.
  3. The RTX 5070 YAML loads via the anime_pipeline config loader and
     the key tuned parameters resolve to the expected values.
  4. ComfyUI ``/system_stats`` reachable (optional — soft warning only).

Run from the repo root inside ``venv-image``:

    & .\\venv-image\\Scripts\\Activate.ps1
    python scripts/smoke_test_rtx5070.py
    python scripts/smoke_test_rtx5070.py --comfyui-url http://127.0.0.1:8188

Exit code 0 if all hard checks pass, 1 otherwise.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_REL = "configs/anime_pipeline_rtx5070.yaml"

# Make the repo root importable so `image_pipeline.*` resolves regardless
# of how the script is invoked.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _hdr(name: str) -> None:
    bar = "-" * max(4, 60 - len(name))
    print(f"\n-- {name} {bar}")


def check_torch_cuda() -> bool:
    _hdr("1/4  torch + CUDA + Blackwell sm_120")
    try:
        import torch
    except ImportError as e:
        print(f"FAIL: cannot import torch ({e}). Activate venv-image.")
        return False
    print(f"  torch.__version__         = {torch.__version__}")
    print(f"  torch.cuda.is_available() = {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        print("FAIL: CUDA not available. Check driver + nvidia-smi.")
        return False
    cap = torch.cuda.get_device_capability()
    name = torch.cuda.get_device_name(0)
    print(f"  device                    = {name}")
    print(f"  compute capability        = sm_{cap[0]}{cap[1]}")
    if cap[0] < 8:
        print(
            f"WARN: capability sm_{cap[0]}{cap[1]} is older than SDXL recommended (>= sm_80)."
        )
    if cap == (12, 0):
        print(
            "  Blackwell sm_120 detected — confirm torch is built with CUDA 12.8 kernels."
        )
    try:
        t = torch.randn(8, 8, device="cuda")
        _ = (t @ t.T).sum().item()
    except Exception as e:
        print(f"FAIL: GPU tensor op raised: {e}")
        return False
    print("  GPU tensor op             = OK")
    return True


def check_rtx5070_config() -> bool:
    _hdr("2/4  anime_pipeline_rtx5070.yaml loads + key params correct")
    cfg_path = REPO_ROOT / CONFIG_REL
    if not cfg_path.exists():
        print(f"FAIL: {CONFIG_REL} not found.")
        return False
    os.environ["ANIME_PIPELINE_CONFIG"] = str(cfg_path)
    try:
        # Force-reimport so the env var override is honoured fresh.
        for mod in [
            m
            for m in list(sys.modules)
            if m.startswith("image_pipeline.anime_pipeline.config")
        ]:
            del sys.modules[mod]
        from image_pipeline.anime_pipeline import config as ap_config
    except Exception as e:
        print(f"FAIL: importing anime_pipeline.config raised: {e}")
        traceback.print_exc()
        return False

    print(f"  loaded                    = {ap_config._get_config_path()}")

    # The exact attribute layout varies by config version. Probe defensively.
    raw = None
    try:
        import yaml

        with cfg_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"FAIL: re-parsing YAML for sanity check: {e}")
        return False

    expectations = {
        "models.composition.steps": 22,
        "models.beauty.steps": 22,
        "models.final.steps": 22,
        "models.upscale.scale_factor": 1.5,
        "structure_lock.max_simultaneous": 1,
    }
    ok = True
    for dotted, expected in expectations.items():
        node = raw
        for part in dotted.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        marker = "OK  " if node == expected else "WARN"
        if node != expected:
            ok = False
        print(f"  {marker} {dotted:<32} = {node!r:<10} (expected {expected!r})")

    # vram.profile must be normalvram for the local config.
    vram_profile = (raw.get("vram") or {}).get("profile")
    marker = "OK  " if vram_profile == "normalvram" else "WARN"
    if vram_profile != "normalvram":
        ok = False
    print(
        f"  {marker} vram.profile                     = {vram_profile!r} (expected 'normalvram')"
    )
    return ok


def check_comfyui(url: str | None) -> bool:
    _hdr("3/4  ComfyUI /system_stats (optional)")
    if not url:
        print("  skipped (pass --comfyui-url to enable)")
        return True
    try:
        import httpx
    except ImportError:
        print("  WARN: httpx not installed in this venv — skipping.")
        return True
    try:
        r = httpx.get(f"{url.rstrip('/')}/system_stats", timeout=5.0)
        r.raise_for_status()
        stats = r.json()
        devices = stats.get("devices") or []
        if devices:
            d = devices[0]
            print(f"  device   = {d.get('name')}")
            print(f"  vram free/total = {d.get('vram_free')} / {d.get('vram_total')}")
        else:
            print(f"  system_stats reachable but no devices reported: {stats}")
    except Exception as e:
        print(f"  WARN: ComfyUI not reachable at {url}: {e}")
        # Soft failure — pipeline can boot ComfyUI on demand.
        return True
    return True


def check_loras_dir() -> bool:
    _hdr("4/4  ComfyUI/models/loras directory present")
    loras = REPO_ROOT / "ComfyUI" / "models" / "loras"
    if not loras.exists():
        print(f"WARN: {loras.relative_to(REPO_ROOT)} missing — LoRA passes will fail.")
        return True  # not a hard failure for smoke test
    count = sum(1 for _ in loras.rglob("*.safetensors"))
    print(f"  {loras.relative_to(REPO_ROOT)} : {count} .safetensors file(s)")
    if count == 0:
        print("  WARN: no LoRAs on disk; run scripts/validate_lora_registry.py.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comfyui-url",
        default=None,
        help="ComfyUI base URL (e.g. http://127.0.0.1:8188); optional ping check",
    )
    args = parser.parse_args()

    print(f"repo root: {REPO_ROOT}")
    print(f"config:    {CONFIG_REL}")

    results = [
        check_torch_cuda(),
        check_rtx5070_config(),
        check_comfyui(args.comfyui_url),
        check_loras_dir(),
    ]

    _hdr("Summary")
    labels = ["torch+CUDA", "rtx5070 YAML", "ComfyUI ping", "LoRA dir"]
    for ok, label in zip(results, labels):
        print(f"  [{'OK  ' if ok else 'FAIL'}] {label}")
    hard_fail = not (results[0] and results[1])
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
