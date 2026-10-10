"""Deterministic GST layer: rules, input normalisation, accounting and validation."""

from decimal import Decimal
import unittest

import pandas as pd

from vyom.gst import accounting, normalize, validation
from vyom.gst.config import AnalysisLimits, ConfigError, load_settings
from vyom.gst.rules import TAXONOMY, GstRules, gstin_status
from vyom.gst.schemas import VoucherClassification

from gst_fixtures import BUSINESS, CUSTOMER, OTHER_STATE_SUPPLIER, SUPPLIER, clean_records, workbook

LIMITS = AnalysisLimits()
RULES = GstRules()


def features_for(records, categories, business=BUSINESS, ambiguous=()):
    tx, _ = normalize.normalize_records(records, LIMITS)
    cl = [VoucherClassification(source_ref=t.source_ref, category=c, score_uncalibrated=0.9,
                                ambiguous=t.source_ref in ambiguous) for t, c in zip(tx, categories)]
    return accounting.extract_features(tx, cl, RULES, business)


def codes(discrepancies):
    return {d.code for d in discrepancies}


class TestRulesAndConfig(unittest.TestCase):

    def test_gstin_validation(self):
        self.assertEqual(gstin_status("27AAPFU0939F1ZV"), "valid")
        self.assertEqual(gstin_status("27AAPFU0939F1ZX"), "invalid_checksum")
        self.assertEqual(gstin_status("27AAPFU0939F"), "invalid_format")
        self.assertEqual(gstin_status(None), "missing")

    def test_taxonomy_matches_label_guidelines(self):
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / "data/synthetic/synthetic_voucher_dataset_v5_review_ready.xlsx"
        guide = pd.read_excel(path, sheet_name="label_guidelines_v5")["voucher_type"].str.strip().tolist()
        self.assertEqual(len(TAXONOMY), 27)
        self.assertSetEqual(set(TAXONOMY), set(guide))

    def test_settings_hide_key_and_validate_numbers(self):
        s = load_settings({"GROQ_API_KEY": "gsk_secret_abc", "GROQ_TEMPERATURE": "0"})
        self.assertTrue(s.groq.configured)
        self.assertNotIn("gsk_secret_abc", repr(s))
        self.assertNotIn("gsk_secret_abc", str(s.groq.public()))
        self.assertFalse(load_settings({}).groq.configured)
        with self.assertRaises(ConfigError):
            load_settings({"GROQ_MAX_RETRIES": "50"})
        with self.assertRaises(ConfigError):
            load_settings({"GROQ_TIMEOUT": "abc"})


class TestNormalization(unittest.TestCase):

    def test_json_records_map_fields_and_drop_labels(self):
        rows, warnings = normalize.normalize_records(
            [{"Invoice No": "A1", "Taxable Value": "₹1,234.50", "Voucher Category": "Sales", "Notes": "x"}], LIMITS)
        self.assertEqual(rows[0].fields["taxable_value"], "1234.50")
        self.assertNotIn("Voucher Category", rows[0].raw)
        self.assertTrue(any("Voucher Category" in w for w in warnings))

    def test_money_parsing(self):
        self.assertEqual(normalize.parse_money("(100.25)"), Decimal("-100.25"))
        self.assertEqual(normalize.parse_money("INR 2,00,000"), Decimal("200000"))
        self.assertIsNone(normalize.parse_money("-"))
        with self.assertRaises(ValueError):
            normalize.parse_money("abc")

    def test_unparseable_cells_are_reported_not_invented(self):
        rows, _ = normalize.normalize_records([{"Taxable Value": "twelve", "Invoice Date": "not a date"}], LIMITS)
        self.assertNotIn("taxable_value", rows[0].fields)
        self.assertNotIn("invoice_date", rows[0].fields)
        self.assertEqual(len(rows[0].parse_warnings), 2)

    def test_json_validation_errors(self):
        with self.assertRaises(normalize.InputValidationError):
            normalize.normalize_records([], LIMITS)
        with self.assertRaises(normalize.InputValidationError):
            normalize.normalize_records(["not an object"], LIMITS)
        with self.assertRaises(normalize.InputValidationError):
            normalize.parse_json_string("{not json", LIMITS)
        with self.assertRaises(normalize.InputValidationError):
            normalize.parse_json_string('{"rows": []}', LIMITS)
        with self.assertRaises(normalize.InputValidationError):
            normalize.normalize_records([{"a": 1}] * (LIMITS.max_rows + 1), LIMITS)
        self.assertEqual(normalize.parse_json_string('{"records": [{"a": 1}]}', LIMITS), [{"a": 1}])

    def test_workbook_multiple_sheets_keep_references(self):
        content = workbook(Sales=clean_records()[:1], Purchases=clean_records()[1:], Empty=[])
        rows, warnings = normalize.normalize_workbook(content, "books.xlsx", LIMITS)
        self.assertEqual([r.source_ref for r in rows], ["Sales!R2", "Purchases!R2"])
        self.assertTrue(any("Empty" in w for w in warnings))

    def test_workbook_errors(self):
        with self.assertRaises(normalize.InputValidationError):
            normalize.normalize_workbook(b"", "x.xlsx", LIMITS)
        with self.assertRaises(normalize.InputValidationError):
            normalize.normalize_workbook(b"this is not excel", "x.xlsx", LIMITS)
        with self.assertRaises(normalize.InputValidationError):
            normalize.normalize_workbook(workbook(Only=[]), "x.xlsx", LIMITS)
        with self.assertRaises(normalize.InputValidationError):
            normalize.normalize_workbook(b"abc", "x.pdf", LIMITS)


class TestAccounting(unittest.TestCase):

    def calc(self, result, name):
        for section in ("accounting_summary", "gst_summary"):
            for c in result[section]["calculations"]:
                if c["name"] == name:
                    return c
        raise KeyError(name)

    def test_totals_and_net_liability(self):
        f = features_for(clean_records(), ["Sales", "Purchase"])
        r = accounting.calculate(f, RULES)
        self.assertEqual(self.calc(r, "outward_total_tax")["value"], "1800.00")
        self.assertEqual(self.calc(r, "itc_tax_with_basic_evidence")["value"], "900.00")
        net = self.calc(r, "potential_net_gst_liability")
        self.assertEqual((net["value"], net["status"]), ("900.00", "COMPLETE"))
        self.assertIn("Sales", r["accounting_summary"]["counts_by_category"])
        self.assertEqual(self.calc(r, "credit_notes_total_tax")["status"], "NOT_APPLICABLE")

    def test_rounding_half_up_after_summation(self):
        recs = [{"Invoice No": f"S{i}", "Taxable Value": "0.005", "Tax Amount": "0.005"} for i in range(3)]
        r = accounting.calculate(features_for(recs, ["Sales"] * 3), RULES)
        self.assertEqual(self.calc(r, "outward_taxable_value")["value"], "0.02")  # 0.015 -> 0.02

    def test_missing_values_are_not_invented(self):
        recs = [{"Invoice No": "S1", "Taxable Value": 100, "Tax Amount": 18}, {"Invoice No": "S2"}]
        r = accounting.calculate(features_for(recs, ["Sales", "Sales"]), RULES)
        tax = self.calc(r, "outward_total_tax")
        self.assertEqual((tax["value"], tax["status"], tax["rows_missing"]), ("18.00", "INCOMPLETE", 1))
        none = accounting.calculate(features_for([{"Invoice No": "S3"}], ["Sales"]), RULES)
        self.assertEqual(self.calc(none, "outward_total_tax")["status"], "UNRESOLVED")
        self.assertIsNone(self.calc(none, "outward_total_tax")["value"])

    def test_itc_requires_evidence_not_just_label(self):
        recs = [{"Invoice No": "P1", "Invoice Date": "2026-09-01", "Taxable Value": 1000, "Tax Amount": 180}]
        r = accounting.calculate(features_for(recs, ["Purchase"]), RULES)
        self.assertEqual(self.calc(r, "itc_tax_with_basic_evidence")["status"], "NOT_APPLICABLE")
        self.assertEqual(self.calc(r, "itc_tax_without_basic_evidence")["value"], "180.00")

    def test_ambiguous_classification_makes_totals_incomplete(self):
        f = features_for(clean_records(), ["Sales", "Purchase"], ambiguous=("records[1]",))
        r = accounting.calculate(f, RULES)
        itc = self.calc(r, "itc_tax_with_basic_evidence")
        self.assertEqual((itc["value"], itc["status"]), ("900.00", "INCOMPLETE"))
        self.assertTrue(any("ambiguous" in n for n in itc["notes"]))
        self.assertEqual(self.calc(r, "potential_net_gst_liability")["status"], "INCOMPLETE")
        self.assertEqual(self.calc(r, "outward_total_tax")["status"], "COMPLETE")

    def test_foreign_currency_excluded(self):
        recs = clean_records() + [{"Invoice No": "E1", "Currency": "USD", "Taxable Value": 99}]
        r = accounting.calculate(features_for(recs, ["Sales", "Purchase", "Sales"]), RULES)
        self.assertEqual(r["accounting_summary"]["rows_excluded_foreign_currency"], 1)
        self.assertEqual(self.calc(r, "outward_taxable_value")["value"], "10000.00")

    def test_receipts_are_not_sales(self):
        recs = [{"Received Amount": 5000}]
        r = accounting.calculate(features_for(recs, ["Receipt"]), RULES)
        self.assertEqual(self.calc(r, "receipts_amount")["value"], "5000.00")
        self.assertEqual(self.calc(r, "outward_taxable_value")["status"], "NOT_APPLICABLE")

    def test_balance_sheet_is_gated(self):
        r = accounting.calculate(features_for(clean_records(), ["Sales", "Purchase"]), RULES)
        self.assertFalse(r["balance_summary"]["available"])
        recs = [{"Ledger": "Bank", "Opening Balance": 100, "Debit": 50, "Credit": 20, "Closing Balance": 130}]
        r2 = accounting.calculate(features_for(recs, ["Journal"]), RULES)
        self.assertTrue(r2["balance_summary"]["ledgers"][0]["reconciles"])


class TestValidation(unittest.TestCase):

    def run_checks(self, records, categories, business=BUSINESS, ambiguous=()):
        found, missing = validation.run_checks(features_for(records, categories, business, ambiguous), RULES, business)
        return found, missing

    def test_clean_records_have_only_info_findings(self):
        found, missing = self.run_checks(clean_records(), ["Sales", "Purchase"])
        self.assertEqual({d.severity for d in found}, {"INFO"})
        self.assertEqual(missing, [])

    def test_missing_gstin_and_invoice_fields(self):
        recs = [{"Taxable Value": 100, "GST Rate": 18, "Tax Amount": 18}]
        found, missing = self.run_checks(recs, ["Purchase"])
        self.assertTrue({"SUPPLIER_GSTIN_MISSING", "INVOICE_NUMBER_MISSING", "INVOICE_DATE_MISSING",
                         "ITC_EVIDENCE_INCOMPLETE"} <= codes(found))
        self.assertEqual({m["field"] for m in missing} >= {"supplier_gstin", "invoice_number", "invoice_date"}, True)
        status = {d.code: d.status for d in found}
        self.assertEqual(status["SUPPLIER_GSTIN_MISSING"], "CONFIRMED")
        self.assertEqual(status["ITC_EVIDENCE_INCOMPLETE"], "POSSIBLE")

    def test_duplicates(self):
        dup = clean_records()[:1] * 2
        self.assertIn("DUPLICATE_INVOICE_NUMBER", codes(self.run_checks(dup, ["Sales", "Sales"])[0]))
        near = [dict(clean_records()[1]), dict(clean_records()[1], **{"Invoice No": "P-78"})]
        self.assertIn("POSSIBLE_DUPLICATE_DOCUMENT", codes(self.run_checks(near, ["Purchase", "Purchase"])[0]))

    def test_conflicting_tax_components(self):
        rec = dict(clean_records()[0], CGST=900, SGST=800, IGST=100)
        found = codes(self.run_checks([rec], ["Sales"])[0])
        self.assertTrue({"CGST_SGST_UNEQUAL", "IGST_WITH_CGST_SGST"} <= found)
        inter = dict(clean_records()[1], **{"Supplier GSTIN": OTHER_STATE_SUPPLIER})
        self.assertIn("TAX_TYPE_STATE_MISMATCH", codes(self.run_checks([inter], ["Purchase"])[0]))

    def test_tax_arithmetic_and_rates(self):
        wrong = dict(clean_records()[0], CGST=950, SGST=950, **{"Invoice Value": 11900})
        self.assertIn("TAX_AMOUNT_MISMATCH", codes(self.run_checks([wrong], ["Sales"])[0]))
        odd = dict(clean_records()[0], **{"GST Rate": 17})
        self.assertIn("UNSUPPORTED_TAX_RATE", codes(self.run_checks([odd], ["Sales"])[0]))
        total = dict(clean_records()[0], **{"Invoice Value": 12000})
        self.assertIn("INVOICE_TOTAL_UNRECONCILED", codes(self.run_checks([total], ["Sales"])[0]))

    def test_notes_need_original_invoice(self):
        note = {"Kind": "Sales Return / Credit Note", "Note Number": "CN1", "Note Date": "2026-09-09",
                "Customer GSTIN": CUSTOMER, "Taxable Value": 100, "GST Rate": 18, "Tax Amount": 18}
        self.assertIn("NOTE_WITHOUT_ORIGINAL_INVOICE", codes(self.run_checks([note], ["Sales Return / Credit Note"])[0]))
        linked = dict(note, **{"Original Invoice Ref": "S-001"})
        self.assertNotIn("NOTE_WITHOUT_ORIGINAL_INVOICE", codes(self.run_checks([linked], ["Sales Return / Credit Note"])[0]))

    def test_classification_evidence(self):
        found = codes(self.run_checks(clean_records(), ["Sales", "Purchase"], ambiguous=("records[0]",))[0])
        self.assertIn("AMBIGUOUS_CLASSIFICATION", found)
        order = [{"PO Number": "PO1", "Tax Amount": 18}]
        self.assertIn("TAX_ON_NON_TAX_DOCUMENT", codes(self.run_checks(order, ["Purchase Order"])[0]))

    def test_invalid_business_gstin(self):
        found = codes(self.run_checks(clean_records(), ["Sales", "Purchase"], business="27AAAAA0000A1Z0")[0])
        self.assertIn("BUSINESS_GSTIN_INVALID", found)


if __name__ == "__main__":
    unittest.main()
