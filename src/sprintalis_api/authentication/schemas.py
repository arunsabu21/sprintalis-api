import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


def normalize_email(email: str) -> str:
    return email.strip().lower()


class EmailCheckRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize(cls, v: str) -> str:
        return normalize_email(v)


class EmailCheckResponse(BaseModel):
    message: str = "If this email is available, an OTP has been sent."


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)

    @field_validator("email")
    @classmethod
    def normalize(cls, v: str) -> str:
        return normalize_email(v)

    @field_validator("otp")
    @classmethod
    def digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP must be numeric")

        return v


class OTPVerifyResponse(BaseModel):
    verified: bool
    registration_ticket: str


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    registration_ticket: str

    @field_validator("email")
    @classmethod
    def normalize(cls, v: str) -> str:
        return normalize_email(v)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize(cls, v: str) -> str:
        return normalize_email(v)


class GoogleLoginRequest(BaseModel):
    id_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    user: UserPublic
    tokens: TokenPair


class PasswordResetRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize(cls, v: str) -> str:
        return normalize_email(v)


class PasswordResetRequestResponse(BaseModel):
    message: str = (
        "If an eligible account exists for this email, password instructions will be sent."
    )


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        return v


class PasswordResetConfirmResponse(BaseModel):
    message: str = "Your password has been reset. Please log in with your new password."
