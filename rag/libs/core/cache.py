"""Redis client factory."""

import redis.asyncio as redis

from libs.core.settings import get_settings


def get_redis() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis.url, decode_responses=True)
