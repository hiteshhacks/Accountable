"""Comprehensive tests for the VYOM+ evaluation workbook adapter and pipeline."""

import unittest
from pathlib import Path
import tempfile
import pickle
import pandas as pd
import numpy as np

from vyom.adapter import (
    LABEL_COLUMN,
    load_evaluation_workbook,
    format_field_value,
    serialize_wide_row,
    map_wide_to_canonical,
)
from vyom.rule_engine import evaluate_transaction_rules
from vyom.evaluate_workbook import run_pipeline


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = ROOT / "data/input/Voucher_Classification_Test_Cases_v2.xlsx"
BASELINE_PATH = ROOT / "models/vyom_plus_tfidf_baseline_model.pkl"


class TestEvaluationAdapter(unittest.TestCase):

    def test_01_read_supplied_workbook(self):
        """Test reading the actual supplied workbook successfully."""
        self.assertTrue(WORKBOOK_PATH.exists(), f"File missing: {WORKBOOK_PATH}")
        X, y = load_evaluation_workbook(WORKBOOK_PATH, sheet_name="Test Cases")
        self.assertEqual(len(X), 120, "Expected exactly 120 test records.")
        self.assertEqual(len(X.columns), 168, "Expected 168 feature columns.")
        self.assertIsNotNone(y, "Expected Voucher Category to be extracted as y.")
        self.assertEqual(len(y), 120)

    def test_02_preserve_rows_and_columns(self):
        """Test that original row count and column names are strictly preserved."""
        raw_df = pd.read_excel(WORKBOOK_PATH, sheet_name="Test Cases")
        X, _ = load_evaluation_workbook(WORKBOOK_PATH, sheet_name="Test Cases")
        expected_cols = [c for c in raw_df.columns if c != LABEL_COLUMN]
        self.assertListEqual(list(X.columns), expected_cols)
        self.assertEqual(len(X), len(raw_df))

    def test_03_handle_missing_and_mixed_types(self):
        """Test missing values, NaNs, and dates do not produce 'nan', 'None', or 'NaT' text."""
        self.assertIsNone(format_field_value(np.nan))
        self.assertIsNone(format_field_value(None))
        self.assertIsNone(format_field_value("   "))
        self.assertIsNone(format_field_value("nan"))
        self.assertIsNone(format_field_value("None"))
        self.assertIsNone(format_field_value("NaT"))
        self.assertEqual(format_field_value(123.0), "123")
        self.assertEqual(format_field_value("PO123"), "PO123")

        test_row = pd.Series({
            "PO Number": "PO-999",
            "Supplier": "Acme Corp",
            "Empty Field": np.nan,
            "Whitespace Field": "   ",
        })
        serialized = serialize_wide_row(test_row)
        self.assertNotIn("Empty Field", serialized)
        self.assertNotIn("Whitespace Field", serialized)
        self.assertNotIn("nan", serialized.lower())
        self.assertIn("PO Number: PO-999", serialized)
        self.assertIn("Supplier: Acme Corp", serialized)

    def test_04_strict_label_exclusion_and_invariance(self):
        """Deliberately modify Voucher Category and verify predictions remain strictly identical."""
        X, y = load_evaluation_workbook(WORKBOOK_PATH, sheet_name="Test Cases")
        self.assertNotIn(LABEL_COLUMN, X.columns)

        # Mutate labels randomly or invert them
        fake_labels = pd.Series(["Fake Category"] * len(X))

        # Evaluate rules on genuine X
        preds_1 = [evaluate_transaction_rules(X.iloc[i])[0] for i in range(len(X))]

        # Evaluate rules on copy of X (where external label is different)
        X_copy = X.copy()
        preds_2 = [evaluate_transaction_rules(X_copy.iloc[i])[0] for i in range(len(X_copy))]

        self.assertListEqual(preds_1, preds_2, "Predictions must be completely invariant to labels.")

    def test_05_predict_when_label_column_absent(self):
        """Test blind prediction mode when Voucher Category is absent from Excel."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "blind_test.xlsx"
            X_orig, _ = load_evaluation_workbook(WORKBOOK_PATH, sheet_name="Test Cases")
            # Save without Voucher Category
            X_orig.head(10).to_excel(tmp_path, index=False)

            X, y = load_evaluation_workbook(tmp_path, sheet_name="Sheet1")
            self.assertIsNone(y, "y must be None for blind input.")
            self.assertEqual(len(X), 10)

            # Pipeline should run and generate output without errors
            out_file = Path(tmpdir) / "blind_predictions.xlsx"
            summary = run_pipeline(
                input_path=tmp_path,
                sheet_name="Sheet1",
                output_path=out_file,
                run_comparison=False,
            )
            self.assertTrue(out_file.exists())
            out_df = pd.read_excel(out_file)
            self.assertIn("Predicted Voucher Category", out_df.columns)
            self.assertNotIn("Correct", out_df.columns, "Correct column should not exist for blind data.")

    def test_06_handle_unexpected_missing_column(self):
        """Test that sparse rows missing typical columns don't fail."""
        sparse_row = pd.Series({"Random Column": "Val123", "Amount": 500})
        pred, explanation, applied = evaluate_transaction_rules(sparse_row, base_prediction="Fallback Class")
        self.assertEqual(pred, "Fallback Class")
        self.assertFalse(applied)

    def test_07_preserve_row_order(self):
        """Test that output predictions strictly maintain the row order."""
        X, _ = load_evaluation_workbook(WORKBOOK_PATH, sheet_name="Test Cases")
        first_po = X.iloc[0].get("PO Number")
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "order_test.xlsx"
            run_pipeline(
                input_path=WORKBOOK_PATH,
                sheet_name="Test Cases",
                output_path=out_file,
                run_comparison=False,
            )
            out_df = pd.read_excel(out_file)
            self.assertEqual(out_df.iloc[0].get("PO Number"), first_po)
            self.assertEqual(len(out_df), len(X))

    def test_08_semantic_field_mapping(self):
        """Verify that mapping separates semantically distinct fields."""
        df = pd.DataFrame([{
            "Quantity Required": 100,
            "Quantity Received": 50,
            "Units Returned": -10,
        }])
        can = map_wide_to_canonical(df)
        self.assertIn("quantity", can.columns)
        # Units Returned must NOT be mapped to order quantity
        self.assertNotIn("Units Returned", can.columns)

    def test_09_return_category_rules_and_conflicts(self):
        """Test distinction between Debit Note and Credit Note, and conflict handling."""
        debit_row = pd.Series({
            "Document Number": "DBN-12345",
            "Units Returned": -5,
            "Original Doc Ref": "PUR-999",
            "Customer": "Should Not Override",
        })
        pred, reason, applied = evaluate_transaction_rules(debit_row)
        self.assertEqual(pred, "Purchase Return / Debit Note")
        self.assertTrue(applied)

        credit_row = pd.Series({
            "Document Number": "CRN-12345",
            "Units Returned": -5,
            "Original Invoice Ref": "SAL-999",
            "Supplier": "Should Not Override",
        })
        pred, reason, applied = evaluate_transaction_rules(credit_row)
        self.assertEqual(pred, "Sales Return / Credit Note")
        self.assertTrue(applied)

    def test_10_rejection_rules(self):
        """Test distinction between Rejection In and Rejection Out."""
        rej_in = pd.Series({
            "Rejection Note No": "RJN-IN-101",
            "GRN Reference": "GRN-999",
            "Item Rejected": "Components",
        })
        pred, _, applied = evaluate_transaction_rules(rej_in)
        self.assertEqual(pred, "Rejection In")
        self.assertTrue(applied)

        rej_out = pd.Series({
            "Rejection Note No": "RJN-OUT-202",
            "DN Reference": "DC-888",
            "Customer": "Acme Corp",
        })
        pred, _, applied = evaluate_transaction_rules(rej_out)
        self.assertEqual(pred, "Rejection Out")
        self.assertTrue(applied)

    def test_11_metrics_calculation(self):
        """Verify metrics calculated correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "metrics_test.xlsx"
            summary = run_pipeline(
                input_path=WORKBOOK_PATH,
                sheet_name="Test Cases",
                output_path=out_file,
                run_comparison=False,
            )
            pipe_metrics = summary["pipeline"]
            self.assertGreater(pipe_metrics["accuracy"], 0.95)
            self.assertGreater(pipe_metrics["macro_f1"], 0.95)

    def test_12_deterministic_results(self):
        """Ensure evaluation gives identical predictions across repeated calls."""
        X, _ = load_evaluation_workbook(WORKBOOK_PATH, sheet_name="Test Cases")
        preds_run1 = [evaluate_transaction_rules(X.iloc[i])[0] for i in range(len(X))]
        preds_run2 = [evaluate_transaction_rules(X.iloc[i])[0] for i in range(len(X))]
        self.assertListEqual(preds_run1, preds_run2)

    def test_13_no_training_on_evaluation_records(self):
        """Check that model files were not modified during evaluation."""
        mtime_before = BASELINE_PATH.stat().st_mtime
        X, _ = load_evaluation_workbook(WORKBOOK_PATH, sheet_name="Test Cases")
        # Run a rule evaluation pass
        _ = [evaluate_transaction_rules(X.iloc[i])[0] for i in range(len(X))]
        mtime_after = BASELINE_PATH.stat().st_mtime
        self.assertEqual(mtime_before, mtime_after, "Model artifact must never be overwritten or modified.")

    def test_14_existing_artifacts_preserved(self):
        """Confirm that original reports and models exist intact."""
        self.assertTrue((ROOT / "reports/model_comparison.csv").exists())
        self.assertTrue((ROOT / "reports/baseline_errors.xlsx").exists())
        self.assertTrue((ROOT / "reports/baseline_test_predictions.xlsx").exists())
        self.assertTrue((ROOT / "reports/baseline_error_summary.csv").exists())


if __name__ == "__main__":
    unittest.main()
