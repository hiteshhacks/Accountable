"""Deterministic accounting and GST calculations (Decimal arithmetic, with provenance).

Every figure records the fields and rows it used and whether it is COMPLETE,
INCOMPLETE (some rows lack the input), UNRESOLVED (no row has it) or
NOT_APPLICABLE (no rows of that kind). Nothing is estimated or invented: a
missing value stays missing. The LLM never produces or alters these numbers.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Callable, Dict, Iterable, List, Optional

from vyom.gst.rules import GstRules, gstin_status
from vyom.gst.schemas import Calculation, NormalizedTransaction, VoucherClassification


CENT = Decimal("0.01")
ROUNDING = "ROUND_HALF_UP to 0.01 after summation"
MAX_REFS = 50
GROUPS = ("outward", "inward", "credit_notes", "debit_notes", "receipts", "payments", "expenses")
SUPPLIER_IS_BUSINESS = {"outward", "credit_notes"}


def q(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _dec(value: Any) -> Optional[Decimal]:
    return None if value is None else Decimal(str(value))


# ==========================================
# FEATURE EXTRACTION
# ==========================================

def extract_features(transactions: List[NormalizedTransaction], classifications: List[VoucherClassification],
                     rules: GstRules, business_gstin: Optional[str] = None) -> List[Dict[str, Any]]:
    """One feature dict per row, combining canonical fields with the classifier's category."""
    by_ref = {c.source_ref: c for c in classifications}
    business = (business_gstin or "").replace(" ", "").upper() or None
    rows = []
    for t in transactions:
        f = t.fields
        c = by_ref.get(t.source_ref)
        category = c.category if c else None
        group = rules.group_of(category)
        components = {k: _dec(f.get(k)) for k in ("cgst", "sgst", "igst", "cess")}
        present = {k: v for k, v in components.items() if v is not None}
        reported_total = _dec(f.get("total_tax"))
        tax = sum(present.values(), Decimal("0")) if present else reported_total

        supplier, recipient = f.get("supplier_gstin"), f.get("recipient_gstin")
        party = f.get("party_gstin")
        if group in SUPPLIER_IS_BUSINESS:
            recipient = recipient or party
            supplier = supplier or business
            party_name = f.get("customer_name") or f.get("supplier_name")
        else:
            supplier = supplier or party
            recipient = recipient or business
            party_name = f.get("supplier_name") or f.get("customer_name")
        currency = f.get("currency")
        rows.append({
            "ref": t.source_ref, "category": category, "group": group,
            "ambiguous": bool(c and c.ambiguous), "score": c.score_uncalibrated if c else None,
            "currency": currency or rules.base_currency, "currency_stated": currency is not None,
            "in_base_currency": currency is None or currency == rules.base_currency,
            "taxable": _dec(f.get("taxable_value")), "rate": _dec(f.get("gst_rate")),
            **components, "tax_components_present": sorted(present), "reported_total_tax": reported_total,
            "tax": tax, "total_amount": _dec(f.get("total_amount")), "amount": _dec(f.get("amount")),
            "invoice_number": f.get("invoice_number"), "invoice_date": f.get("invoice_date"),
            "supplier_gstin": supplier, "recipient_gstin": recipient,
            "supplier_gstin_status": gstin_status(supplier, rules.verify_gstin_checksum),
            "recipient_gstin_status": gstin_status(recipient, rules.verify_gstin_checksum),
            "party_name": party_name, "original_invoice_ref": f.get("original_invoice_ref"),
            "place_of_supply": f.get("place_of_supply"), "hsn_sac": f.get("hsn_sac"),
            "ledger": f.get("ledger"), "opening_balance": _dec(f.get("opening_balance")),
            "closing_balance": _dec(f.get("closing_balance")), "debit": _dec(f.get("debit")),
            "credit": _dec(f.get("credit")),
        })
    return rows


def has_itc_evidence(row: Dict[str, Any]) -> bool:
    """Basic documentary evidence only; not a determination of legal eligibility."""
    return (row["supplier_gstin_status"] == "valid" and bool(row["invoice_number"]) and bool(row["invoice_date"])
            and row["tax"] is not None and row["tax"] > 0)


# ==========================================
# CALCULATIONS
# ==========================================

def _refs(rows: Iterable[Dict[str, Any]]) -> List[str]:
    refs = [r["ref"] for r in rows]
    return refs[:MAX_REFS]


def sum_rows(name: str, rows: List[Dict[str, Any]], getter: Callable[[Dict[str, Any]], Optional[Decimal]],
             method: str, inputs: List[str], currency: str, notes: Optional[List[str]] = None) -> Calculation:
    values = [(r, getter(r)) for r in rows]
    have = [(r, v) for r, v in values if v is not None]
    missing = len(values) - len(have)
    if not values:
        status, value = "NOT_APPLICABLE", "0.00"
    elif not have:
        status, value = "UNRESOLVED", None
    else:
        status = "COMPLETE" if missing == 0 else "INCOMPLETE"
        value = str(q(sum((v for _, v in have), Decimal("0"))))
    extra = list(notes or [])
    uncertain = sum(1 for r, _ in have if r.get("ambiguous"))
    if uncertain:
        extra.append(f"{uncertain} included rows rely on an ambiguous voucher classification")
        if status == "COMPLETE":
            status = "INCOMPLETE"
    if len(have) > MAX_REFS:
        extra.append(f"source_refs lists the first {MAX_REFS} of {len(have)} rows")
    return Calculation(name=name, value=value, status=status, method=method, inputs_used=inputs, currency=currency,
                       rounding=ROUNDING, rows_included=len(have), rows_missing=missing,
                       source_refs=_refs(r for r, _ in have), notes=extra)


def combine(name: str, terms: List[tuple], method: str, currency: str, notes: Optional[List[str]] = None) -> Calculation:
    """Signed combination of other calculations: terms = [(+1|-1, Calculation)]."""
    statuses = [c.status for _, c in terms]
    if all(s == "NOT_APPLICABLE" for s in statuses):
        status = "NOT_APPLICABLE"
    elif any(s == "UNRESOLVED" for s in statuses):
        status = "UNRESOLVED"
    elif any(s == "INCOMPLETE" for s in statuses):
        status = "INCOMPLETE"
    else:
        status = "COMPLETE"
    value = None
    if status != "UNRESOLVED":
        value = str(q(sum((sign * Decimal(c.value or "0") for sign, c in terms), Decimal("0"))))
    refs: List[str] = []
    for _, c in terms:
        refs.extend(r for r in c.source_refs if r not in refs)
    return Calculation(name=name, value=value, status=status, method=method,
                       inputs_used=[c.name for _, c in terms], currency=currency, rounding=ROUNDING,
                       rows_included=sum(c.rows_included for _, c in terms),
                       rows_missing=sum(c.rows_missing for _, c in terms), source_refs=refs[:MAX_REFS],
                       notes=list(notes or []))


def calculate(features: List[Dict[str, Any]], rules: GstRules) -> Dict[str, Any]:
    cur = rules.base_currency
    base = [r for r in features if r["in_base_currency"]]
    foreign = [r for r in features if not r["in_base_currency"]]
    by_group = {g: [r for r in base if r["group"] == g] for g in GROUPS}
    assumed_currency = sum(1 for r in base if not r["currency_stated"])

    counts_by_category: Dict[str, int] = {}
    for r in features:
        counts_by_category[r["category"] or "Unclassified"] = counts_by_category.get(r["category"] or "Unclassified", 0) + 1

    doc_value = lambda r: r["total_amount"] if r["total_amount"] is not None else r["amount"]  # noqa: E731
    accounting = []
    for g in GROUPS:
        rows = by_group[g]
        if g in ("receipts", "payments"):
            accounting.append(sum_rows(f"{g}_amount", rows, doc_value,
                                       "Sum of total_amount (or amount when total is absent) per row", ["total_amount", "amount"], cur))
        else:
            accounting.append(sum_rows(f"{g}_taxable_value", rows, lambda r: r["taxable"],
                                       "Sum of taxable_value per row", ["taxable_value"], cur))
            accounting.append(sum_rows(f"{g}_document_value", rows, doc_value,
                                       "Sum of invoice value (total_amount, else amount) per row", ["total_amount", "amount"], cur))

    gst = []
    tax_calcs = {}
    for g in ("outward", "inward", "credit_notes", "debit_notes", "expenses"):
        rows = by_group[g]
        for comp in ("cgst", "sgst", "igst", "cess"):
            gst.append(sum_rows(f"{g}_{comp}", [r for r in rows if r["tax_components_present"]],
                                lambda r, k=comp: r[k] if r[k] is not None else Decimal("0"),
                                f"Sum of {comp.upper()} on rows that report tax components (unreported component = 0)",
                                [comp], cur))
        tax_calcs[g] = sum_rows(f"{g}_total_tax", rows, lambda r: r["tax"],
                                "Per row: CGST+SGST+IGST+cess when components are present, else reported total tax; summed",
                                ["cgst", "sgst", "igst", "cess", "total_tax"], cur)
        gst.append(tax_calcs[g])

    output_tax = combine("output_tax_after_credit_notes", [(1, tax_calcs["outward"]), (-1, tax_calcs["credit_notes"])],
                         "outward_total_tax - credit_notes_total_tax", cur)
    itc_rows = [r for r in base if r["category"] in rules.itc_categories]
    with_evidence = [r for r in itc_rows if has_itc_evidence(r)]
    without_evidence = [r for r in itc_rows if not has_itc_evidence(r) and r["tax"] is not None and r["tax"] > 0]
    itc_evidenced = sum_rows("itc_tax_with_basic_evidence", with_evidence, lambda r: r["tax"],
                             "Sum of tax on purchase/import/expense rows with a valid supplier GSTIN, invoice number "
                             "and invoice date", ["tax", "supplier_gstin", "invoice_number", "invoice_date"], cur,
                             ["Basic documentary evidence only; legal eligibility is not determined."])
    itc_unevidenced = sum_rows("itc_tax_without_basic_evidence", without_evidence, lambda r: r["tax"],
                               "Sum of tax on purchase/import/expense rows missing GSTIN, invoice number or date",
                               ["tax"], cur, ["Not counted in potential ITC."])
    potential_itc = combine("potential_itc_after_debit_notes",
                            [(1, itc_evidenced), (-1, tax_calcs["debit_notes"])],
                            "itc_tax_with_basic_evidence - debit_notes_total_tax", cur,
                            ["Potential amount only; eligibility, blocked credits, reversals and GSTR-2B matching "
                             "are not evaluated."])
    net_notes = ["Potential figure before eligibility rules, reversals, interest, fees, cash/credit ledger "
                 "balances and reconciliation with GST portal data."]
    net = combine("potential_net_gst_liability", [(1, output_tax), (-1, potential_itc)],
                  "output_tax_after_credit_notes - potential_itc_after_debit_notes", cur, net_notes)
    if without_evidence and net.status == "COMPLETE":
        net = net.model_copy(update={"status": "INCOMPLETE", "notes": net_notes + [
            f"{len(without_evidence)} inward rows with tax lack basic ITC evidence and are excluded."]})
    zero_tax = sum_rows("zero_tax_value", [r for r in base if r["group"] in ("outward", "inward")
                                           and r["taxable"] is not None
                                           and ((r["rate"] is not None and r["rate"] == 0) or (r["tax"] is not None and r["tax"] == 0))],
                        lambda r: r["taxable"], "Taxable value of outward/inward rows with 0 % rate or 0 tax",
                        ["taxable_value", "gst_rate", "tax"], cur,
                        ["Nil-rated, exempt, non-GST and zero-rated supplies are not distinguished."])
    gst.extend([output_tax, itc_evidenced, itc_unevidenced, potential_itc, net, zero_tax])

    return {
        "accounting_summary": {
            "transaction_count": len(features),
            "rows_in_base_currency": len(base),
            "rows_excluded_foreign_currency": len(foreign),
            "rows_with_assumed_base_currency": assumed_currency,
            "base_currency": cur,
            "counts_by_category": dict(sorted(counts_by_category.items())),
            "counts_by_group": {g: len(by_group[g]) for g in GROUPS} | {
                "other": sum(1 for r in base if r["group"] == "other")},
            "calculations": [c.model_dump() for c in accounting],
        },
        "gst_summary": {"calculations": [c.model_dump() for c in gst]},
        "filing_preparation": filing_preparation(by_group, features, rules),
        "balance_summary": balance_summary(base),
    }


def _section(rows: List[Dict[str, Any]], required: List[str]) -> Dict[str, Any]:
    if not rows:
        return {"rows": 0, "status": "NO_DATA"}
    complete = all(all(r.get(k) not in (None, "") for k in required) for r in rows)
    taxable = [r["taxable"] for r in rows if r["taxable"] is not None]
    tax = [r["tax"] for r in rows if r["tax"] is not None]
    return {"rows": len(rows), "taxable_value": str(q(sum(taxable, Decimal("0")))) if taxable else None,
            "tax": str(q(sum(tax, Decimal("0")))) if tax else None,
            "status": "PREPARED_FOR_REVIEW" if complete else "INCOMPLETE",
            "required_fields": required, "source_refs": _refs(rows)}


def filing_preparation(by_group: Dict[str, List[Dict[str, Any]]], features: List[Dict[str, Any]],
                       rules: GstRules) -> Dict[str, Any]:
    outward = by_group["outward"]
    b2b = [r for r in outward if r["recipient_gstin_status"] == "valid" and r["category"] != "Export"]
    exports = [r for r in outward if r["category"] == "Export"]
    placed = {r["ref"] for r in b2b} | {r["ref"] for r in exports}
    unregistered = [r for r in outward if r["ref"] not in placed]
    b2c_by_rate: Dict[str, List[Dict[str, Any]]] = {}
    for r in unregistered:
        key = str(r["rate"]) if r["rate"] is not None else "rate not stated"
        b2c_by_rate.setdefault(key, []).append(r)
    inward = by_group["inward"] + by_group["expenses"]
    return {
        "note": "Data organised for professional review. Not a return, not validated against the GST portal, "
                "and not filed.",
        "outward_b2b": _section(b2b, ["invoice_number", "invoice_date", "recipient_gstin", "taxable", "tax"]),
        "outward_without_valid_recipient_gstin": {k: _section(v, ["invoice_number", "invoice_date", "taxable", "tax"])
                                                  for k, v in sorted(b2c_by_rate.items())},
        "exports": _section(exports, ["invoice_number", "invoice_date", "taxable"]),
        "inward_with_basic_itc_evidence": _section([r for r in inward if has_itc_evidence(r)],
                                                   ["invoice_number", "invoice_date", "supplier_gstin", "tax"]),
        "inward_without_basic_itc_evidence": _section([r for r in inward if not has_itc_evidence(r)],
                                                      ["invoice_number", "invoice_date", "supplier_gstin", "tax"]),
        "credit_notes": _section(by_group["credit_notes"], ["invoice_number", "invoice_date", "original_invoice_ref", "tax"]),
        "debit_notes": _section(by_group["debit_notes"], ["invoice_number", "invoice_date", "original_invoice_ref", "tax"]),
    }


def balance_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Ledger balances only when ledger names with opening/closing balances are supplied."""
    ledger_rows = [r for r in rows if r["ledger"] and (r["opening_balance"] is not None or r["closing_balance"] is not None)]
    if not ledger_rows:
        return {"available": False,
                "reason": "The input has transactions but no ledger opening/closing balances, so no balance sheet "
                          "or ledger balance summary can be produced.",
                "missing_fields": ["ledger", "opening_balance", "closing_balance"]}
    ledgers: Dict[str, Dict[str, Any]] = {}
    for r in ledger_rows:
        entry = ledgers.setdefault(r["ledger"], {"opening": Decimal("0"), "debit": Decimal("0"), "credit": Decimal("0"),
                                                "closing": None, "refs": []})
        entry["opening"] += r["opening_balance"] or Decimal("0")
        entry["debit"] += r["debit"] or Decimal("0")
        entry["credit"] += r["credit"] or Decimal("0")
        if r["closing_balance"] is not None:
            entry["closing"] = (entry["closing"] or Decimal("0")) + r["closing_balance"]
        entry["refs"].append(r["ref"])
    out = []
    for name, e in sorted(ledgers.items()):
        expected = e["opening"] + e["debit"] - e["credit"]
        out.append({"ledger": name, "opening": str(q(e["opening"])), "debits": str(q(e["debit"])),
                    "credits": str(q(e["credit"])), "closing_reported": None if e["closing"] is None else str(q(e["closing"])),
                    "closing_computed_debit_positive": str(q(expected)),
                    "reconciles": None if e["closing"] is None else q(expected) == q(e["closing"]),
                    "source_refs": e["refs"][:MAX_REFS]})
    return {"available": True, "sign_convention": "opening + debits - credits (debit-positive); for credit-balance "
            "ledgers the comparison may need the opposite sign", "ledgers": out,
            "note": "Ledger summary only; not a complete balance sheet unless every ledger is supplied."}
