"""
image_pipeline.multi_reference.reference_manager — Download, cache, crop, tag.

Responsibilities (§3.3, §12 Stage 2):
    1. Resolve reference images: URL → download → base64
    2. Cache to storage/references/ for reuse
    3. Crop to region (face, upper_body, full) when needed
    4. Build the indexed image map for FLUX.2 prompt engineering
       ("image 1" = face ref, "image 2" = outfit ref, ...)

Does NOT call any generation API.  Pure data-prep utility.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

from image_pipeline.job_schema import ReferenceImage, ReferenceRole

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────

_CACHE_DIR = Path("storage/references")
_DOWNLOAD_TIMEOUT = 30.0
_MAX_IMAGE_SIZE = 20 * 1024 * 1024   # 20 MB — BFL limit


# ── Data types ───────────────────────────────────────────────────────

@dataclass
class ResolvedRef:
    """A reference image ready for FLUX.2: has base64 data + metadata."""
    index:      int                       # 1-based index for FLUX.2 prompt
    role:       ReferenceRole
    label:      str           = ""        # "face from ref_0"
    image_b64:  str           = ""        # Raw base64 (no data URI prefix)
    weight:     float         = 1.0
    cached_path: Optional[str] = None

    @property
    def data_uri(self) -> str:
        """Full data URI for BFL API."""
        return f"data:image/png;base64,{self.image_b64}"

    @property
    def prompt_ref(self) -> str:
        """How to reference this image in a FLUX.2 prompt."""
        if self.label:
            return f"the {self.label} from image {self.index}"
        role_label = self.role.value.replace("_", " ")
        return f"the {role_label} from image {self.index}"


@dataclass
class RefPlan:
    """Ordered set of resolved references + prompt fragment."""
    refs:            list[ResolvedRef] = field(default_factory=list)
    prompt_fragment: str               = ""      # "image 1 = face, image 2 = outfit, ..."
    total_bytes:     int               = 0
    resolve_ms:      float             = 0.0

    @property
    def count(self) -> int:
        return len(self.refs)

    def input_image_map(self) -> dict[str, str]:
        """
        Build the FLUX.2 API payload keys.

        Returns:
            {"input_image": "<b64 or url>", "input_image_2": "...", ...}
        """
        result: dict[str, str] = {}
        for ref in self.refs:
            if ref.index == 1:
                result["input_image"] = ref.data_uri
            else:
                result[f"input_image_{ref.index}"] = ref.data_uri
        return result


# ── Manager ──────────────────────────────────────────────────────────

class ReferenceManager:
    """
    Resolves and prepares reference images for multi-ref composition.

    Usage:
        mgr = ReferenceManager(cache_dir="storage/references")
        plan = mgr.resolve(job.reference_images, max_refs=8)
        # plan.refs[0].data_uri  → ready for FLUX.2
        # plan.input_image_map() → {"input_image": ..., "input_image_2": ...}
    """

    def __init__(self, cache_dir: str | Path = _CACHE_DIR):
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._http: Optional[httpx.Client] = None

    def resolve(
        self,
        references: list[ReferenceImage],
        max_refs: int = 8,
        source_image_b64: Optional[str] = None,
    ) -> RefPlan:
        """
        Resolve all reference images into base64 + assign indices.

        Args:
            references:       ReferenceImage list from ImageJob
            max_refs:         Max images to include (FLUX.2 API limit)
            source_image_b64: If present, occupies index 1 (the primary image)

        Returns:
            RefPlan with ordered refs and prompt fragment.
        """
        t0 = time.time()
        plan = RefPlan()
        idx = 1

        # Source image gets index 1 if present
        if source_image_b64:
            plan.refs.append(ResolvedRef(
                index=idx,
                role=ReferenceRole.FULL,
                label="source image",
                image_b64=source_image_b64,
                weight=1.0,
            ))
            plan.total_bytes += len(source_image_b64) * 3 // 4
            idx += 1

        # Resolve each reference
        for ref in references[:max_refs - (idx - 1)]:
            b64 = self._resolve_single(ref)
            if not b64:
                logger.warning(
                    "[RefManager] Could not resolve ref role=%s label=%s",
                    ref.role.value, ref.label,
                )
                continue

            plan.refs.append(ResolvedRef(
                index=idx,
                role=ref.role,
                label=ref.label or ref.role.value,
                image_b64=b64,
                weight=ref.weight,
                cached_path=ref.cached_path,
            ))
            plan.total_bytes += len(b64) * 3 // 4
            idx += 1

        # Build prompt fragment for FLUX.2
        fragments = []
        for r in plan.refs:
            fragments.append(f"image {r.index} = {r.label or r.role.value}")
        plan.prompt_fragment = ", ".join(fragments)

        plan.resolve_ms = (time.time() - t0) * 1000
        logger.info(
            "[RefManager] Resolved %d refs (%.1f KB) in %.0f ms",
            plan.count,
            plan.total_bytes / 1024,
            plan.resolve_ms,
        )

        return plan

    # ── Single reference resolution ──────────────────────────────

    def _resolve_single(self, ref: ReferenceImage) -> Optional[str]:
        """
        Resolve a single ReferenceImage to base64.

        Priority: image_b64 → cached_path → image_url (download)
        """
        # Already have base64
        if ref.image_b64:
            return ref.image_b64

        # Check local cache
        if ref.cached_path and os.path.isfile(ref.cached_path):
            return self._load_cached(ref.cached_path)

        # Download from URL
        if ref.image_url:
            return self._download_and_cache(ref.image_url)

        return None

    def _load_cached(self, path: str) -> Optional[str]:
        """Load image from cache and return base64."""
        try:
            data = Path(path).read_bytes()
            if len(data) > _MAX_IMAGE_SIZE:
                logger.warning("[RefManager] Cached file too large: %s (%d bytes)", path, len(data))
                return None
            return base64.b64encode(data).decode("ascii")
        except Exception as e:
            logger.warning("[RefManager] Failed to read cache %s: %s", path, e)
            return None

    def _download_and_cache(self, url: str) -> Optional[str]:
        """Download image from URL, cache locally, return base64."""
        try:
            if self._http is None:
                self._http = httpx.Client(timeout=_DOWNLOAD_TIMEOUT)

            resp = self._http.get(url)
            resp.raise_for_status()

            data = resp.content
            if len(data) > _MAX_IMAGE_SIZE:
                logger.warning("[RefManager] Downloaded image too large: %d bytes", len(data))
                return None

            # Cache with content hash
            h = hashlib.sha256(data).hexdigest()[:16]
            ext = _guess_extension(resp.headers.get("content-type", ""))
            cache_path = self._cache_dir / f"{h}{ext}"
            cache_path.write_bytes(data)

            logger.info("[RefManager] Cached %s → %s (%d bytes)", url[:60], cache_path, len(data))
            return base64.b64encode(data).decode("ascii")

        except Exception as e:
            logger.warning("[RefManager] Download failed for %s: %s", url[:60], e)
            return None

    # ── Prompt helpers ────────────────────────────────────────────

    @staticmethod
    def build_ref_prompt(plan: RefPlan, base_instruction: str) -> str:
        """
        Augment the user instruction with explicit image references
        for FLUX.2's multi-reference understanding.

        FLUX.2 understands "image 1", "image 2", etc. as reference
        indices matching input_image, input_image_2, etc.

        Example:
            "A person wearing the outfit from image 2, with the
             background from image 3, in the same pose as image 1"
        """
        if plan.count <= 1:
            return base_instruction

        # Only add reference mapping if not already in the instruction
        if "image 1" in base_instruction.lower() or "image 2" in base_instruction.lower():
            return base_instruction

        ref_map = []
        for r in plan.refs:
            ref_map.append(f"image {r.index}: {r.prompt_ref}")

        return (
            f"{base_instruction}\n\n"
            f"Reference images: {'; '.join(ref_map)}"
        )

    def close(self) -> None:
        """Release HTTP client."""
        if self._http:
            self._http.close()
            self._http = None


# ── Helpers ──────────────────────────────────────────────────────────

def _guess_extension(content_type: str) -> str:
    """Map content-type to file extension."""
    ct = content_type.lower().split(";")[0].strip()
    return {
        "image/png":  ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/gif":  ".gif",
    }.get(ct, ".png")
