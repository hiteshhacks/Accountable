"""Shared GST analysis service: one entry point for both Excel and JSON input.

Returns (GstAnalysisResponse, http_status). Input problems -> 422 with a clear
message; unexpected internal errors -> 500 with a generic message (details only in
server logs, keyed by request_id). LLM failures never fail the request: the
report falls back to deterministic results.
"""

import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from vyom.gst.config import Settings, load_settings
from vyom.gst.graph import GraphDeps, build_graph
from vyom.gst.llm import GstLLMService
from vyom.gst.report import render_error_report
from vyom.gst.rules import GstRules, load_rules
from vyom.gst.schemas import Discrepancy, GstAnalysisResponse, GstJsonRequest


logger = logging.getLogger("vyom.gst")


class GstAnalysisService:
    def __init__(self, classifier: Callable[[pd.DataFrame], List[Any]], classifier_labels: List[str],
                 settings: Optional[Settings] = None, llm: Optional[GstLLMService] = None,
                 rules: Optional[GstRules] = None):
        self.settings = settings or load_settings()
        self.rules = rules or load_rules(self.settings.rules_path)
        self.llm = llm or GstLLMService(self.settings.groq)
        self.deps = GraphDeps(classifier=classifier, classifier_labels=list(classifier_labels), llm=self.llm,
                              rules=self.rules, limits=self.settings.limits)
        self.graph = build_graph(self.deps)

    def analyze_json(self, request: GstJsonRequest, request_id: Optional[str] = None) -> Tuple[GstAnalysisResponse, int]:
        payload = {"records": request.records, "json_string": request.json_string}
        return self._run("json", payload, request.business_gstin, request_id, period=request.period)

    def analyze_workbook(self, content: bytes, filename: str, business_gstin: Optional[str] = None,
                         request_id: Optional[str] = None) -> Tuple[GstAnalysisResponse, int]:
        return self._run("excel", {"content": content, "filename": filename}, business_gstin, request_id)

    @staticmethod
    def _row_summaries(final: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Per-row classification, the GST fields used, and every finding touching the row (for UI tables)."""
        features = {f["ref"]: f for f in final.get("features", [])}
        findings = final.get("row_findings", {})
        rows = []
        for c in final["voucher_classifications"]:
            f = features.get(c["source_ref"], {})
            text = lambda v: None if v is None else str(v)  # noqa: E731
            gstin = f.get("supplier_gstin") if f.get("group") in ("inward", "debit_notes", "expenses") else f.get("recipient_gstin")
            rows.append({
                **{k: c[k] for k in ("source_ref", "category", "score_uncalibrated", "ambiguous", "review_flags")},
                "group": f.get("group"),
                "invoice_number": f.get("invoice_number"), "invoice_date": f.get("invoice_date"),
                "party": f.get("party_name"), "counterparty_gstin": gstin,
                "taxable_value": text(f.get("taxable")), "tax": text(f.get("tax")),
                "currency": f.get("currency"),
                "findings": findings.get(c["source_ref"], []),
            })
        return rows

    def _run(self, input_type: str, payload: Dict[str, Any], business_gstin: Optional[str],
             request_id: Optional[str], period: Optional[str] = None) -> Tuple[GstAnalysisResponse, int]:
        request_id = request_id or uuid.uuid4().hex
        started = time.monotonic()
        state = {"request_id": request_id, "input_type": input_type, "input": payload,
                 "business_gstin": (business_gstin or None) and business_gstin.strip(),
                 "deadline": started + self.settings.limits.analysis_deadline_seconds,
                 "warnings": [], "errors": [], "stage_log": []}
        try:
            final = self.graph.invoke(state)
        except Exception as exc:
            logger.exception(json.dumps({"event": "analysis_failed", "request_id": request_id,
                                         "error_type": type(exc).__name__}))
            message = "Internal error while analysing the input. Quote the request_id when reporting it."
            return GstAnalysisResponse(success=False, report=render_error_report(request_id, [message]),
                                       status="PROCESSING_FAILED", warnings=[], summary={}, discrepancies=[],
                                       request_id=request_id, errors=[message]), 500
        duration = round((time.monotonic() - started) * 1000)
        meta = final.get("llm_meta") or {}
        logger.info(json.dumps({"event": "analysis_done", "request_id": request_id, "input_type": input_type,
                                "status": final.get("status"), "duration_ms": duration, "model": meta.get("model"),
                                "llm_status": meta.get("status"), "token_usage": meta.get("token_usage")}))
        if final.get("errors"):
            return GstAnalysisResponse(success=False, report=final["report_markdown"], status="PROCESSING_FAILED",
                                       warnings=final.get("warnings", []), summary={}, discrepancies=[],
                                       request_id=request_id, errors=final["errors"]), 422
        summary = {
            "period": period,
            "accounting_summary": final["accounting_summary"],
            "gst_summary": final["gst_summary"],
            "filing_preparation": final["filing_preparation"],
            "filing_readiness": final["filing_readiness"],
            "balance_summary": final["balance_summary"],
            "missing_fields": final["missing_fields"],
            "calculation_checks": final["calculation_checks"],
            "classification": {**final["classifier_info"], "rows": self._row_summaries(final)},
            "narrative": {"available": final.get("llm_analysis") is not None, **{k: meta.get(k) for k in
                          ("status", "model", "attempts", "error_kind", "message")}},
            "assumptions": final["assumptions"],
            "rules": self.rules.public(),
            "stages": final.get("stage_log", []),
            "duration_ms": duration,
        }
        return GstAnalysisResponse(success=True, report=final["report_markdown"], status=final["status"],
                                   warnings=final.get("warnings", []), summary=summary,
                                   discrepancies=[Discrepancy(**d) for d in final["discrepancies"]],
                                   request_id=request_id), 200
