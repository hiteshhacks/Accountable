"""Groq-backed narrative analysis through LangChain, with bounded retries and safe failure.

The LLM receives only aggregated, redacted context and returns an LLMAnalysis
(Pydantic, validated). It never produces authoritative numbers. Transient errors
(429, timeouts, connection failures, 5xx) are retried with exponential backoff up
to GROQ_MAX_RETRIES; schema failures get one repair attempt; everything else fails
fast. The API key is never logged or returned.
"""

import json
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, ValidationError

from vyom.gst.config import AnalysisLimits, GroqSettings
from vyom.gst.prompts import ANALYSIS_PROMPT, MODE_INSTRUCTIONS, REPAIR_PROMPT
from vyom.gst.schemas import LLMAnalysis


logger = logging.getLogger("vyom.gst.llm")

MAX_TEXT = 1200
MAX_ITEMS = 12
SENSITIVE_KEY = re.compile(r"gstin|name|party|supplier|customer|vendor|exporter|importer|company|organi[sz]ation|"
                           r"employee|address|bank|account|phone|email|pan|ifsc|contact|principal|processor|"
                           r"contractor|subcontractor|payer|payee|approved|authori[sz]ed|inspected|counted|adjusted",
                           re.IGNORECASE)


class LLMResult(BaseModel):
    status: str                                  # OK | UNAVAILABLE | FAILED
    analysis: Optional[LLMAnalysis] = None
    model: str
    attempts: int = 0
    error_kind: Optional[str] = None
    message: Optional[str] = None
    token_usage: Dict[str, Any] = {}


def classify_error(exc: Exception) -> Tuple[str, bool, Optional[float]]:
    """(error kind, transient?, retry-after seconds). Uses the groq SDK's typed errors when present."""
    try:
        import groq
    except ImportError:  # pragma: no cover - langchain-groq depends on groq
        groq = None
    retry_after = None
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            retry_after = float(response.headers.get("retry-after"))
        except (TypeError, ValueError, AttributeError):
            retry_after = None
    if isinstance(exc, TimeoutError) or type(exc).__name__ in ("TimeoutException", "ReadTimeout", "ConnectTimeout"):
        return "timeout", True, None
    if groq is not None:
        if isinstance(exc, groq.RateLimitError):
            return "rate_limited", True, retry_after
        if isinstance(exc, groq.APITimeoutError):
            return "timeout", True, None
        if isinstance(exc, groq.APIConnectionError):
            return "connection_error", True, None
        if isinstance(exc, (groq.AuthenticationError, groq.PermissionDeniedError)):
            return "provider_auth", False, None
        if isinstance(exc, groq.NotFoundError):
            return "model_unavailable", False, None
        if isinstance(exc, groq.InternalServerError):
            return "provider_error", True, retry_after
        if isinstance(exc, groq.BadRequestError):
            text = str(exc).lower()
            if "model" in text and any(w in text for w in ("decommission", "not exist", "not found", "not supported", "does not support")):
                return "model_unavailable", False, None
            if any(w in text for w in ("json", "schema", "tool", "validation", "parse")):
                return "structured_output_invalid", False, None
            return "provider_bad_request", False, None
        if isinstance(exc, groq.APIStatusError) and getattr(exc, "status_code", 0) in (502, 503, 504):
            return "provider_error", True, retry_after
    return "provider_error", False, None


USER_MESSAGES = {
    "not_configured": "Narrative analysis unavailable: GROQ_API_KEY is not configured.",
    "rate_limited": "Narrative analysis unavailable: the Groq rate limit was reached after bounded retries.",
    "timeout": "Narrative analysis unavailable: the Groq request timed out after bounded retries.",
    "connection_error": "Narrative analysis unavailable: could not connect to Groq.",
    "provider_error": "Narrative analysis unavailable: the Groq service returned an error.",
    "provider_auth": "Narrative analysis unavailable: Groq rejected the API key or permissions.",
    "model_unavailable": "Narrative analysis unavailable: the configured GROQ_MODEL is not available; check the "
                         "Groq models list and update GROQ_MODEL.",
    "provider_bad_request": "Narrative analysis unavailable: Groq rejected the request.",
    "structured_output_invalid": "Narrative analysis unavailable: the model's output did not match the required schema.",
    "deadline_exceeded": "Narrative analysis skipped: the analysis time budget was exhausted.",
}


def redact(record: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for key, value in record.items():
        if SENSITIVE_KEY.search(str(key)):
            out[key] = "[redacted]"
        elif isinstance(value, str):
            out[key] = value[:200]
        else:
            out[key] = value
    return out


def build_context(state: Dict[str, Any], limits: AnalysisLimits) -> str:
    """Aggregated, redacted, size-bounded JSON for the prompt. No raw workbook, no GSTINs or party names."""
    acc, gst = state.get("accounting_summary", {}), state.get("gst_summary", {})
    calcs = [{k: c[k] for k in ("name", "value", "status", "rows_included", "rows_missing")}
             for c in acc.get("calculations", []) + gst.get("calculations", [])]
    discrepancies = [{"code": d["code"], "severity": d["severity"], "status": d["status"], "message": d["message"],
                      "affected_rows": d["evidence"].get("affected_rows", len(d["source_rows"])),
                      "sample_rows": d["source_rows"][:5]}
                     for d in state.get("discrepancies", [])][:limits.llm_max_discrepancy_groups]
    classifications = {c["source_ref"]: c for c in state.get("voucher_classifications", [])}
    review_rows = []
    for t in state.get("normalized_transactions", []):
        c = classifications.get(t["source_ref"], {})
        if c.get("ambiguous") or any(t["source_ref"] in d["source_rows"] for d in state.get("discrepancies", [])
                                     if d["code"] == "TAX_ON_NON_TAX_DOCUMENT"):
            review_rows.append({"source_row": t["source_ref"], "classifier_category": c.get("category"),
                                "score_uncalibrated": c.get("score_uncalibrated"), "fields": redact(t["raw"])})
        if len(review_rows) >= 20:
            break
    context = {
        "report_status": state.get("status"),
        "rows": acc.get("transaction_count"),
        "counts_by_group": acc.get("counts_by_group"),
        "counts_by_category": acc.get("counts_by_category"),
        "base_currency": acc.get("base_currency"),
        "calculations": calcs,
        "discrepancies": discrepancies,
        "discrepancy_groups_total": len(state.get("discrepancies", [])),
        "missing_fields": [{k: m[k] for k in ("field", "required_for", "rows_missing")} for m in state.get("missing_fields", [])],
        "filing_readiness": {k: state.get("filing_readiness", {}).get(k) for k in ("level", "reasons")},
        "balance_summary_available": state.get("balance_summary", {}).get("available"),
        "classifier": state.get("classifier_info", {}),
        "rows_for_classification_review_untrusted": review_rows,
    }
    text = json.dumps(context, default=str)
    while len(text) > limits.llm_max_context_chars and (context["rows_for_classification_review_untrusted"] or context["discrepancies"]):
        if context["rows_for_classification_review_untrusted"]:
            context["rows_for_classification_review_untrusted"].pop()
        else:
            context["discrepancies"].pop()
        text = json.dumps(context, default=str)
    return text


def sanitize_analysis(analysis: LLMAnalysis, valid_codes: Set[str], valid_refs: Set[str]) -> Tuple[LLMAnalysis, List[str]]:
    """Drop references the deterministic layer does not know and bound text sizes."""
    warnings = []
    trim = lambda s: s.strip()[:MAX_TEXT]  # noqa: E731
    explanations = [e for e in analysis.discrepancy_explanations if e.code in valid_codes]
    if len(explanations) != len(analysis.discrepancy_explanations):
        warnings.append("LLM referred to unknown discrepancy codes; those explanations were dropped.")
    concerns = [c for c in analysis.possible_classification_mismatches if c.source_row in valid_refs]
    if len(concerns) != len(analysis.possible_classification_mismatches):
        warnings.append("LLM referred to unknown source rows; those classification concerns were dropped.")
    clean = LLMAnalysis(
        executive_summary=trim(analysis.executive_summary),
        accounting_observations=[trim(x) for x in analysis.accounting_observations][:MAX_ITEMS],
        gst_observations=[trim(x) for x in analysis.gst_observations][:MAX_ITEMS],
        discrepancy_explanations=[e.model_copy(update={"explanation": trim(e.explanation),
                                                       "why_it_matters": trim(e.why_it_matters)})
                                  for e in explanations][:30],
        recommended_actions=[trim(x) for x in analysis.recommended_actions][:MAX_ITEMS],
        missing_information=[trim(x) for x in analysis.missing_information][:MAX_ITEMS],
        limitations=[trim(x) for x in analysis.limitations][:MAX_ITEMS],
        possible_classification_mismatches=[c.model_copy(update={"concern": trim(c.concern)}) for c in concerns][:20],
    )
    return clean, warnings


class GstLLMService:
    def __init__(self, settings: GroqSettings, runnable: Any = None, sleep: Callable[[float], None] = time.sleep):
        self.settings = settings
        self._runnable = runnable
        self._sleep = sleep

    def _get_runnable(self):
        if self._runnable is None:
            from langchain_groq import ChatGroq
            s = self.settings
            llm = ChatGroq(model=s.model, temperature=s.temperature, max_tokens=s.max_tokens, timeout=s.timeout,
                           max_retries=0, api_key=s.api_key)
            kwargs: Dict[str, Any] = {"method": s.structured_method, "include_raw": True}
            if s.structured_method == "json_schema":
                kwargs["strict"] = True
            self._runnable = llm.with_structured_output(LLMAnalysis, **kwargs)
        return self._runnable

    def analyze(self, context_json: str, mode: str, deadline: Optional[float] = None,
                request_id: str = "") -> LLMResult:
        s = self.settings
        if self._runnable is None and not s.configured:
            return LLMResult(status="UNAVAILABLE", model=s.model, error_kind="not_configured",
                             message=USER_MESSAGES["not_configured"])
        messages = ANALYSIS_PROMPT.format_messages(mode=mode, mode_instructions=MODE_INSTRUCTIONS[mode],
                                                   context_json=context_json)
        retries_left, repairs_left, attempts = s.max_retries, 1, 0
        while True:
            if deadline is not None and time.monotonic() + min(s.timeout, 5.0) > deadline:
                return self._fail("deadline_exceeded", attempts, "UNAVAILABLE")
            attempts += 1
            started = time.monotonic()
            try:
                result = self._get_runnable().invoke(messages)
            except Exception as exc:  # classified below; never re-raised to the caller
                kind, transient, retry_after = classify_error(exc)
                logger.warning(json.dumps({"event": "llm_error", "request_id": request_id, "model": s.model,
                                           "attempt": attempts, "error_kind": kind, "error_type": type(exc).__name__}))
                if kind == "structured_output_invalid" and repairs_left:
                    repairs_left -= 1
                    messages = messages + [HumanMessage(REPAIR_PROMPT.format(problem="provider rejected the output"))]
                    continue
                if transient and retries_left > 0:
                    delay = min(s.backoff_base * (2 ** (s.max_retries - retries_left)), s.backoff_max)
                    if retry_after is not None:
                        delay = min(max(delay, retry_after), s.backoff_max)
                    retries_left -= 1
                    self._sleep(delay)
                    continue
                return self._fail(kind, attempts, "FAILED")

            parsed, raw = self._unpack(result)
            usage = getattr(raw, "usage_metadata", None) or {}
            logger.info(json.dumps({"event": "llm_call", "request_id": request_id, "model": s.model, "attempt": attempts,
                                    "duration_ms": round((time.monotonic() - started) * 1000),
                                    "token_usage": usage, "parsed": parsed is not None}))
            if parsed is not None:
                return LLMResult(status="OK", analysis=parsed, model=s.model, attempts=attempts, token_usage=dict(usage))
            if repairs_left:
                repairs_left -= 1
                messages = messages + [HumanMessage(REPAIR_PROMPT.format(problem="invalid or missing fields"))]
                continue
            return self._fail("structured_output_invalid", attempts, "FAILED")

    @staticmethod
    def _unpack(result: Any) -> Tuple[Optional[LLMAnalysis], Any]:
        raw = None
        if isinstance(result, dict) and "parsed" in result:
            raw, result = result.get("raw"), result.get("parsed")
        if isinstance(result, LLMAnalysis):
            return result, raw
        if isinstance(result, dict):
            try:
                return LLMAnalysis.model_validate(result), raw
            except ValidationError:
                return None, raw
        return None, raw

    def _fail(self, kind: str, attempts: int, status: str) -> LLMResult:
        return LLMResult(status=status, model=self.settings.model, attempts=attempts, error_kind=kind,
                         message=USER_MESSAGES.get(kind, USER_MESSAGES["provider_error"]))
