"""Configurable GST rules and the assumptions behind them.

These defaults are working assumptions for validation, not a statement of GST
law. Rates, tolerances and category groupings can be overridden with a JSON file
(GST_RULES_PATH) without code changes. Verify them against current notifications
and professional advice before relying on any result.
"""

from dataclasses import dataclass, field, replace
from decimal import Decimal
import json
from pathlib import Path
import re
from typing import Dict, FrozenSet, Optional, Tuple


ASSUMPTIONS = (
    "Tax rates are checked against a configurable list of commonly published GST slab rates; the list is not "
    "a determination of the correct rate for any supply.",
    "Monetary values are rounded half-up to 2 decimal places (paise) after summation.",
    "A row's tax is the sum of CGST, SGST/UTGST, IGST and cess when any component is present; otherwise the "
    "reported total tax amount. When a row reports at least one component, components it does not report are "
    "treated as not charged (0).",
    "Intra-state vs inter-state is inferred only from the state codes of two valid GSTINs; place-of-supply "
    "rules are not evaluated.",
    "Input tax credit (ITC) is reported only as a potential amount with basic documentary evidence (supplier "
    "GSTIN, invoice number and date). Legal eligibility, blocked credits, reversals and GSTR-2B matching are "
    "not determined.",
    "Rows in a currency other than the base currency are excluded from totals; no exchange conversion is made.",
    "Voucher categories come from the existing VYOM+ classifier and are treated as evidence, not facts.",
)

# The VYOM+ 27-category taxonomy (label_guidelines_v5 in the synthetic dataset; a test checks they match).
TAXONOMY = (
    "Purchase", "Sales", "Expense", "Payment", "Receipt", "Contra", "Receipt Note", "Delivery Note",
    "Rejection In", "Rejection Out", "Import", "Export", "Job Work In Order", "Job Work Out Order", "Material In",
    "Material Out", "Stock Journal", "Physical Stock", "Salary / Payroll", "Attendance", "Purchase Order",
    "Sales Order", "Advance / Prepayment", "Journal", "Other / Miscellaneous", "Purchase Return / Debit Note",
    "Sales Return / Credit Note",
)

GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_checksum_ok(gstin: str) -> bool:
    """Standard GSTIN check-digit (base-36, alternating weights 1 and 2)."""
    total = 0
    for i, ch in enumerate(gstin[:14]):
        product = _GSTIN_CHARS.index(ch) * (1 if i % 2 == 0 else 2)
        total += product // 36 + product % 36
    return _GSTIN_CHARS[(36 - total % 36) % 36] == gstin[14]


def gstin_status(value: Optional[str], verify_checksum: bool = True) -> str:
    """'missing', 'invalid_format', 'invalid_checksum' or 'valid'."""
    if not value:
        return "missing"
    if not GSTIN_PATTERN.match(value):
        return "invalid_format"
    if verify_checksum and not gstin_checksum_ok(value):
        return "invalid_checksum"
    return "valid"


@dataclass(frozen=True)
class GstRules:
    base_currency: str = "INR"
    valid_rates: Tuple[Decimal, ...] = tuple(Decimal(r) for r in
                                             ("0", "0.1", "0.25", "1", "1.5", "3", "5", "6", "7.5", "12", "18", "28", "40"))
    tax_tolerance: Decimal = Decimal("1.00")
    rate_match_tolerance: Decimal = Decimal("0.25")
    verify_gstin_checksum: bool = True
    ambiguous_score_threshold: float = 0.50
    ambiguous_margin_threshold: float = 0.15
    outward: FrozenSet[str] = frozenset({"Sales", "Export"})
    inward: FrozenSet[str] = frozenset({"Purchase", "Import"})
    credit_notes: FrozenSet[str] = frozenset({"Sales Return / Credit Note"})
    debit_notes: FrozenSet[str] = frozenset({"Purchase Return / Debit Note"})
    receipts: FrozenSet[str] = frozenset({"Receipt"})
    payments: FrozenSet[str] = frozenset({"Payment"})
    expenses: FrozenSet[str] = frozenset({"Expense"})
    # Inward-side categories whose tax may support an ITC claim, given evidence.
    itc_categories: FrozenSet[str] = frozenset({"Purchase", "Import", "Expense"})
    assumptions: Tuple[str, ...] = ASSUMPTIONS

    def group_of(self, category: Optional[str]) -> str:
        for name in ("outward", "inward", "credit_notes", "debit_notes", "receipts", "payments", "expenses"):
            if category in getattr(self, name):
                return name
        return "other"

    @property
    def invoice_groups(self) -> FrozenSet[str]:
        """Groups whose records are tax documents needing invoice number, date and GSTINs."""
        return frozenset({"outward", "inward", "credit_notes", "debit_notes"})

    def public(self) -> Dict:
        return {"base_currency": self.base_currency, "valid_rates": [str(r) for r in self.valid_rates],
                "tax_tolerance": str(self.tax_tolerance), "verify_gstin_checksum": self.verify_gstin_checksum,
                "ambiguous_score_threshold": self.ambiguous_score_threshold,
                "ambiguous_margin_threshold": self.ambiguous_margin_threshold}


def load_rules(path: Optional[Path] = None) -> GstRules:
    """Default rules, optionally overridden by a JSON file with any subset of the public keys."""
    rules = GstRules()
    if not path:
        return rules
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    updates = {}
    if "base_currency" in data:
        updates["base_currency"] = str(data["base_currency"]).upper()
    if "valid_rates" in data:
        updates["valid_rates"] = tuple(Decimal(str(r)) for r in data["valid_rates"])
    for key in ("tax_tolerance", "rate_match_tolerance"):
        if key in data:
            updates[key] = Decimal(str(data[key]))
    for key in ("verify_gstin_checksum",):
        if key in data:
            updates[key] = bool(data[key])
    for key in ("ambiguous_score_threshold", "ambiguous_margin_threshold"):
        if key in data:
            updates[key] = float(data[key])
    for key in ("outward", "inward", "credit_notes", "debit_notes", "receipts", "payments", "expenses", "itc_categories"):
        if key in data:
            updates[key] = frozenset(data[key])
    if "assumptions" in data:
        updates["assumptions"] = tuple(data["assumptions"])
    return replace(rules, **updates)
