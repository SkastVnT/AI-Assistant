"""
Hermes Agent adapter — HTTP proxy to the Hermes sidecar.

Proxies requests to the Hermes Gateway API (sidecar service).
Returns markdown string matching the tool-response-contract.
"""
import json
import logging
import sys
import time
from pathlib import Path

import requests

CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import (
    HERMES_API_KEY,
    HERMES_API_URL,
    HERMES_ENABLED,
    HERMES_TIMEOUT,
)

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 10_000


def hermes_chat(
    message: str,
    *,
    conversation_history: list | None = None,
    model: str | None = None,
) -> dict:
    """Send a message to the Hermes Agent sidecar and return the response.

    Parameters
    ----------
    message : str
        User message to forward.
    conversation_history : list | None
        Previous conversation turns (list of {role, content} dicts).
    model : str | None
        Model override for Hermes (optional).

    Returns
    -------
    dict
        {success: bool, result: str, error: str|None, elapsed_s: float}
    """
    _start = time.monotonic()

    # ── Gate: feature flag ────────────────────────────────────────────
    if not HERMES_ENABLED:
        logger.debug("[HERMES] Adapter disabled (HERMES_ENABLED=false)")
        return {
            "success": False,
            "result": "",
            "error": "Hermes agent chưa được bật. Set HERMES_ENABLED=true trong env.",
            "elapsed_s": 0,
        }

    # ── Input validation ──────────────────────────────────────────────
    message = (message or "").strip()
    if not message:
        return {
            "success": False,
            "result": "",
            "error": "Thiếu message cho Hermes agent.",
            "elapsed_s": 0,
        }
    if len(message) > MAX_MESSAGE_LENGTH:
        return {
            "success": False,
            "result": "",
            "error": f"Message quá dài ({len(message)} chars, tối đa {MAX_MESSAGE_LENGTH}).",
            "elapsed_s": 0,
        }

    # ── Build request ─────────────────────────────────────────────────
    url = f"{HERMES_API_URL.rstrip('/')}/chat"
    headers = {"Content-Type": "application/json"}
    if HERMES_API_KEY:
        headers["Authorization"] = f"Bearer {HERMES_API_KEY}"

    payload = {"message": message}
    if conversation_history:
        payload["conversation_history"] = conversation_history
    if model:
        payload["model"] = model

    logger.info(
        "[HERMES] Request started: url=%s msg_len=%d",
        url, len(message),
    )

    # ── Send request ──────────────────────────────────────────────────
    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=HERMES_TIMEOUT,
        )
    except requests.ConnectionError:
        elapsed = round(time.monotonic() - _start, 2)
        logger.error("[HERMES] Connection refused — sidecar not running? url=%s", url)
        return {
            "success": False,
            "result": "",
            "error": f"Không thể kết nối Hermes tại {url}. Kiểm tra sidecar đang chạy.",
            "elapsed_s": elapsed,
        }
    except requests.Timeout:
        elapsed = round(time.monotonic() - _start, 2)
        logger.warning("[HERMES] Request timed out after %.1fs (limit=%ds)", elapsed, HERMES_TIMEOUT)
        return {
            "success": False,
            "result": "",
            "error": f"Hermes timeout ({HERMES_TIMEOUT}s). Thử lại hoặc dùng model nhẹ hơn.",
            "elapsed_s": elapsed,
        }
    except Exception as e:
        elapsed = round(time.monotonic() - _start, 2)
        logger.error("[HERMES] Unexpected error: %s", e)
        return {
            "success": False,
            "result": "",
            "error": "Hermes request failed",
            "elapsed_s": elapsed,
        }

    elapsed = round(time.monotonic() - _start, 2)

    # ── Parse response ────────────────────────────────────────────────
    if resp.status_code != 200:
        body_snippet = (resp.text or "")[:500]
        logger.warning(
            "[HERMES] Non-200 response (%d) after %.1fs: %s",
            resp.status_code, elapsed, body_snippet,
        )
        return {
            "success": False,
            "result": "",
            "error": f"Hermes returned HTTP {resp.status_code}",
            "elapsed_s": elapsed,
        }

    try:
        data = resp.json()
    except (json.JSONDecodeError, ValueError):
        result_text = resp.text[:4000] if resp.text else ""
        logger.info("[HERMES] Completed (raw text): elapsed=%.1fs len=%d", elapsed, len(result_text))
        return {
            "success": True,
            "result": result_text,
            "error": None,
            "elapsed_s": elapsed,
        }

    result_text = data.get("response") or data.get("result") or data.get("message") or ""
    logger.info("[HERMES] Completed: elapsed=%.1fs result_len=%d", elapsed, len(result_text))

    return {
        "success": True,
        "result": result_text,
        "error": None,
        "elapsed_s": elapsed,
    }
