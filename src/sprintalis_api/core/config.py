from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    debug: bool = True

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5
    otp_secret_key: str

    google_client_id: str
    google_client_secret: str

    password_reset_expire_minutes: int = 15
    frontend_url: str


settings = Settings()
