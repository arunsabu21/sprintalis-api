from dataclasses import dataclass
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from sprintalis_api.core.config import settings
from sprintalis_api.core.exceptions import InvalidGoogleTokenError


@dataclass
class GoogleUserInfo:
    sub: str
    email: str
    email_verified: bool
    full_name: str


_google_request = google_requests.Request()


def verify_google_id_token(raw_id_token: str) -> GoogleUserInfo:
    try:
        claims = google_id_token.verify_oauth2_token(
            raw_id_token,
            _google_request,
            audience=settings.google_client_id,
        )
    except ValueError as exc:
        raise InvalidGoogleTokenError(str(exc)) from exc

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise InvalidGoogleTokenError("Invalid token issuer")

    sub = claims.get("sub")

    if not sub:
        raise InvalidGoogleTokenError("Google token did not include a subject")

    email = claims.get("email")

    if not email:
        raise InvalidGoogleTokenError("Google token did not include an email")

    if not claims.get("email_verified", False):
        raise InvalidGoogleTokenError("Google email is not verified")

    return GoogleUserInfo(
        sub=sub,
        email=email.strip().lower(),
        email_verified=True,
        full_name=claims.get("name", ""),
    )
