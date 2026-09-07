from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from sprintalis_api.core.database import get_db
from sprintalis_api.core.redis_client import get_redis
from sprintalis_api.core.rate_limiter import check_rate_limit, hash_identifier
from sprintalis_api.authentication.schemas import normalize_email
from sprintalis_api.core.security import decode_access_token
from sprintalis_api.authentication.models import User

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW.Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW.Authenticate": "Bearer"},
        )

    user = await db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exist.",
            headers={"WWW.Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been disabled",
        )

    return user


def get_client_metadata(request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    return user_agent, ip_address


async def rate_limit_registration_request(
    request: Request,
    payload_email: str,
    redis_client: redis.Redis,
) -> None:
    ip = request.client.host if request.client else "unknown"

    await check_rate_limit(
        redis_client,
        key=f"rate_limit:register_request:ip:{hash_identifier(ip)}",
        limit=10,
        window_seconds=900,
    )

    email_hash = hash_identifier(normalize_email(payload_email))

    await check_rate_limit(
        redis_client,
        key=f"rate_limit:register_request:email:{email_hash}",
        limit=3,
        window_seconds=900,
    )


async def rate_limit_registration_resend(
    request: Request,
    payload_email: str,
    redis_client: redis.Redis,
) -> None:
    ip = request.client.host if request.client else "unknown"

    await check_rate_limit(
        redis_client,
        key=f"rate_limit:register_resend:ip:{hash_identifier(ip)}",
        limit=10,
        window_seconds=900,
    )

    email_hash = hash_identifier(normalize_email(payload_email))

    await check_rate_limit(
        redis_client,
        key=f"rate_limit:register_resend:email:{email_hash}",
        limit=3,
        window_seconds=3,
    )
