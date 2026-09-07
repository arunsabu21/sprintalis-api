from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sprintalis_api.core import security
from sprintalis_api.core.config import settings
from sprintalis_api.core.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidOtpError,
    OTPExpiredError,
    OTPMaxAttemptsExceededError,
    InvalidRegistrationTicketError,
    InvalidCredentialsError,
    AccountLockedError,
    AccountDisabledError,
    AccountUsesGoogleError,
    AccountUsesPasswordError,
    InvalidGoogleTokenError,
    InvalidRefreshTokenError,
    InvalidResetTokenError,
    SamePasswordError,
)

from sprintalis_api.authentication.models import (
    User,
    AuthIdentity,
    AuthProvider,
    EmailVerification,
    OTPPurpose,
    RefreshToken,
)
from sprintalis_api.authentication.schemas import TokenPair
from sprintalis_api.authentication.oauth_google import verify_google_id_token

FAILED_LOGIN_LOCK_THRESHOLD = 5
FAILED_LOGIN_LOCK_MINUTES = 15


async def request_registration_otp(db: AsyncSession, email: str) -> None:
    existing_user = await db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise EmailAlreadyRegisteredError("An account with this email already exists.")

    result = await db.execute(
        select(EmailVerification).where(
            EmailVerification.email == email,
            EmailVerification.purpose == OTPPurpose.REGISTER,
            EmailVerification.consumed.is_(False),
        )
    )

    old_rows = result.scalars().all()

    for row in old_rows:
        row.consumed = True

    raw_otp = security.generate_otp()
    verification = EmailVerification(
        email=email,
        otp_hash=security.hash_otp(raw_otp),
        purpose=OTPPurpose.REGISTER,
        expires_at=security.get_otp_expiry(),
    )

    db.add(verification)
    await db.commit()

    # TODO: Logging for dev only - never use in prod
    print(f"[DEV] OTP for {email}: {raw_otp}")


async def resend_registration_otp(db: AsyncSession, email: str) -> None:
    existing_user = await db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        return

    pending = await db.scalar(
        select(EmailVerification)
        .where(
            EmailVerification.email == email,
            EmailVerification.purpose == OTPPurpose.REGISTER,
            EmailVerification.consumed.is_(False),
        )
        .order_by(EmailVerification.created_at.desc())
        .limit(1)
    )

    if pending is None:
        return

    pending.consumed = True

    raw_otp = security.generate_otp()
    new_verification = EmailVerification(
        email=email,
        otp_hash=security.hash_otp(raw_otp),
        purpose=OTPPurpose.REGISTER,
        expires_at=security.get_otp_expiry(),
    )
    db.add(new_verification)
    await db.commit()

    # TODO: real email provider. Dev-only logging
    print(f"[DEV] Resent OTP for {email}: {raw_otp}")


async def verify_registration_otp(db: AsyncSession, email: str, otp: str) -> str:
    verification = await db.scalar(
        select(EmailVerification)
        .where(
            EmailVerification.email == email,
            EmailVerification.purpose == OTPPurpose.REGISTER,
            EmailVerification.consumed == False,
        )
        .order_by(EmailVerification.created_at.desc())
        .limit(1)
    )

    if verification is None:
        raise InvalidOtpError("No pending verification found for this email.")

    if verification.expires_at < datetime.now(timezone.utc):
        verification.consumed = True
        await db.commit()
        raise OTPExpiredError("OTP has expired. Please request a new one.")

    if verification.attempts >= settings.otp_max_attempts:
        verification.consumed = True
        await db.commit()
        raise OTPMaxAttemptsExceededError(
            "Too many attempts. Please request a new otp."
        )

    if not security.verify_otp(otp, verification.otp_hash):
        verification.attempts += 1
        await db.commit()
        raise InvalidOtpError("Incorrect otp. Please try again.")

    verification.consumed = True
    await db.commit()

    return security.create_registration_ticket(email)


async def register_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    password: str,
    registration_ticket: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[User, TokenPair]:
    ticket_email = security.decode_registration_ticket(registration_ticket)

    if ticket_email is None or ticket_email != email:
        raise InvalidRegistrationTicketError(
            "Registration ticket is invalid or does not match this email."
        )

    existing_user = await db.scalar(select(User).where(User.email == email))

    if existing_user is not None:
        raise EmailAlreadyRegisteredError("An account with this email already exists.")

    user = User(full_name=full_name, email=email, is_active=True)
    db.add(user)
    await db.flush()

    identity = AuthIdentity(
        user_id=user.id,
        provider=AuthProvider.PASSWORD,
        password_hash=security.hash_password(password),
    )
    db.add(identity)
    await db.commit()
    await db.refresh(user)

    tokens = await _issue_token_pair(db, user, user_agent, ip_address)
    return user, tokens


async def login_with_password(
    db: AsyncSession,
    email: str,
    password: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[User, TokenPair]:
    user = await db.scalar(select(User).where(User.email == email))

    if user is None:
        raise InvalidCredentialsError("Incorrect email or password.")

    now = datetime.now(timezone.utc)

    if user.locked_until is not None and user.locked_until > now:
        raise AccountLockedError(
            "Account is temporary locked due to some security reasons.",
            locked_until=user.locked_until,
        )

    identity = await db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.user_id == user.id,
            AuthIdentity.provider == AuthProvider.PASSWORD,
        )
    )

    if identity is None or identity.password_hash is None:
        raise AccountUsesGoogleError(
            "This account was created using Google. Please continue with Google to sign in."
        )

    if not security.verify_password(password, identity.password_hash):
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= FAILED_LOGIN_LOCK_THRESHOLD:
            user.locked_until = now + timedelta(minutes=FAILED_LOGIN_LOCK_MINUTES)
        await db.commit()
        raise InvalidCredentialsError("Incorrect email or password.")

    if not user.is_active:
        raise AccountDisabledError("This account has been disabled.")

    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()

    tokens = await _issue_token_pair(db, user, user_agent, ip_address)
    return user, tokens


async def login_with_google(
    db: AsyncSession,
    id_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[User, TokenPair]:
    try:
        google_info = verify_google_id_token(id_token)
    except InvalidGoogleTokenError:
        raise

    identity = await db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.provider == AuthProvider.GOOGLE,
            AuthIdentity.provider_user_id == google_info.sub,
        )
    )

    if identity is not None:
        user = await db.get(User, identity.user_id)
        if not user.is_active:
            raise AccountDisabledError("This account has been disabled.")
        tokens = await _issue_token_pair(db, user, user_agent, ip_address)
        return user, tokens

    existing_user = await db.scalar(select(User).where(User.email == google_info.email))

    if existing_user is not None:
        raise AccountUsesPasswordError(
            "This account already exists. Please sign in using your email and password."
        )

    user = User(
        full_name=google_info.full_name or google_info.email.split("@")[0],
        email=google_info.email,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    identity = AuthIdentity(
        user_id=user.id,
        provider=AuthProvider.GOOGLE,
        provider_user_id=google_info.sub,
    )
    db.add(identity)
    await db.commit()
    await db.refresh(user)

    tokens = await _issue_token_pair(db, user, user_agent, ip_address)
    return user, tokens


async def refresh_access_token(
    db: AsyncSession,
    raw_refresh_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair:
    token_hash = security.hash_refresh_token(raw_refresh_token)
    existing = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )

    if existing is None or existing.revoked:
        raise InvalidRefreshTokenError("Refresh token is invalid or has been revoked.")

    if existing.expires_at < datetime.now(timezone.utc):
        existing.revoked = True
        await db.commit()
        raise InvalidRefreshTokenError("Refresh token has expired.")

    user = await db.get(User, existing.user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError("Account is currently not active.")

    existing.revoked = True
    tokens = await _issue_token_pair(db, user, user_agent, ip_address)
    return tokens


async def logout(db: AsyncSession, raw_refresh_token: str) -> None:
    token_hash = security.hash_refresh_token(raw_refresh_token)
    existing = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )

    if existing is not None:
        existing.revoked = True
        await db.commit()


async def logout_all_sessions(db: AsyncSession, user_id) -> None:
    tokens = await db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
        )
    )

    for token in tokens:
        token.revoked = True
    await db.commit()


async def _issue_token_pair(
    db: AsyncSession,
    user: User,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair:
    access_token = security.create_access_token(str(user.id))
    raw_refresh = security.generate_refresh_token()

    refresh_row = RefreshToken(
        user_id=user.id,
        token_hash=security.hash_refresh_token(raw_refresh),
        expires_at=security.get_refresh_token_expiry(),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(refresh_row)
    await db.commit()

    return TokenPair(access_token=access_token, refresh_token=raw_refresh)


async def request_password_reset(db: AsyncSession, email: str) -> None:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        return

    identity = await db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.user_id == user.id,
            AuthIdentity.provider == AuthProvider.PASSWORD,
        )
    )

    if identity is None or identity.password_hash is None:
        return

    old_rows = await db.scalars(
        select(EmailVerification).where(
            EmailVerification.email == email,
            EmailVerification.purpose == OTPPurpose.PASSWORD_RESET,
            EmailVerification.consumed.is_(False),
        )
    )

    for row in old_rows:
        row.consumed = True

    raw_token = security.generate_password_reset_token()
    verification = EmailVerification(
        email=email,
        otp_hash=security.hash_password_reset_token(raw_token),
        purpose=OTPPurpose.PASSWORD_RESET,
        expires_at=security.get_password_reset_expiry(),
    )
    db.add(verification)
    await db.commit()

    # TODO: real email provider. Dev-only logging
    reset_link = f"{settings.frontend_url}/reset-password?token={raw_token}"
    print(f"[DEV] Password reset link for {email}: {reset_link}")


async def reset_password(db: AsyncSession, raw_token: str, new_password: str) -> None:
    token_hash = security.hash_password_reset_token(raw_token)
    now = datetime.now(timezone.utc)

    stmt = (
        update(EmailVerification)
        .where(
            EmailVerification.otp_hash == token_hash,
            EmailVerification.purpose == OTPPurpose.PASSWORD_RESET,
            EmailVerification.consumed.is_(False),
            EmailVerification.expires_at > now,
        )
        .values(consumed=True)
        .returning(EmailVerification.email)
    )

    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        await db.rollback()
        raise InvalidResetTokenError("This reset link is invalid or has expired.")

    email = row[0]

    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        await db.rollback()
        raise InvalidResetTokenError("This reset link is invalid or has expired.")

    identity = await db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.user_id == user.id,
            AuthIdentity.provider == AuthProvider.PASSWORD,
        )
    )

    if identity is None:
        await db.rollback()
        raise InvalidResetTokenError("This reset link is invalid or has expired.")

    if identity.password_hash and security.verify_password(
        new_password, identity.password_hash
    ):
        await db.rollback()
        raise SamePasswordError(
            "New password must be different from your current password."
        )

    identity.password_hash = security.hash_password(new_password)

    active_tokens = await db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked.is_(False),
        )
    )

    for token in active_tokens:
        token.revoked = True

    await db.commit()

    # TODO: real email provider. Dev-only logging
    print(f"[DEV] Password reset successful for {email}. All sessions revoked.")
