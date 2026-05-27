"""Health check routes."""

from fastapi import APIRouter

from apps.api.schemas import HealthResponse
from libs.core.cache import get_redis
from libs.core.database import engine
from libs.core.settings import get_settings
from libs.core.storage import get_storage_client

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check connectivity to all infrastructure services."""
    pg_ok = False
    redis_ok = False
    minio_ok = False

    # PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        pg_ok = True
    except Exception:
        pass

    # Redis
    try:
        r = get_redis()
        await r.ping()
        redis_ok = True
        await r.aclose()
    except Exception:
        pass

    # MinIO
    try:
        settings = get_settings()
        client = get_storage_client()
        client.bucket_exists(settings.minio.bucket)
        minio_ok = True
    except Exception:
        pass

    all_ok = pg_ok and redis_ok and minio_ok
    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        postgres=pg_ok,
        redis=redis_ok,
        minio=minio_ok,
    )
