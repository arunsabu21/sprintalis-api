import pytest
import pytest_asyncio
from sprintalis_api.core.security import (
    set_test_otp_override,
    set_test_reset_token_override,
)

TEST_OTP = "123456"
TEST_RESET_TOKEN = "fixed-reset-token-for-testing-only"


@pytest.fixture(autouse=True)
def fixed_otp():
    set_test_otp_override(TEST_OTP)
    yield
    set_test_otp_override(None)


@pytest.fixture(autouse=True)
def fixed_reset_token():
    set_test_reset_token_override(TEST_RESET_TOKEN)
    yield
    set_test_reset_token_override(None)
