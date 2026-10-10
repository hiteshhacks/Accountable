"""LangGraph orchestration of the GST analysis workflow.

START -> validate_input -> normalize_input -> classify_vouchers -> extract_features
      -> calculate_accounting -> validate_gst -> check_evidence
      -> (sufficient) generate_analysis | (review) generate_review_analysis
      -> (llm ok) format_report | (llm failed) deterministic_fallback -> format_report -> END
Invalid input at validation or normalisation -> validation_error -> END.

Each node is a small function of the state, testable on its own. Dependencies
(classifier, LLM service, rules, limits) are injected through GraphDeps.
"""

from dataclasses import dataclass, field
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph

from vyom.gst import accounting, normalize, validation
from vyom.gst.config import AnalysisLimits
from vyom.gst.llm import GstLLMService, build_context, sanitize_analysis
from vyom.gst.report import render_error_report, render_report
from vyom.gst.rules import TAXONOMY, GstRules
from vyom.gst.schemas import Discrepancy, NormalizedTransaction, VoucherClassification


logger = logging.getLogger("vyom.gst")


class GstState(TypedDict, total=False):
    request_id: str
    input_type: str                       # "json" | "excel"
    input: Dict[str, Any]                 # raw payload; content bytes are dropped after normalisation
    business_gstin: Optional[str]
    deadline: float
    normalized_transactions: List[Dict[str, Any]]
    voucher_classifications: List[Dict[str, Any]]
    classifier_info: Dict[str, Any]
    features: List[Dict[str, Any]]
    accounting_summary: Dict[str, Any]
    gst_summary: Dict[str, Any]
    filing_preparation: Dict[str, Any]
    balance_summary: Dict[str, Any]
    discrepancies: List[Dict[str, Any]]
    missing_fields: List[Dict[str, Any]]
    calculation_checks: List[Dict[str, Any]]
    filing_readiness: Dict[str, Any]
    route: str                            # "sufficient" | "review"
    status: str
    llm_analysis: Optional[Dict[str, Any]]
    llm_meta: Dict[str, Any]
    report_markdown: str
    assumptions: List[str]
    stage_log: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]


@dataclass
class GraphDeps:
    classifier: Callable[[pd.DataFrame], List[Any]]
    classifier_labels: List[str]
    llm: GstLLMService
    rules: GstRules = field(default_factory=GstRules)
    limits: AnalysisLimits = field(default_factory=AnalysisLimits)


def _stage(name: str, fn: Callable[[GstState], Dict[str, Any]]):
    """Wrap a node: time it and log stage status (never payloads)."""
    def run(state: GstState) -> Dict[str, Any]:
        started = time.monotonic()
        update = fn(state)
        duration = round((time.monotonic() - started) * 1000)
        status = "error" if update.get("errors") else "ok"
        logger.info(json.dumps({"event": "stage", "request_id": state.get("request_id"), "stage": name,
                                "status": status, "duration_ms": duration}))
        update["stage_log"] = state.get("stage_log", []) + [{"stage": name, "status": status, "duration_ms": duration}]
        return update
    return run


# ==========================================
# NODES
# ==========================================

def validate_input(state: GstState) -> Dict[str, Any]:
    payload, errors = state.get("input") or {}, []
    kind = state.get("input_type")
    if kind == "json":
        has_records, has_string = payload.get("records") is not None, payload.get("json_string") is not None
        if has_records == has_string:
            errors.append("Provide exactly one of `records` or `json_string`.")
    elif kind == "excel":
        if not payload.get("content"):
            errors.append("The uploaded file is empty.")
    else:
        errors.append("Unsupported input type.")
    gstin = state.get("business_gstin")
    if gstin is not None and not isinstance(gstin, str):
        errors.append("`business_gstin` must be a string.")
    return {"errors": errors, "warnings": state.get("warnings", [])}


def make_normalize(deps: GraphDeps):
    def normalize_input(state: GstState) -> Dict[str, Any]:
        payload = state["input"]
        try:
            if state["input_type"] == "json":
                records = payload.get("records")
                if records is None:
                    records = normalize.parse_json_string(payload["json_string"], deps.limits)
                rows, warnings = normalize.normalize_records(records, deps.limits)
            else:
                rows, warnings = normalize.normalize_workbook(payload["content"], payload.get("filename") or "",
                                                              deps.limits)
        except normalize.InputValidationError as exc:
            return {"errors": [str(exc)], "input": {}}
        parse_issues = sum(len(t.parse_warnings) for t in rows)
        if parse_issues:
            warnings.append(f"{parse_issues} cell values could not be parsed and were ignored; see row parse warnings.")
        return {"normalized_transactions": [t.model_dump() for t in rows], "input": {},
                "warnings": state.get("warnings", []) + warnings}
    return normalize_input


def make_classify(deps: GraphDeps):
    def classify_vouchers(state: GstState) -> Dict[str, Any]:
        rows = state["normalized_transactions"]
        predictions = deps.classifier(pd.DataFrame([r["raw"] for r in rows]))
        out = []
        rules = deps.rules
        for row, pred in zip(rows, predictions):
            top = [{"label": s.label, "score_uncalibrated": s.score_uncalibrated} for s in pred.top_predictions]
            score = top[0]["score_uncalibrated"] if top else None
            margin = (top[0]["score_uncalibrated"] - top[1]["score_uncalibrated"]) if len(top) > 1 else None
            ambiguous = (score is not None and score < rules.ambiguous_score_threshold) or \
                        (margin is not None and margin < rules.ambiguous_margin_threshold)
            flags = []
            if ambiguous:
                flags.append("AMBIGUOUS_SCORE")
            if pred.predicted_voucher_category not in TAXONOMY:
                flags.append("OUTSIDE_TAXONOMY")
            out.append(VoucherClassification(source_ref=row["source_ref"], category=pred.predicted_voucher_category,
                                             score_uncalibrated=score, top_predictions=top, ambiguous=ambiguous,
                                             review_flags=flags).model_dump())
        info = {"labels_supported": len(deps.classifier_labels),
                "taxonomy_categories_not_predictable": sorted(set(TAXONOMY) - set(deps.classifier_labels)),
                "ambiguous_rows": sum(1 for c in out if c["ambiguous"]),
                "scores": "uncalibrated class probabilities, not confidence"}
        return {"voucher_classifications": out, "classifier_info": info}
    return classify_vouchers


def make_extract(deps: GraphDeps):
    def extract_features(state: GstState) -> Dict[str, Any]:
        tx = [NormalizedTransaction(**t) for t in state["normalized_transactions"]]
        cl = [VoucherClassification(**c) for c in state["voucher_classifications"]]
        return {"features": accounting.extract_features(tx, cl, deps.rules, state.get("business_gstin"))}
    return extract_features


def make_calculate(deps: GraphDeps):
    def calculate_accounting(state: GstState) -> Dict[str, Any]:
        result = accounting.calculate(state["features"], deps.rules)
        checks = []
        for section in ("accounting_summary", "gst_summary"):
            for c in result[section]["calculations"]:
                checks.append({"name": c["name"], "status": c["status"], "rows_included": c["rows_included"],
                               "rows_missing": c["rows_missing"]})
        for ledger in result["balance_summary"].get("ledgers", []):
            checks.append({"name": f"ledger_balance:{ledger['ledger']}", "status":
                           "COMPLETE" if ledger["reconciles"] else ("UNRESOLVED" if ledger["reconciles"] is None else "INCOMPLETE"),
                           "rows_included": len(ledger["source_refs"]), "rows_missing": 0})
        return {**result, "calculation_checks": checks, "assumptions": list(deps.rules.assumptions)}
    return calculate_accounting


def make_validate(deps: GraphDeps):
    def validate_gst(state: GstState) -> Dict[str, Any]:
        found, missing = validation.run_checks(state["features"], deps.rules, state.get("business_gstin"))
        for ledger in state.get("balance_summary", {}).get("ledgers", []):
            if ledger["reconciles"] is False:
                found.append(Discrepancy(
                    code="LEDGER_BALANCE_UNRECONCILED", severity="MEDIUM", status="POSSIBLE",
                    message="Opening + debits - credits does not equal the reported closing balance for a ledger.",
                    source_rows=ledger["source_refs"], evidence={"ledger": ledger["ledger"],
                    "closing_reported": ledger["closing_reported"], "closing_computed": ledger["closing_computed_debit_positive"]},
                    recommended_action="Check the ledger's sign convention and missing entries."))
        return {"discrepancies": [d.model_dump() for d in found], "missing_fields": missing}
    return validate_gst


def check_evidence(state: GstState) -> Dict[str, Any]:
    discrepancies = [Discrepancy(**d) for d in state["discrepancies"]]
    route, status, reasons = validation.evidence_route(state["features"], discrepancies,
                                                       state["gst_summary"]["calculations"])
    return {"route": route, "status": status, "filing_readiness": validation.filing_readiness(status, discrepancies, reasons)}


def make_llm_node(deps: GraphDeps, mode: str):
    def generate(state: GstState) -> Dict[str, Any]:
        context = build_context(state, deps.limits)
        result = deps.llm.analyze(context, mode, deadline=state.get("deadline"), request_id=state.get("request_id", ""))
        meta = {"status": result.status, "model": result.model, "attempts": result.attempts,
                "error_kind": result.error_kind, "message": result.message, "token_usage": result.token_usage}
        if result.status != "OK":
            return {"llm_analysis": None, "llm_meta": meta}
        codes = {d["code"] for d in state["discrepancies"]}
        refs = {t["source_ref"] for t in state["normalized_transactions"]}
        clean, warnings = sanitize_analysis(result.analysis, codes, refs)
        update: Dict[str, Any] = {"llm_analysis": clean.model_dump(), "llm_meta": meta,
                                  "warnings": state.get("warnings", []) + warnings}
        if clean.possible_classification_mismatches:
            # The LLM never relabels: its concerns become POSSIBLE discrepancies for human review.
            concern = Discrepancy(
                code="LLM_CLASSIFICATION_CONCERN", severity="MEDIUM", status="POSSIBLE", origin="llm",
                message="The narrative model flagged rows whose classifier category may not fit the data.",
                source_rows=[c.source_row for c in clean.possible_classification_mismatches],
                evidence={"affected_rows": len(clean.possible_classification_mismatches),
                          "samples": [c.model_dump() for c in clean.possible_classification_mismatches[:10]]},
                recommended_action="Review these rows' voucher type; the classifier category was not changed.")
            update["discrepancies"] = state["discrepancies"] + [concern.model_dump()]
            if state["status"] == "ANALYSIS_COMPLETE":
                update["status"] = "REVIEW_REQUIRED"
                readiness = dict(state["filing_readiness"])
                readiness["level"] = "REVIEW_REQUIRED"
                readiness["reasons"] = readiness["reasons"] + ["Possible classification mismatches need review."]
                update["filing_readiness"] = readiness
        return update
    return generate


def deterministic_fallback(state: GstState) -> Dict[str, Any]:
    message = (state.get("llm_meta") or {}).get("message") or "Narrative analysis unavailable."
    warnings = state.get("warnings", [])
    note = f"{message} The report was built from deterministic results only."
    return {"llm_analysis": None, "warnings": warnings + ([note] if note not in warnings else [])}


def format_report(state: GstState) -> Dict[str, Any]:
    return {"report_markdown": render_report(state)}


def validation_error(state: GstState) -> Dict[str, Any]:
    return {"status": "PROCESSING_FAILED",
            "report_markdown": render_error_report(state.get("request_id", ""), state.get("errors", []))}


# ==========================================
# GRAPH
# ==========================================

def _ok_or_invalid(state: GstState) -> str:
    return "invalid" if state.get("errors") else "ok"


def build_graph(deps: GraphDeps):
    g = StateGraph(GstState)
    g.add_node("validate_input", _stage("validate_input", validate_input))
    g.add_node("normalize_input", _stage("normalize_input", make_normalize(deps)))
    g.add_node("classify_vouchers", _stage("classify_vouchers", make_classify(deps)))
    g.add_node("extract_features", _stage("extract_features", make_extract(deps)))
    g.add_node("calculate_accounting", _stage("calculate_accounting", make_calculate(deps)))
    g.add_node("validate_gst", _stage("validate_gst", make_validate(deps)))
    g.add_node("check_evidence", _stage("check_evidence", check_evidence))
    g.add_node("generate_analysis", _stage("generate_analysis", make_llm_node(deps, "standard")))
    g.add_node("generate_review_analysis", _stage("generate_review_analysis", make_llm_node(deps, "review")))
    g.add_node("deterministic_fallback", _stage("deterministic_fallback", deterministic_fallback))
    g.add_node("format_report", _stage("format_report", format_report))
    g.add_node("validation_error", _stage("validation_error", validation_error))

    g.add_edge(START, "validate_input")
    g.add_conditional_edges("validate_input", _ok_or_invalid, {"ok": "normalize_input", "invalid": "validation_error"})
    g.add_conditional_edges("normalize_input", _ok_or_invalid, {"ok": "classify_vouchers", "invalid": "validation_error"})
    g.add_edge("classify_vouchers", "extract_features")
    g.add_edge("extract_features", "calculate_accounting")
    g.add_edge("calculate_accounting", "validate_gst")
    g.add_edge("validate_gst", "check_evidence")
    g.add_conditional_edges("check_evidence", lambda s: s["route"],
                            {"sufficient": "generate_analysis", "review": "generate_review_analysis"})
    for node in ("generate_analysis", "generate_review_analysis"):
        g.add_conditional_edges(node, lambda s: "ok" if s.get("llm_analysis") else "fallback",
                                {"ok": "format_report", "fallback": "deterministic_fallback"})
    g.add_edge("deterministic_fallback", "format_report")
    g.add_edge("format_report", END)
    g.add_edge("validation_error", END)
    return g.compile()
