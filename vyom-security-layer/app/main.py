from contextlib import asynccontextmanager
from uuid import uuid4
import base64
import binascii
import logging
import time
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from .audit import record_event
from .authorization import Permission, can, require_permission
from .config import Settings
from .database import Base, make_engine, make_session_factory
from .dependencies import get_current_user, get_db
from .gst_rules import GSTRuleRejected, evaluate_gst
from .ingestion import UploadRejected, validate_upload
from .llm_boundary import LLMBoundaryRejected, validate_llm_boundary
from .models import AuditEvent, Invoice, User, utcnow
from .schemas import (AuditEventResponse, GSTEvaluationRequest, GSTEvaluationResponse, HealthResponse,
                      InvoiceCreate, InvoiceResponse, InvoiceUpdate, LLMValidationRequest,
                      LLMValidationResponse, LoginRequest, PipelineValidationRequest,
                      PipelineValidationResponse, TokenResponse, UploadValidationRequest,
                      UploadValidationResponse)
from .security import create_access_token, verify_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _rate_limit_key(request: Request, email: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{email.lower()}"


def _is_login_rate_limited(request: Request, email: str, settings: Settings) -> bool:
    attempts: dict[str, list[float]] = request.app.state.login_attempts
    now = time.monotonic()
    key = _rate_limit_key(request, email)
    window_start = now - settings.login_rate_limit_window_seconds
    recent = [stamp for stamp in attempts.get(key, []) if stamp >= window_start]
    attempts[key] = recent
    return len(recent) >= settings.login_rate_limit_attempts


def _record_failed_login(request: Request, email: str) -> None:
    attempts: dict[str, list[float]] = request.app.state.login_attempts
    attempts.setdefault(_rate_limit_key(request, email), []).append(time.monotonic())


def _clear_failed_logins(request: Request, email: str) -> None:
    request.app.state.login_attempts.pop(_rate_limit_key(request, email), None)


def _decode_upload_content(content_base64: str) -> bytes:
    try:
        return base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid base64 upload content") from exc

def create_app(settings: Settings | None = None, *, database_url: str | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    engine = make_engine(database_url or settings.database_url)
    session_factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(bind=engine)
        yield
        engine.dispose()

    app = FastAPI(title="VYOM+ Security Layer Prototype", version="0.1.0",
                  description="Standalone prototype; not integrated with the VYOM+ application.",
                  debug=settings.debug, lifespan=lifespan)
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.login_attempts = {}

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled request error", extra={"request_id": getattr(request.state, "request_id", "unknown")})
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": getattr(request.state, "request_id", "unknown")},
            headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")},
        )

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", "")[:64] or str(uuid4())
        request.state.request_id = request_id
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > settings.max_request_bytes:
                    return Response('{"detail":"Request body too large"}', status_code=413,
                                    media_type="application/json", headers={"X-Request-ID": request_id})
            except ValueError:
                return Response('{"detail":"Invalid Content-Length"}', status_code=400,
                                media_type="application/json", headers={"X-Request-ID": request_id})
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    # CORS is disabled unless explicit origins are configured by the deployment.
    # For production, configure a trusted reverse proxy and TLS as well.
    import os
    origins = [x.strip() for x in os.getenv("VYOM_ALLOWED_ORIGINS", "").split(",") if x.strip()]
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                           allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type", "X-Request-ID"])

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    def health():
        return {"status": "ok"}

    @app.post("/auth/token", response_model=TokenResponse, tags=["authentication"])
    def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
        email = str(payload.email).lower()
        if _is_login_rate_limited(request, email, settings):
            record_event(db, actor_id=None, organization_id=None, action="auth.login",
                resource_type="user", resource_id=None, outcome="denied",
                reason_code="rate_limited", request_id=request.state.request_id)
            raise HTTPException(status_code=429, detail="Too many failed login attempts")
        user = db.scalar(select(User).where(User.email == email))
        if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
            _record_failed_login(request, email)
            record_event(db, actor_id=user.id if user else None,
                organization_id=user.organization_id if user else None, action="auth.login",
                resource_type="user", resource_id=str(user.id) if user else None,
                outcome="denied", reason_code="invalid_credentials", request_id=request.state.request_id)
            raise HTTPException(status_code=401, detail="Invalid email or password")
        _clear_failed_logins(request, email)
        token = create_access_token(user, settings)
        record_event(db, actor_id=user.id, organization_id=user.organization_id, action="auth.login",
            resource_type="user", resource_id=str(user.id), outcome="success", request_id=request.state.request_id)
        return {"access_token": token, "token_type": "bearer", "expires_in": settings.access_token_minutes * 60}

    @app.get("/me", tags=["identity"])
    def me(user: User = Depends(get_current_user)):
        return {"id": user.id, "email": user.email, "organization_id": user.organization_id, "role": user.role}

    @app.post("/invoices", response_model=InvoiceResponse, status_code=201, tags=["invoices"])
    def create_invoice(payload: InvoiceCreate, request: Request,
        user: User = Depends(require_permission(Permission.CREATE_INVOICE)), db: Session = Depends(get_db)):
        invoice = Invoice(organization_id=user.organization_id, invoice_number=payload.invoice_number,
            supplier_gstin=payload.supplier_gstin, taxable_value=payload.taxable_value,
            description=payload.description, created_by=user.id)
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        record_event(db, actor_id=user.id, organization_id=user.organization_id, action="invoice.create",
            resource_type="invoice", resource_id=str(invoice.id), outcome="success", request_id=request.state.request_id)
        return invoice

    @app.get("/invoices", response_model=list[InvoiceResponse], tags=["invoices"])
    def list_invoices(request: Request, user: User = Depends(require_permission(Permission.READ_INVOICE)), db: Session = Depends(get_db)):
        rows = db.scalars(select(Invoice).where(Invoice.organization_id == user.organization_id,
                                                Invoice.deleted_at.is_(None))
                          .order_by(Invoice.id).limit(500)).all()
        record_event(db, actor_id=user.id, organization_id=user.organization_id, action="invoice.list",
            resource_type="invoice_collection", resource_id=None, outcome="success", request_id=request.state.request_id)
        return rows

    @app.get("/invoices/{invoice_id}", response_model=InvoiceResponse, tags=["invoices"])
    def get_invoice(invoice_id: int, request: Request,
        user: User = Depends(require_permission(Permission.READ_INVOICE)), db: Session = Depends(get_db)):
        # Scope is part of the database query, not a post-fetch client-side check.
        invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id,
                                  Invoice.organization_id == user.organization_id,
                                  Invoice.deleted_at.is_(None)))
        if invoice is None:
            record_event(db, actor_id=user.id, organization_id=user.organization_id, action="invoice.read",
                resource_type="invoice", resource_id=str(invoice_id), outcome="denied",
                reason_code="not_found_or_out_of_scope", request_id=request.state.request_id)
            raise HTTPException(status_code=404, detail="Invoice not found")
        record_event(db, actor_id=user.id, organization_id=user.organization_id, action="invoice.read",
            resource_type="invoice", resource_id=str(invoice.id), outcome="success", request_id=request.state.request_id)
        return invoice

    @app.patch("/invoices/{invoice_id}", response_model=InvoiceResponse, tags=["invoices"])
    def update_invoice(invoice_id: int, payload: InvoiceUpdate, request: Request,
        user: User = Depends(require_permission(Permission.UPDATE_INVOICE)), db: Session = Depends(get_db)):
        invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id,
                                  Invoice.organization_id == user.organization_id,
                                  Invoice.deleted_at.is_(None)))
        if invoice is None:
            record_event(db, actor_id=user.id, organization_id=user.organization_id, action="invoice.update",
                resource_type="invoice", resource_id=str(invoice_id), outcome="denied",
                reason_code="not_found_or_out_of_scope", request_id=request.state.request_id)
            raise HTTPException(status_code=404, detail="Invoice not found")
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            raise HTTPException(status_code=400, detail="No invoice fields supplied")
        for field, value in changes.items():
            setattr(invoice, field, value)
        db.commit()
        db.refresh(invoice)
        record_event(db, actor_id=user.id, organization_id=user.organization_id, action="invoice.update",
            resource_type="invoice", resource_id=str(invoice.id), outcome="success", request_id=request.state.request_id)
        return invoice

    @app.delete("/invoices/{invoice_id}", status_code=204, tags=["invoices"])
    def delete_invoice(invoice_id: int, request: Request,
        user: User = Depends(require_permission(Permission.DELETE_INVOICE)), db: Session = Depends(get_db)):
        invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id,
                                  Invoice.organization_id == user.organization_id,
                                  Invoice.deleted_at.is_(None)))
        if invoice is None:
            record_event(db, actor_id=user.id, organization_id=user.organization_id, action="invoice.delete",
                resource_type="invoice", resource_id=str(invoice_id), outcome="denied",
                reason_code="not_found_or_out_of_scope", request_id=request.state.request_id)
            raise HTTPException(status_code=404, detail="Invoice not found")
        invoice.deleted_at = utcnow()
        db.commit()
        record_event(db, actor_id=user.id, organization_id=user.organization_id, action="invoice.delete",
            resource_type="invoice", resource_id=str(invoice.id), outcome="success", request_id=request.state.request_id)
        return Response(status_code=204)

    @app.post("/uploads/validate", response_model=UploadValidationResponse, tags=["ingestion"])
    def validate_upload_endpoint(payload: UploadValidationRequest, request: Request,
        user: User = Depends(require_permission(Permission.VALIDATE_UPLOAD)), db: Session = Depends(get_db)):
        content = _decode_upload_content(payload.content_base64)
        try:
            result = validate_upload(payload.filename, content)
        except UploadRejected as exc:
            record_event(db, actor_id=user.id, organization_id=user.organization_id, action="upload.validate",
                resource_type="upload", resource_id=payload.filename, outcome="denied",
                reason_code=str(exc), request_id=request.state.request_id)
            raise HTTPException(status_code=400, detail={"reason": str(exc), "diagnostics": exc.diagnostics}) from exc
        record_event(db, actor_id=user.id, organization_id=user.organization_id, action="upload.validate",
            resource_type="upload", resource_id=payload.filename, outcome="success", request_id=request.state.request_id)
        return result

    @app.post("/llm/validate-classification", response_model=LLMValidationResponse, tags=["llm-boundary"])
    def validate_llm_classification_endpoint(payload: LLMValidationRequest, request: Request,
        user: User = Depends(require_permission(Permission.RUN_CLASSIFICATION)), db: Session = Depends(get_db)):
        try:
            result = validate_llm_boundary(payload.transaction_text, payload.model_output)
        except LLMBoundaryRejected as exc:
            record_event(db, actor_id=user.id, organization_id=user.organization_id, action="llm.validate_output",
                resource_type="classification", resource_id=None, outcome="denied",
                reason_code=str(exc), request_id=request.state.request_id)
            raise HTTPException(status_code=400, detail=f"LLM boundary rejected: {exc}") from exc
        record_event(db, actor_id=user.id, organization_id=user.organization_id, action="llm.validate_output",
            resource_type="classification", resource_id=result.voucher_type, outcome="success", request_id=request.state.request_id)
        return {**result.model_dump(), "accepted": True}

    @app.post("/gst/evaluate", response_model=GSTEvaluationResponse, tags=["gst"])
    def evaluate_gst_endpoint(payload: GSTEvaluationRequest, request: Request,
        user: User = Depends(require_permission(Permission.EVALUATE_GST)), db: Session = Depends(get_db)):
        try:
            result = evaluate_gst(payload.taxable_value, payload.rate_percent, payload.supply_type)
        except GSTRuleRejected as exc:
            record_event(db, actor_id=user.id, organization_id=user.organization_id, action="gst.evaluate",
                resource_type="gst_rule", resource_id=None, outcome="denied",
                reason_code=str(exc), request_id=request.state.request_id)
            raise HTTPException(status_code=400, detail=f"GST rule rejected: {exc}") from exc
        record_event(db, actor_id=user.id, organization_id=user.organization_id, action="gst.evaluate",
            resource_type="gst_rule", resource_id=result["rule_version"], outcome="success", request_id=request.state.request_id)
        return result

    @app.post("/pipeline/validate", response_model=PipelineValidationResponse, tags=["pipeline"])
    def validate_pipeline(payload: PipelineValidationRequest, request: Request,
        user: User = Depends(require_permission(Permission.RUN_CLASSIFICATION)), db: Session = Depends(get_db)):
        if not (can(user, Permission.VALIDATE_UPLOAD) and can(user, Permission.EVALUATE_GST)):
            record_event(db, actor_id=user.id, organization_id=user.organization_id, action="authorization.denied",
                resource_type="permission", resource_id="pipeline:validate", outcome="denied",
                reason_code="insufficient_permission", request_id=request.state.request_id)
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        try:
            upload_result = validate_upload(payload.upload.filename, _decode_upload_content(payload.upload.content_base64))
            classification = validate_llm_boundary(payload.llm.transaction_text, payload.llm.model_output)
            gst_result = evaluate_gst(payload.gst.taxable_value, payload.gst.rate_percent, payload.gst.supply_type)
        except (UploadRejected, LLMBoundaryRejected, GSTRuleRejected) as exc:
            record_event(db, actor_id=user.id, organization_id=user.organization_id, action="pipeline.validate",
                resource_type="pipeline", resource_id=payload.upload.filename, outcome="denied",
                reason_code=str(exc), request_id=request.state.request_id)
            diagnostics = exc.diagnostics if isinstance(exc, UploadRejected) else {}
            raise HTTPException(status_code=400, detail={"reason": str(exc), "diagnostics": diagnostics}) from exc
        record_event(db, actor_id=user.id, organization_id=user.organization_id, action="pipeline.validate",
            resource_type="pipeline", resource_id=payload.upload.filename, outcome="success", request_id=request.state.request_id)
        return {
            "upload": upload_result,
            "classification": {**classification.model_dump(), "accepted": True},
            "gst": gst_result,
            "organization_id": user.organization_id,
            "request_id": request.state.request_id,
        }

    @app.get("/audit/events", response_model=list[AuditEventResponse], tags=["audit"])
    def list_audit_events(user: User = Depends(require_permission(Permission.VIEW_AUDIT)), db: Session = Depends(get_db)):
        rows = db.scalars(select(AuditEvent).where(AuditEvent.organization_id == user.organization_id)
                          .order_by(AuditEvent.id.desc()).limit(200)).all()
        return [{"event_id": r.id, "timestamp": r.timestamp.isoformat(), "actor_id": r.actor_id,
                 "organization_id": r.organization_id, "action": r.action, "resource_type": r.resource_type,
                 "resource_id": r.resource_id, "outcome": r.outcome, "reason_code": r.reason_code,
                 "request_id": r.request_id} for r in rows]

    return app

app = create_app()
