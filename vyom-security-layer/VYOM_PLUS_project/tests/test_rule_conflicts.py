"""Conflict, ambiguity and identifier-robustness tests for the rule engine.

All records are synthetic and hand-built; none is taken from the evaluation
workbook, so these tests cannot be satisfied by fitting that workbook.
"""

import unittest

import pandas as pd

from vyom import legacy_rule_engine
from vyom.rule_engine import (
    AMBIGUOUS,
    NO_RULE,
    REVIEW_REQUIRED,
    RULE_MATCH,
    RuleDecision,
    assess_transaction,
    evaluate_transaction_rules,
)


PAYMENT = {
    "Payment ID": "PMT-000101",
    "Payer Organization": "Alpha Traders",
    "Payee Organization": "Beta Supplies",
    "Payment Amount": 12500.0,
    "Payment Type": "Bank Transfer",
}
CONTRA = {
    "Contra ID": "CTR-000201",
    "Source Account": "Main Current Account",
    "Destination Account": "Petty Cash",
    "Transfer Amount": 5000.0,
}
DEBIT_NOTE = {
    "Document Number": "DBN-000301",
    "Vendor Name": "Beta Supplies",
    "Units Returned": -4,
    "Reason for Return": "Damaged in transit",
    "Original Doc Ref": "PUR-000302",
}
CREDIT_NOTE = {
    "Document Number": "CRN-000401",
    "Vendor Name": "Gamma Retail",
    "Units Returned": -2,
    "Reason for Return": "Customer complaint",
    "Original Invoice Ref": "SAL-000402",
}
REJECTION_IN = {
    "Rejection Note No": "RJN-IN-000501",
    "Item Rejected": "Bearings",
    "Quantity Rejected": 10,
    "Rejection Reason": "Out of tolerance",
    "GRN Reference": "GRN-000502",
    "Receiving Company": "Alpha Traders",
}
REJECTION_OUT = {
    "Rejection Note No": "RJN-OUT-000601",
    "Item Rejected": "Panels",
    "Quantity Rejected": 3,
    "Rejection Reason": "Wrong specification",
    "DN Reference": "DC-000602",
    "Customer": "Gamma Retail",
}


def record(base=None, drop=(), **changes):
    data = dict(base or {})
    for field in drop:
        data.pop(field, None)
    data.update(changes)
    return pd.Series(data, dtype=object)


class RuleDecisionAssertions(unittest.TestCase):

    def assertDecision(self, row, status, category=None, candidates=None):
        decision = assess_transaction(row)
        self.assertEqual(decision.status, status, decision.explanation)
        self.assertEqual(decision.category, category, decision.explanation)
        if candidates is not None:
            self.assertSetEqual(set(decision.candidates), set(candidates), decision.explanation)
        return decision

    def assertModelKept(self, row, status):
        """Without a RULE_MATCH the caller's model prediction is returned and no rule is applied."""
        pred, explanation, applied = evaluate_transaction_rules(row, base_prediction="Model Guess")
        self.assertEqual(pred, "Model Guess")
        self.assertFalse(applied)
        if status != NO_RULE:
            self.assertTrue(explanation.startswith(status), explanation)


class TestPaymentContraConflicts(RuleDecisionAssertions):

    def test_clean_records_match(self):
        self.assertDecision(record(PAYMENT), RULE_MATCH, "Payment")
        self.assertDecision(record(CONTRA), RULE_MATCH, "Contra")

    def test_stray_contra_id_on_payment_requires_review(self):
        row = record(PAYMENT, **{"Contra ID": "CTR-000102"})
        self.assertDecision(row, REVIEW_REQUIRED, candidates={"Contra", "Payment"})
        self.assertModelKept(row, REVIEW_REQUIRED)
        # The audited first-match engine let the identifier override the payment evidence.
        self.assertEqual(legacy_rule_engine.evaluate_transaction_rules(row)[0], "Contra")

    def test_payment_id_on_account_transfer_requires_review(self):
        row = record(CONTRA, **{"Payment ID": "PMT-000202"})
        self.assertDecision(row, REVIEW_REQUIRED, candidates={"Contra", "Payment"})

    def test_transfer_and_payment_fields_without_identifiers_require_review(self):
        row = record(CONTRA, drop=["Contra ID"], **{"Payment Amount": 5000.0, "Payee Organization": "Beta Supplies"})
        self.assertDecision(row, REVIEW_REQUIRED, candidates={"Contra", "Payment"})

    def test_payment_style_value_in_contra_id_column_does_not_create_payment(self):
        row = record(CONTRA, **{"Contra ID": "PMT-000203"})
        decision = self.assertDecision(row, RULE_MATCH, "Contra")
        self.assertTrue(all(e.basis == "fields" for e in decision.evidence))


class TestReturnConflicts(RuleDecisionAssertions):

    def test_clean_records_match(self):
        self.assertDecision(record(DEBIT_NOTE), RULE_MATCH, "Purchase Return / Debit Note")
        self.assertDecision(record(CREDIT_NOTE), RULE_MATCH, "Sales Return / Credit Note")

    def test_debit_identifier_on_sales_return_requires_review(self):
        row = record(CREDIT_NOTE, **{"Document Number": "DBN-000403"})
        self.assertDecision(row, REVIEW_REQUIRED,
                            candidates={"Purchase Return / Debit Note", "Sales Return / Credit Note"})
        self.assertModelKept(row, REVIEW_REQUIRED)
        self.assertEqual(legacy_rule_engine.evaluate_transaction_rules(row)[0], "Purchase Return / Debit Note")

    def test_credit_identifier_on_purchase_return_requires_review(self):
        row = record(DEBIT_NOTE, **{"Document Number": "CRN-000303"})
        self.assertDecision(row, REVIEW_REQUIRED,
                            candidates={"Purchase Return / Debit Note", "Sales Return / Credit Note"})

    def test_conflicting_original_references_require_review(self):
        row = record(DEBIT_NOTE, drop=["Document Number"], **{"Original Invoice Ref": "SAL-000304"})
        self.assertDecision(row, REVIEW_REQUIRED,
                            candidates={"Purchase Return / Debit Note", "Sales Return / Credit Note"})

    def test_return_without_direction_is_ambiguous(self):
        row = record(DEBIT_NOTE, drop=["Document Number", "Original Doc Ref"])
        self.assertDecision(row, AMBIGUOUS,
                            candidates={"Purchase Return / Debit Note", "Sales Return / Credit Note"})
        self.assertModelKept(row, AMBIGUOUS)

    def test_invoice_number_with_return_details_is_not_an_invoice(self):
        row = record(DEBIT_NOTE, drop=["Original Doc Ref"], **{"Document Number": "PUR-000305"})
        self.assertDecision(row, AMBIGUOUS,
                            candidates={"Purchase Return / Debit Note", "Sales Return / Credit Note"})


class TestRejectionDirectionConflicts(RuleDecisionAssertions):

    def test_clean_records_match(self):
        self.assertDecision(record(REJECTION_IN), RULE_MATCH, "Rejection In")
        self.assertDecision(record(REJECTION_OUT), RULE_MATCH, "Rejection Out")

    def test_inward_note_with_outward_evidence_requires_review(self):
        row = record(REJECTION_IN, **{"Customer": "Gamma Retail", "DN Reference": "DC-000503"})
        self.assertDecision(row, REVIEW_REQUIRED, candidates={"Rejection In", "Rejection Out"})
        self.assertEqual(legacy_rule_engine.evaluate_transaction_rules(row)[0], "Rejection In")

    def test_outward_note_with_inward_evidence_requires_review(self):
        row = record(REJECTION_OUT, **{"GRN Reference": "GRN-000603", "Receiving Company": "Alpha Traders"})
        self.assertDecision(row, REVIEW_REQUIRED, candidates={"Rejection In", "Rejection Out"})

    def test_both_directions_without_note_number_require_review(self):
        row = record(REJECTION_IN, drop=["Rejection Note No"],
                     **{"Customer": "Gamma Retail", "DN Reference": "DC-000504"})
        self.assertDecision(row, REVIEW_REQUIRED, candidates={"Rejection In", "Rejection Out"})
        # The audited engine resolved this silently through rule order.
        self.assertEqual(legacy_rule_engine.evaluate_transaction_rules(row)[0], "Rejection Out")

    def test_rejection_details_without_direction_are_ambiguous(self):
        row = record({k: REJECTION_IN[k] for k in ("Item Rejected", "Quantity Rejected", "Rejection Reason")},
                     **{"Supplier": "Beta Supplies"})
        self.assertDecision(row, AMBIGUOUS, candidates={"Rejection In", "Rejection Out"})
        self.assertModelKept(row, AMBIGUOUS)


class TestMissingIdentifiers(RuleDecisionAssertions):

    def test_inward_rejection_without_note_number_matches_on_fields(self):
        row = record(REJECTION_IN, drop=["Rejection Note No", "GRN Reference"])
        decision = self.assertDecision(row, RULE_MATCH, "Rejection In")
        self.assertTrue(all(e.basis == "fields" for e in decision.evidence))

    def test_receipt_note_without_grn_number_matches_on_fields(self):
        row = record({"Item Received": "Bearings", "Quantity Received": 40, "Receiving Company": "Alpha Traders"})
        self.assertDecision(row, RULE_MATCH, "Receipt Note")

    def test_return_direction_from_reference_when_document_number_missing(self):
        row = record(CREDIT_NOTE, drop=["Document Number"])
        self.assertDecision(row, RULE_MATCH, "Sales Return / Credit Note")

    def test_order_fields_without_order_number_leave_decision_to_model(self):
        # Known gap: order rules require an order number, so no rule decides here.
        row = record({"Supplier": "Beta Supplies", "Quantity Required": 200, "Promised Delivery": "2026-11-01"})
        self.assertDecision(row, NO_RULE, candidates=set())
        self.assertModelKept(row, NO_RULE)

    def test_empty_record_has_no_rule_evidence(self):
        self.assertDecision(record({}), NO_RULE, candidates=set())
        self.assertEqual(evaluate_transaction_rules(record({}))[0], "Unclassified")


class TestMisleadingIdentifierPrefixes(RuleDecisionAssertions):

    def test_identifier_prefix_alone_is_insufficient(self):
        for row, category in [
            (record({"Document Number": "DBN-000701"}), "Purchase Return / Debit Note"),
            (record({"Contra ID": "CTR-000702"}), "Contra"),
            (record({"Document Number": "PUR-000703", "Vendor Name": "Beta Supplies"}), "Purchase"),
        ]:
            self.assertDecision(row, AMBIGUOUS, candidates={category})
            self.assertModelKept(row, AMBIGUOUS)

    def test_inward_prefix_on_outward_record_requires_review(self):
        row = record(REJECTION_OUT, **{"Rejection Note No": "RJN-IN-000604"})
        self.assertDecision(row, REVIEW_REQUIRED, candidates={"Rejection In", "Rejection Out"})
        self.assertEqual(legacy_rule_engine.evaluate_transaction_rules(row)[0], "Rejection In")

    def test_outward_prefix_on_inward_record_requires_review(self):
        row = record(REJECTION_IN, **{"Rejection Note No": "RJN-OUT-000505"})
        self.assertDecision(row, REVIEW_REQUIRED, candidates={"Rejection In", "Rejection Out"})

    def test_prefix_of_another_type_in_wrong_column_is_ignored(self):
        row = record({"Stock Count ID": "SA000801", "Book Quantity": 120, "Counted Quantity": 117})
        self.assertDecision(row, RULE_MATCH, "Physical Stock")

    def test_identifier_cannot_override_contradictory_fields(self):
        # Payment fields with a receipt identifier: the identifier does not win.
        row = record(PAYMENT, drop=["Payment ID"], **{"Receipt ID": "RCP-000901"})
        self.assertDecision(row, REVIEW_REQUIRED, candidates={"Payment", "Receipt"})


class TestDecisionSeparation(unittest.TestCase):

    ROWS = [PAYMENT, CONTRA, DEBIT_NOTE, CREDIT_NOTE, REJECTION_IN, REJECTION_OUT,
            {**PAYMENT, "Contra ID": "CTR-000103"}, {"Document Number": "DBN-000702"}, {}]

    def test_decision_carries_status_not_probability(self):
        self.assertSetEqual(set(RuleDecision.__dataclass_fields__),
                            {"status", "category", "candidates", "evidence", "explanation"})
        for data in self.ROWS:
            decision = assess_transaction(record(data))
            self.assertIn(decision.status, {RULE_MATCH, REVIEW_REQUIRED, AMBIGUOUS, NO_RULE})
            self.assertEqual(decision.category is not None, decision.status == RULE_MATCH)

    def test_decision_ignores_label_and_output_columns(self):
        for data in self.ROWS:
            plain = assess_transaction(record(data))
            injected = assess_transaction(record(data, **{
                "Voucher Category": "Journal", "Correct": True, "Predicted Voucher Category": "Journal"}))
            self.assertEqual(plain, injected)

    def test_decision_is_deterministic(self):
        for data in self.ROWS:
            self.assertEqual(assess_transaction(record(data)), assess_transaction(record(data)))


if __name__ == "__main__":
    unittest.main()
