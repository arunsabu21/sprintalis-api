from sqlalchemy import select
from sprintalis_api.authentication.models import User, AuthIdentity, AuthProvider
from sprintalis_api.authentication.oauth_google import GoogleUserInfo
from sprintalis_api.core.exceptions import InvalidGoogleTokenError


def _fake_google_info(
    sub="google-sub-123", email="googleuser@example.com", full_name="Google User"
):
    return GoogleUserInfo(
        sub=sub, email=email, email_verified=True, full_name=full_name
    )


async def test_google_login_creates_new_user(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "sprintalis_api.authentication.service.verify_google_id_token",
        lambda token: _fake_google_info(),
    )

    resp = await client.post("/api/v1/auth/google", json={"id_token": "fake_token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "googleuser@example.com"
    assert "access_token" in body["tokens"]

    identity = await db_session.scalar(
        select(AuthIdentity).where(AuthIdentity.provider_user_id == "google-sub-123")
    )
    assert identity is not None
    assert identity.provider == AuthProvider.GOOGLE
    assert identity.password_hash is None


async def test_google_login_existing_identity_logs_in_no_duplicate(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        "sprintalis_api.authentication.service.verify_google_id_token",
        lambda token: _fake_google_info(),
    )

    resp1 = await client.post("/api/v1/auth/google", json={"id_token": "fake_token"})
    assert resp1.status_code == 200
    user_id_1 = resp1.json()["user"]["id"]

    resp2 = await client.post("/api/v1/auth/google", json={"id_token": "fake_token"})
    assert resp2.status_code == 200
    user_id_2 = resp2.json()["user"]["id"]

    assert user_id_1 == user_id_2

    count = await db_session.scalar(
        select(User).where(User.email == "googleuser@example.com")
    )
    all_users = (
        await db_session.scalars(
            select(User).where(User.email == "googleuser@example.com")
        )
    ).all()
    assert len(all_users) == 1


async def test_google_login_with_existing_password_account_fails(
    client,
    registered_user,
    monkeypatch,
):
    monkeypatch.setattr(
        "sprintalis_api.authentication.service.verify_google_id_token",
        lambda token: _fake_google_info(email=registered_user["email"]),
    )

    resp = await client.post("/api/v1/auth/google", json={"id_token": "fake_token"})
    assert resp.status_code == 400
    assert (
        "password" in resp.json()["detail"].lower()
        or "exists" in resp.json()["detail"].lower()
    )


async def test_google_login_invalid_token_returns_401(client, monkeypatch):
    def raise_invalid(token):
        raise InvalidGoogleTokenError("Invalid token")

    monkeypatch.setattr(
        "sprintalis_api.authentication.service.verify_google_id_token",
        raise_invalid,
    )

    resp = await client.post("/api/v1/auth/google", json={"id_token": "garbage"})
    assert resp.status_code == 401
