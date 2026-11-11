from redis.asyncio import Redis

from app.core.config import settings


def get_redis() -> Redis:
    """Get a Redis client instance."""
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    """Close the Redis connection pool."""
    redis = get_redis()
    await redis.aclose()