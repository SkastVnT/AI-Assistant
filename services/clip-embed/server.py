"""
CLIP embedding sidecar — FastAPI service producing multimodal (text + image)
embeddings in a shared vector space for the RAG image subsystem.

Runs on the image dependency profile (``venv-image``) only; never import this
module from ``venv-core``. The chatbot calls it over HTTP via
``services/chatbot/core/clip_adapter.py``.
"""

from __future__ import annotations

import base64
import binascii
import io
import logging
import os
import threading

import requests
from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel

logger = logging.getLogger("clip-embed")
logging.basicConfig(level=logging.INFO)

MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "ViT-B-32")
PRETRAINED = os.getenv("CLIP_PRETRAINED", "laion2b_s34b_b79k")
DEVICE = os.getenv("CLIP_DEVICE", "cpu")
PORT = int(os.getenv("CLIP_EMBED_PORT", "8200"))

app = FastAPI(title="CLIP Embed Sidecar", version="1.0.0")

# Lazy, thread-safe singletons so import stays cheap and model loads once.
_lock = threading.Lock()
_model = None
_preprocess = None
_tokenizer = None
_dim: int | None = None


def _load_model():
    """Load the open-clip model once (idempotent, thread-safe)."""
    global _model, _preprocess, _tokenizer, _dim
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        import open_clip  # imported lazily; image-profile only
        import torch

        logger.info("[CLIP] loading %s / %s on %s", MODEL_NAME, PRETRAINED, DEVICE)
        model, _, preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME, pretrained=PRETRAINED, device=DEVICE
        )
        model.eval()
        tokenizer = open_clip.get_tokenizer(MODEL_NAME)

        with torch.no_grad():
            probe = tokenizer(["dim probe"])
            feats = model.encode_text(probe.to(DEVICE))
        _dim = int(feats.shape[-1])

        _model, _preprocess, _tokenizer = model, preprocess, tokenizer
        logger.info("[CLIP] ready, dim=%s", _dim)


def _decode_image(src: str) -> Image.Image:
    """Decode an image from base64, data URL, or http(s) URL."""
    data: bytes
    if src.startswith("http://") or src.startswith("https://"):
        resp = requests.get(src, timeout=15)
        resp.raise_for_status()
        data = resp.content
    else:
        payload = src.split(",", 1)[1] if src.startswith("data:") else src
        try:
            data = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image: {exc}")
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:  # noqa: BLE001 - surface decode error to client
        raise HTTPException(status_code=400, detail=f"Cannot decode image: {exc}")


class TextRequest(BaseModel):
    texts: list[str]


class ImageRequest(BaseModel):
    images: list[str]


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    dim: int


@app.get("/health")
def health() -> dict:
    try:
        _load_model()
        return {"status": "ok", "model": f"{MODEL_NAME}/{PRETRAINED}", "dim": _dim}
    except Exception as exc:  # noqa: BLE001
        logger.exception("[CLIP] health failed")
        return {"status": "error", "model": MODEL_NAME, "dim": None, "error": str(exc)}


@app.post("/embed/text", response_model=EmbedResponse)
def embed_text(req: TextRequest) -> EmbedResponse:
    _load_model()
    if not req.texts:
        return EmbedResponse(embeddings=[], dim=_dim or 0)
    import torch

    with torch.no_grad():
        tokens = _tokenizer(req.texts).to(DEVICE)
        feats = _model.encode_text(tokens)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return EmbedResponse(embeddings=feats.cpu().tolist(), dim=_dim or 0)


@app.post("/embed/image", response_model=EmbedResponse)
def embed_image(req: ImageRequest) -> EmbedResponse:
    _load_model()
    if not req.images:
        return EmbedResponse(embeddings=[], dim=_dim or 0)
    import torch

    tensors = [_preprocess(_decode_image(src)) for src in req.images]
    batch = torch.stack(tensors).to(DEVICE)
    with torch.no_grad():
        feats = _model.encode_image(batch)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return EmbedResponse(embeddings=feats.cpu().tolist(), dim=_dim or 0)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)  # nosec B104  # Intentional: containerized service
