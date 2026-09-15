import os

os.environ.setdefault("ENV_FILE", ".env.test")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import fakeredis.aioredis

from sprintalis_api.main import app
from sprintalis_api.core.database import Base, get_db
from sprintalis_api.core.redis_client import get_redis
from sprintalis_api.core.config import settings
from sprintalis_api.core.security import set_test_otp_override

SHARED_TEST_OTP = "123456"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(settings.database_url, echo=False)
    session_local = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_local() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def fake_redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session, fake_redis):
    async def override_get_db():
        yield db_session

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client):
    set_test_otp_override(SHARED_TEST_OTP)

    email = "testuser@example.com"
    password = "TestPass123"
    full_name = "Test User"

    await client.post("/api/v1/auth/register/request-otp", json={"email": email})

    verify_resp = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": email, "otp": SHARED_TEST_OTP},
    )
    ticket = verify_resp.json()["registration_ticket"]

    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": full_name,
            "password": password,
            "registration_ticket": ticket,
        },
    )
    data = register_resp.json()

    set_test_otp_override(None)

    return {
        "access_token": data["tokens"]["access_token"],
        "refresh_token": data["tokens"]["refresh_token"],
        "user": data["user"],
        "email": email,
        "password": password,
    }
