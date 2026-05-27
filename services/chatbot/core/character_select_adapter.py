"""
Character Select SAA adapter — lightweight HTTP probe to the standalone
Electron character picker sidecar (mirabarukaso/character_select_stand_alone_app).

The SAA app is a self-hosted Electron + Express + WebSocket service. This
adapter does NOT proxy chat traffic; it only exposes status/URL information
so the chatbot UI can deep-link into the running picker. Contract mirrors
``hermes_adapter`` for consistency.
"""

from __future__ import annotations

import logging
import socket
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from core.config import (
    CHARACTER_SELECT_ENABLED,
    CHARACTER_SELECT_PATH,
    CHARACTER_SELECT_PORT,
    CHARACTER_SELECT_TIMEOUT,
    CHARACTER_SELECT_URL,
)

CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))


logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    """Return True when the Character Select sidecar is enabled."""
    return bool(CHARACTER_SELECT_ENABLED)


def _parse_host_port(url: str, default_port: int) -> tuple[str, int]:
    parsed = urlparse(url)
    return (parsed.hostname or "127.0.0.1"), (parsed.port or default_port)


def _port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def get_status() -> dict:
    """Return the current status of the SAA sidecar.

    Shape::
        {
            "enabled": bool,
            "url": str,
            "port": int,
            "reachable": bool,
            "running": bool,            # alias of reachable
            "install_path": str,
            "elapsed_s": float,
            "error": str | None,
        }
    """
    started = time.monotonic()
    payload: dict = {
        "enabled": CHARACTER_SELECT_ENABLED,
        "url": CHARACTER_SELECT_URL,
        "port": CHARACTER_SELECT_PORT,
        "install_path": str(CHARACTER_SELECT_PATH),
        "reachable": False,
        "running": False,
        "error": None,
    }

    if not CHARACTER_SELECT_ENABLED:
        payload["error"] = (
            "Character Select disabled. Set CHARACTER_SELECT_ENABLED=true to enable."
        )
        payload["elapsed_s"] = round(time.monotonic() - started, 4)
        return payload

    host, port = _parse_host_port(CHARACTER_SELECT_URL, CHARACTER_SELECT_PORT)
    if not _port_is_open(host, port, timeout=min(CHARACTER_SELECT_TIMEOUT, 2.0)):
        payload["error"] = f"Sidecar not reachable on {host}:{port}."
        payload["elapsed_s"] = round(time.monotonic() - started, 4)
        return payload

    # Port open — try a best-effort HTTP GET on root so we can also detect
    # HTTP-vs-other listeners. Failure to GET is non-fatal: the WebSocket
    # transport may still be operational.
    try:
        resp = requests.get(CHARACTER_SELECT_URL, timeout=CHARACTER_SELECT_TIMEOUT)
        payload["http_status"] = resp.status_code
        payload["reachable"] = True
        payload["running"] = True
    except requests.RequestException as exc:
        # Port open but HTTP probe failed — still mark reachable=true,
        # because the SAA WebSocket may be the only listener.
        logger.debug("[CHARACTER-SELECT] HTTP probe failed (port still open): %s", exc)
        payload["reachable"] = True
        payload["running"] = True
        payload["http_status"] = None

    payload["elapsed_s"] = round(time.monotonic() - started, 4)
    return payload


def install_path_exists() -> bool:
    """Return True when the SAA install directory exists on disk."""
    try:
        return Path(CHARACTER_SELECT_PATH).expanduser().resolve().exists()
    except OSError:
        return False
