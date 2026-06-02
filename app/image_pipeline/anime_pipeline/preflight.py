"""Asset and endpoint preflight for standalone LOCAL anime deployments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from image_pipeline.paths import COMFYUI_DIR, CONFIGS_DIR

from .config import AnimePipelineConfig, load_config
from .runtime_policy import RuntimePolicy

_PROVISIONING_MANIFEST = CONFIGS_DIR / "anime_pipeline_assets.yaml"
_CAPABILITY_NODE_CONTRACTS: dict[str, frozenset[str]] = {
    "controlnet": frozenset(
        {
            "SetUnionControlNetType",
            "DWPreprocessor",
            "AnimeLineArtPreprocessor",
            "DepthAnythingV2Preprocessor",
            "CannyEdgePreprocessor",
        }
    ),
    "ipadapter": frozenset({"IPAdapterUnifiedLoader", "IPAdapter"}),
}


@dataclass
class AssetCheck:
    asset_id: str
    path: str
    required: bool
    exists: bool
    checksum_ok: bool | None = None
    checksum_required: bool = False
    detail: str = ""

    @property
    def ready(self) -> bool:
        return (
            self.exists
            and self.checksum_ok is not False
            and not (self.checksum_required and self.checksum_ok is None)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "path": self.path,
            "required": self.required,
            "exists": self.exists,
            "checksum_ok": self.checksum_ok,
            "checksum_required": self.checksum_required,
            "detail": self.detail,
        }


@dataclass
class PreflightReport:
    profile: str
    runtime_policy: dict[str, object]
    parity: bool = False
    checks: list[AssetCheck] = field(default_factory=list)
    capabilities: dict[str, str] = field(default_factory=dict)
    active_models: list[str] = field(default_factory=list)
    endpoint_health: dict[str, bool] = field(default_factory=dict)
    node_contract: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def missing_assets(self) -> list[str]:
        return [check.path for check in self.checks if not check.ready]

    @property
    def readiness(self) -> str:
        if self.errors or any(c.required and not c.ready for c in self.checks):
            return "blocked"
        if self.parity and any(not ok for ok in self.endpoint_health.values()):
            return "blocked"
        if self.missing_assets or any(not ok for ok in self.endpoint_health.values()):
            return "degraded"
        return "ready"

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "parity": self.parity,
            "runtime_policy": self.runtime_policy,
            "readiness": self.readiness,
            "capabilities": self.capabilities,
            "missing_assets": self.missing_assets,
            "active_models": self.active_models,
            "endpoint_health": self.endpoint_health,
            "node_contract": self.node_contract,
            "missing_nodes": [
                node for node, ready in self.node_contract.items() if not ready
            ],
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
    checksum_required: bool = False,
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
        checksum_required=checksum_required,
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


def _probe_json(url: str, path: str, timeout: float = 2.0) -> dict[str, Any] | None:
    import httpx

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{url.rstrip('/')}/{path.lstrip('/')}")
            if response.status_code != 200:
                return None
            payload = response.json()
            return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _workflow_node_types(path: Path) -> set[str]:
    try:
        workflow = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    if not isinstance(workflow, dict) or _contains_stub_workflow(workflow):
        return set()
    return {
        str(node.get("class_type", ""))
        for node in workflow.values()
        if isinstance(node, dict) and node.get("class_type")
    }


def run_preflight(
    config: AnimePipelineConfig | None = None,
    *,
    comfyui_dir: str | Path | None = None,
    probe_remote: bool = False,
    parity: bool = False,
) -> PreflightReport:
    cfg = config or load_config()
    comfy_root = Path(comfyui_dir or COMFYUI_DIR)
    policy = RuntimePolicy.from_config(cfg)
    report = PreflightReport(
        profile=cfg.deployment_profile,
        runtime_policy=policy.to_dict(),
        parity=parity,
    )
    try:
        policy.assert_worker_ready()
    except Exception as exc:
        report.errors.append(str(exc))

    manifest_assets = _manifest_assets(cfg.deployment_profile)
    checkpoint_manifests = {
        Path(str(item.get("destination", ""))).name: item
        for item in manifest_assets
        if item.get("destination")
    }
    checkpoints: list[str] = []
    for model in (cfg.composition_model, cfg.beauty_model, cfg.final_model):
        if model.checkpoint and model.checkpoint not in checkpoints:
            checkpoints.append(model.checkpoint)
    for checkpoint in checkpoints:
        checkpoint_manifest = checkpoint_manifests.get(checkpoint, {})
        _check_path(
            report,
            f"checkpoint:{checkpoint}",
            comfy_root / "models" / "checkpoints" / checkpoint,
            required=True,
            expected_sha256=str(checkpoint_manifest.get("sha256", "")),
            checksum_required=parity,
            detail="Active checkpoint",
        )
        if parity:
            if not checkpoint_manifest:
                report.errors.append(
                    f"Parity manifest has no active checkpoint entry for {checkpoint}"
                )
            for key in ("sha256", "source_url", "license"):
                if not str(checkpoint_manifest.get(key, "")).strip():
                    report.errors.append(
                        f"Parity manifest requires {key} for active checkpoint {checkpoint}"
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

    manifest_checks: list[tuple[dict[str, Any], AssetCheck]] = []
    native_workflow_nodes: set[str] = set()
    for item in manifest_assets:
        destination = str(item.get("destination", ""))
        if not destination or destination.endswith(
            "waiIllustriousSDXL_v170.safetensors"
        ):
            continue
        path = Path(destination)
        if not path.is_absolute():
            path = comfy_root.parent / path
        capability = str(item.get("required_for_capability", ""))
        required = bool(capability and cfg.capabilities.get(capability, False))
        check = _check_path(
            report,
            str(item.get("id", destination)),
            path,
            required=required,
            expected_sha256=str(item.get("sha256", "")),
            checksum_required=required,
            detail="Provision manually; runtime downloads are disabled",
        )
        manifest_checks.append((item, check))
        if required and path.suffix.lower() == ".json" and check.exists:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if _contains_stub_workflow(raw):
                    check.checksum_ok = False
                    check.detail = "Replace operator-export workflow stub"
                else:
                    native_workflow_nodes.update(_workflow_node_types(path))
            except Exception as exc:
                check.checksum_ok = False
                check.detail = f"Invalid workflow JSON: {exc}"
        if parity and required:
            for key in ("sha256", "source_url", "license"):
                if not str(item.get(key, "")).strip():
                    report.errors.append(
                        f"Parity manifest requires {key} for {item.get('id', destination)}"
                    )

    if (
        cfg.deployment_profile == "vps_96gb"
        and cfg.capabilities.get("flux2_klein", False)
        and os.getenv("ANIME_PIPELINE_ACCEPT_FLUX2_KLEIN_9B_NONCOMMERCIAL", "")
        .strip()
        .lower()
        not in {"1", "true", "yes", "on"}
    ):
        report.errors.append(
            "vps_96gb FLUX.2 Klein 9B requires "
            "ANIME_PIPELINE_ACCEPT_FLUX2_KLEIN_9B_NONCOMMERCIAL=1"
        )

    for capability, enabled in cfg.capabilities.items():
        if not enabled:
            report.capabilities[capability] = "blocked"
            continue
        related = [
            check
            for item, check in manifest_checks
            if item.get("required_for_capability") == capability
        ]
        report.capabilities[capability] = (
            "ready" if related and all(check.ready for check in related) else "blocked"
        )

    if parity and not probe_remote:
        report.errors.append("Parity preflight requires remote endpoint probes")

    if probe_remote:
        comfy_url = cfg.comfyui_url or "http://127.0.0.1:8188"
        try:
            policy.assert_url(comfy_url, purpose="comfyui_health")
            report.endpoint_health["comfyui"] = _probe(comfy_url, "/system_stats")
            object_info = _probe_json(comfy_url, "/object_info")
            report.endpoint_health["comfyui_object_info"] = object_info is not None
            if parity and object_info is not None:
                required_nodes = set(native_workflow_nodes)
                for capability, contract in _CAPABILITY_NODE_CONTRACTS.items():
                    if cfg.capabilities.get(capability, False):
                        required_nodes.update(contract)
                for node in sorted(required_nodes):
                    report.node_contract[node] = node in object_info
                missing_nodes = [
                    node for node, ready in report.node_contract.items() if not ready
                ]
                if missing_nodes:
                    report.errors.append(
                        "ComfyUI is missing required node classes: "
                        + ", ".join(missing_nodes)
                    )
            elif parity:
                report.errors.append("ComfyUI /object_info is required for parity")
        except Exception as exc:
            report.endpoint_health["comfyui"] = False
            report.errors.append(str(exc))

        if cfg.local_vlm_url and cfg.local_vlm_required:
            try:
                policy.assert_url(cfg.local_vlm_url, purpose="local_vlm_health")
                report.endpoint_health["local_vlm"] = _probe(
                    cfg.local_vlm_url, "/models", timeout=3.0
                )
                if not report.endpoint_health["local_vlm"]:
                    report.errors.append("Required local VLM is not reachable")
            except Exception as exc:
                report.endpoint_health["local_vlm"] = False
                report.errors.append(str(exc))
        elif cfg.local_vlm_url:
            # VLM optional — probe but don't block on failure; use short timeout
            try:
                policy.assert_url(cfg.local_vlm_url, purpose="local_vlm_health")
                report.endpoint_health["local_vlm"] = _probe(
                    cfg.local_vlm_url, "/models", timeout=1.5
                )
            except Exception:
                report.endpoint_health["local_vlm"] = False

    return report


def _contains_stub_workflow(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("class_type") == "STUB_OPERATOR_MUST_EXPORT":
            return True
        meta = value.get("_meta")
        if isinstance(meta, dict) and meta.get("stub") is True:
            return True
        return any(_contains_stub_workflow(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_stub_workflow(item) for item in value)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", action="store_true", help="Probe local HTTP workers")
    parser.add_argument(
        "--parity",
        action="store_true",
        help="Require checksums, provenance, endpoints, and ComfyUI node contracts",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()
    report = run_preflight(probe_remote=args.remote or args.parity, parity=args.parity)
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
