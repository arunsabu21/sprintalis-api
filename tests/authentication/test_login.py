from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sprintalis_api.authentication.models import User, AuthIdentity, AuthProvider


async def test_login_success(client, registered_user):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body["tokens"]
    assert "refresh_token" in body["tokens"]
    assert body["user"]["email"] == registered_user["email"]


async def test_login_wrong_password_increments_failed_attempts(
    client, registered_user, db_session
):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": "WrongPassword123",
        },
    )
    assert resp.status_code == 401

    user = await db_session.scalar(
        select(User).where(User.email == registered_user["email"])
    )
    assert user.failed_login_attempts == 1


async def test_login_locks_account_after_max_failed_attempts(
    client,
    registered_user,
    db_session,
):
    email = registered_user["email"]

    for _ in range(5):
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "WrongPassword123",
            },
        )

    user = await db_session.scalar(select(User).where(User.email == email))
    assert user.locked_until is not None
    assert user.locked_until > datetime.now(timezone.utc)

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 423


async def test_successful_login_resets_failed_attempts(
    client,
    registered_user,
    db_session,
):
    email = registered_user["email"]

    for _ in range(2):
        await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": registered_user["password"],
            },
        )

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 200

    user = await db_session.scalar(select(User).where(User.email == email))
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


async def test_login_with_google_only_account_fails(client, db_session):
    user = User(
        full_name="Google Only",
        email="googleonly@example.com",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    identity = AuthIdentity(
        user_id=user.id,
        provider=AuthProvider.GOOGLE,
        provider_user_id="fake_google_sub_123",
    )
    db_session.add(identity)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "googleonly@example.com", "password": "AnyPassword123"},
    )
    assert resp.status_code == 400
    assert "google" in resp.json()["detail"].lower()


async def test_login_nonexistent_user_returns_generic_error(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "doesnotexist@example.com", "password": "SomePassword123"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect email or password."


async def test_login_disabled_account(client, registered_user, db_session):
    user = await db_session.scalar(
        select(User).where(User.email == registered_user["email"])
    )
    user.is_active = False
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 403
