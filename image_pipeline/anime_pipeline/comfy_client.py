"""
image_pipeline.anime_pipeline.comfy_client — Robust ComfyUI HTTP client.

Features:
  - Read base URL from config or env
  - Workflow submission via POST /prompt
  - Job status polling via GET /history/{prompt_id}
  - Image download via GET /view
  - Retry with exponential backoff + jitter for transient failures
  - Validation error surfacing when ComfyUI rejects a workflow
  - Workflow JSON debug saving per pass
  - Request/response logging (job_id, pass_name, duration, output paths)
  - Timeout handling and cancellation support
  - Debug mode: stores intermediate layer images with named filenames
"""

from __future__ import annotations

import base64
import json
import logging
import os
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://localhost:8188"
_DEFAULT_TIMEOUT = 180
_POLL_INTERVAL = 1.5
_MAX_RETRIES = 3
_WORKFLOW_VERSION = "2.0.0"

# Debug-mode filenames per pass name
_DEBUG_FILENAMES: dict[str, str] = {
    "composition": "base.png",
    "structure_lock_lineart": "lineart.png",
    "structure_lock_lineart_anime": "lineart.png",
    "structure_lock_depth": "depth.png",
    "structure_lock_canny": "canny.png",
    "cleanup": "cleanup.png",
    "beauty": "beauty_pass.png",
    "detail_face": "detail_face.png",
    "detail_eyes": "detail_eyes.png",
    "detail_hand": "detail_hand.png",
    "upscale": "final_upscaled.png",
}


@dataclass
class ComfyJobResult:
    """Result of a submitted ComfyUI workflow."""
    prompt_id: str = ""
    success: bool = False
    images_b64: list[str] = field(default_factory=list)
    output_filenames: list[str] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    error: str = ""
    validation_error: str = ""
    raw_outputs: dict[str, Any] = field(default_factory=dict)
    workflow_version: str = _WORKFLOW_VERSION
    workflow_file: str = ""              # path to saved workflow JSON (debug mode)
    cancelled: bool = False


class ComfyClient:
    """HTTP client for ComfyUI prompt API with logging, retry, debug, and cancellation.

    Usage:
        client = ComfyClient()                           # reads URL from env
        client = ComfyClient(base_url="http://gpu:8188") # explicit URL

        result = client.submit_workflow(workflow, job_id="abc", pass_name="composition")
        if result.success:
            print(f"Got {len(result.images_b64)} images in {result.duration_ms:.0f}ms")

        # Cancel a running job
        client.cancel(result.prompt_id)
    """

    def __init__(
        self,
        base_url: str = "",
        timeout_s: int = _DEFAULT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
        debug_dir: str = "",
        debug_mode: bool = False,
    ):
        self._base_url = (
            base_url
            or os.getenv("ANIME_PIPELINE_COMFYUI_URL")
            or os.getenv("COMFYUI_URL")
            or _DEFAULT_URL
        ).rstrip("/")
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._debug_mode = debug_mode or os.getenv(
            "ANIME_PIPELINE_DEBUG", ""
        ).lower() in ("true", "1")
        self._debug_dir = Path(debug_dir) if debug_dir else Path("storage/debug")
        self._cancelled: dict[str, bool] = {}
        self._lock = threading.Lock()

    # ── Public properties ─────────────────────────────────────────────

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def workflow_version(self) -> str:
        return _WORKFLOW_VERSION

    @property
    def debug_mode(self) -> bool:
        return self._debug_mode

    # ── Primary API ───────────────────────────────────────────────────

    def upload_image_b64(self, image_b64: str) -> str:
        """Upload a base64-encoded image to ComfyUI /upload/image.

        Returns the ComfyUI filename to use in LoadImage nodes.
        Strips a data-URI prefix (``data:image/...;base64,``) if present.

        Raises:
            httpx.HTTPStatusError: If ComfyUI rejects the upload.
        """
        raw_b64 = image_b64.split(",", 1)[-1] if "," in image_b64 else image_b64
        image_bytes = base64.b64decode(raw_b64)
        filename = f"pipeline_{uuid.uuid4().hex[:8]}.png"
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{self._base_url}/upload/image",
                files={"image": (filename, image_bytes, "image/png")},
                data={"type": "input", "overwrite": "true"},
            )
            resp.raise_for_status()
            return resp.json().get("name", filename)

    def _preprocess_workflow(self, workflow: dict) -> dict:
        """Replace ``LoadImageFromBase64`` nodes with standard ``LoadImage`` nodes.

        For each node using ``LoadImageFromBase64``:
          1. Uploads the base64 payload to ComfyUI /upload/image.
          2. Replaces the node with a ``LoadImage`` node referencing the
             uploaded filename.

        Nodes that fail to upload are left unchanged so ComfyUI surfaces
        the error rather than silently skipping the pass.
        """
        needs_upload = [
            nid for nid, node in workflow.items()
            if node.get("class_type") == "LoadImageFromBase64"
        ]
        if not needs_upload:
            return workflow

        new_workflow = dict(workflow)
        for nid in needs_upload:
            b64 = workflow[nid].get("inputs", {}).get("base64_image", "")
            if not b64:
                continue
            try:
                filename = self.upload_image_b64(b64)
                new_workflow[nid] = {
                    "class_type": "LoadImage",
                    "inputs": {"image": filename},
                }
                logger.debug(
                    "[ComfyClient] Uploaded image for node %s → %s", nid, filename,
                )
            except Exception as e:
                logger.warning(
                    "[ComfyClient] Failed to upload image for node %s: %s — "
                    "leaving node unchanged",
                    nid, e,
                )

        if len(needs_upload) > 0:
            logger.info(
                "[ComfyClient] Preprocessed %d LoadImageFromBase64 → LoadImage",
                len(needs_upload),
            )
        return new_workflow

    def submit_workflow(
        self,
        workflow: dict,
        job_id: str = "",
        pass_name: str = "",
    ) -> ComfyJobResult:
        """Submit workflow with retry, logging, and optional debug save.

        Args:
            workflow: ComfyUI workflow JSON (node_id → node_def).
            job_id:   Pipeline job identifier for log correlation.
            pass_name: Current pass name (composition, beauty, etc.).

        Returns:
            ComfyJobResult with images or error details.
        """
        job_id = job_id or uuid.uuid4().hex[:12]

        # Replace LoadImageFromBase64 with LoadImage (standard ComfyUI node).
        # This handles cases where custom nodes are not installed.
        workflow = self._preprocess_workflow(workflow)

        # Save workflow JSON for debugging before any attempt
        workflow_file = ""
        if self._debug_mode:
            workflow_file = self._save_workflow_json(workflow, job_id, pass_name)

        last_error = ""
        for attempt in range(self._max_retries + 1):
            try:
                result = self._submit_and_wait(workflow, job_id, pass_name)
                result.workflow_file = workflow_file

                # Debug: save output images with named filenames
                if self._debug_mode and result.success:
                    result.output_paths = self._save_debug_images(
                        result, job_id, pass_name,
                    )

                return result
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = str(e)
                if attempt < self._max_retries:
                    wait = min(2 ** attempt + random.uniform(0, 1), 30)
                    logger.warning(
                        "[ComfyClient] job=%s pass=%s attempt=%d/%d failed (%s), "
                        "retrying in %.1fs",
                        job_id, pass_name, attempt + 1, self._max_retries + 1,
                        type(e).__name__, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "[ComfyClient] job=%s pass=%s all %d attempts exhausted",
                        job_id, pass_name, self._max_retries + 1,
                    )
            except Exception as e:
                logger.error(
                    "[ComfyClient] job=%s pass=%s unexpected error: %s",
                    job_id, pass_name, e,
                )
                return ComfyJobResult(error=str(e), workflow_file=workflow_file)

        return ComfyJobResult(
            error=f"All retries failed: {last_error}",
            workflow_file=workflow_file,
        )

    def cancel(self, prompt_id: str) -> bool:
        """Request cancellation of a running job.

        Sets an internal flag so the polling loop exits, and sends
        POST /interrupt to ComfyUI to stop the current execution.
        """
        if not prompt_id:
            return False
        with self._lock:
            self._cancelled[prompt_id] = True

        try:
            with httpx.Client(timeout=5) as client:
                resp = client.post(f"{self._base_url}/interrupt")
                logger.info(
                    "[ComfyClient] Cancel requested for prompt_id=%s (status=%d)",
                    prompt_id, resp.status_code,
                )
                return resp.status_code == 200
        except Exception as e:
            logger.warning("[ComfyClient] Cancel request failed: %s", e)
            return False

    def check_health(self) -> bool:
        """Quick health check — GET /system_stats."""
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self._base_url}/system_stats")
                return resp.status_code == 200
        except Exception:
            return False

    def get_queue_status(self) -> dict[str, Any]:
        """Get current ComfyUI queue status (running + pending counts)."""
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self._base_url}/queue")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning("[ComfyClient] Queue status failed: %s", e)
        return {}

    # ── Internal: submit + poll ───────────────────────────────────────

    def _is_cancelled(self, prompt_id: str) -> bool:
        with self._lock:
            return self._cancelled.get(prompt_id, False)

    def _cleanup_cancelled(self, prompt_id: str) -> None:
        with self._lock:
            self._cancelled.pop(prompt_id, None)

    def _submit_and_wait(
        self,
        workflow: dict,
        job_id: str,
        pass_name: str,
    ) -> ComfyJobResult:
        """Submit prompt, poll until done, download output images."""
        client_id = uuid.uuid4().hex[:8]
        payload = {"prompt": workflow, "client_id": client_id}
        t0 = time.time()

        logger.info(
            "[ComfyClient] job=%s pass=%s submitting workflow (%d nodes) to %s",
            job_id, pass_name, len(workflow), self._base_url,
        )

        with httpx.Client(timeout=self._timeout_s) as client:
            # ── Submit ────────────────────────────────────────────
            resp = client.post(f"{self._base_url}/prompt", json=payload)

            # Surface validation errors clearly
            if resp.status_code != 200:
                error_body: Any = ""
                try:
                    error_body = resp.json()
                except Exception:
                    error_body = resp.text

                error_msg = f"ComfyUI rejected workflow (HTTP {resp.status_code})"
                if isinstance(error_body, dict):
                    node_errors = error_body.get("node_errors", {})
                    error_detail = error_body.get("error", {})
                    if node_errors:
                        error_msg += f": node_errors={json.dumps(node_errors, indent=2)}"
                    elif error_detail:
                        error_msg += f": {error_detail.get('message', str(error_detail))}"
                else:
                    error_msg += f": {str(error_body)[:500]}"

                logger.error(
                    "[ComfyClient] job=%s pass=%s validation error: %s",
                    job_id, pass_name, error_msg,
                )
                return ComfyJobResult(
                    error=error_msg,
                    validation_error=str(error_body)[:2000],
                    duration_ms=(time.time() - t0) * 1000,
                )

            body = resp.json()
            prompt_id = body.get("prompt_id")
            if not prompt_id:
                return ComfyJobResult(error="ComfyUI did not return prompt_id")

            logger.info(
                "[ComfyClient] job=%s pass=%s prompt_id=%s queued",
                job_id, pass_name, prompt_id,
            )

            # ── Poll ──────────────────────────────────────────────
            try:
                return self._poll_until_done(
                    client, prompt_id, job_id, pass_name, t0,
                )
            finally:
                self._cleanup_cancelled(prompt_id)

    def _poll_until_done(
        self,
        client: httpx.Client,
        prompt_id: str,
        job_id: str,
        pass_name: str,
        t0: float,
    ) -> ComfyJobResult:
        """Poll /history/{prompt_id} until completed, errored, or timed out."""
        deadline = time.time() + self._timeout_s

        while time.time() < deadline:
            # Check cancellation
            if self._is_cancelled(prompt_id):
                duration = (time.time() - t0) * 1000
                logger.info(
                    "[ComfyClient] job=%s pass=%s cancelled (%.0fms)",
                    job_id, pass_name, duration,
                )
                return ComfyJobResult(
                    prompt_id=prompt_id,
                    error="Cancelled",
                    duration_ms=duration,
                    cancelled=True,
                )

            time.sleep(_POLL_INTERVAL)

            try:
                hist_resp = client.get(
                    f"{self._base_url}/history/{prompt_id}"
                )
            except httpx.TimeoutException:
                continue

            if hist_resp.status_code != 200:
                continue
            history = hist_resp.json()
            if prompt_id not in history:
                continue

            entry = history[prompt_id]
            status_info = entry.get("status", {})

            # Check for ComfyUI-level error
            if not status_info.get("completed", False):
                status_str = status_info.get("status_str", "")
                if "error" in status_str.lower():
                    duration = (time.time() - t0) * 1000
                    logger.error(
                        "[ComfyClient] job=%s pass=%s ComfyUI error: %s (%.0fms)",
                        job_id, pass_name, status_str, duration,
                    )
                    return ComfyJobResult(
                        prompt_id=prompt_id,
                        error=f"ComfyUI error: {status_str}",
                        duration_ms=duration,
                    )
                continue

            # ── Completed — collect output images ─────────────────
            duration = (time.time() - t0) * 1000
            outputs = entry.get("outputs", {})
            images_b64: list[str] = []
            filenames: list[str] = []

            for _node_id, node_output in outputs.items():
                for img_info in node_output.get("images", []):
                    img_b64 = self._download_image(client, img_info)
                    if img_b64:
                        images_b64.append(img_b64)
                        filenames.append(img_info.get("filename", ""))

            logger.info(
                "[ComfyClient] job=%s pass=%s completed: %d images, %.0fms, files=%s",
                job_id, pass_name, len(images_b64), duration, filenames,
            )

            return ComfyJobResult(
                prompt_id=prompt_id,
                success=True,
                images_b64=images_b64,
                output_filenames=filenames,
                duration_ms=duration,
                raw_outputs=outputs,
            )

        # Timeout
        duration = (time.time() - t0) * 1000
        logger.error(
            "[ComfyClient] job=%s pass=%s timed out after %ds (%.0fms)",
            job_id, pass_name, self._timeout_s, duration,
        )
        return ComfyJobResult(
            prompt_id=prompt_id,
            error=f"Timed out after {self._timeout_s}s",
            duration_ms=duration,
        )

    # ── Internal: image download ──────────────────────────────────────

    def _download_image(
        self, client: httpx.Client, img_info: dict
    ) -> Optional[str]:
        """Download a single image from ComfyUI /view endpoint."""
        try:
            resp = client.get(
                f"{self._base_url}/view",
                params={
                    "filename": img_info.get("filename", ""),
                    "subfolder": img_info.get("subfolder", ""),
                    "type": img_info.get("type", "output"),
                },
            )
            if resp.status_code == 200:
                return base64.b64encode(resp.content).decode("utf-8")
        except Exception as e:
            logger.warning("[ComfyClient] Failed to download image: %s", e)
        return None

    # ── Internal: debug persistence ───────────────────────────────────

    def _save_workflow_json(
        self, workflow: dict, job_id: str, pass_name: str
    ) -> str:
        """Save workflow JSON to debug directory. Returns file path."""
        from .workflow_serializer import serialize_workflow

        job_dir = self._debug_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        filename = f"workflow_{pass_name or 'unknown'}.json"
        filepath = job_dir / filename

        serialized = serialize_workflow(
            workflow, pass_name=pass_name, job_id=job_id,
        )
        try:
            filepath.write_text(
                json.dumps(serialized, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("[ComfyClient] Saved workflow JSON: %s", filepath)
        except Exception as e:
            logger.warning("[ComfyClient] Failed to save workflow: %s", e)
        return str(filepath)

    def _save_debug_images(
        self, result: ComfyJobResult, job_id: str, pass_name: str
    ) -> list[str]:
        """Save output images with debug filenames. Returns file paths."""
        job_dir = self._debug_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []
        debug_name = _DEBUG_FILENAMES.get(pass_name, f"{pass_name}.png")

        for i, img_b64 in enumerate(result.images_b64):
            if len(result.images_b64) > 1:
                stem = Path(debug_name).stem
                suffix = Path(debug_name).suffix
                fname = f"{stem}_{i}{suffix}"
            else:
                fname = debug_name

            filepath = job_dir / fname
            try:
                raw = img_b64.split(",", 1)[-1] if "," in img_b64 else img_b64
                filepath.write_bytes(base64.b64decode(raw))
                paths.append(str(filepath))
                logger.debug("[ComfyClient] Debug image saved: %s", filepath)
            except Exception as e:
                logger.warning(
                    "[ComfyClient] Failed to save debug image %s: %s",
                    filepath, e,
                )

        return paths
