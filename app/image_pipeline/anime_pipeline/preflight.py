"""Asset and endpoint preflight for standalone LOCAL anime deployments."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from image_pipeline.paths import COMFYUI_DIR, CONFIGS_DIR

from .config import AnimePipelineConfig, load_config
from .runtime_policy import RuntimePolicy

_PROVISIONING_MANIFEST = CONFIGS_DIR / "anime_pipeline_assets.yaml"


@dataclass
class AssetCheck:
    asset_id: str
    path: str
    required: bool
    exists: bool
    checksum_ok: bool | None = None
    detail: str = ""

    @property
    def ready(self) -> bool:
        return self.exists and self.checksum_ok is not False

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "path": self.path,
            "required": self.required,
            "exists": self.exists,
            "checksum_ok": self.checksum_ok,
            "detail": self.detail,
        }


@dataclass
class PreflightReport:
    profile: str
    runtime_policy: dict[str, object]
    checks: list[AssetCheck] = field(default_factory=list)
    capabilities: dict[str, str] = field(default_factory=dict)
    active_models: list[str] = field(default_factory=list)
    endpoint_health: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def missing_assets(self) -> list[str]:
        return [check.path for check in self.checks if not check.ready]

    @property
    def readiness(self) -> str:
        if self.errors or any(c.required and not c.ready for c in self.checks):
            return "blocked"
        if self.missing_assets or any(not ok for ok in self.endpoint_health.values()):
            return "degraded"
        return "ready"

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "runtime_policy": self.runtime_policy,
            "readiness": self.readiness,
            "capabilities": self.capabilities,
            "missing_assets": self.missing_assets,
            "active_models": self.active_models,
            "endpoint_health": self.endpoint_health,
            "errors": self.errors,
            "checks": [check.to_dict() for check in self.checks],
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_assets(profile: str) -> list[dict[str, Any]]:
    if not _PROVISIONING_MANIFEST.exists():
        return []
    raw = yaml.safe_load(_PROVISIONING_MANIFEST.read_text(encoding="utf-8")) or {}
    assets = raw.get("assets", []) if isinstance(raw, dict) else []
    return [
        asset
        for asset in assets
        if isinstance(asset, dict) and profile in (asset.get("profiles") or [])
    ]


def configured_asset_checksums(profile: str) -> dict[str, str]:
    """Return operator-declared checksums for provenance manifests."""

    return {
        str(asset.get("id", "")): str(asset.get("sha256", ""))
        for asset in _manifest_assets(profile)
        if asset.get("id") and asset.get("sha256")
    }


def _check_path(
    report: PreflightReport,
    asset_id: str,
    path: Path,
    *,
    required: bool,
    expected_sha256: str = "",
    detail: str = "",
) -> AssetCheck:
    exists = path.is_file()
    checksum_ok: bool | None = None
    if exists and expected_sha256:
        checksum_ok = _sha256(path).lower() == expected_sha256.lower()
    check = AssetCheck(
        asset_id=asset_id,
        path=str(path),
        required=required,
        exists=exists,
        checksum_ok=checksum_ok,
        detail=detail,
    )
    report.checks.append(check)
    return check


def _probe(url: str, path: str, timeout: float = 2.0) -> bool:
    import httpx

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{url.rstrip('/')}/{path.lstrip('/')}")
            return response.status_code == 200
    except Exception:
        return False


def run_preflight(
    config: AnimePipelineConfig | None = None,
    *,
    comfyui_dir: str | Path | None = None,
    probe_remote: bool = False,
) -> PreflightReport:
    cfg = config or load_config()
    comfy_root = Path(comfyui_dir or COMFYUI_DIR)
    policy = RuntimePolicy.from_config(cfg)
    report = PreflightReport(
        profile=cfg.deployment_profile,
        runtime_policy=policy.to_dict(),
    )

    checkpoints: list[str] = []
    for model in (cfg.composition_model, cfg.beauty_model, cfg.final_model):
        if model.checkpoint and model.checkpoint not in checkpoints:
            checkpoints.append(model.checkpoint)
    for checkpoint in checkpoints:
        _check_path(
            report,
            f"checkpoint:{checkpoint}",
            comfy_root / "models" / "checkpoints" / checkpoint,
            required=True,
        )
    report.active_models.extend(checkpoints)

    for layer in cfg.structure_layers:
        if not layer.enabled or not layer.controlnet_model:
            continue
        model_name = layer.controlnet_model
        if not Path(model_name).suffix:
            model_name = f"{model_name}.safetensors"
        _check_path(
            report,
            f"controlnet:{layer.layer_type}",
            comfy_root / "models" / "controlnet" / model_name,
            required=not layer.optional,
            detail="Enabled structure layer",
        )

    for item in _manifest_assets(cfg.deployment_profile):
        destination = str(item.get("destination", ""))
        if not destination or destination.endswith(
            "waiIllustriousSDXL_v170.safetensors"
        ):
            continue
        path = Path(destination)
        if not path.is_absolute():
            path = comfy_root.parent / path
        _check_path(
            report,
            str(item.get("id", destination)),
            path,
            required=False,
            expected_sha256=str(item.get("sha256", "")),
            detail="Provision manually; runtime downloads are disabled",
        )

    for capability, enabled in cfg.capabilities.items():
        if not enabled:
            report.capabilities[capability] = "blocked"
            continue
        related = [
            check
            for check in report.checks
            if capability in check.asset_id
            or (capability == "flux2_klein" and "flux2_klein" in check.asset_id)
            or (capability == "qwen_image_edit" and "qwen_image_edit" in check.asset_id)
        ]
        report.capabilities[capability] = (
            "ready" if related and all(check.ready for check in related) else "degraded"
        )

    if probe_remote:
        comfy_url = cfg.comfyui_url or "http://127.0.0.1:8188"
        try:
            policy.assert_url(comfy_url, purpose="comfyui_health")
            report.endpoint_health["comfyui"] = _probe(comfy_url, "/system_stats")
            report.endpoint_health["comfyui_object_info"] = _probe(
                comfy_url, "/object_info"
            )
        except Exception as exc:
            report.endpoint_health["comfyui"] = False
            report.errors.append(str(exc))

        if cfg.local_vlm_url:
            try:
                policy.assert_url(cfg.local_vlm_url, purpose="local_vlm_health")
                report.endpoint_health["local_vlm"] = _probe(
                    cfg.local_vlm_url, "/models"
                )
                if cfg.local_vlm_required and not report.endpoint_health["local_vlm"]:
                    report.errors.append("Required local VLM is not reachable")
            except Exception as exc:
                report.endpoint_health["local_vlm"] = False
                report.errors.append(str(exc))

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", action="store_true", help="Probe local HTTP workers")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()
    report = run_preflight(probe_remote=args.remote)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Anime LOCAL preflight: {report.profile} -> {report.readiness}")
        for missing in report.missing_assets:
            print(f"  missing: {missing}")
        for name, state in sorted(report.capabilities.items()):
            print(f"  capability {name}: {state}")
    return 1 if report.readiness == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
