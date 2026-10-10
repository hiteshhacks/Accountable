import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_issuer: str = "vyom-security-layer"
    jwt_audience: str = "vyom-api"
    access_token_minutes: int = 15
    debug: bool = False
    max_request_bytes: int = 2_000_000
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    @classmethod
    def from_env(cls):
        secret = os.getenv("VYOM_JWT_SECRET", "")
        if len(secret.encode()) < 32:
            raise RuntimeError("Set VYOM_JWT_SECRET to a random value of at least 32 bytes")
        access_token_minutes = int(os.getenv("VYOM_ACCESS_TOKEN_MINUTES", "15"))
        if not 1 <= access_token_minutes <= 60:
            raise RuntimeError("VYOM_ACCESS_TOKEN_MINUTES must be between 1 and 60")
        max_request_bytes = int(os.getenv("VYOM_MAX_REQUEST_BYTES", "2000000"))
        if not 1_024 <= max_request_bytes <= 20_000_000:
            raise RuntimeError("VYOM_MAX_REQUEST_BYTES must be between 1024 and 20000000")
        login_rate_limit_attempts = int(os.getenv("VYOM_LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
        if not 1 <= login_rate_limit_attempts <= 50:
            raise RuntimeError("VYOM_LOGIN_RATE_LIMIT_ATTEMPTS must be between 1 and 50")
        login_rate_limit_window_seconds = int(os.getenv("VYOM_LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
        if not 10 <= login_rate_limit_window_seconds <= 3600:
            raise RuntimeError("VYOM_LOGIN_RATE_LIMIT_WINDOW_SECONDS must be between 10 and 3600")
        return cls(
            database_url=os.getenv("VYOM_DATABASE_URL", "sqlite:///./vyom_security.db"),
            jwt_secret=secret,
            jwt_issuer=os.getenv("VYOM_JWT_ISSUER", "vyom-security-layer"),
            jwt_audience=os.getenv("VYOM_JWT_AUDIENCE", "vyom-api"),
            access_token_minutes=access_token_minutes,
            debug=os.getenv("VYOM_DEBUG", "false").lower() == "true",
            max_request_bytes=max_request_bytes,
            login_rate_limit_attempts=login_rate_limit_attempts,
            login_rate_limit_window_seconds=login_rate_limit_window_seconds,
        )
