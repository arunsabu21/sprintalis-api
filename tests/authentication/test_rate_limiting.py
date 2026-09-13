async def test_request_otp_email_rate_limit(client):
    email = "ratelimited@example.com"

    for _ in range(3):
        resp = await client.post(
            "/api/v1/auth/register/request-otp",
            json={"email": email},
        )
        assert resp.status_code == 200

    resp = await client.post(
        "/api/v1/auth/register/request-otp",
        json={"email": email},
    )
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


async def test_login_ip_rate_limit(client):
    for _ in range(20):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "irrelevant@example.com", "password": "wrong"},
        )

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "irrelevant@example.com", "password": "wrong"},
    )
    assert resp.status_code == 429


async def test_resend_otp_email_rate_limit(client):
    email = "resendlimited@example.com"
    await client.post(
        "/api/v1/auth/register/request-otp",
        json={"email": email},
    )

    for _ in range(3):
        resp = await client.post(
            "/api/v1/auth/register/resend-otp",
            json={"email": email},
        )
        assert resp.status_code == 200

    resp = await client.post(
        "/api/v1/auth/register/resend-otp",
        json={"email": email},
    )
    assert resp.status_code == 429
