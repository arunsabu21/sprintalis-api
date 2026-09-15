import pytest_asyncio
from sprintalis_api.core.security import set_test_otp_override


@pytest_asyncio.fixture
async def second_user(client):
    set_test_otp_override("123456")

    email = "seconduser@example.com"
    password = "SecondUser123"

    await client.post("/api/v1/auth/register/request-otp", json={"email": email})

    verify_resp = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": email, "otp": "123456"},
    )
    ticket = verify_resp.json()["registration_ticket"]

    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Second User",
            "password": password,
            "registration_ticket": ticket,
        },
    )
    data = register_resp.json()

    set_test_otp_override(None)

    return {
        "access_token": data["tokens"]["access_token"],
        "user": data["user"],
        "email": email,
        "password": password,
    }
