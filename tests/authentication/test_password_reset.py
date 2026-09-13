from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sprintalis_api.authentication.models import (
    User,
    AuthIdentity,
    AuthProvider,
    EmailVerification,
    OTPPurpose,
    RefreshToken,
)
from tests.authentication.conftest import TEST_RESET_TOKEN


async def test_request_reset_for_password_user_creates_token(
    client,
    registered_user,
    db_session,
):
    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": registered_user["email"]},
    )
    assert resp.status_code == 200

    row = await db_session.scalar(
        select(EmailVerification).where(
            EmailVerification.email == registered_user["email"],
            EmailVerification.purpose == OTPPurpose.PASSWORD_RESET,
            EmailVerification.consumed.is_(False),
        )
    )
    assert row is not None


async def test_request_reset_for_google_only_user_no_token(client, db_session):
    user = User(
        full_name="Google Only", email="googleonlyreset@example.com", is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        AuthIdentity(
            user_id=user.id, provider=AuthProvider.GOOGLE, provider_user_id="sub-abc"
        )
    )
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "googleonlyreset@example.com"},
    )
    assert resp.status_code == 200

    row = await db_session.scalar(
        select(EmailVerification).where(
            EmailVerification.email == "googleonlyreset@example.com"
        )
    )
    assert row is None


async def test_request_reset_for_nonexistent_user_no_token(client, db_session):
    resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "nobody@example.com"},
    )
    assert resp.status_code == 200

    row = await db_session.scalar(
        select(EmailVerification).where(EmailVerification.email == "nobody@example.com")
    )
    assert row is None


async def test_confirm_reset_success_and_revokes_sessions(
    client, registered_user, db_session
):
    old_access_token = registered_user["access_token"]

    await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": registered_user["email"]},
    )

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": TEST_RESET_TOKEN, "new_password": "BrandNewPass123"},
    )
    assert resp.status_code == 200

    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_access_token}"},
    )
    assert me_resp.status_code == 401

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered_user["refresh_token"]},
    )
    assert refresh_resp.status_code == 401

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": "BrandNewPass123"},
    )
    assert login_resp.status_code == 200


async def test_confirm_reset_token_reuse_fails(client, registered_user):
    await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": registered_user["email"]},
    )

    first = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": TEST_RESET_TOKEN, "new_password": "FirstNewPass123"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": TEST_RESET_TOKEN, "new_password": "SecondNewPass123"},
    )
    assert second.status_code == 400


async def test_confirm_reset_same_password_rejected(client, registered_user):
    await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": registered_user["email"]},
    )

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": TEST_RESET_TOKEN, "new_password": registered_user["password"]},
    )
    assert resp.status_code == 400


async def test_confirm_reset_expired_token(client, registered_user, db_session):
    await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": registered_user["email"]},
    )

    row = await db_session.scalar(
        select(EmailVerification).where(
            EmailVerification.email == registered_user["email"],
            EmailVerification.purpose == OTPPurpose.PASSWORD_RESET,
        )
    )
    row.expires_at = datetime.now(timezone.utc)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": TEST_RESET_TOKEN, "new_password": "NewPass123"},
    )
    assert resp.status_code == 400
