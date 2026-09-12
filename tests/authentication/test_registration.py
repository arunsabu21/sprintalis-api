from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sprintalis_api.authentication.models import EmailVerification, OTPPurpose
from sprintalis_api.core.security import hash_otp, create_registration_ticket

TEST_OTP = "123456"


async def test_request_otp_success(client):
    resp = await client.post(
        "/api/v1/auth/register/request-otp",
        json={"email": "newuser@example.com"},
    )
    assert resp.status_code == 200
    assert "message" in resp.json()


async def test_full_registration_flow(client):
    email = "flowtest@example.com"

    await client.post("/api/v1/auth/register/request-otp", json={"email": email})

    verify_resp = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": email, "otp": TEST_OTP},
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verified"] is True
    ticket = verify_resp.json()["registration_ticket"]

    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Flow Test",
            "password": "FlowTest123",
            "registration_ticket": ticket,
        },
    )
    assert register_resp.status_code == 201
    body = register_resp.json()
    assert body["user"]["email"] == email
    assert "access_token" in body["tokens"]
    assert "refresh_token" in body["tokens"]


async def test_me_endpoint_with_registered_user(client, registered_user):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {registered_user['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == registered_user["email"]


async def test_request_otp_for_existing_user_returns_generic_message(
    client, registered_user
):
    resp = await client.post(
        "/api/v1/auth/register/request-otp",
        json={"email": registered_user["email"]},
    )
    assert resp.status_code == 200
    assert "message" in resp.json()


async def test_verify_otp_wrong_code_increments_attempts(client, db_session):
    email = "wrongotp@example.com"
    await client.post("/api/v1/auth/register/request-otp", json={"email": email})

    resp = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": email, "otp": "999999"},
    )
    assert resp.status_code == 400

    verification = await db_session.scalar(
        select(EmailVerification).where(EmailVerification.email == email)
    )
    assert verification.attempts == 1


async def test_verify_otp_max_attempts_exceeded(client):
    email = "maxattempts@example.com"
    await client.post("/api/v1/auth/register/request-otp", json={"email": email})

    for _ in range(5):
        resp = await client.post(
            "/api/v1/auth/register/verify-otp",
            json={"email": email, "otp": "999999"},
        )

    assert resp.status_code == 400

    resp = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": email, "otp": TEST_OTP},
    )
    assert resp.status_code == 400


async def test_verify_otp_expired(client, db_session):
    email = "expiredotp@example.com"
    await client.post("/api/v1/auth/register/request-otp", json={"email": email})

    verification = await db_session.scalar(
        select(EmailVerification).where(EmailVerification.email == email)
    )
    verification.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": email, "otp": TEST_OTP},
    )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


async def test_register_with_stale_ticket_after_already_registered(
    client, registered_user
):
    ticket = create_registration_ticket(registered_user["email"])

    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": registered_user["email"],
            "full_name": "Duplicate Attempt",
            "password": "SomePass123",
            "registration_ticket": ticket,
        },
    )
    assert resp.status_code == 409


async def test_register_with_ticket_for_different_email(client):
    email_a = "ticketownera@example.com"
    email_b = "ticketownerb@example.com"

    await client.post("/api/v1/auth/register/request-otp", json={"email": email_a})
    verify_resp = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": email_a, "otp": TEST_OTP},
    )
    ticket = verify_resp.json()["registration_ticket"]

    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email_b,
            "full_name": "Mismatch Test",
            "password": "Mismatch123",
            "registration_ticket": ticket,
        },
    )
    assert resp.status_code == 400


async def test_register_with_garbage_ticket(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "garbagetest@example.com",
            "full_name": "Garbage Test",
            "password": "Garbage123",
            "registration_ticket": "not.a.real.jwt.token",
        },
    )
    assert resp.status_code == 400


async def test_resend_otp_on_pending_verification(client, db_session):
    email = "resendtest@example.com"
    await client.post("/api/v1/auth/register/request-otp", json={"email": email})

    original = await db_session.scalar(
        select(EmailVerification).where(EmailVerification.email == email)
    )
    original_id = original.id

    resp = await client.post(
        "/api/v1/auth/register/resend-otp",
        json={"email": email},
    )
    assert resp.status_code == 200

    await db_session.refresh(original)
    assert original.consumed is True

    new_row = await db_session.scalar(
        select(EmailVerification).where(
            EmailVerification.email == email,
            EmailVerification.consumed.is_(False),
        )
    )
    assert new_row is not None
    assert new_row.id != original_id
    assert new_row.attempts == 0


async def test_resend_otp_for_existing_user_returns_generic(client, registered_user):
    resp = await client.post(
        "/api/v1/auth/register/resend-otp",
        json={"email": registered_user["email"]},
    )
    assert resp.status_code == 200
    assert "message" in resp.json()


async def test_resend_otp_with_no_pending_verification(client):
    resp = await client.post(
        "/api/v1/auth/register/resend-otp",
        json={"email": "neverrequested@example.com"},
    )
    assert resp.status_code == 200
    assert "message" in resp.json()


async def test_old_otp_invalid_after_resend(client, db_session):
    email = "oldotpinvalid@example.com"
    await client.post("/api/v1/auth/register/request-otp", json={"email": email})
    await client.post("/api/v1/auth/register/resend-otp", json={"email": email})

    old_rows = await db_session.scalars(
        select(EmailVerification)
        .where(EmailVerification.email == email)
        .order_by(EmailVerification.created_at.asc())
    )
    rows = old_rows.all()
    assert len(rows) == 2
    assert rows[0].consumed is True
    assert rows[1].consumed is False
