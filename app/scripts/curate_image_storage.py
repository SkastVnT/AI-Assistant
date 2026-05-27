"""CPU-only image storage curator.

Scans ``app/storage/outputs/`` and ``app/storage/intermediate/`` for image files,
validates them, detects near-duplicates via a stdlib dHash, picks up any
sidecar / manifest metadata that already lives next to the image, and
emits a curation report under ``app/storage/metadata/curation/``.

What this script DOES NOT do (intentional, per project policy — see
``docs/CHARACTER_PROFILE_FALLBACK.md`` and
``docs/IDENTITY_COLLISION_POLICY.md``):

* No vision / no image classifier.
* No network / web search / crawl.
* No GPU. CPU-only. PIL is required; OpenCV is optional (used only for
  the Laplacian blur metric — gracefully skipped when absent).
* No automatic promotion of ambiguous / unresolved-unknown / low-data
  images. They are reported as ``candidates`` (review) only.
* Never deletes or moves anything. The original storage tree is
  read-only as far as this script is concerned.
* Never imports ``image_pipeline``.

Outputs (JSON Lines, one record per image, plus a summary JSON):

* ``rejected.jsonl``        — failed a hard validation check.
* ``duplicates.jsonl``      — dHash matched an earlier scanned image.
* ``candidates.jsonl``      — passed validation but cannot auto-promote
                              (governance, manifest review flags, low
                              score, etc.). Curator review needed.
* ``promote_candidates.jsonl`` — passed validation, has trusted manifest
                              metadata (``canonical_id`` set,
                              ``needs_review`` not true, mode not
                              ambiguous/unresolved/low-data), high
                              score. Still requires a human to actually
                              promote — this script never does it.
* ``failures.jsonl``        — image could not be opened / decoded.
* ``summary.json``          — counts, score histogram, estimated vision
                              time saved.

Usage::

    python app/scripts/curate_image_storage.py \
        --root app/storage \
        --output-dir app/storage/metadata/curation \
        --avg-vision-sec 5
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Hard / soft dependencies
# ---------------------------------------------------------------------------

try:
    from PIL import Image, ImageStat
except ImportError as exc:  # pragma: no cover - venv-core ships Pillow
    print(
        f"[fatal] Pillow is required (`pip install Pillow`). Original error: {exc}",
        file=sys.stderr,
    )
    sys.exit(2)

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    _HAVE_CV2 = True
except Exception:  # noqa: BLE001 - any import failure → skip blur
    _HAVE_CV2 = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
REPO_ROOT = Path(__file__).resolve().parents[2]
APP_STORAGE_DIR = REPO_ROOT / "app" / "storage"

# Hard validation thresholds.
_MIN_FILE_BYTES = 1024  # 1 KiB — anything smaller is empty/corrupt
_MAX_FILE_BYTES = 64 * 1024 * 1024  # 64 MiB — refuse runaway files
_MIN_DIMENSION = 64  # below this is unusable

# "Good" thresholds (additive scoring, not gates).
_GOOD_RESOLUTION_PIXELS = 512 * 512  # >= 512x512 equivalent
_GOOD_FILE_BYTES_MIN = 50 * 1024  # 50 KiB
_GOOD_FILE_BYTES_MAX = 30 * 1024 * 1024  # 30 MiB

# Blank / monochrome detection.
_BLANK_STDDEV = 3.0  # luminance stddev below this == blank
_BLACK_MEAN = 8.0
_WHITE_MEAN = 247.0

# Blur (cv2 only).
_BLUR_VARIANCE_THRESHOLD = 60.0

# dHash size (8x8 → 64-bit signature).
_DHASH_SIZE = 8

# Hamming distance below this == near-duplicate.
_DHASH_NEAR_DUPLICATE = 5

# Governance flags that block auto-promotion regardless of score.
_BLOCKING_MODES = {"ambiguous", "unresolved_unknown", "low_data_profile"}
_BLOCKING_DATA_STATUS = {"unknown", "low_data", "manual_override"}

# Score required for promote_candidates.jsonl (in addition to governance).
_PROMOTE_SCORE_THRESHOLD = 90

# Skip these directory names anywhere in the tree.
_SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    "venv-core",
    "venv-image",
    "node_modules",
    "metadata",  # don't scan our own output directory
    "references",  # references are curator-managed, not generation outputs
    "prompts",
    "character_db",
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _iter_images(root: Path) -> list[Path]:
    """Walk ``root`` for image files (case-insensitive extension)."""
    if not root.exists() or not root.is_dir():
        return []
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES]
        for fn in filenames:
            if Path(fn).suffix.lower() in IMAGE_EXTS:
                found.append(Path(dirpath) / fn)
    return found


def _safe_size(p: Path) -> int:
    try:
        return p.stat().st_size
    except OSError:
        return -1


def _dhash(img: Image.Image) -> int:
    """Difference hash. Returns a 64-bit int. PIL-only, no numpy required."""
    small = img.convert("L").resize(
        (_DHASH_SIZE + 1, _DHASH_SIZE), Image.Resampling.LANCZOS
    )
    pixels = list(small.getdata())
    bits = 0
    for row in range(_DHASH_SIZE):
        base = row * (_DHASH_SIZE + 1)
        for col in range(_DHASH_SIZE):
            left = pixels[base + col]
            right = pixels[base + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return bits


def _hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _blank_kind(img: Image.Image) -> str | None:
    """Return ``"blank"``, ``"black"``, ``"white"`` or ``None``."""
    gray = img.convert("L")
    stat = ImageStat.Stat(gray)
    mean = stat.mean[0]
    stddev = stat.stddev[0]
    if stddev < _BLANK_STDDEV:
        if mean < _BLACK_MEAN:
            return "black"
        if mean > _WHITE_MEAN:
            return "white"
        return "blank"
    return None


def _blur_score(img: Image.Image) -> float | None:
    """Variance of Laplacian. Returns ``None`` if cv2 is unavailable."""
    if not _HAVE_CV2:
        return None
    arr = np.asarray(img.convert("L"), dtype=np.uint8)
    lap = cv2.Laplacian(arr, cv2.CV_64F)
    return float(lap.var())


def _file_sha1(p: Path, chunk: int = 65536) -> str:
    h = hashlib.sha1()
    try:
        with p.open("rb") as fh:
            while True:
                buf = fh.read(chunk)
                if not buf:
                    break
                h.update(buf)
    except OSError:
        return ""
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Manifest discovery
# ---------------------------------------------------------------------------


def _load_json(p: Path) -> dict | None:
    try:
        with p.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if isinstance(data, dict):
        return data
    return None


def _find_manifest(image_path: Path) -> tuple[dict, str]:
    """Return ``(manifest_dict, source_str)``.

    Discovery order:

    1. Sidecar JSON next to the image: ``foo.png`` -> ``foo.json``.
    2. ``manifest.json`` in the same directory (lookup by filename).
    3. Empty dict + ``"none"`` source.
    """
    sidecar = image_path.with_suffix(".json")
    data = _load_json(sidecar)
    if data is not None:
        return data, "sidecar"

    parent_manifest = image_path.parent / "manifest.json"
    data = _load_json(parent_manifest)
    if data is not None:
        # Manifests sometimes index by filename. Look up first; otherwise
        # treat the whole dict as the metadata.
        entry = data.get(image_path.name)
        if isinstance(entry, dict):
            return entry, "manifest"
        # Some manifests use "items" / "entries" lists.
        for key in ("items", "entries", "images"):
            seq = data.get(key)
            if isinstance(seq, list):
                for item in seq:
                    if isinstance(item, dict) and item.get("file") == image_path.name:
                        return item, "manifest"
        return data, "manifest"

    return {}, "none"


def _extract_identity(meta: dict) -> dict:
    """Pull the curator-relevant fields out of arbitrary manifest data."""
    # Tolerant lookup — manifests vary across producers.
    canonical = meta.get("canonical_id")
    provisional = meta.get("provisional_id")
    mode = meta.get("mode") or meta.get("character_mode") or ""
    data_status = meta.get("data_status") or ""
    needs_review = bool(meta.get("needs_review"))

    # Some manifests nest these under "understanding" (mirrors the
    # response payload from /api/reasoning-image-gen/generate).
    understanding = meta.get("understanding")
    if isinstance(understanding, dict):
        canonical = canonical or understanding.get("canonical_id")
        provisional = provisional or understanding.get("provisional_id")
        mode = (
            mode or understanding.get("mode") or understanding.get("character_mode", "")
        )
        data_status = data_status or understanding.get("data_status", "")
        needs_review = needs_review or bool(understanding.get("needs_review"))

    return {
        "canonical_id": canonical,
        "provisional_id": provisional,
        "mode": mode,
        "data_status": data_status,
        "needs_review": needs_review,
    }


# ---------------------------------------------------------------------------
# Per-image inspection
# ---------------------------------------------------------------------------


def _inspect(image_path: Path) -> dict[str, Any]:
    """Run all CPU-only checks. Returns a record dict (never raises)."""
    rec: dict[str, Any] = {
        "path": str(image_path),
        "name": image_path.name,
        "size_bytes": _safe_size(image_path),
        "ext_ok": image_path.suffix.lower() in IMAGE_EXTS,
        "decoded": False,
        "width": None,
        "height": None,
        "blank_kind": None,
        "blur_variance": None,
        "blur_skipped": not _HAVE_CV2,
        "is_blurry": None,
        "dhash": None,
        "sha1": "",
        "rejection_reason": None,
        "failure_reason": None,
        "manifest_source": "none",
        "manifest": {},
        "identity": {},
    }

    size = rec["size_bytes"]
    if size < 0:
        rec["failure_reason"] = "stat_failed"
        return rec
    if size < _MIN_FILE_BYTES:
        rec["rejection_reason"] = "file_too_small"
        return rec
    if size > _MAX_FILE_BYTES:
        rec["rejection_reason"] = "file_too_large"
        return rec
    if not rec["ext_ok"]:
        rec["rejection_reason"] = "bad_extension"
        return rec

    # Manifest is independent of decode — pick it up either way.
    meta, source = _find_manifest(image_path)
    rec["manifest"] = meta
    rec["manifest_source"] = source
    rec["identity"] = _extract_identity(meta) if meta else {}

    try:
        with Image.open(image_path) as img:
            img.load()  # force decode
            rec["decoded"] = True
            rec["width"], rec["height"] = img.size
            if rec["width"] < _MIN_DIMENSION or rec["height"] < _MIN_DIMENSION:
                rec["rejection_reason"] = "image_too_small"
                return rec

            rec["blank_kind"] = _blank_kind(img)
            blur = _blur_score(img)
            rec["blur_variance"] = blur
            if blur is not None:
                rec["is_blurry"] = blur < _BLUR_VARIANCE_THRESHOLD
            rec["dhash"] = _dhash(img)
    except Exception as exc:  # noqa: BLE001 - PIL raises many types
        rec["failure_reason"] = f"decode_error: {type(exc).__name__}: {exc}"
        return rec

    rec["sha1"] = _file_sha1(image_path)
    return rec


# ---------------------------------------------------------------------------
# Scoring + classification
# ---------------------------------------------------------------------------


def _score(rec: dict[str, Any], is_duplicate: bool) -> tuple[int, dict]:
    """Apply the additive score rubric. Returns ``(score, breakdown)``."""
    bd: dict[str, int] = {}
    if rec["decoded"]:
        bd["valid"] = 30
    if rec["width"] and rec["height"]:
        if rec["width"] * rec["height"] >= _GOOD_RESOLUTION_PIXELS:
            bd["resolution"] = 20
    size = rec["size_bytes"]
    if _GOOD_FILE_BYTES_MIN <= size <= _GOOD_FILE_BYTES_MAX:
        bd["file_size"] = 10
    if rec["decoded"] and rec["blank_kind"] is None:
        bd["not_blank"] = 15
    # +10 for not blurry OR blur skipped (cv2 missing → don't penalize).
    if rec["decoded"] and (rec["is_blurry"] is False or rec["blur_skipped"]):
        bd["not_blurry_or_skipped"] = 10
    if rec["manifest_source"] != "none":
        bd["metadata"] = 10
    if not is_duplicate:
        bd["unique"] = 5
    return sum(bd.values()), bd


def _governance_blocked(identity: dict) -> tuple[bool, str]:
    """Decide whether identity metadata blocks auto-promote."""
    if not identity:
        # No manifest at all → can't trust origin → block.
        return True, "no_manifest_identity"
    if identity.get("needs_review"):
        return True, "needs_review"
    mode = (identity.get("mode") or "").strip()
    if mode in _BLOCKING_MODES:
        return True, f"mode={mode}"
    status = (identity.get("data_status") or "").strip()
    if status in _BLOCKING_DATA_STATUS:
        return True, f"data_status={status}"
    if not identity.get("canonical_id"):
        return True, "no_canonical_id"
    return False, ""


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


class _JsonlWriter:
    """Lazy JSONL writer — only opens the file on first write."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fh = None
        self._count = 0

    def write(self, record: dict) -> None:
        if self._fh is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = self._path.open("w", encoding="utf-8")
        self._fh.write(json.dumps(record, ensure_ascii=False, default=str))
        self._fh.write("\n")
        self._count += 1

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()

    @property
    def count(self) -> int:
        return self._count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="CPU-only image storage curator (no vision, no auto-promote).",
    )
    p.add_argument(
        "--root",
        default=str(APP_STORAGE_DIR),
        help="Storage root containing outputs/ and intermediate/ (default: app/storage).",
    )
    p.add_argument(
        "--output-dir",
        default=str(APP_STORAGE_DIR / "metadata" / "curation"),
        help="Directory for JSONL + summary outputs (default: app/storage/metadata/curation).",
    )
    p.add_argument(
        "--avg-vision-sec",
        type=float,
        default=5.0,
        help="Average per-image vision-classifier seconds, used to estimate "
        "time saved by rejecting/deduping (default: 5).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(args.root).resolve()
    out_dir = Path(args.output_dir).resolve()

    scan_dirs = [root / "outputs", root / "intermediate"]
    started = time.time()

    files: list[Path] = []
    for d in scan_dirs:
        files.extend(_iter_images(d))

    out_dir.mkdir(parents=True, exist_ok=True)
    rejected = _JsonlWriter(out_dir / "rejected.jsonl")
    duplicates = _JsonlWriter(out_dir / "duplicates.jsonl")
    candidates = _JsonlWriter(out_dir / "candidates.jsonl")
    promote = _JsonlWriter(out_dir / "promote_candidates.jsonl")
    failures = _JsonlWriter(out_dir / "failures.jsonl")

    seen_hashes: list[tuple[int, str]] = []  # (dhash, original_path)
    seen_sha1: dict[str, str] = {}  # sha1 -> original path
    score_buckets: Counter[str] = Counter()
    governance_reasons: Counter[str] = Counter()

    counts = {
        "scanned": 0,
        "rejected": 0,
        "duplicates": 0,
        "candidates": 0,
        "promote_candidates": 0,
        "failures": 0,
    }

    for path in files:
        counts["scanned"] += 1
        rec = _inspect(path)

        # Hard failure — couldn't even decode.
        if rec["failure_reason"] is not None:
            counts["failures"] += 1
            failures.write(rec)
            continue

        # Hard rejection — failed a gate.
        if rec["rejection_reason"] is not None:
            counts["rejected"] += 1
            rejected.write(rec)
            continue

        # Duplicate detection. Exact (sha1) is checked first; otherwise
        # near-dup via dHash Hamming distance.
        is_duplicate = False
        dup_reason = ""
        original_path = ""

        if rec["sha1"] and rec["sha1"] in seen_sha1:
            is_duplicate = True
            dup_reason = "exact_sha1"
            original_path = seen_sha1[rec["sha1"]]
        elif rec["dhash"] is not None:
            for prev_hash, prev_path in seen_hashes:
                if _hamming(prev_hash, rec["dhash"]) <= _DHASH_NEAR_DUPLICATE:
                    is_duplicate = True
                    dup_reason = "near_dhash"
                    original_path = prev_path
                    break

        if is_duplicate:
            counts["duplicates"] += 1
            duplicates.write(
                {
                    **rec,
                    "duplicate_of": original_path,
                    "duplicate_reason": dup_reason,
                }
            )
            continue

        # Track for future dup checks.
        if rec["sha1"]:
            seen_sha1[rec["sha1"]] = rec["path"]
        if rec["dhash"] is not None:
            seen_hashes.append((rec["dhash"], rec["path"]))

        score, breakdown = _score(rec, is_duplicate=False)
        rec["score"] = score
        rec["score_breakdown"] = breakdown
        score_buckets[f"{(score // 10) * 10:03d}-{(score // 10) * 10 + 9:03d}"] += 1

        blocked, reason = _governance_blocked(rec["identity"])
        rec["governance_blocked"] = blocked
        rec["governance_reason"] = reason
        if blocked:
            governance_reasons[reason] += 1

        if not blocked and score >= _PROMOTE_SCORE_THRESHOLD:
            counts["promote_candidates"] += 1
            promote.write(rec)
        else:
            counts["candidates"] += 1
            candidates.write(rec)

    for w in (rejected, duplicates, candidates, promote, failures):
        w.close()

    elapsed = time.time() - started
    saved_seconds = (counts["rejected"] + counts["duplicates"]) * float(
        args.avg_vision_sec
    )

    summary = {
        "root": str(root),
        "scan_dirs": [str(d) for d in scan_dirs],
        "output_dir": str(out_dir),
        "have_cv2": _HAVE_CV2,
        "thresholds": {
            "min_file_bytes": _MIN_FILE_BYTES,
            "max_file_bytes": _MAX_FILE_BYTES,
            "min_dimension": _MIN_DIMENSION,
            "good_resolution_pixels": _GOOD_RESOLUTION_PIXELS,
            "blank_stddev": _BLANK_STDDEV,
            "blur_variance_threshold": _BLUR_VARIANCE_THRESHOLD if _HAVE_CV2 else None,
            "dhash_near_duplicate": _DHASH_NEAR_DUPLICATE,
            "promote_score_threshold": _PROMOTE_SCORE_THRESHOLD,
        },
        "counts": counts,
        "score_histogram": dict(sorted(score_buckets.items())),
        "governance_reasons": dict(governance_reasons),
        "estimated_vision_seconds_saved": saved_seconds,
        "avg_vision_sec": float(args.avg_vision_sec),
        "elapsed_seconds": round(elapsed, 3),
    }

    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Console report — concise, no emojis.
    print("Image storage curation complete.")
    print(f"  scanned:            {counts['scanned']}")
    print(f"  rejected:           {counts['rejected']}")
    print(f"  duplicates:         {counts['duplicates']}")
    print(f"  candidates:         {counts['candidates']}")
    print(f"  promote_candidates: {counts['promote_candidates']}")
    print(f"  failures:           {counts['failures']}")
    print(f"  cv2 available:      {_HAVE_CV2}")
    print(
        f"  estimated vision time saved: {saved_seconds:.1f}s "
        f"(@ {float(args.avg_vision_sec):.2f}s/image over rejected+duplicates)"
    )
    print(f"  output dir:         {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
