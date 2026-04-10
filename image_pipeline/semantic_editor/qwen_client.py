"""
image_pipeline.semantic_editor.qwen_client — Qwen-Image-Edit-2511 via vLLM.

Primary semantic editor (§5.1).  Deployed on VPS behind a vLLM instance
that exposes an OpenAI-compatible chat-completion endpoint with vision.

Capabilities:
  - Instruction-based image editing ("add sunglasses", "change background to beach")
  - Multi-image context (up to 4 reference images)
  - Multi-turn editing via conversation history
  - Bilingual (EN + VI / ZH)

Connection:
  POST {vps_base_url}/v1/chat/completions
  Model: "qwen-image-edit" (mapped by vLLM serve command)

Image protocol:
  Images are sent as base64 data URIs in the `image_url` field of a
  `content` list inside the user message, following the OpenAI vision format.

Returns:
  The model responds with an edited image inlined as a base64 data URI
  inside the assistant message content.  We extract and return it.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────

_DEFAULT_VPS_URL = "http://localhost:8000"
_DEFAULT_MODEL = "qwen-image-edit"
_TIMEOUT_SECONDS = 180          # vLLM can be slow on first request
_MAX_RETRIES = 2
_RETRY_BACKOFF = 2.0            # seconds


# ── Data types ───────────────────────────────────────────────────────

@dataclass
class EditResponse:
    """Result from a single Qwen edit call."""
    success:      bool
    image_b64:    Optional[str] = None     # Raw base64 (no data-uri prefix)
    latency_ms:   float         = 0.0
    model:        str           = _DEFAULT_MODEL
    provider:     str           = "vps"
    error:        Optional[str] = None
    raw_text:     str           = ""       # Full assistant reply (may contain text + image)
    usage:        dict          = field(default_factory=dict)  # token counts


@dataclass
class ConversationTurn:
    """One turn of multi-turn editing context."""
    role:       str                     # "user" | "assistant"
    text:       str           = ""
    image_b64:  Optional[str] = None    # Image sent or received in this turn


# ── Client ───────────────────────────────────────────────────────────

class QwenClient:
    """
    Async client for Qwen-Image-Edit-2511 running on vLLM.

    Usage:
        client = QwenClient(base_url="http://vps-ip:8000")
        resp = await client.edit(
            instruction="Add a straw hat",
            source_image_b64="...",
        )
        if resp.success:
            edited_b64 = resp.image_b64
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_VPS_URL,
        api_key: str = "EMPTY",
        model: str = _DEFAULT_MODEL,
        timeout: float = _TIMEOUT_SECONDS,
        max_retries: int = _MAX_RETRIES,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    # ── Session management ────────────────────────────────────────

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # ── Core edit call ────────────────────────────────────────────

    async def edit(
        self,
        instruction: str,
        source_image_b64: Optional[str] = None,
        reference_images_b64: Optional[list[str]] = None,
        history: Optional[list[ConversationTurn]] = None,
        generation_params: Optional[dict] = None,
    ) -> EditResponse:
        """
        Send an edit instruction to Qwen-Image-Edit.

        Args:
            instruction:          Natural-language edit command
            source_image_b64:     Source image to edit (raw base64, no prefix)
            reference_images_b64: Additional reference images for context
            history:              Previous turns for multi-turn editing
            generation_params:    Extra vLLM params (temperature, max_tokens, etc.)

        Returns:
            EditResponse with the edited image (or error).
        """
        messages = self._build_messages(
            instruction=instruction,
            source_image_b64=source_image_b64,
            reference_images_b64=reference_images_b64 or [],
            history=history or [],
        )

        params = {
            "model": self._model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        if generation_params:
            params.update(generation_params)

        return await self._call_with_retry(params)

    # ── Generate (text-to-image mode) ─────────────────────────────

    async def generate(
        self,
        prompt: str,
        generation_params: Optional[dict] = None,
    ) -> EditResponse:
        """
        Text-to-image generation using Qwen (no source image).
        Qwen-Image-Edit can generate from text, though diffusion models
        are generally better for pure t2i.
        """
        return await self.edit(
            instruction=prompt,
            source_image_b64=None,
            generation_params=generation_params,
        )

    # ── Multi-turn edit ───────────────────────────────────────────

    async def multi_turn_edit(
        self,
        turns: list[ConversationTurn],
        new_instruction: str,
        current_image_b64: Optional[str] = None,
    ) -> EditResponse:
        """
        Continue a multi-turn editing session.

        The full conversation history is sent for context continuity.
        The latest image is sent as the source for the new edit.
        """
        return await self.edit(
            instruction=new_instruction,
            source_image_b64=current_image_b64,
            history=turns,
        )

    # ── Health check ──────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Check if the vLLM server is reachable."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._base_url}/v1/models",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ── Internal: message building ────────────────────────────────

    def _build_messages(
        self,
        instruction: str,
        source_image_b64: str | None,
        reference_images_b64: list[str],
        history: list[ConversationTurn],
    ) -> list[dict]:
        """
        Build OpenAI-compatible messages with vision content.

        Message format (vLLM + Qwen):
        [
          {"role": "system", "content": "..."},
          {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
            {"type": "text", "text": "Add sunglasses"}
          ]},
          {"role": "assistant", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
          ]},
          ...
        ]
        """
        messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are an expert image editor. Follow the user's instructions "
                    "precisely. Preserve all elements not explicitly asked to change. "
                    "Output the edited image."
                ),
            }
        ]

        # ── Replay multi-turn history ────────────────────────────
        for turn in history:
            content: list[dict] = []
            if turn.image_b64:
                content.append(self._image_content(turn.image_b64))
            if turn.text:
                content.append({"type": "text", "text": turn.text})
            if content:
                messages.append({"role": turn.role, "content": content})

        # ── Current turn: source + references + instruction ──────
        user_content: list[dict] = []

        # Source image first (the image being edited)
        if source_image_b64:
            user_content.append(self._image_content(source_image_b64))

        # Reference images (face, outfit, style, etc.)
        for ref_b64 in reference_images_b64[:4]:   # Qwen supports up to ~4
            user_content.append(self._image_content(ref_b64))

        # Text instruction last
        user_content.append({"type": "text", "text": instruction})

        messages.append({"role": "user", "content": user_content})

        return messages

    @staticmethod
    def _image_content(b64: str) -> dict:
        """Wrap base64 image into OpenAI vision content block."""
        # Ensure no double-prefix
        if b64.startswith("data:"):
            data_uri = b64
        else:
            data_uri = f"data:image/png;base64,{b64}"
        return {
            "type": "image_url",
            "image_url": {"url": data_uri},
        }

    # ── Internal: API call with retry ─────────────────────────────

    async def _call_with_retry(self, params: dict) -> EditResponse:
        """POST to vLLM with exponential backoff retry."""
        last_error = ""
        url = f"{self._base_url}/v1/chat/completions"

        for attempt in range(self._max_retries + 1):
            t0 = time.time()
            try:
                session = await self._get_session()
                async with session.post(url, json=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        latency = (time.time() - t0) * 1000
                        return self._parse_response(data, latency)

                    body = await resp.text()
                    last_error = f"HTTP {resp.status}: {body[:300]}"
                    logger.warning(
                        "[QwenClient] attempt %d/%d failed: %s",
                        attempt + 1, self._max_retries + 1, last_error,
                    )

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self._timeout}s"
                logger.warning(
                    "[QwenClient] attempt %d/%d timeout",
                    attempt + 1, self._max_retries + 1,
                )
            except aiohttp.ClientError as e:
                last_error = f"Connection error: {e}"
                logger.warning(
                    "[QwenClient] attempt %d/%d connection error: %s",
                    attempt + 1, self._max_retries + 1, e,
                )

            # Backoff before retry (skip on last attempt)
            if attempt < self._max_retries:
                await asyncio.sleep(_RETRY_BACKOFF * (2 ** attempt))

        return EditResponse(
            success=False,
            error=f"All {self._max_retries + 1} attempts failed. Last: {last_error}",
            model=self._model,
            provider="vps",
        )

    # ── Internal: parse vLLM response ─────────────────────────────

    def _parse_response(self, data: dict, latency_ms: float) -> EditResponse:
        """
        Extract the edited image from vLLM / Qwen response.

        Qwen-Image-Edit returns the image as a base64 data URI inline
        in the assistant's content.  The content may be a string or
        a list of content blocks (text + image_url).
        """
        try:
            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content", "")
            usage = data.get("usage", {})

            image_b64 = None
            raw_text = ""

            # Case 1: content is a list of blocks (structured)
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        btype = block.get("type", "")
                        if btype == "image_url":
                            url = block.get("image_url", {}).get("url", "")
                            image_b64 = self._extract_b64_from_uri(url)
                        elif btype == "text":
                            raw_text += block.get("text", "")
                    elif isinstance(block, str):
                        raw_text += block

            # Case 2: content is a plain string (may contain embedded base64)
            elif isinstance(content, str):
                raw_text = content
                image_b64 = self._extract_b64_from_text(content)

            if image_b64:
                return EditResponse(
                    success=True,
                    image_b64=image_b64,
                    latency_ms=latency_ms,
                    model=self._model,
                    provider="vps",
                    raw_text=raw_text,
                    usage=usage,
                )
            else:
                return EditResponse(
                    success=False,
                    error="No image found in Qwen response",
                    latency_ms=latency_ms,
                    model=self._model,
                    provider="vps",
                    raw_text=raw_text,
                    usage=usage,
                )

        except (KeyError, IndexError) as e:
            return EditResponse(
                success=False,
                error=f"Unexpected response format: {e}",
                model=self._model,
                provider="vps",
            )

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _extract_b64_from_uri(data_uri: str) -> Optional[str]:
        """Strip data URI prefix to get raw base64."""
        if not data_uri:
            return None
        # data:image/png;base64,iVBOR...
        if ";base64," in data_uri:
            return data_uri.split(";base64,", 1)[1]
        return data_uri if len(data_uri) > 100 else None

    @staticmethod
    def _extract_b64_from_text(text: str) -> Optional[str]:
        """
        Try to find embedded base64 image in plain text response.
        Some vLLM/Qwen configurations return images as inline base64.
        """
        # Look for data URI pattern
        if "data:image/" in text and ";base64," in text:
            # Find the base64 segment
            idx = text.index(";base64,") + len(";base64,")
            # Base64 can contain A-Z, a-z, 0-9, +, /, =
            b64_chars = []
            for ch in text[idx:]:
                if ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r":
                    b64_chars.append(ch)
                else:
                    break
            candidate = "".join(b64_chars).replace("\n", "").replace("\r", "")
            if len(candidate) > 100:
                return candidate

        return None
