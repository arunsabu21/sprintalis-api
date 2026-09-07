from datetime import datetime


class AppError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class EmailAlreadyRegisteredError(AppError):
    pass


class InvalidOtpError(AppError):
    pass


class OTPExpiredError(AppError):
    pass


class OTPMaxAttemptsExceededError(AppError):
    pass


class InvalidRegistrationTicketError(AppError):
    pass


class InvalidCredentialsError(AppError):
    pass


class AccountLockedError(AppError):
    def __init__(self, message: str, locked_until: datetime):
        self.locked_until = locked_until
        super().__init__(message)


class AccountDisabledError(AppError):
    pass


class AccountUsesGoogleError(AppError):
    pass


class AccountUsesPasswordError(AppError):
    pass


class InvalidGoogleTokenError(AppError):
    pass


class InvalidRefreshTokenError(AppError):
    pass


class InvalidResetTokenError(AppError):
    pass


class SamePasswordError(AppError):
    pass
