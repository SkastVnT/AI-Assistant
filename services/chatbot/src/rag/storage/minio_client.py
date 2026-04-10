"""
RagFileStore — object-storage backend for the RAG ingestion pipeline.

Backends (tried in order)
--------------------------
1. **MinIO / S3** — used when the ``minio`` package is installed *and* the
   configured endpoint is reachable.
2. **Local disk** — a simple ``pathlib.Path``-based fallback that stores
   blobs under ``RAG_DATA_DIR/objects/``.  Suitable for development and CI.

The public API is intentionally synchronous; the async ingestion service
runs these calls in a thread-pool executor (or the single-thread FastAPI
default) so they do not block the event loop.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class RagFileStore:
    """Unified file-store interface with MinIO-or-local fallback.

    Parameters
    ----------
    endpoint : str | None
        MinIO endpoint (``"host:port"``).  Defaults to the value from
        :func:`core.rag_settings.get_rag_settings`.
    access_key : str | None
        MinIO access key.  Defaults to settings.
    secret_key : str | None
        MinIO secret key.  Defaults to settings.
    bucket : str | None
        Bucket / container name.  Defaults to settings.
    local_root : Path | str | None
        Root directory used by the local-disk fallback.
        Defaults to ``<RAG_DATA_DIR>/objects``.
    """

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        local_root: "Path | str | None" = None,
    ) -> None:
        from core.rag_settings import get_rag_settings

        cfg = get_rag_settings()

        self._bucket = bucket or cfg.minio_bucket
        self._minio: object | None = None  # minio.Minio instance or None

        # ── Try MinIO ────────────────────────────────────────────────────
        _endpoint = endpoint or cfg.minio_endpoint
        _access = access_key or cfg.minio_access_key
        _secret = secret_key or cfg.minio_secret_key

        try:
            from minio import Minio  # type: ignore[import]

            client = Minio(
                _endpoint,
                access_key=_access,
                secret_key=_secret,
                secure=False,
            )
            # Ping: list buckets (cheap, validates connectivity)
            client.list_buckets()
            if not client.bucket_exists(self._bucket):
                client.make_bucket(self._bucket)
            self._minio = client
            logger.info("RagFileStore: using MinIO at %s (bucket=%s)", _endpoint, self._bucket)
        except ImportError:
            logger.debug("RagFileStore: minio package not installed — using local disk")
        except OSError as exc:
            logger.debug(
                "RagFileStore: MinIO unreachable (%s) — falling back to local disk", exc
            )
        except Exception as exc:  # noqa: BLE001 — catch-all for unexpected MinIO errors
            logger.debug(
                "RagFileStore: MinIO unavailable (%s) — falling back to local disk", exc
            )

        # ── Local-disk fallback root ────────────────────────────────────
        if local_root is not None:
            self._local_root = Path(local_root)
        else:
            data_dir = os.getenv("RAG_DATA_DIR", "data/rag")
            self._local_root = Path(data_dir) / "objects"

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def backend_name(self) -> str:
        """Return ``"minio"`` or ``"local"`` to describe the active backend."""
        return "minio" if self._minio is not None else "local"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(self, data: bytes, object_path: str) -> None:
        """Store *data* at *object_path* in the active backend.

        Parameters
        ----------
        data : bytes
            Raw file content to persist.
        object_path : str
            Logical path within the bucket / local root
            (e.g. ``"<tenant>/<doc_id>/filename.pdf"``).
        """
        if self._minio is not None:
            self._upload_minio(data, object_path)
        else:
            self._upload_local(data, object_path)

    def delete(self, object_path: str) -> None:
        """Remove *object_path* from the active backend.

        Failure is logged but not re-raised (best-effort cleanup).
        """
        try:
            if self._minio is not None:
                self._delete_minio(object_path)
            else:
                self._delete_local(object_path)
        except Exception:
            logger.warning(
                "RagFileStore.delete: failed to remove %s", object_path, exc_info=True
            )

    # ------------------------------------------------------------------
    # MinIO helpers
    # ------------------------------------------------------------------

    def _upload_minio(self, data: bytes, object_path: str) -> None:
        import io

        from minio.error import S3Error  # type: ignore[import]

        assert self._minio is not None
        try:
            self._minio.put_object(  # type: ignore[attr-defined]
                self._bucket,
                object_path,
                io.BytesIO(data),
                length=len(data),
            )
        except S3Error as exc:
            raise IOError(f"MinIO upload failed for {object_path!r}: {exc}") from exc

    def _delete_minio(self, object_path: str) -> None:
        assert self._minio is not None
        self._minio.remove_object(self._bucket, object_path)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Local-disk helpers
    # ------------------------------------------------------------------

    def _upload_local(self, data: bytes, object_path: str) -> None:
        dest = self._local_root / object_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        logger.debug("RagFileStore(local): wrote %d bytes → %s", len(data), dest)

    def _delete_local(self, object_path: str) -> None:
        dest = self._local_root / object_path
        if dest.exists():
            dest.unlink()
            logger.debug("RagFileStore(local): removed %s", dest)
