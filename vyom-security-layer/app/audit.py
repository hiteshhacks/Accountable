from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .models import AuditEvent

def record_event(db: Session, *, actor_id: int | None, organization_id: str | None,
                 action: str, resource_type: str, resource_id: str | None,
                 outcome: str, request_id: str, reason_code: str | None = None) -> None:
    """Store a minimal event. Never pass passwords, tokens, or complete ledger rows."""
    db.add(AuditEvent(timestamp=datetime.now(timezone.utc), actor_id=actor_id,
        organization_id=organization_id, action=action, resource_type=resource_type,
        resource_id=resource_id, outcome=outcome, reason_code=reason_code, request_id=request_id))
    db.commit()
