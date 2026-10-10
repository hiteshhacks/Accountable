from datetime import datetime, timedelta, timezone
import jwt
from jwt import InvalidTokenError
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from .config import Settings
from .models import User

password_hash = PasswordHasher()
ALLOWED_ROLES = {"admin", "finance_analyst", "reviewer", "auditor"}

def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hash.verify(hashed, password)
    except (VerificationError, VerifyMismatchError, ValueError):
        return False

def create_access_token(user: User, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id), "org": user.organization_id, "role": user.role,
        "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
        "iat": now, "nbf": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

def decode_access_token(token: str, settings: Settings) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], issuer=settings.jwt_issuer,
                      audience=settings.jwt_audience,
                      options={"require": ["sub", "org", "role", "iss", "aud", "iat", "nbf", "exp"]})
