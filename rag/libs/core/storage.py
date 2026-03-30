"""MinIO / S3-compatible object storage client."""

from minio import Minio

from libs.core.settings import get_settings


def get_storage_client() -> Minio:
    settings = get_settings()
    return Minio(
        endpoint=settings.minio.endpoint,
        access_key=settings.minio.access_key,
        secret_key=settings.minio.secret_key,
        secure=settings.minio.use_ssl,
    )
