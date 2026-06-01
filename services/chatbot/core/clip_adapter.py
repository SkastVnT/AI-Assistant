"""
CLIP embedding adapter — lightweight HTTP client to the CLIP embedding
sidecar (``services/clip-embed``).

The sidecar runs on the image dependency profile (``venv-image``) because it
depends on ``torch`` / ``open-clip-torch``. The chatbot (``venv-core``) must
never import those packages directly, so all CLIP work is delegated over HTTP.

Contract mirrors ``character_select_adapter`` / ``hermes_adapter`` for
consistency: a thin, dependency-light probe + request layer that fails soft.

Sidecar endpoints
~~~~~~~~~~~~~~~~~~
- ``GET  /health``        → ``{"status": "ok", "model": str, "dim": int}``
- ``POST /embed/text``    → body ``{"texts": [str, ...]}``  → ``{"embeddings": [[float], ...], "dim": int}``
- ``POST /embed/image``   → body ``{"images": [str, ...]}`` (base64 or URL)
                            → ``{"embeddings": [[float], ...], "dim": int}``

Both encoders share the same vector space, so a text query embedded via
``/embed/text`` can be cosine-matched against image vectors from
``/embed/image``.
"""

from __future__ import annotations

import logging

import requests

from core.rag_settings import get_rag_settings

logger = logging.getLogger(__name__)


class ClipUnavailableError(RuntimeError):
    """Raised when the CLIP sidecar is disabled or unreachable."""


def is_enabled() -> bool:
    """Return True when image RAG (CLIP) is enabled in settings."""
    return bool(get_rag_settings().image_enabled)


def _base_url() -> str:
    return get_rag_settings().clip_embed_url.rstrip("/")


def _timeout() -> float:
    return get_rag_settings().clip_embed_timeout


def get_status() -> dict:
    """Probe the CLIP sidecar.

    Shape::
        {
            "enabled": bool,
            "url": str,
            "reachable": bool,
            "model": str | None,
            "dim": int | None,
            "error": str | None,
        }
    """
    settings = get_rag_settings()
    payload: dict = {
        "enabled": settings.image_enabled,
        "url": settings.clip_embed_url,
        "reachable": False,
        "model": None,
        "dim": None,
        "error": None,
    }

    if not settings.image_enabled:
        payload["error"] = (
            "Image RAG disabled. Set RAG_IMAGE_ENABLED=true to enable CLIP."
        )
        return payload

    try:
        resp = requests.get(f"{_base_url()}/health", timeout=min(_timeout(), 5.0))
        resp.raise_for_status()
        data = resp.json()
        payload["reachable"] = True
        payload["model"] = data.get("model")
        payload["dim"] = data.get("dim")
    except requests.RequestException as exc:
        payload["error"] = f"CLIP sidecar unreachable: {exc}"
    except ValueError as exc:  # JSON decode
        payload["error"] = f"CLIP sidecar bad response: {exc}"

    return payload


def _post_embed(path: str, key: str, items: list[str]) -> list[list[float]]:
    """POST a batch to an embed endpoint and return the vectors.

    Raises ``ClipUnavailableError`` when disabled or the sidecar fails.
    """
    settings = get_rag_settings()
    if not settings.image_enabled:
        raise ClipUnavailableError(
            "Image RAG disabled. Set RAG_IMAGE_ENABLED=true to enable CLIP."
        )
    if not items:
        return []

    try:
        resp = requests.post(
            f"{_base_url()}{path}",
            json={key: items},
            timeout=_timeout(),
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise ClipUnavailableError(f"CLIP sidecar request failed: {exc}") from exc
    except ValueError as exc:
        raise ClipUnavailableError(f"CLIP sidecar bad response: {exc}") from exc

    embeddings = data.get("embeddings")
    if not isinstance(embeddings, list):
        raise ClipUnavailableError("CLIP sidecar returned no embeddings")

    returned_dim = data.get("dim")
    if returned_dim is not None and returned_dim != settings.clip_embed_dim:
        logger.warning(
            "[CLIP] dim mismatch: sidecar=%s settings.clip_embed_dim=%s",
            returned_dim,
            settings.clip_embed_dim,
        )
    return embeddings


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed text in CLIP space (shared with images)."""
    return _post_embed("/embed/text", "texts", texts)


def embed_query(text: str) -> list[float]:
    """Embed a single text query in CLIP space."""
    vectors = embed_texts([text])
    if not vectors:
        raise ClipUnavailableError("CLIP sidecar returned no query embedding")
    return vectors[0]


def embed_images(images: list[str]) -> list[list[float]]:
    """Embed images (base64 data URLs or HTTP URLs) in CLIP space."""
    return _post_embed("/embed/image", "images", images)
