from collections.abc import Generator
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session
from .audit import record_event
from .models import User
from .security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

def get_db(request: Request) -> Generator[Session, None, None]:
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db)) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        record_event(db, actor_id=None, organization_id=None, action="auth.token",
            resource_type="access_token", resource_id=None, outcome="denied",
            reason_code="missing_bearer_token", request_id=getattr(request.state, "request_id", "unknown"))
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = decode_access_token(credentials.credentials, request.app.state.settings)
        user_id = int(claims["sub"])
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        record_event(db, actor_id=None, organization_id=None, action="auth.token",
            resource_type="access_token", resource_id=None, outcome="denied",
            reason_code="invalid_or_expired_token", request_id=getattr(request.state, "request_id", "unknown"))
        raise HTTPException(status_code=401, detail="Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        record_event(db, actor_id=user_id if "user_id" in locals() else None, organization_id=None, action="auth.token",
            resource_type="access_token", resource_id=None, outcome="denied",
            reason_code="inactive_or_unknown_user", request_id=getattr(request.state, "request_id", "unknown"))
        raise HTTPException(status_code=401, detail="Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"})
    # Re-check current database authority; tokens alone do not establish current role/scope.
    if claims.get("org") != user.organization_id or claims.get("role") != user.role:
        record_event(db, actor_id=user.id, organization_id=user.organization_id, action="auth.token",
            resource_type="access_token", resource_id=None, outcome="denied",
            reason_code="stale_authority_claims", request_id=getattr(request.state, "request_id", "unknown"))
        raise HTTPException(status_code=401, detail="Credentials are no longer valid", headers={"WWW-Authenticate": "Bearer"})
    return user

def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency
