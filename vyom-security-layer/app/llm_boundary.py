from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


PROMPT_INJECTION_PATTERNS = (
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "developer message",
    "reveal your instructions",
    "exfiltrate",
    "tool call",
    "run shell",
    "delete database",
)

ALLOWED_VOUCHER_TYPES = {
    "sales",
    "purchase",
    "payment",
    "receipt",
    "journal",
    "contra",
    "credit_note",
    "debit_note",
}


class LLMBoundaryRejected(ValueError):
    pass


class LLMClassificationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    voucher_type: str = Field(min_length=1, max_length=40)
    confidence: float = Field(ge=0, le=1)
    reason_code: str = Field(min_length=1, max_length=80)

    @field_validator("voucher_type")
    @classmethod
    def voucher_type_allowed(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in ALLOWED_VOUCHER_TYPES:
            raise ValueError("unsupported voucher_type")
        return normalized


def detect_prompt_injection(text: str) -> list[str]:
    lowered = text.lower()
    return [pattern for pattern in PROMPT_INJECTION_PATTERNS if pattern in lowered]


def validate_llm_boundary(transaction_text: str, model_output: dict) -> LLMClassificationOutput:
    if len(transaction_text) > 2_000:
        raise LLMBoundaryRejected("transaction_text_too_long")
    matches = detect_prompt_injection(transaction_text)
    if matches:
        raise LLMBoundaryRejected("prompt_injection_detected")
    try:
        return LLMClassificationOutput.model_validate(model_output)
    except ValidationError as exc:
        raise LLMBoundaryRejected("malformed_model_output") from exc
