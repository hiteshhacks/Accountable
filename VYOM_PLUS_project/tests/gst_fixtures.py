"""Shared fixtures for GST tests: valid GSTINs, a fake classifier and a scripted fake LLM."""

from io import BytesIO
from types import SimpleNamespace
from typing import Any, List

import httpx
import pandas as pd

from vyom.gst.config import AnalysisLimits, GroqSettings, Settings
from vyom.gst.llm import GstLLMService
from vyom.gst.rules import _GSTIN_CHARS
from vyom.gst.schemas import LLMAnalysis
from vyom.gst.service import GstAnalysisService


def make_gstin(state: str, pan: str = "AAPFU0939F", entity: str = "1") -> str:
    body = f"{state}{pan}{entity}Z"
    total = 0
    for i, ch in enumerate(body):
        product = _GSTIN_CHARS.index(ch) * (1 if i % 2 == 0 else 2)
        total += product // 36 + product % 36
    return body + _GSTIN_CHARS[(36 - total % 36) % 36]


BUSINESS = make_gstin("27", "AAACB1234C")
CUSTOMER = make_gstin("27", "AABCC5678D")
SUPPLIER = make_gstin("27", "AACCS9012E")
OTHER_STATE_SUPPLIER = make_gstin("29", "AADCS3456F")


def classify_by_kind(frame: pd.DataFrame) -> List[Any]:
    """Fake classifier: reads the 'Kind' column, confident unless Kind ends with '?'."""
    out = []
    for kind in frame.get("Kind", pd.Series(["Journal"] * len(frame))).fillna("Journal"):
        weak = str(kind).endswith("?")
        label = str(kind).rstrip("?")
        top = [SimpleNamespace(label=label, score_uncalibrated=0.40 if weak else 0.95),
               SimpleNamespace(label="Journal", score_uncalibrated=0.35 if weak else 0.01)]
        out.append(SimpleNamespace(predicted_voucher_category=label, top_predictions=top))
    return out


CLASSIFIER_LABELS = ["Sales", "Purchase", "Sales Return / Credit Note", "Purchase Return / Debit Note", "Receipt",
                     "Payment", "Expense", "Journal", "Purchase Order"]


def clean_records() -> List[dict]:
    return [
        {"Kind": "Sales", "Invoice No": "S-001", "Invoice Date": "2026-09-05", "Customer": "Gamma Retail",
         "Customer GSTIN": CUSTOMER, "Taxable Value": 10000, "GST Rate": 18, "CGST": 900, "SGST": 900,
         "Invoice Value": 11800},
        {"Kind": "Purchase", "Invoice No": "P-77", "Invoice Date": "2026-09-06", "Supplier": "Beta Supplies",
         "Supplier GSTIN": SUPPLIER, "Taxable Value": 5000, "GST Rate": 18, "CGST": 450, "SGST": 450,
         "Invoice Value": 5900},
    ]


def analysis(**overrides) -> LLMAnalysis:
    data = dict(executive_summary="Two documents reviewed.", accounting_observations=["One sale, one purchase."],
                gst_observations=["Output tax exceeds potential ITC."], discrepancy_explanations=[],
                recommended_actions=["Reconcile with GSTR-2B."], missing_information=[], limitations=["Synthetic test."],
                possible_classification_mismatches=[])
    data.update(overrides)
    return LLMAnalysis(**data)


class ScriptedRunnable:
    """Returns or raises the scripted items in order; records how often it was called."""

    def __init__(self, *items):
        self.items, self.calls = list(items), 0

    def invoke(self, messages):
        self.calls += 1
        self.last_messages = messages
        item = self.items.pop(0) if self.items else self.items_last
        self.items_last = item
        if isinstance(item, Exception):
            raise item
        if isinstance(item, LLMAnalysis):
            return {"raw": SimpleNamespace(usage_metadata={"input_tokens": 10, "output_tokens": 5}),
                    "parsed": item, "parsing_error": None}
        return item


def groq_error(cls_name: str, status: int, message: str = "error", headers=None):
    import groq
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    if cls_name in ("APITimeoutError",):
        return groq.APITimeoutError(request=request)
    if cls_name == "APIConnectionError":
        return groq.APIConnectionError(request=request)
    response = httpx.Response(status, request=request, headers=headers or {})
    return getattr(groq, cls_name)(message, response=response, body=None)


def settings(api_key: str = "gsk_test_secret_value_123", **groq_overrides) -> Settings:
    from pydantic import SecretStr
    groq = GroqSettings(api_key=SecretStr(api_key) if api_key else None, backoff_base=0.0, backoff_max=0.0,
                        **groq_overrides)
    return Settings(groq=groq, limits=AnalysisLimits())


def service(runnable=None, api_key: str = "gsk_test_secret_value_123", sleeps=None, **groq_overrides) -> GstAnalysisService:
    s = settings(api_key, **groq_overrides)
    llm = GstLLMService(s.groq, runnable=runnable, sleep=(sleeps.append if sleeps is not None else (lambda _: None)))
    return GstAnalysisService(classify_by_kind, CLASSIFIER_LABELS, settings=s, llm=llm)


def workbook(**sheets) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, index=False)
    return buf.getvalue()
