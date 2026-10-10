import re
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def validate_safe_text(value: str) -> str:
    if CONTROL_CHARS.search(value):
        raise ValueError("text contains unsupported control characters")
    return value

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class InvoiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    invoice_number: str = Field(min_length=1, max_length=100)
    supplier_gstin: str | None = Field(default=None, min_length=15, max_length=15)
    taxable_value: float = Field(ge=0, le=1_000_000_000_000)
    description: str = Field(min_length=1, max_length=500)

    @field_validator("invoice_number", "description")
    @classmethod
    def validate_text_fields(cls, value):
        return validate_safe_text(value)

    @field_validator("supplier_gstin")
    @classmethod
    def validate_gstin_shape(cls, value):
        if value is not None and not re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", value):
            raise ValueError("supplier_gstin has an invalid format")
        return value


class InvoiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    invoice_number: str | None = Field(default=None, min_length=1, max_length=100)
    supplier_gstin: str | None = Field(default=None, min_length=15, max_length=15)
    taxable_value: float | None = Field(default=None, ge=0, le=1_000_000_000_000)
    description: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("invoice_number", "description")
    @classmethod
    def validate_text_fields(cls, value):
        if value is None:
            return value
        return validate_safe_text(value)

    @field_validator("supplier_gstin")
    @classmethod
    def validate_gstin_shape(cls, value):
        if value is not None and not re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", value):
            raise ValueError("supplier_gstin has an invalid format")
        return value

class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_number: str
    supplier_gstin: str | None
    taxable_value: float
    description: str


class AuditEventResponse(BaseModel):
    event_id: int
    timestamp: datetime
    actor_id: int | None
    organization_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    outcome: str
    reason_code: str | None
    request_id: str


class HealthResponse(BaseModel):
    status: str


class UploadValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(min_length=1, max_length=180)
    content_base64: str = Field(min_length=1, max_length=2_000_000)


class UploadValidationResponse(BaseModel):
    filename: str
    extension: str
    size_bytes: int
    detected_type: str
    row_count: int | None
    warning_count: int
    diagnostics: dict | None = None


class LLMValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_text: str = Field(min_length=1, max_length=2_000)
    model_output: dict


class LLMValidationResponse(BaseModel):
    voucher_type: str
    confidence: float
    reason_code: str
    accepted: bool = True


class GSTEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    taxable_value: Decimal = Field(ge=0, le=1_000_000_000_000)
    rate_percent: Decimal = Field(ge=0, le=28)
    supply_type: str = Field(pattern="^(intra_state|inter_state)$")


class GSTEvaluationResponse(BaseModel):
    trace_id: str
    rule_version: str
    source_name: str
    source_url: str
    taxable_value: str
    rate_percent: str
    supply_type: str
    cgst: str
    sgst: str
    igst: str
    total_tax: str
    formula: str


class PipelineValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    upload: UploadValidationRequest
    llm: LLMValidationRequest
    gst: GSTEvaluationRequest


class PipelineValidationResponse(BaseModel):
    upload: UploadValidationResponse
    classification: LLMValidationResponse
    gst: GSTEvaluationResponse
    organization_id: str
    request_id: str
