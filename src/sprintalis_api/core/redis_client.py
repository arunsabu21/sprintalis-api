from collections.abc import AsyncGenerator
import redis.asyncio as redis
from sprintalis_api.core.config import settings

redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,
    max_connections=20,
)


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    client = redis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        await client.aclose()
