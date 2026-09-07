from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from sprintalis_api.api.v1.router import api_router
from sprintalis_api.core.database import get_db
from sprintalis_api.core.redis_client import get_redis

app = FastAPI()

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    status_report = {"status": "ok", "database": "unknown", "redis": "unknown"}

    try:
        await db.execute(text("SELECT 1"))
        status_report["database"] = "ok"
    except Exception:
        status_report["database"] = "unreachable"
        status_report["status"] = "degraded"

    try:
        await redis_client.ping()
        status_report["redis"] = "ok"
    except Exception:
        status_report["redis"] = "unreachable"
        status_report["status"] = "degraded"

    return status_report
