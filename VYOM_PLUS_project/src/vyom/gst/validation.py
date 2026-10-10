"""Deterministic GST validation and discrepancy detection.

CONFIRMED means the supplied data itself shows the problem (a field is missing,
two figures do not agree). POSSIBLE means the data suggests an issue that needs a
human to judge (e.g. a likely duplicate, a classification that conflicts with tax
evidence). No check reconciles with GST portal data or GSTR-2B: none is supplied.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from vyom.gst.accounting import MAX_REFS, has_itc_evidence, q
from vyom.gst.rules import GstRules, gstin_status
from vyom.gst.schemas import Discrepancy


MAX_EVIDENCE_SAMPLES = 10
SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}


class _Collector:
    """Groups row-level findings into one discrepancy per code (or per explicit key)."""

    def __init__(self):
        self.items: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def add(self, code, severity, status, message, action, ref=None, evidence=None, key=""):
        item = self.items.setdefault((code, key), {"code": code, "severity": severity, "status": status,
                                                   "message": message, "recommended_action": action,
                                                   "rows": [], "samples": []})
        if ref and ref not in item["rows"]:
            item["rows"].append(ref)
        if evidence and len(item["samples"]) < MAX_EVIDENCE_SAMPLES:
            item["samples"].append(evidence)

    def build(self) -> List[Discrepancy]:
        out = []
        for item in self.items.values():
            rows = item["rows"]
            evidence = {"affected_rows": len(rows)}
            if item["samples"]:
                evidence["samples"] = item["samples"]
            if len(rows) > MAX_REFS:
                evidence["note"] = f"source_rows lists the first {MAX_REFS} of {len(rows)} rows"
            out.append(Discrepancy(code=item["code"], severity=item["severity"], message=item["message"],
                                   source_rows=rows[:MAX_REFS], evidence=evidence,
                                   recommended_action=item["recommended_action"], status=item["status"]))
        return sorted(out, key=lambda d: (SEVERITY_ORDER[d.severity], d.code))


def _s(value) -> Optional[str]:
    return None if value is None else str(value)


def run_checks(features: List[Dict[str, Any]], rules: GstRules, business_gstin: Optional[str] = None
               ) -> Tuple[List[Discrepancy], List[Dict[str, Any]]]:
    """Returns (discrepancies, missing_fields)."""
    c = _Collector()
    tol = rules.tax_tolerance
    missing = defaultdict(lambda: {"rows": 0, "refs": []})

    def need(field, r, why):
        entry = missing[(field, why)]
        entry["rows"] += 1
        if len(entry["refs"]) < MAX_REFS:
            entry["refs"].append(r["ref"])

    if business_gstin:
        status = gstin_status(business_gstin.replace(" ", "").upper(), rules.verify_gstin_checksum)
        if status != "valid":
            c.add("BUSINESS_GSTIN_INVALID", "HIGH", "CONFIRMED",
                  f"The supplied business GSTIN fails validation ({status}).",
                  "Correct the business GSTIN supplied with the request.", evidence={"status": status})

    for r in features:
        ref, group, cat = r["ref"], r["group"], r["category"]
        if not r["in_base_currency"]:
            c.add("FOREIGN_CURRENCY_EXCLUDED", "MEDIUM", "CONFIRMED",
                  f"Rows in a currency other than {rules.base_currency} were excluded from totals.",
                  "Provide base-currency values or exchange rates used in the books.", ref,
                  {"row": ref, "currency": r["currency"]})
            continue

        # Classification evidence.
        if r["ambiguous"]:
            c.add("AMBIGUOUS_CLASSIFICATION", "MEDIUM", "POSSIBLE",
                  "The voucher classifier's top category is weak or close to the runner-up.",
                  "Confirm the voucher type before using the row in GST totals.", ref,
                  {"row": ref, "category": cat, "score_uncalibrated": r["score"]}, key="")
        if group == "other" and ((r["tax"] or 0) > 0 or r["tax_components_present"]):
            c.add("TAX_ON_NON_TAX_DOCUMENT", "MEDIUM", "POSSIBLE",
                  "Tax amounts appear on rows classified as a non-invoice voucher type (e.g. order, delivery or stock record).",
                  "Check whether the classification or the tax fields are wrong; such rows are excluded from GST totals.",
                  ref, {"row": ref, "category": cat, "tax": _s(r["tax"])})

        if group not in rules.invoice_groups and group != "expenses":
            continue
        invoice_doc = group in rules.invoice_groups

        # Document identity.
        if invoice_doc and not r["invoice_number"]:
            need("invoice_number", r, "tax document identity")
            c.add("INVOICE_NUMBER_MISSING", "HIGH", "CONFIRMED", "Tax documents without an invoice/note number.",
                  "Add the invoice or note number from the source document.", ref)
        if invoice_doc and not r["invoice_date"]:
            need("invoice_date", r, "tax period and document identity")
            c.add("INVOICE_DATE_MISSING", "HIGH", "CONFIRMED", "Tax documents without an invoice/note date.",
                  "Add the document date; it determines the tax period.", ref)

        # GSTINs.
        if group in ("inward", "debit_notes") or (group == "expenses" and (r["tax"] or 0) > 0):
            st = r["supplier_gstin_status"]
            if st == "missing":
                need("supplier_gstin", r, "input tax credit evidence")
                c.add("SUPPLIER_GSTIN_MISSING", "HIGH", "CONFIRMED", "Inward documents without a supplier GSTIN.",
                      "Obtain the supplier GSTIN from the purchase invoice.", ref)
            elif st != "valid":
                c.add("SUPPLIER_GSTIN_INVALID", "HIGH", "CONFIRMED", "Supplier GSTINs that fail format or checksum validation.",
                      "Correct the supplier GSTIN against the invoice.", ref, {"row": ref, "status": st})
        if group in ("outward", "credit_notes") and cat != "Export":
            st = r["recipient_gstin_status"]
            if st == "missing":
                c.add("RECIPIENT_GSTIN_MISSING", "MEDIUM", "POSSIBLE",
                      "Outward documents without a recipient GSTIN: either unregistered (B2C) supplies or missing data.",
                      "Confirm whether each recipient is unregistered; add the GSTIN for registered recipients.", ref)
            elif st != "valid":
                c.add("RECIPIENT_GSTIN_INVALID", "HIGH", "CONFIRMED", "Recipient GSTINs that fail format or checksum validation.",
                      "Correct the recipient GSTIN.", ref, {"row": ref, "status": st})

        # Values.
        if invoice_doc and r["taxable"] is None and r["tax"] is None:
            need("taxable_value", r, "supply value")
            c.add("SUPPLY_VALUE_MISSING", "MEDIUM", "CONFIRMED",
                  "Tax documents with neither a taxable value nor a tax amount.",
                  "Add taxable value and tax amounts from the source document.", ref)

        # Tax arithmetic.
        cg, sg, ig = r["cgst"], r["sgst"], r["igst"]
        if cg is not None and sg is not None and abs(cg - sg) > tol:
            c.add("CGST_SGST_UNEQUAL", "HIGH", "CONFIRMED", "CGST and SGST/UTGST differ on the same document.",
                  "Check the tax split; intra-state tax is normally split equally.", ref,
                  {"row": ref, "cgst": _s(cg), "sgst": _s(sg)})
        if (ig or 0) > 0 and ((cg or 0) > 0 or (sg or 0) > 0):
            c.add("IGST_WITH_CGST_SGST", "HIGH", "CONFIRMED", "IGST and CGST/SGST are both charged on the same document.",
                  "Determine whether the supply is inter-state (IGST) or intra-state (CGST+SGST).", ref,
                  {"row": ref, "igst": _s(ig), "cgst": _s(cg), "sgst": _s(sg)})
        if r["tax_components_present"] and r["reported_total_tax"] is not None:
            comp_sum = r["tax"]
            if abs(comp_sum - r["reported_total_tax"]) > tol:
                c.add("TAX_COMPONENTS_DO_NOT_SUM", "MEDIUM", "CONFIRMED",
                      "Tax components do not add up to the reported total tax.",
                      "Reconcile the tax columns with the invoice.", ref,
                      {"row": ref, "components_sum": _s(q(comp_sum)), "reported_total_tax": _s(r["reported_total_tax"])})
        sup_state = r["supplier_gstin"][:2] if r["supplier_gstin_status"] == "valid" else None
        rec_state = r["recipient_gstin"][:2] if r["recipient_gstin_status"] == "valid" else None
        if sup_state and rec_state and r["tax_components_present"]:
            inter = sup_state != rec_state
            if inter and ((cg or 0) > 0 or (sg or 0) > 0):
                c.add("TAX_TYPE_STATE_MISMATCH", "MEDIUM", "POSSIBLE",
                      "GSTIN state codes differ but CGST/SGST was charged (inter-state supplies normally carry IGST).",
                      "Check the place of supply; special place-of-supply rules may apply.", ref,
                      {"row": ref, "supplier_state": sup_state, "recipient_state": rec_state})
            if not inter and (ig or 0) > 0:
                c.add("TAX_TYPE_STATE_MISMATCH", "MEDIUM", "POSSIBLE",
                      "GSTIN state codes match but IGST was charged (intra-state supplies normally carry CGST+SGST).",
                      "Check the place of supply; special place-of-supply rules may apply.", ref,
                      {"row": ref, "supplier_state": sup_state, "recipient_state": rec_state})

        rate, taxable, tax = r["rate"], r["taxable"], r["tax"]
        if rate is not None and rate not in rules.valid_rates:
            c.add("UNSUPPORTED_TAX_RATE", "MEDIUM", "CONFIRMED", "Tax rates not in the configured rate list.",
                  "Verify the rate; update the configured rate list if it is legitimately missing.", ref,
                  {"row": ref, "rate": _s(rate)})
        if taxable is not None and tax is not None and rate is not None:
            expected = q(taxable * rate / Decimal("100"))
            if abs(expected - tax) > tol:
                c.add("TAX_AMOUNT_MISMATCH", "HIGH", "CONFIRMED",
                      "Tax amount differs from taxable value x rate by more than the configured tolerance.",
                      "Recompute the tax on the source document; check rate, value and rounding.", ref,
                      {"row": ref, "taxable_value": _s(taxable), "rate": _s(rate), "expected_tax": _s(expected),
                       "reported_tax": _s(q(tax)), "tolerance": _s(tol)})
        elif taxable is not None and tax is not None and rate is None and taxable > 0:
            implied = q(tax / taxable * Decimal("100"))
            near = any(abs(implied - v) <= rules.rate_match_tolerance for v in rules.valid_rates)
            need("gst_rate", r, "tax arithmetic verification")
            if near:
                c.add("TAX_RATE_MISSING", "LOW", "CONFIRMED",
                      "Tax rate not stated; the implied rate (tax / taxable value) is shown for review only, not used.",
                      "Add the tax rate from the invoice.", ref, {"row": ref, "implied_rate_percent": _s(implied)})
            else:
                c.add("IMPLIED_TAX_RATE_UNUSUAL", "MEDIUM", "POSSIBLE",
                      "Tax rate not stated and tax / taxable value does not match any configured rate.",
                      "Check the tax amount and add the rate from the invoice.", ref,
                      {"row": ref, "implied_rate_percent": _s(implied)})
        elif tax is not None and tax > 0 and taxable is None:
            need("taxable_value", r, "tax arithmetic verification")
            c.add("TAXABLE_VALUE_MISSING", "MEDIUM", "CONFIRMED", "Tax is reported without a taxable value.",
                  "Add the taxable value so the tax can be verified.", ref)

        if taxable is not None and tax is not None and r["total_amount"] is not None:
            if abs(q(taxable + tax) - r["total_amount"]) > tol:
                c.add("INVOICE_TOTAL_UNRECONCILED", "MEDIUM", "CONFIRMED",
                      "Taxable value + tax does not equal the invoice total (round-off, other charges or errors).",
                      "Reconcile the invoice total with its components.", ref,
                      {"row": ref, "taxable_plus_tax": _s(q(taxable + tax)), "invoice_total": _s(r["total_amount"])})

        # Notes need the original document.
        if group in ("credit_notes", "debit_notes") and not r["original_invoice_ref"]:
            need("original_invoice_ref", r, "credit/debit note linkage")
            c.add("NOTE_WITHOUT_ORIGINAL_INVOICE", "HIGH", "CONFIRMED",
                  "Credit/debit notes without a reference to the original invoice.",
                  "Record the original invoice number and date for each note.", ref)

        # ITC evidence.
        if cat in rules.itc_categories and tax is not None and tax > 0 and not has_itc_evidence(r):
            c.add("ITC_EVIDENCE_INCOMPLETE", "HIGH", "POSSIBLE",
                  "Inward tax that lacks basic ITC evidence (valid supplier GSTIN, invoice number and date); excluded "
                  "from potential ITC.", "Collect the missing invoice details before claiming any credit.", ref)

    # Duplicates.
    invoice_rows = [r for r in features if r["in_base_currency"] and r["group"] in rules.invoice_groups and r["invoice_number"]]
    seen = defaultdict(list)
    for r in invoice_rows:
        own_series = r["group"] in ("outward", "credit_notes")
        party = "" if own_series else (r["supplier_gstin"] or (r["party_name"] or "").strip().lower())
        seen[(r["group"], party, str(r["invoice_number"]).strip().upper())].append(r)
    for (group, _, number), rows in seen.items():
        if len(rows) > 1:
            for r in rows:
                c.add("DUPLICATE_INVOICE_NUMBER", "HIGH", "CONFIRMED",
                      "The same invoice/note number appears more than once for the same series or supplier.",
                      "Check whether these rows are duplicates or need distinct numbers.", r["ref"],
                      {"group": group, "invoice_number": number, "rows": [x["ref"] for x in rows][:10]},
                      key=f"{group}|{number}")
    near = defaultdict(list)
    for r in invoice_rows:
        value = r["total_amount"] if r["total_amount"] is not None else r["taxable"]
        if value is not None and r["invoice_date"]:
            near[(r["group"], (r["party_name"] or "").strip().lower(), r["invoice_date"], str(q(value)))].append(r)
    for key, rows in near.items():
        numbers = {str(r["invoice_number"]).strip().upper() for r in rows}
        if len(rows) > 1 and len(numbers) > 1:
            for r in rows:
                c.add("POSSIBLE_DUPLICATE_DOCUMENT", "MEDIUM", "POSSIBLE",
                      "Different invoice numbers with the same party, date and amount.",
                      "Confirm these are separate transactions.", r["ref"],
                      {"group": key[0], "date": key[2], "amount": key[3], "rows": [x["ref"] for x in rows][:10]},
                      key="|".join(key))

    if any(r["category"] in rules.itc_categories and (r["tax"] or 0) > 0 for r in features):
        c.add("ITC_NOT_RECONCILED_EXTERNALLY", "INFO", "CONFIRMED",
              "Input tax credit has not been reconciled with GSTR-2B or GST portal data; none was supplied.",
              "Reconcile purchases with GSTR-2B before relying on any ITC figure.")

    missing_fields = [{"field": f, "required_for": why, "rows_missing": v["rows"], "source_rows": v["refs"]}
                      for (f, why), v in sorted(missing.items())]
    return c.build(), missing_fields


def evidence_route(features: List[Dict[str, Any]], discrepancies: List[Discrepancy],
                   gst_calcs: List[Dict[str, Any]]) -> Tuple[str, str, List[str]]:
    """Decide (route, report status, reasons). Route is 'sufficient' or 'review'."""
    gst_rows = [r for r in features if r["in_base_currency"] and r["group"] in ("outward", "inward", "credit_notes",
                                                                                 "debit_notes", "expenses")
                and (r["taxable"] is not None or r["tax"] is not None)]
    reasons = []
    if not gst_rows:
        reasons.append("No outward, inward, note or expense rows with taxable value or tax were found.")
        return "review", "INSUFFICIENT_DATA", reasons
    blocking = [d for d in discrepancies if d.severity in ("HIGH", "MEDIUM")]
    if blocking:
        reasons.append(f"{len(blocking)} high/medium discrepancy groups need review.")
    incomplete = [c["name"] for c in gst_calcs if c["status"] in ("INCOMPLETE", "UNRESOLVED")]
    if incomplete:
        reasons.append("Incomplete calculations: " + ", ".join(incomplete[:8]))
    if reasons:
        return "review", "REVIEW_REQUIRED", reasons
    return "sufficient", "ANALYSIS_COMPLETE", ["All configured checks passed on the supplied data."]


def filing_readiness(status: str, discrepancies: List[Discrepancy], reasons: List[str]) -> Dict[str, Any]:
    confirmed_high = [d.code for d in discrepancies if d.severity == "HIGH" and d.status == "CONFIRMED"]
    if status == "INSUFFICIENT_DATA" or confirmed_high:
        level = "NOT_READY"
    elif status == "REVIEW_REQUIRED":
        level = "REVIEW_REQUIRED"
    else:
        level = "PREPARED_FOR_PROFESSIONAL_REVIEW"
    return {"level": level, "reasons": reasons + ([f"Confirmed high-severity issues: {', '.join(sorted(set(confirmed_high)))}"]
                                                  if confirmed_high else []),
            "not_filed": True,
            "note": "This analysis prepares data for review. It is not a filed return, and readiness does not depend "
                    "on the narrative analysis succeeding."}
