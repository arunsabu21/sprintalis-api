from datetime import datetime


class AppError(Exception):
    code: str = "UNKNOWN_ERROR"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class EmailAlreadyRegisteredError(AppError):
    code = "EMAIL_ALREADY_REGISTERED"


class InvalidOtpError(AppError):
    code = "INVALID_OTP"


class OTPExpiredError(AppError):
    code = "OTP_EXPIRED"


class OTPMaxAttemptsExceededError(AppError):
    code = "OTP_MAX_ATTEMPTS_EXCEEDED"


class InvalidRegistrationTicketError(AppError):
    code = "INVALID_REGISTRATION_TICKET"


class InvalidCredentialsError(AppError):
    code = "INVALID_CREDENTIALS"


class AccountLockedError(AppError):
    code = "ACCOUNT_LOCKED"
    
    def __init__(self, message: str, locked_until: datetime):
        self.locked_until = locked_until
        super().__init__(message)


class AccountDisabledError(AppError):
    code = "ACCOUNT_DISABLED"


class AccountUsesGoogleError(AppError):
    code = "ACCOUNT_USES_GOOGLE"


class AccountUsesPasswordError(AppError):
    code = "ACCOUNT_USES_PASSWORD"


class InvalidGoogleTokenError(AppError):
    code = "INVALID_GOOGLE_TOKEN"


class InvalidRefreshTokenError(AppError):
    code = "INVALID_REFRESH_TOKEN"


class InvalidResetTokenError(AppError):
    code = "INVALID_RESET_TOKEN"


class SamePasswordError(AppError):
    code = "SAME_PASSWORD"


# Workspaces
class SlugConflictError(AppError):
    code = "SLUG_CONFLICT"


class WorkspaceNotFoundError(AppError):
    code = "WORKSPACE_NOT_FOUND"
