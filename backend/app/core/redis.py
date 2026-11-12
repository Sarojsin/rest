from redis.asyncio import Redis

from app.core.config import settings


def get_redis() -> Redis:
    """Get a Redis client instance.

    ``protocol=2`` keeps compatibility with Redis servers older than 6.0,
    which do not implement the RESP3 ``HELLO`` command. Newer redis-py
    releases default to RESP3 and fail with ``unknown command 'HELLO'``.
    """
    return Redis.from_url(settings.redis_url, decode_responses=True, protocol=2)


async def close_redis() -> None:
    """Close the Redis connection pool."""
    redis = get_redis()
    await redis.aclose()