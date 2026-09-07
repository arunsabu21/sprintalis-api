import hashlib
import redis.asyncio as redis
from fastapi import HTTPException, status


def hash_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def check_rate_limit(
        redis_client: redis.Redis,
        key: str,
        limit: int,
        window_seconds: int,
) -> None:
    current = await redis_client.incr(key)

    if current == 1:
        await redis_client.expire(key, window_seconds)

    if current > limit:
        ttl = await redis_client.ttl(key)
        retry_after = ttl if ttl > 0 else window_seconds
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Something went wrong. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )