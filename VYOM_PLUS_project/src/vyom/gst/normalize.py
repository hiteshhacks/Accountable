"""Shared input adapters: Excel workbooks and JSON records -> NormalizedTransaction.

Both input modes end in the same representation. Cell values are untrusted:
strings are cleaned and truncated, money is parsed with Decimal, and label or
prediction output columns are removed before anything else sees the data.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import json
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from vyom.gst.config import AnalysisLimits
from vyom.gst.schemas import NormalizedTransaction


class InputValidationError(ValueError):
    """The request cannot be analysed; message is safe to show to the user."""


# Label-bearing and prediction-output columns never reach analysis or the classifier.
DROPPED_COLUMNS = {"voucher category", "voucher_type", "document_type", "target", "correct",
                   "predicted voucher category", "model score (uncalibrated)", "top 3 (uncalibrated)",
                   "review required"}

# normalised header -> canonical field. Exact matches only, so "Unit Rate" is not "rate".
ALIASES: Dict[str, Tuple[str, ...]] = {
    "invoice_number": ("invoice number", "invoice no", "inv no", "bill no", "bill number", "document number",
                       "doc no", "voucher no", "voucher number", "invoice_number", "export invoice no",
                       "import bill no", "credit note no", "debit note no", "note number"),
    "invoice_date": ("invoice date", "document date", "bill date", "voucher date", "date", "transaction date",
                     "transaction_date", "note date"),
    "supplier_name": ("supplier", "supplier name", "vendor name", "vendor", "seller", "seller_supplier", "exporter",
                      "vendor/provider"),
    "customer_name": ("customer", "customer name", "buyer", "buyer_customer", "importer", "party", "party name"),
    "supplier_gstin": ("supplier gstin", "vendor gstin", "seller gstin", "gstin of supplier", "supplier_gstin"),
    "recipient_gstin": ("customer gstin", "recipient gstin", "buyer gstin", "gstin of recipient", "customer_gstin",
                        "recipient_gstin"),
    "party_gstin": ("gstin", "party gstin", "gst number", "gstin/uin", "gst no", "party_gstin"),
    "place_of_supply": ("place of supply", "pos", "place_of_supply"),
    "hsn_sac": ("hsn", "hsn/sac", "sac", "hsn code", "hsn_sac"),
    "taxable_value": ("taxable value", "taxable amount", "base amount", "assessable value", "taxable_value"),
    "gst_rate": ("gst rate", "tax rate", "gst %", "gst rate %", "gst_rate_percent", "gst_rate", "rate of tax"),
    "cgst": ("cgst", "cgst amount", "central tax"),
    "sgst": ("sgst", "sgst amount", "utgst", "sgst/utgst", "state tax"),
    "igst": ("igst", "igst amount", "integrated tax", "import gst"),
    "cess": ("cess", "cess amount"),
    "total_tax": ("tax amount", "gst amount", "total tax", "gst_amount", "total gst"),
    "total_amount": ("invoice value", "invoice amount", "total amount", "grand total", "total invoice value"),
    "amount": ("amount", "payment amount", "received amount", "amount claimed", "transfer amount", "total value",
               "net amount"),
    "currency": ("currency", "currency code", "payment currency", "original currency"),
    "original_invoice_ref": ("original invoice ref", "original doc ref", "original invoice", "original invoice number",
                             "original_invoice_number", "against invoice", "reference invoice"),
    "ledger": ("ledger", "ledger name", "account", "account name"),
    "opening_balance": ("opening balance", "opening_balance"),
    "closing_balance": ("closing balance", "closing_balance"),
    "debit": ("debit", "debit amount", "dr amount"),
    "credit": ("credit", "credit amount", "cr amount"),
}
MONEY_FIELDS = {"taxable_value", "cgst", "sgst", "igst", "cess", "total_tax", "total_amount", "amount",
                "opening_balance", "closing_balance", "debit", "credit"}
GSTIN_FIELDS = {"supplier_gstin", "recipient_gstin", "party_gstin"}
_ALIAS_LOOKUP = {alias: canonical for canonical, aliases in ALIASES.items() for alias in aliases}
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_header(name: Any) -> str:
    return re.sub(r"\s+", " ", str(name)).strip().lower()


def clean_value(value: Any, max_chars: int) -> Any:
    """JSON-safe, cleaned cell value; None for empty cells."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.date().isoformat() if not pd.isna(value) else None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
            return int(value)
        return float(value) if isinstance(value, Decimal) else value
    text = _CONTROL.sub("", str(value)).strip()
    if not text or text.lower() in {"nan", "none", "nat", "null"}:
        return None
    return text[:max_chars]


def parse_money(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not an amount")
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = str(value).strip()
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"(?i)inr|rs\.?|₹|,|\s|\(|\)", "", text)
    if text in ("", "-"):
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"not a number: {str(value)[:40]!r}")
    return -amount if negative else amount


def parse_rate(value: Any) -> Optional[Decimal]:
    """Percentage as written (18 or '18%'). Fractions such as 0.18 are not rescaled, because
    0.1 % and 0.25 % are real slabs; an unexpected value is reported by validation instead."""
    if value is None:
        return None
    return parse_money(str(value).strip().rstrip("%").strip())


def parse_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    try:
        parsed = pd.to_datetime(value, dayfirst=True, errors="raise")
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f"not a date: {str(value)[:40]!r}")
    return parsed.date().isoformat()


def extract_fields(raw: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Map cleaned columns to canonical fields. First matching column wins; conflicts are reported."""
    fields: Dict[str, Any] = {}
    warnings: List[str] = []
    for column, value in raw.items():
        canonical = _ALIAS_LOOKUP.get(normalize_header(column))
        if canonical is None or value is None:
            continue
        try:
            if canonical in MONEY_FIELDS:
                parsed = parse_money(value)
                parsed = None if parsed is None else str(parsed)
            elif canonical == "gst_rate":
                parsed = parse_rate(value)
                parsed = None if parsed is None else str(parsed)
            elif canonical == "invoice_date":
                parsed = parse_date(value)
            elif canonical in GSTIN_FIELDS:
                parsed = re.sub(r"\s", "", str(value)).upper()
            elif canonical == "currency":
                parsed = str(value).strip().upper()
            else:
                parsed = str(value).strip()
        except ValueError as exc:
            warnings.append(f"Column '{column}': {exc}")
            continue
        if parsed is None:
            continue
        if canonical in fields and fields[canonical] != parsed:
            warnings.append(f"Column '{column}' conflicts with another column mapped to {canonical}; first value kept")
            continue
        fields.setdefault(canonical, parsed)
    return fields, warnings


def _row_to_transaction(raw_row: Dict[str, Any], ref: str, sheet: Optional[str], row_number: int,
                        limits: AnalysisLimits) -> NormalizedTransaction:
    raw = {}
    for column, value in raw_row.items():
        name = str(column).strip()[:200]
        if not name or (name.lower().startswith("unnamed:") and value is None):
            continue
        if normalize_header(name) in DROPPED_COLUMNS:
            continue
        cleaned = clean_value(value, limits.max_cell_chars)
        if cleaned is not None:
            raw[name] = cleaned
    fields, warnings = extract_fields(raw)
    return NormalizedTransaction(source_ref=ref, source_sheet=sheet, source_row=row_number, raw=raw,
                                 fields=fields, parse_warnings=warnings)


def dropped_columns(columns) -> List[str]:
    return sorted({str(c) for c in columns if normalize_header(c) in DROPPED_COLUMNS})


def normalize_records(records: List[Dict[str, Any]], limits: AnalysisLimits) -> Tuple[List[NormalizedTransaction], List[str]]:
    if not isinstance(records, list) or not records:
        raise InputValidationError("`records` must be a non-empty list of objects")
    if len(records) > limits.max_rows:
        raise InputValidationError(f"Too many records: {len(records)} (limit {limits.max_rows})")
    warnings: List[str] = []
    out = []
    columns = set()
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise InputValidationError(f"records[{i}] must be a JSON object")
        if len(record) > limits.max_columns:
            raise InputValidationError(f"records[{i}] has too many fields (limit {limits.max_columns})")
        columns.update(record.keys())
        out.append(_row_to_transaction(record, f"records[{i}]", None, i, limits))
    dropped = dropped_columns(columns)
    if dropped:
        warnings.append(f"Ignored label/output fields: {', '.join(dropped)}")
    if not any(t.raw for t in out):
        raise InputValidationError("All records are empty")
    return out, warnings


def parse_json_string(text: str, limits: AnalysisLimits) -> List[Dict[str, Any]]:
    if len(text.encode("utf-8")) > limits.max_json_bytes:
        raise InputValidationError(f"JSON input exceeds {limits.max_json_bytes} bytes")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputValidationError(f"Malformed JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
    if isinstance(data, dict) and "records" in data:
        data = data["records"]
    if not isinstance(data, list):
        raise InputValidationError("JSON must be a list of records or an object with a `records` list")
    return data


def normalize_workbook(content: bytes, filename: str, limits: AnalysisLimits) -> Tuple[List[NormalizedTransaction], List[str]]:
    if not content:
        raise InputValidationError("The uploaded file is empty")
    if len(content) > limits.max_upload_bytes:
        raise InputValidationError(f"File exceeds {limits.max_upload_bytes} bytes")
    name = (filename or "").lower()
    try:
        if name.endswith(".csv"):
            sheets = {"csv": pd.read_csv(BytesIO(content), dtype=object)}
        elif name.endswith((".xlsx", ".xlsm")) or not name:
            sheets = pd.read_excel(BytesIO(content), sheet_name=None, dtype=object, engine="openpyxl")
        else:
            raise InputValidationError("Unsupported file type; upload .xlsx, .xlsm or .csv")
    except InputValidationError:
        raise
    except Exception:
        raise InputValidationError("The file could not be read as an Excel workbook or CSV")
    if len(sheets) > limits.max_sheets:
        raise InputValidationError(f"Workbook has {len(sheets)} sheets (limit {limits.max_sheets})")

    transactions: List[NormalizedTransaction] = []
    warnings: List[str] = []
    for sheet_name, frame in sheets.items():
        frame = frame.dropna(how="all").dropna(axis=1, how="all")
        if frame.empty:
            warnings.append(f"Sheet '{sheet_name}' is empty and was skipped")
            continue
        if frame.shape[1] > limits.max_columns:
            raise InputValidationError(f"Sheet '{sheet_name}' has too many columns (limit {limits.max_columns})")
        headers = [str(c) for c in frame.columns]
        if all(h.lower().startswith("unnamed:") for h in headers):
            warnings.append(f"Sheet '{sheet_name}' has no header row and was skipped")
            continue
        known = [h for h in headers if normalize_header(h) in _ALIAS_LOOKUP]
        if not known:
            warnings.append(f"Sheet '{sheet_name}': no recognised GST/accounting columns; rows are still classified")
        dropped = dropped_columns(frame.columns)
        if dropped:
            warnings.append(f"Sheet '{sheet_name}': ignored label/output columns {', '.join(dropped)}")
        if len(transactions) + len(frame) > limits.max_rows:
            raise InputValidationError(f"Workbook has more than {limits.max_rows} data rows")
        for index, row in frame.iterrows():
            excel_row = int(index) + 2  # header is row 1
            label = "csv" if sheet_name == "csv" else sheet_name
            transactions.append(_row_to_transaction(row.to_dict(), f"{label}!R{excel_row}", label, excel_row, limits))
    if not transactions:
        raise InputValidationError("The workbook contains no data rows")
    return transactions, warnings
