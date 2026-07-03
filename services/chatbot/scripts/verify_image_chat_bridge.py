"""PR4 — Automated end-to-end verification of the Thinking-with-Images bridge.

Drives the REAL backend (+ ComfyUI + GPU) through /chat/stream and asserts the
bridge behaves. Covers the PR4 checklist items that do NOT need Electron eyes:

  happy    — image prompt → ap_status..ap_result..ap_done → caption chunk →
             complete{has_image:true}; exactly one image file persisted.
  cancel   — start a generation, capture job_id, hard-close mid-stream →
             JobQueue marks cancel_requested + ComfyUI queue drains
             (the GeneratorExit path fired request_cancel + _interrupt_comfyui).
  rollback — with IMAGE_PIPELINE_CHAT_BRIDGE=false the bridge must NOT engage
             (zero ap_* frames). Requires the backend restarted with the flag off.

Electron-only manual checks are printed at the end (persistence-after-reload,
modal fallback UX, DOM duplicate-save).

Usage (backend on :5000, ComfyUI on :8188 already running):
    python scripts/verify_image_chat_bridge.py --phase happy
    python scripts/verify_image_chat_bridge.py --phase cancel
    python scripts/verify_image_chat_bridge.py --phase rollback   # flag off
    python scripts/verify_image_chat_bridge.py --phase all         # happy+cancel

Exit code is non-zero if any run phase fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

_CHATBOT_DIR = Path(__file__).resolve().parents[1]
_IMAGE_STORAGE_DIR = _CHATBOT_DIR / "Storage" / "Image_Gen"

# Generous timeouts: a cold first generation loads the checkpoint (~30s) then
# runs the multi-pass pipeline (~160s on RTX 5070).
_STREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=900.0, write=30.0, pool=30.0)
_PROMPT = "vẽ một cô gái anime tóc bạc, áo trắng, ánh sáng dịu"


# ── SSE helpers ────────────────────────────────────────────────────────────
def _iter_sse(resp):
    """Yield (event_name, data_dict) tuples from an httpx streaming response."""
    event = "message"
    for raw in resp.iter_lines():
        line = raw.decode() if isinstance(raw, (bytes, bytearray)) else raw
        if line is None:
            continue
        if line == "":
            event = "message"  # blank line = end of one SSE frame
            continue
        if line.startswith(":"):
            continue  # keepalive comment
        if line.startswith("event:"):
            event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            payload = line[len("data:"):].strip()
            try:
                data = json.loads(payload)
            except (ValueError, json.JSONDecodeError):
                data = {"_raw": payload}
            yield event, data


def _post_body(force_bridge: bool = True) -> dict:
    ts = int(time.time())
    body = {
        "message": _PROMPT,
        "model": "grok",
        "conversation_id": f"pr4-verify-{ts}",
    }
    if force_bridge:
        body["force_image_bridge"] = True
    return body


# ── Readiness ──────────────────────────────────────────────────────────────
def _wait_ready(base: str, comfy: str, timeout_s: float = 300.0) -> dict:
    deadline = time.time() + timeout_s
    last = {}
    while time.time() < deadline:
        try:
            h = httpx.get(f"{base}/api/anime-pipeline/health", timeout=10.0)
            s = httpx.get(f"{comfy}/system_stats", timeout=10.0)
            if h.status_code == 200 and s.status_code == 200:
                last = h.json()
                if last.get("available"):
                    return last
        except httpx.HTTPError:
            pass
        time.sleep(3.0)
    raise TimeoutError(f"backend/ComfyUI not ready in {timeout_s}s (last health={last})")


# ── Phases ─────────────────────────────────────────────────────────────────
def phase_happy(base: str, comfy: str) -> bool:
    print("[happy] waiting for backend + ComfyUI readiness…")
    health = _wait_ready(base, comfy)
    assert health.get("chat_bridge") is True, f"chat_bridge flag off: {health}"
    print(f"[happy] ready: available={health.get('available')} chat_bridge={health.get('chat_bridge')}")

    events: list[str] = []
    job_id = None
    result_payload = None
    complete_payload = None
    saw_caption_chunk = False

    with httpx.stream(
        "POST", f"{base}/chat/stream",
        json=_post_body(), headers={"Accept": "text/event-stream"},
        timeout=_STREAM_TIMEOUT,
    ) as resp:
        assert resp.status_code == 200, f"HTTP {resp.status_code}"
        for name, data in _iter_sse(resp):
            events.append(name)
            if name == "ap_status" and job_id is None and data.get("job_id"):
                job_id = data["job_id"]
                print(f"[happy] job_id={job_id}")
            elif name == "ap_result":
                result_payload = data
            elif name == "chunk":
                saw_caption_chunk = True
            elif name == "complete":
                complete_payload = data
                break
            elif name == "error":
                raise AssertionError(f"unexpected error frame: {data}")

    # Order + presence assertions.
    assert "ap_status" in events, "no ap_status frame"
    assert events.count("ap_result") == 1, f"expected exactly 1 ap_result, got {events.count('ap_result')}"
    assert "ap_done" in events, "no ap_done frame"
    assert saw_caption_chunk, "no caption chunk streamed"
    assert complete_payload is not None, "no complete frame"
    assert complete_payload.get("has_image") is True, f"complete.has_image != true: {complete_payload}"
    i_result, i_done = events.index("ap_result"), events.index("ap_done")
    assert i_result < i_done, "ap_result must precede ap_done"
    print(f"[happy] event flow OK: {_compact(events)}")

    # Duplicate-save: exactly one file for this job.
    assert result_payload is not None, "no ap_result payload"
    if job_id:
        matches = list(_IMAGE_STORAGE_DIR.glob(f"anime_pipeline_*_{job_id[:8]}.png"))
        assert len(matches) == 1, f"expected exactly 1 saved image, found {len(matches)}: {matches}"
        assert matches[0].stat().st_size > 10_000, f"saved image too small: {matches[0].stat().st_size}B"
        print(f"[happy] persisted exactly one image: {matches[0].name} ({matches[0].stat().st_size} B)")

        # Cross-check job queue state.
        j = httpx.get(f"{base}/api/jobs/{job_id}", timeout=10.0)
        if j.status_code == 200:
            state = j.json().get("job", {}).get("state")
            print(f"[happy] job state = {state}")
            assert state == "completed", f"expected completed, got {state}"

    print("[happy] PASS")
    return True


def phase_cancel(base: str, comfy: str) -> bool:
    print("[cancel] waiting for readiness…")
    _wait_ready(base, comfy)

    job_id = None
    generating = False
    # Open the stream, break out as soon as generation is actually on the GPU.
    with httpx.stream(
        "POST", f"{base}/chat/stream",
        json=_post_body(), headers={"Accept": "text/event-stream"},
        timeout=_STREAM_TIMEOUT,
    ) as resp:
        assert resp.status_code == 200, f"HTTP {resp.status_code}"
        for name, data in _iter_sse(resp):
            if name == "ap_status" and job_id is None and data.get("job_id"):
                job_id = data["job_id"]
                print(f"[cancel] job_id={job_id}")
            if name in ("ap_stage_start", "ap_stage_heartbeat", "ap_preview"):
                generating = True
                print(f"[cancel] generation started ({name}) — hard-closing connection")
                break  # context exit closes the socket → server GeneratorExit
            if name in ("ap_result", "ap_done", "complete"):
                raise AssertionError("generation finished before we could cancel — rerun")

    assert job_id, "never captured a job_id"
    assert generating, "generation never started"

    # request_cancel sets cancel_requested=True on the job.
    ok_cancel = _poll(
        lambda: _job_field(base, job_id, "cancel_requested") is True,
        timeout_s=60.0, label="job.cancel_requested",
    )
    assert ok_cancel, "job.cancel_requested never became True"
    print("[cancel] job.cancel_requested = True")

    # _interrupt_comfyui clears the queue then interrupts the sampler.
    ok_queue = _poll(
        lambda: _comfy_queue_empty(comfy),
        timeout_s=180.0, label="ComfyUI queue drained",
    )
    assert ok_queue, "ComfyUI queue never drained"
    print("[cancel] ComfyUI queue drained")
    print("[cancel] PASS")
    return True


def phase_rollback(base: str, comfy: str) -> bool:
    print("[rollback] verifying bridge is OFF (backend must be restarted with "
          "IMAGE_PIPELINE_CHAT_BRIDGE=false)…")
    try:
        h = httpx.get(f"{base}/api/anime-pipeline/health", timeout=10.0).json()
        assert h.get("chat_bridge") is False, (
            f"chat_bridge is still ON ({h.get('chat_bridge')}) — restart backend "
            "with IMAGE_PIPELINE_CHAT_BRIDGE=false before running this phase"
        )
    except httpx.HTTPError as exc:
        raise AssertionError(f"health probe failed: {exc}")

    ap_frames = []
    with httpx.stream(
        "POST", f"{base}/chat/stream",
        json=_post_body(), headers={"Accept": "text/event-stream"},
        timeout=_STREAM_TIMEOUT,
    ) as resp:
        assert resp.status_code == 200, f"HTTP {resp.status_code}"
        for name, _data in _iter_sse(resp):
            if name.startswith("ap_"):
                ap_frames.append(name)
            if name in ("complete", "error"):
                break

    assert not ap_frames, f"bridge engaged despite flag off: {ap_frames}"
    print("[rollback] no ap_* frames — bridge correctly bypassed. PASS")
    return True


# ── small utilities ────────────────────────────────────────────────────────
def _compact(events: list[str]) -> str:
    out, prev = [], None
    for e in events:
        if e != prev:
            out.append(e)
            prev = e
    return " → ".join(out)


def _poll(pred, timeout_s: float, label: str) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if pred():
                return True
        except httpx.HTTPError:
            pass
        time.sleep(2.0)
    print(f"[poll] timed out waiting for: {label}")
    return False


def _job_field(base: str, job_id: str, field: str):
    r = httpx.get(f"{base}/api/jobs/{job_id}", timeout=10.0)
    if r.status_code != 200:
        return None
    return r.json().get("job", {}).get(field)


def _comfy_queue_empty(comfy: str) -> bool:
    r = httpx.get(f"{comfy}/queue", timeout=10.0)
    if r.status_code != 200:
        return False
    q = r.json()
    return not q.get("queue_running") and not q.get("queue_pending")


_MANUAL = """
─────────────────────────────────────────────────────────────────
Remaining MANUAL checks (need the Electron UI — cannot be scripted):
  ★ Persistence: generate an image → reload the app → image + caption
    still render in the conversation.
  • Modal fallback: with IMAGE_PIPELINE_CHAT_BRIDGE=false, an image prompt
    opens the legacy modal (visual).
  • DOM duplicate-save: addGeneratedImage fires once per turn (the
    backend side — one ap_result, one file — is covered by [happy]).
  • No caption after Stop: verify the UI shows the cancel message, no
    LLM caption (unobservable server-side once the socket closes).
─────────────────────────────────────────────────────────────────
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="PR4 bridge verification")
    ap.add_argument("--phase", choices=["happy", "cancel", "rollback", "all"], default="all")
    ap.add_argument("--base", default="http://127.0.0.1:5000")
    ap.add_argument("--comfy", default="http://127.0.0.1:8188")
    args = ap.parse_args()

    phases = {
        "happy": phase_happy,
        "cancel": phase_cancel,
        "rollback": phase_rollback,
    }
    to_run = ["happy", "cancel"] if args.phase == "all" else [args.phase]

    results: dict[str, str] = {}
    for name in to_run:
        try:
            phases[name](args.base, args.comfy)
            results[name] = "PASS"
        except Exception as exc:  # noqa: BLE001 — report, don't crash the runner
            results[name] = f"FAIL: {exc}"
            print(f"[{name}] FAIL: {exc}")

    print("\n" + "=" * 50)
    print("PR4 verification summary")
    print("=" * 50)
    for name, verdict in results.items():
        print(f"  {name:10s} {verdict}")
    print(_MANUAL)

    return 0 if all(v == "PASS" for v in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
