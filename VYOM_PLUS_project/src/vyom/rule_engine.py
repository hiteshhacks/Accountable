"""Voucher Semantic Rule Engine.

Collects explicit transaction evidence from wide voucher fields and decides a
category only when that evidence is consistent. Rules do not use the target label.

Every rule is evaluated; there is no first-match precedence. Each satisfied
clause becomes an Evidence item with one of these bases:

- ``identifier``         the record's own document-number prefix, nothing else
- ``identifier+fields``  a document-number prefix together with supporting fields
- ``reference+fields``   the prefix of a referenced document plus transaction fields
- ``fields``             transaction fields only

Decision statuses describe the evidence; they are not probabilities:

- ``RULE_MATCH``       exactly one category is supported, by at least one clause
                       that goes beyond an identifier prefix, and nothing contradicts it.
- ``REVIEW_REQUIRED``  the evidence supports two or more categories. An identifier
                       prefix therefore never overrides contradictory transaction evidence.
- ``AMBIGUOUS``        the evidence is insufficient: an identifier prefix alone, or
                       return / rejection details that do not establish a direction.
- ``NO_RULE``          no rule evidence; the caller's model prediction stands.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import pandas as pd


RULE_MATCH = "RULE_MATCH"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
AMBIGUOUS = "AMBIGUOUS"
NO_RULE = "NO_RULE"

IDENTIFIER = "identifier"
IDENTIFIER_FIELDS = "identifier+fields"
REFERENCE_FIELDS = "reference+fields"
FIELDS = "fields"


def _clean(val: Any) -> str:
    """Normalize field value to trimmed string."""
    if pd.isna(val):
        return ""
    val_str = str(val).strip()
    if val_str.lower() in {"nan", "none", "nat"}:
        return ""
    return val_str


@dataclass(frozen=True)
class Clause:
    """A conjunction of tests on one record; satisfied when every test holds."""
    prefix: Optional[Tuple[str, str]] = None     # (field, prefix) on the record's own document number
    reference: Optional[Tuple[str, str]] = None  # (field, prefix) on a referenced document number
    all_of: Tuple[str, ...] = ()                 # every field must be present
    any_of: Tuple[Tuple[str, ...], ...] = ()     # each group needs at least one present field
    none_of: Tuple[str, ...] = ()                # every field must be empty

    @property
    def basis(self) -> str:
        has_fields = bool(self.all_of or self.any_of)
        if self.prefix:
            return IDENTIFIER_FIELDS if has_fields else IDENTIFIER
        if self.reference:
            return REFERENCE_FIELDS
        return FIELDS

    def match(self, row) -> Optional[Dict[str, str]]:
        """Return the triggering field values, or None when the clause does not hold."""
        evidence: Dict[str, str] = {}
        for test in (self.prefix, self.reference):
            if test:
                field, prefix = test
                value = _clean(row.get(field))
                if not value.startswith(prefix):
                    return None
                evidence[field] = value
        for field in self.all_of:
            value = _clean(row.get(field))
            if not value:
                return None
            evidence[field] = value
        for group in self.any_of:
            hits = {f: _clean(row.get(f)) for f in group}
            hits = {f: v for f, v in hits.items() if v}
            if not hits:
                return None
            evidence.update(hits)
        if any(_clean(row.get(f)) for f in self.none_of):
            return None
        return evidence


@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str
    clauses: Tuple[Clause, ...]
    unless: Tuple[str, ...] = ()  # rule is skipped when any of these fields is present


@dataclass(frozen=True)
class Evidence:
    rule_id: str
    category: str
    basis: str
    fields: Tuple[Tuple[str, str], ...]

    def describe(self) -> str:
        values = ", ".join(f"{k}={v}" for k, v in self.fields)
        return f"{self.category} [{self.rule_id}, {self.basis}: {values}]"


@dataclass(frozen=True)
class RuleDecision:
    status: str
    category: Optional[str]      # set only when status is RULE_MATCH
    candidates: Tuple[str, ...]  # categories the evidence points to
    evidence: Tuple[Evidence, ...]
    explanation: str


REJECTION_DETAILS = ("Item Rejected", "Quantity Rejected", "Rejection Reason")
RETURN_DETAILS = ("Units Returned", "Reason for Return")

# Clauses carry over the audited engine's conditions (vyom.legacy_rule_engine) with
# one exception: Rejection In no longer requires Customer and DN Reference to be
# empty. That exclusion silently resolved inward/outward conflicts in favour of
# Rejection Out; without it, both directions produce evidence and the record is
# sent to review.
RULES: Tuple[Rule, ...] = (
    Rule("R01", "Rejection In", (
        Clause(prefix=("Rejection Note No", "RJN-IN")),
        Clause(any_of=(REJECTION_DETAILS, ("GRN Reference", "Receiving Company"))),
    )),
    Rule("R02", "Rejection Out", (
        Clause(prefix=("Rejection Note No", "RJN-OUT")),
        Clause(any_of=(REJECTION_DETAILS, ("DN Reference", "Customer"))),
    )),
    Rule("R03", "Purchase Return / Debit Note", (
        Clause(prefix=("Document Number", "DBN")),
        Clause(reference=("Original Doc Ref", "PUR"), any_of=(RETURN_DETAILS,)),
    )),
    Rule("R04", "Sales Return / Credit Note", (
        Clause(prefix=("Document Number", "CRN")),
        Clause(reference=("Original Invoice Ref", "SAL"), any_of=(RETURN_DETAILS,)),
    )),
    Rule("R05", "Purchase", (
        Clause(prefix=("Document Number", "PUR-")),
        Clause(reference=("PO Ref", "PO"), all_of=("Vendor Name",)),
    ), unless=RETURN_DETAILS),
    Rule("R06", "Sales", (
        Clause(prefix=("Document Number", "SAL-")),
        Clause(reference=("Delivery Ref", "DN"), all_of=("Product",)),
    ), unless=RETURN_DETAILS),
    Rule("R07", "Purchase Order", (
        Clause(prefix=("PO Number", "PO"), any_of=(("Quantity Required", "Supplier", "Promised Delivery"),)),
    )),
    Rule("R08", "Sales Order", (
        Clause(prefix=("SO Number", "SO"), any_of=(("Quantity Ordered", "Selling Company", "Customer"),)),
    )),
    Rule("R09", "Delivery Note", (
        Clause(prefix=("Delivery Challan No", "DC")),
        Clause(all_of=("Item Dispatched", "Quantity Shipped")),
    )),
    Rule("R10", "Receipt Note", (
        Clause(prefix=("GRN Number", "GRN")),
        Clause(all_of=("Item Received", "Quantity Received"), none_of=("Outward Job Work No",)),
    )),
    Rule("R11", "Contra", (
        Clause(prefix=("Contra ID", "CTR")),
        Clause(all_of=("Source Account", "Destination Account", "Transfer Amount")),
    )),
    Rule("R12", "Payment", (
        Clause(prefix=("Payment ID", "PMT")),
        Clause(all_of=("Payment Amount",), any_of=(("Payer Organization", "Payee Organization"),)),
    )),
    Rule("R13", "Receipt", (
        Clause(prefix=("Receipt ID", "RCP")),
        Clause(all_of=("Received Amount",), any_of=(("Receipt Nature", "Receiving Organization"),)),
    )),
    Rule("R14", "Salary / Payroll", (
        Clause(prefix=("Employee Code", "EMP")),
        Clause(all_of=("Gross Salary", "Net Payable", "Payroll Period")),
    )),
    Rule("R15", "Expense", (
        Clause(prefix=("Expense Claim No", "EXP"), any_of=(("Expense Type", "Amount Claimed"),)),
    )),
    Rule("R16", "Export", (
        Clause(prefix=("Export Invoice No", "EXP"), any_of=(("Destination Country", "Units Exported", "Free on Board Value"),)),
    )),
    Rule("R17", "Import", (
        Clause(prefix=("Import Bill No", "IBL")),
        Clause(all_of=("Originating Country",), any_of=(("Units Imported", "Customs Duty"),)),
    )),
    Rule("R18", "Journal", (
        Clause(prefix=("Journal ID", "JNL")),
        Clause(all_of=("Debit Side", "Credit Side", "Journal Type")),
    )),
    Rule("R19", "Stock Journal", (
        Clause(prefix=("Stock Adj ID", "SA")),
        Clause(all_of=("Adjustment Qty", "Storage Facility")),
    )),
    Rule("R20", "Physical Stock", (
        Clause(prefix=("Stock Count ID", "SC")),
        Clause(all_of=("Book Quantity", "Counted Quantity")),
    )),
    Rule("R21", "Job Work In Order", (
        Clause(prefix=("JWIO Ref", "JWIO")),
        Clause(all_of=("Processing Rate", "Processor"), none_of=("Service Charge",)),
    )),
    Rule("R22", "Job Work Out Order", (
        Clause(prefix=("JWOO Ref", "JWOO")),
        Clause(all_of=("Service Charge", "Agreement Terms")),
    )),
    Rule("R23", "Material In", (
        Clause(prefix=("Inward Job Work No", "MIW")),
        Clause(all_of=("Subcontractor", "Quantity Sent", "Date of Dispatch")),
    )),
    Rule("R24", "Material Out", (
        Clause(prefix=("Outward Job Work No", "MOW")),
        Clause(all_of=("Contractor", "Quantity Received", "Date of Receipt")),
    )),
)

# Details that establish a transaction family but not its direction.
FAMILIES = (
    ("Return", RETURN_DETAILS, ("Purchase Return / Debit Note", "Sales Return / Credit Note")),
    ("Rejection", REJECTION_DETAILS, ("Rejection In", "Rejection Out")),
)


def collect_evidence(row) -> Tuple[Evidence, ...]:
    """Evaluate every rule and return all satisfied clauses as evidence."""
    found = []
    for rule in RULES:
        if any(_clean(row.get(f)) for f in rule.unless):
            continue
        for clause in rule.clauses:
            matched = clause.match(row)
            if matched is not None:
                found.append(Evidence(rule.rule_id, rule.category, clause.basis, tuple(matched.items())))
    return tuple(found)


def assess_transaction(row) -> RuleDecision:
    """Decide from the evidence in ``row``; never reads the target label."""
    evidence = collect_evidence(row)
    candidates = tuple(dict.fromkeys(e.category for e in evidence))
    described = "; ".join(e.describe() for e in evidence)

    if len(candidates) > 1:
        return RuleDecision(REVIEW_REQUIRED, None, candidates, evidence,
                            f"Conflicting evidence for {' vs '.join(candidates)}: {described}")

    for family, details, members in FAMILIES:
        present = [f for f in details if _clean(row.get(f))]
        if present and not set(candidates) & set(members):
            if candidates:
                return RuleDecision(
                    REVIEW_REQUIRED, None, candidates + members, evidence,
                    f"{family} details ({', '.join(present)}) contradict {candidates[0]} evidence: {described}")
            return RuleDecision(
                AMBIGUOUS, None, members, evidence,
                f"{family} details ({', '.join(present)}) without direction evidence: {' or '.join(members)}")

    if not candidates:
        return RuleDecision(NO_RULE, None, (), evidence, "No rule evidence")

    category = candidates[0]
    if all(e.basis == IDENTIFIER for e in evidence):
        return RuleDecision(AMBIGUOUS, None, candidates, evidence,
                            f"Identifier prefix only, no supporting transaction fields: {described}")
    return RuleDecision(RULE_MATCH, category, candidates, evidence, f"Consistent evidence for {described}")


def evaluate_transaction_rules(
    row: pd.Series,
    base_prediction: Optional[str] = None,
) -> Tuple[str, str, bool]:
    """
    Evaluate explicit transaction-specific evidence.

    Args:
        row: Series of transaction fields. MUST NOT contain target label.
        base_prediction: Model prediction kept whenever the rules do not decide.

    Returns:
        (prediction, explanation, rule_applied). rule_applied is True only for
        RULE_MATCH; use assess_transaction for the REVIEW_REQUIRED / AMBIGUOUS status.
    """
    decision = assess_transaction(row)
    if decision.status == RULE_MATCH:
        return decision.category, decision.explanation, True
    if decision.status == NO_RULE:
        if base_prediction:
            return base_prediction, "Model statistical prediction (no rule override)", False
        return "Unclassified", "Insufficient evidence for deterministic rule", False
    return base_prediction or "Unclassified", f"{decision.status}: {decision.explanation}", False
