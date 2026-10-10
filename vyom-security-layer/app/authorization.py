from enum import StrEnum
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .audit import record_event
from .dependencies import get_current_user, get_db
from .models import User


class Permission(StrEnum):
    READ_INVOICE = "invoice:read"
    CREATE_INVOICE = "invoice:create"
    UPDATE_INVOICE = "invoice:update"
    DELETE_INVOICE = "invoice:delete"
    VIEW_AUDIT = "audit:view"
    VALIDATE_UPLOAD = "upload:validate"
    RUN_CLASSIFICATION = "classification:run"
    EVALUATE_GST = "gst:evaluate"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "admin": frozenset(Permission),
    "finance_analyst": frozenset({
        Permission.READ_INVOICE,
        Permission.CREATE_INVOICE,
        Permission.UPDATE_INVOICE,
        Permission.VALIDATE_UPLOAD,
        Permission.RUN_CLASSIFICATION,
        Permission.EVALUATE_GST,
    }),
    "reviewer": frozenset({
        Permission.READ_INVOICE,
        Permission.VIEW_AUDIT,
        Permission.RUN_CLASSIFICATION,
        Permission.EVALUATE_GST,
    }),
    "auditor": frozenset({
        Permission.READ_INVOICE,
        Permission.VIEW_AUDIT,
    }),
}


def can(user: User, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, frozenset())


def require_permission(permission: Permission):
    def dependency(
        request: Request,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if can(user, permission):
            return user
        record_event(
            db,
            actor_id=user.id,
            organization_id=user.organization_id,
            action="authorization.denied",
            resource_type="permission",
            resource_id=permission.value,
            outcome="denied",
            reason_code="insufficient_permission",
            request_id=getattr(request.state, "request_id", "unknown"),
        )
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return dependency
