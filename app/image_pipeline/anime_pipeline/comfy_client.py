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

from image_pipeline.paths import STORAGE_DIR

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://localhost:8188"
_DEFAULT_TIMEOUT = 180
_POLL_INTERVAL = 1.5
_MAX_RETRIES = 3
_WORKFLOW_VERSION = "2.0.0"

# Substrings (case-insensitive) that mark a ComfyUI execution error as a GPU/
# resource exhaustion rather than a config/workflow mistake. Used to derive the
# 3-class error taxonomy (retryable / config_or_workflow / resource) surfaced to
# the chat UI so the user gets an actionable hint.
_RESOURCE_ERROR_PATTERNS = (
    "out of memory",
    "outofmemoryerror",
    "allocation on device",
    "not enough memory",
    "cuda error",
)


def is_resource_error(text: str) -> bool:
    """True when the error text looks like GPU/VRAM/CPU-memory exhaustion."""
    t = (text or "").lower()
    return any(p in t for p in _RESOURCE_ERROR_PATTERNS)


def classify_comfy_error(detail: str) -> str:
    """Classify a ComfyUI execution-error detail string.

    Returns ``"resource"`` for OOM/CUDA exhaustion (non-recoverable, VRAM hint),
    else ``"config_or_workflow"`` (bad node/workflow — non-recoverable, show detail).
    """
    return "resource" if is_resource_error(detail) else "config_or_workflow"


def ws_preview_enabled() -> bool:
    """Phase 3 opt-in flag: stream live denoise previews + progress % over the
    ComfyUI /ws socket. OFF by default — when off, comfy_client never opens a
    websocket and behaves exactly as before (poll /history only)."""
    return os.getenv("ANIME_PIPELINE_WS_PREVIEW", "").lower() in ("1", "true", "yes", "on")


# ComfyUI binary WS frame layout (see ComfyUI/server.py send_image / protocol.py):
#   bytes[0:4]  = big-endian uint32 event type (1 = PREVIEW_IMAGE,
#                                                4 = PREVIEW_IMAGE_WITH_METADATA)
#   for PREVIEW_IMAGE:               bytes[4:8] = image format (1 = JPEG, 2 = PNG),
#                                    bytes[8:]  = raw image bytes
#   for PREVIEW_IMAGE_WITH_METADATA: bytes[4:8] = metadata length,
#                                    bytes[8:8+len] = json, then raw image bytes
_WS_EVENT_PREVIEW_IMAGE = 1
_WS_EVENT_PREVIEW_IMAGE_WITH_METADATA = 4


def parse_ws_preview_frame(data: bytes) -> tuple[str, bytes] | None:
    """Parse a ComfyUI binary WS frame into ``(image_format, image_bytes)``.

    Returns ``("jpeg"|"png", bytes)`` for a preview image, or ``None`` for any
    frame that is not a decodable preview (unknown event, truncated, etc.).
    Pure function — safe to unit-test without a live socket.
    """
    if not data or len(data) < 8:
        return None
    event = int.from_bytes(data[0:4], "big")
    if event == _WS_EVENT_PREVIEW_IMAGE:
        fmt_num = int.from_bytes(data[4:8], "big")
        fmt = "jpeg" if fmt_num == 1 else "png" if fmt_num == 2 else None
        if fmt is None:
            return None
        return fmt, data[8:]
    if event == _WS_EVENT_PREVIEW_IMAGE_WITH_METADATA:
        meta_len = int.from_bytes(data[4:8], "big")
        img_start = 8 + meta_len
        if img_start > len(data):
            return None
        img = data[img_start:]
        # mimetype lives in the metadata JSON; default to jpeg (ComfyUI's default).
        fmt = "jpeg"
        try:
            meta = json.loads(data[8:img_start].decode("utf-8"))
            if str(meta.get("image_type", "")).endswith("png"):
                fmt = "png"
        except Exception:
            pass
        return fmt, img
    return None


def _is_job_cancel_requested(job_id: str) -> bool:
    """Best-effort check against the chatbot job queue cancel flag.

    Mirrors ``orchestrator._is_cancel_requested`` so any ComfyUI
    submission can short-circuit before issuing a new workflow,
    even if the cancel signal arrived while this client was between
    calls. Returns ``False`` when the chatbot process is not
    importable (standalone/test context).
    """
    if not job_id:
        return False
    try:
        from core.job_queue import get_queue  # type: ignore[import-not-found]

        return bool(get_queue().is_cancel_requested(job_id))
    except Exception:
        return False


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
    workflow_file: str = ""  # path to saved workflow JSON (debug mode)
    cancelled: bool = False
    # 3-class error taxonomy for UX: "retryable" (transient connect/timeout),
    # "config_or_workflow" (bad node/workflow), "resource" (GPU/VRAM OOM).
    # None on success or cancellation.
    error_class: str | None = None
    # Phase 3: True if ComfyUI served this pass from its execution cache
    # (observed via the /ws "execution_cached" message). None = unknown.
    execution_cached: bool | None = None


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
        self._debug_dir = Path(debug_dir) if debug_dir else STORAGE_DIR / "debug"
        self._cancelled: dict[str, bool] = {}
        self._lock = threading.Lock()
        # Phase 3 live-preview callbacks (opt-in). Set via set_preview_callbacks();
        # invoked from a background /ws reader thread during _submit_and_wait.
        self._on_progress = None  # callable(pct: float) -> None
        self._on_preview = None   # callable(fmt: str, image_bytes: bytes) -> None
        self._ws_cached: dict[str, bool] = {}  # prompt_id -> execution_cached seen

    def set_preview_callbacks(self, on_progress=None, on_preview=None) -> None:
        """Register (or clear, by passing None) the live-preview callbacks used
        when ANIME_PIPELINE_WS_PREVIEW is enabled. Callbacks fire from a daemon
        /ws reader thread, so their bodies must be cheap + thread-safe."""
        self._on_progress = on_progress
        self._on_preview = on_preview

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

        Upload failures stop submission immediately so ComfyUI never receives
        a graph containing the non-standard placeholder node.
        """
        needs_upload = [
            nid
            for nid, node in workflow.items()
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
                    "[ComfyClient] Uploaded image for node %s → %s",
                    nid,
                    filename,
                )
            except Exception as e:
                raise RuntimeError(
                    f"[ComfyClient] Failed to upload image for node {nid}: {e}"
                ) from e

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

        # Hard cancel gate: if the chatbot job queue already has a
        # cancel request for this job_id, refuse to submit a new
        # workflow. This prevents downstream agents (detection
        # inpaint, eye-emergency, upscale) from queuing additional
        # ComfyUI jobs after the user clicked Stop.
        if _is_job_cancel_requested(job_id):
            logger.info(
                "[ComfyClient] job=%s pass=%s cancel requested — skipping submit",
                job_id,
                pass_name,
            )
            return ComfyJobResult(
                error="Cancelled",
                cancelled=True,
            )

        # Replace LoadImageFromBase64 with LoadImage (standard ComfyUI node).
        # This handles cases where custom nodes are not installed.
        workflow = self._preprocess_workflow(workflow)

        # Remove LoraLoader nodes whose lora_name isn't in ComfyUI's live list.
        # ComfyUI only knows about files present at startup; models added later
        # are invisible until restart. Skipping them prevents hard validation
        # failures — the rest of the workflow still executes.
        available = self.get_available_loras()
        if available:
            workflow, skipped = self._filter_unavailable_loras(workflow, available)
            if skipped:
                logger.warning(
                    "[ComfyClient] job=%s pass=%s skipped %d LoRA(s) unknown to "
                    "ComfyUI (restart ComfyUI to load them): %s",
                    job_id,
                    pass_name,
                    len(skipped),
                    skipped,
                )

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
                        result,
                        job_id,
                        pass_name,
                    )

                return result
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = str(e)
                if attempt < self._max_retries:
                    wait = min(2**attempt + random.uniform(0, 1), 30)
                    logger.warning(
                        "[ComfyClient] job=%s pass=%s attempt=%d/%d failed (%s), "
                        "retrying in %.1fs",
                        job_id,
                        pass_name,
                        attempt + 1,
                        self._max_retries + 1,
                        type(e).__name__,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "[ComfyClient] job=%s pass=%s all %d attempts exhausted",
                        job_id,
                        pass_name,
                        self._max_retries + 1,
                    )
            except Exception as e:
                logger.error(
                    "[ComfyClient] job=%s pass=%s unexpected error: %s",
                    job_id,
                    pass_name,
                    e,
                )
                return ComfyJobResult(error=str(e), workflow_file=workflow_file)

        return ComfyJobResult(
            error=f"All retries failed: {last_error}",
            workflow_file=workflow_file,
            error_class="retryable",
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
                    prompt_id,
                    resp.status_code,
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

    # ── LoRA availability helpers ─────────────────────────────────────

    def get_available_loras(self) -> set[str]:
        """Return ComfyUI's current set of known LoRA filenames.

        Calls ``GET /object_info/LoraLoader`` which ComfyUI serves from its
        in-memory model cache (populated at startup). Returns an empty set on
        any failure so callers can treat it as "skip the filter".
        """
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{self._base_url}/object_info/LoraLoader")
                if resp.status_code == 200:
                    data = resp.json()
                    lora_list = (
                        data.get("LoraLoader", {})
                        .get("input", {})
                        .get("required", {})
                        .get("lora_name", [[]])[0]
                    )
                    if isinstance(lora_list, list):
                        return set(lora_list)
        except Exception as e:
            logger.warning("[ComfyClient] Could not fetch LoRA list: %s", e)
        return set()

    def _filter_unavailable_loras(
        self, workflow: dict, available: set[str]
    ) -> tuple[dict, list[str]]:
        """Remove LoraLoader nodes whose lora_name is absent from *available*.

        Rewires the model/clip chain to bypass each removed node, handling
        chains of any length including multiple consecutive unavailable LoRAs.
        Returns ``(filtered_workflow, skipped_names)``.
        """
        import copy

        # Collect nodes to remove: node_id -> (upstream_model_id, upstream_clip_id)
        to_remove: dict[str, tuple[str, str]] = {}
        for nid, node in workflow.items():
            if node.get("class_type") != "LoraLoader":
                continue
            inputs = node.get("inputs", {})
            lora_name = inputs.get("lora_name", "")
            if lora_name not in available:
                model_ref = inputs.get("model", ["0", 0])
                clip_ref = inputs.get("clip", ["0", 1])
                to_remove[nid] = (str(model_ref[0]), str(clip_ref[0]))

        if not to_remove:
            return workflow, []

        skipped = [workflow[nid]["inputs"]["lora_name"] for nid in to_remove]

        def _resolve(node_id: str, port: int, seen: frozenset[str] = frozenset()) -> list:
            """Walk through removed nodes to find the real upstream."""
            if node_id not in to_remove or node_id in seen:
                return [node_id, port]
            up_model, up_clip = to_remove[node_id]
            upstream = up_model if port == 0 else up_clip
            return _resolve(upstream, port, seen | {node_id})

        new_wf = copy.deepcopy(workflow)
        for removed_id in to_remove:
            for nid, node in new_wf.items():
                if nid == removed_id:
                    continue
                inputs = node.get("inputs", {})
                for key, val in list(inputs.items()):
                    if isinstance(val, list) and len(val) == 2 and str(val[0]) == removed_id:
                        inputs[key] = _resolve(removed_id, int(val[1]))
            del new_wf[removed_id]

        return new_wf, skipped

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
            job_id,
            pass_name,
            len(workflow),
            self._base_url,
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
                        error_msg += (
                            f": node_errors={json.dumps(node_errors, indent=2)}"
                        )
                    elif error_detail:
                        error_msg += (
                            f": {error_detail.get('message', str(error_detail))}"
                        )
                else:
                    error_msg += f": {str(error_body)[:500]}"

                logger.error(
                    "[ComfyClient] job=%s pass=%s validation error: %s",
                    job_id,
                    pass_name,
                    error_msg,
                )
                return ComfyJobResult(
                    error=error_msg,
                    validation_error=str(error_body)[:2000],
                    duration_ms=(time.time() - t0) * 1000,
                    error_class="config_or_workflow",
                )

            body = resp.json()
            prompt_id = body.get("prompt_id")
            if not prompt_id:
                return ComfyJobResult(error="ComfyUI did not return prompt_id")

            logger.info(
                "[ComfyClient] job=%s pass=%s prompt_id=%s queued",
                job_id,
                pass_name,
                prompt_id,
            )

            # ── Optional /ws live-preview reader (opt-in, best-effort) ──
            # Enriches the poll below with progress % + denoise previews via
            # callbacks; polling stays the source of truth for completion.
            _ws_stop = threading.Event()
            _ws_thread = self._maybe_start_ws_reader(client_id, prompt_id, _ws_stop)

            # ── Poll ──────────────────────────────────────────────
            try:
                result = self._poll_until_done(
                    client,
                    prompt_id,
                    job_id,
                    pass_name,
                    t0,
                )
                if _ws_thread is not None and self._ws_cached.get(prompt_id):
                    result.execution_cached = True
                return result
            finally:
                _ws_stop.set()
                if _ws_thread is not None:
                    _ws_thread.join(timeout=2)
                self._ws_cached.pop(prompt_id, None)
                self._cleanup_cancelled(prompt_id)

    def _maybe_start_ws_reader(self, client_id, prompt_id, stop_evt):
        """Start a daemon /ws reader thread if the feature flag is on, the
        websocket-client lib is importable, and at least one preview callback is
        registered. Returns the thread (or None). Never raises — any failure
        just means no live preview (polling still drives completion)."""
        if not ws_preview_enabled():
            return None
        if self._on_progress is None and self._on_preview is None:
            return None
        try:
            import websocket  # noqa: F401 — presence check
        except ImportError:
            logger.info(
                "[ComfyClient] ANIME_PIPELINE_WS_PREVIEW on but websocket-client "
                "not installed — falling back to poll-only (pip install websocket-client)."
            )
            return None
        t = threading.Thread(
            target=self._ws_read_loop,
            args=(client_id, prompt_id, stop_evt),
            daemon=True,
        )
        t.start()
        return t

    def _ws_read_loop(self, client_id, prompt_id, stop_evt) -> None:
        """Consume ComfyUI /ws messages until stop_evt is set. Best-effort:
        forwards progress % + denoise previews to the registered callbacks and
        records execution_cached. All exceptions are swallowed so a WS hiccup
        never affects the polling path that actually resolves the job."""
        import websocket

        ws_url = (
            self._base_url.replace("https://", "wss://").replace("http://", "ws://")
            + f"/ws?clientId={client_id}"
        )
        ws = None
        try:
            ws = websocket.create_connection(ws_url, timeout=5)
            while not stop_evt.is_set():
                try:
                    ws.settimeout(1.0)
                    msg = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception:
                    break
                if not msg:
                    continue
                if isinstance(msg, (bytes, bytearray)):
                    if self._on_preview is None:
                        continue
                    parsed = parse_ws_preview_frame(bytes(msg))
                    if parsed is not None:
                        try:
                            self._on_preview(parsed[0], parsed[1])
                        except Exception:
                            pass
                    continue
                # Text (JSON) status messages.
                try:
                    data = json.loads(msg)
                except Exception:
                    continue
                mtype = data.get("type")
                mdata = data.get("data", {}) or {}
                # Only react to messages for our prompt when a prompt_id is present.
                if mdata.get("prompt_id") and mdata.get("prompt_id") != prompt_id:
                    continue
                if mtype == "progress" and self._on_progress is not None:
                    value = mdata.get("value")
                    maximum = mdata.get("max") or 0
                    if value is not None and maximum:
                        try:
                            self._on_progress(max(0.0, min(100.0, 100.0 * value / maximum)))
                        except Exception:
                            pass
                elif mtype == "execution_cached":
                    nodes = mdata.get("nodes") or []
                    if nodes:
                        self._ws_cached[prompt_id] = True
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("[ComfyClient] ws reader stopped: %s", exc)
        finally:
            try:
                if ws is not None:
                    ws.close()
            except Exception:
                pass

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
            if self._is_cancelled(prompt_id) or _is_job_cancel_requested(job_id):
                duration = (time.time() - t0) * 1000
                # If only job-level cancel fired, proactively tell
                # ComfyUI to interrupt the currently running prompt.
                try:
                    with httpx.Client(timeout=3) as c2:
                        c2.post(f"{self._base_url}/interrupt")
                except Exception:
                    pass
                logger.info(
                    "[ComfyClient] job=%s pass=%s cancelled (%.0fms)",
                    job_id,
                    pass_name,
                    duration,
                )
                return ComfyJobResult(
                    prompt_id=prompt_id,
                    error="Cancelled",
                    duration_ms=duration,
                    cancelled=True,
                )

            time.sleep(_POLL_INTERVAL)

            try:
                hist_resp = client.get(f"{self._base_url}/history/{prompt_id}")
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
                    # Drill into status.messages to surface the real
                    # node-level error. ComfyUI emits entries shaped as
                    # ["execution_error", {node_id, node_type,
                    #   exception_message, exception_type, traceback,...}].
                    node_err: str | None = None
                    node_type: str | None = None
                    node_id: str | None = None
                    exc_type: str | None = None
                    traceback_lines: list[str] = []
                    for msg in status_info.get("messages", []) or []:
                        if (
                            isinstance(msg, (list, tuple))
                            and len(msg) >= 2
                            and msg[0] == "execution_error"
                            and isinstance(msg[1], dict)
                        ):
                            data = msg[1]
                            node_err = (
                                data.get("exception_message")
                                or data.get("error")
                                or node_err
                            )
                            node_type = data.get("node_type") or node_type
                            node_id = str(data.get("node_id") or "") or node_id
                            exc_type = data.get("exception_type") or exc_type
                            tb = data.get("traceback") or []
                            if isinstance(tb, list):
                                traceback_lines = [str(x) for x in tb]
                    # Also check top-level entry.error (older ComfyUI)
                    if not node_err and isinstance(entry.get("error"), str):
                        node_err = entry["error"]

                    parts: list[str] = []
                    if node_type:
                        loc = f"node {node_id} ({node_type})" if node_id else node_type
                        parts.append(loc)
                    if exc_type:
                        parts.append(exc_type)
                    if node_err:
                        parts.append(node_err)
                    detail = ": ".join(parts) if parts else status_str

                    logger.error(
                        "[ComfyClient] job=%s pass=%s ComfyUI error: %s (%.0fms)",
                        job_id,
                        pass_name,
                        detail,
                        duration,
                    )
                    if traceback_lines:
                        logger.error(
                            "[ComfyClient] job=%s pass=%s traceback:\n%s",
                            job_id,
                            pass_name,
                            "".join(traceback_lines)[-2000:],
                        )
                    return ComfyJobResult(
                        prompt_id=prompt_id,
                        error=f"ComfyUI error: {detail}",
                        duration_ms=duration,
                        error_class=classify_comfy_error(detail),
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
                job_id,
                pass_name,
                len(images_b64),
                duration,
                filenames,
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
            job_id,
            pass_name,
            self._timeout_s,
            duration,
        )
        return ComfyJobResult(
            prompt_id=prompt_id,
            error=f"Timed out after {self._timeout_s}s",
            duration_ms=duration,
        )

    # ── Internal: image download ──────────────────────────────────────

    def _download_image(self, client: httpx.Client, img_info: dict) -> Optional[str]:
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

    def _save_workflow_json(self, workflow: dict, job_id: str, pass_name: str) -> str:
        """Save workflow JSON to debug directory. Returns file path."""
        from .workflow_serializer import serialize_workflow

        job_dir = self._debug_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        filename = f"workflow_{pass_name or 'unknown'}.json"
        filepath = job_dir / filename

        serialized = serialize_workflow(
            workflow,
            pass_name=pass_name,
            job_id=job_id,
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
                    filepath,
                    e,
                )

        return paths
