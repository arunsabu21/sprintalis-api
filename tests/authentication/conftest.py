import pytest
import pytest_asyncio
from sprintalis_api.core.security import set_test_otp_override

TEST_OTP = "123456"


@pytest.fixture(autouse=True)
def fixed_otp():
    set_test_otp_override(TEST_OTP)
    yield
    set_test_otp_override(None)


@pytest_asyncio.fixture
async def registered_user(client):
    email = "testuser@example.com"
    password = "TestPass123"
    full_name = "Test User"

    await client.post("/api/v1/auth/register/request-otp", json={"email": email})

    verify_response = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"email": email, "otp": TEST_OTP},
    )
    ticket = verify_response.json()["registration_ticket"]

    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": full_name,
            "password": password,
            "registration_ticket": ticket,
        },
    )
    data = register_response.json()

    return {
        "access_token": data["tokens"]["access_token"],
        "refresh_token": data["tokens"]["refresh_token"],
        "user": data["user"],
        "email": email,
        "password": password,
    }
