from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from sprintalis_api.core.database import get_db
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
)

from sprintalis_api.authentication import service
from sprintalis_api.authentication.dependencies import (
    get_current_user,
    get_client_metadata,
)
from sprintalis_api.authentication.models import User
from sprintalis_api.authentication.schemas import (
    EmailCheckRequest,
    EmailCheckResponse,
    OTPVerifyRequest,
    OTPVerifyResponse,
    RegisterRequest,
    LoginRequest,
    GoogleLoginRequest,
    RefreshRequest,
    TokenPair,
    LoginResponse,
    UserPublic,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register/request-otp", response_model=EmailCheckResponse)
async def request_otp(payload: EmailCheckRequest, db: AsyncSession = Depends(get_db)):
    try:
        await service.request_registration_otp(db, payload.email)
    except EmailAlreadyRegisteredError:
        pass

    return EmailCheckResponse()


@router.post("/register/resend-otp", response_model=EmailCheckResponse)
async def resend_otp(payload: EmailCheckRequest, db: AsyncSession = Depends(get_db)):
    await service.resend_registration_otp(db, payload.email)
    return EmailCheckResponse(
        message="If a verification is pending, a new OTP has been sent."
    )


@router.post("/register/verify-otp", response_model=OTPVerifyResponse)
async def verify_otp(payload: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    try:
        ticket = await service.verify_registration_otp(db, payload.email, payload.otp)
    except (InvalidOtpError, OTPExpiredError, OTPMaxAttemptsExceededError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)

    return OTPVerifyResponse(verified=True, registration_ticket=ticket)


@router.post(
    "/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: Request,
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    user_agent, ip_address = get_client_metadata(request)
    try:
        user, tokens = await service.register_user(
            db,
            email=payload.email,
            full_name=payload.full_name,
            password=payload.password,
            registration_ticket=payload.registration_ticket,
            user_agent=user_agent,
            ip_address=ip_address,
        )
    except InvalidRegistrationTicketError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)

    return LoginResponse(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)
):
    user_agent, ip_address = get_client_metadata(request)
    try:
        user, tokens = await service.login_with_password(
            db, payload.email, payload.password, user_agent, ip_address
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message
        )
    except AccountLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=exc.message)
    except AccountDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message)
    except AccountUsesGoogleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)

    return LoginResponse(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/google", response_model=LoginResponse)
async def google_login(
    request: Request, payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db)
):
    user_agent, ip_address = get_client_metadata(request)
    try:
        user, tokens = await service.login_with_google(
            db, payload.id_token, user_agent, ip_address
        )
    except InvalidGoogleTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message
        )
    except AccountUsesPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    except AccountDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message)

    return LoginResponse(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    request: Request, payload: RefreshRequest, db: AsyncSession = Depends(get_db)
):
    user_agent, ip_address = get_client_metadata(request)
    try:
        tokens = await service.refresh_access_token(
            db, payload.refresh_token, user_agent, ip_address
        )
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message
        )

    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await service.logout(db, payload.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await service.logout_all_sessions(db, current_user.id)


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)):
    return UserPublic.model_validate(current_user)
