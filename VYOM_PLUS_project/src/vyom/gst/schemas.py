"""Pydantic schemas shared by the GST workflow, the LLM service and the API."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


Severity = Literal["HIGH", "MEDIUM", "LOW", "INFO"]
FindingStatus = Literal["CONFIRMED", "POSSIBLE"]
CalcStatus = Literal["COMPLETE", "INCOMPLETE", "UNRESOLVED", "NOT_APPLICABLE"]
ReportStatus = Literal["ANALYSIS_COMPLETE", "REVIEW_REQUIRED", "INSUFFICIENT_DATA", "PROCESSING_FAILED"]


class NormalizedTransaction(BaseModel):
    """One source row: cleaned original columns plus canonical GST fields extracted from them."""
    source_ref: str                      # e.g. "Sales!R5" or "records[3]"
    source_sheet: Optional[str] = None
    source_row: int
    raw: Dict[str, Any]                  # cleaned original columns (label/output columns removed)
    fields: Dict[str, Any]               # canonical fields; money as Decimal strings
    parse_warnings: List[str] = Field(default_factory=list)


class VoucherClassification(BaseModel):
    source_ref: str
    category: str
    score_uncalibrated: Optional[float] = None
    top_predictions: List[Dict[str, Any]] = Field(default_factory=list)
    ambiguous: bool = False
    review_flags: List[str] = Field(default_factory=list)


class Calculation(BaseModel):
    name: str
    value: Optional[str]                 # Decimal string, or None when unresolved
    status: CalcStatus
    method: str
    inputs_used: List[str]
    currency: str
    rounding: str
    rows_included: int
    rows_missing: int = 0
    source_refs: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class Discrepancy(BaseModel):
    code: str
    severity: Severity
    message: str
    source_rows: List[str]
    evidence: Dict[str, Any]
    recommended_action: str
    status: FindingStatus
    origin: Literal["validation", "classification", "llm"] = "validation"


# ---------- LLM structured output (strict-mode compatible: every field required) ----------

class DiscrepancyExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    explanation: str
    why_it_matters: str


class ClassificationConcern(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_row: str
    classifier_category: str
    concern: str


class LLMAnalysis(BaseModel):
    """Narrative only. Authoritative numbers stay in the deterministic summaries."""
    model_config = ConfigDict(extra="forbid")
    executive_summary: str
    accounting_observations: List[str]
    gst_observations: List[str]
    discrepancy_explanations: List[DiscrepancyExplanation]
    recommended_actions: List[str]
    missing_information: List[str]
    limitations: List[str]
    possible_classification_mismatches: List[ClassificationConcern]


# ---------- API ----------

class GstJsonRequest(BaseModel):
    """JSON input: either `records` (same shape as POST /predict) or `json_string` holding that JSON."""
    records: Optional[List[Dict[str, Any]]] = None
    json_string: Optional[str] = None
    business_gstin: Optional[str] = Field(None, description="GSTIN of the business whose books these are (optional)")
    period: Optional[str] = Field(None, description="Free-text reporting period label, e.g. '2026-09'")


class GstAnalysisResponse(BaseModel):
    success: bool
    report: str
    status: ReportStatus
    warnings: List[str]
    summary: Dict[str, Any]
    discrepancies: List[Discrepancy]
    request_id: str
    errors: List[str] = Field(default_factory=list)
