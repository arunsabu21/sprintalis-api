import hmac
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError
from passlib.context import CryptContext

from sprintalis_api.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(
    subject: str, extra_claims: dict[str, Any] | None = None
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None

    if payload.get("type") != "access":
        return None

    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def get_refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )


def generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(raw_otp: str) -> str:
    return hmac.new(
        settings.otp_secret_key.encode("utf-8"),
        raw_otp.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_otp(raw_otp: str, otp_hash: str) -> bool:
    expected_hash = hash_otp(raw_otp)

    return hmac.compare_digest(expected_hash, otp_hash)


def get_otp_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)


def create_registration_ticket(email: str) -> str:
    email = email.strip().lower()

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=15)

    payload = {
        "sub": email,
        "iat": now,
        "exp": expire,
        "type": "registration",
    }

    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_registration_ticket(ticket: str) -> str | None:
    try:
        payload = jwt.decode(
            ticket, settings.jwt_secret_key, algorithms=settings.jwt_algorithm
        )
    except JWTError:
        return None

    if payload.get("type") != "registration":
        return None

    email = payload.get("sub")

    if not isinstance(email, str) or not email:
        return None

    return email


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def get_password_reset_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        minutes=settings.password_reset_expire_minutes
    )
