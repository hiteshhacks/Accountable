"""Comprehensive tests for the VYOM+ evaluation workbook adapter and pipeline."""

import inspect
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
from vyom.evaluate_workbook import (
    compute_metrics,
    run_pipeline,
    side_report_paths,
    unique_output_path,
)


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = ROOT / "data/input/Voucher_Classification_Test_Cases_v2.xlsx"
BASELINE_PATH = ROOT / "models/vyom_plus_tfidf_baseline_model.pkl"

DECISION_COLUMNS = [
    "Predicted Voucher Category", "Decision Source", "Rule Status", "Rule Candidates",
    "Model Prediction", "Model Score (Uncalibrated)", "Rule Overrode Model",
    "Review Required", "Review Reason", "Prediction Explanation",
]


def run_to(tmpdir, name="out.xlsx", input_path=WORKBOOK_PATH, sheet_name="Test Cases", **kwargs):
    """Run the pipeline without the model comparison into a temporary folder."""
    out_file = Path(tmpdir) / name
    summary = run_pipeline(input_path=input_path, sheet_name=sheet_name, output_path=out_file,
                           run_comparison=False, **kwargs)
    return summary, pd.read_excel(out_file)


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

        # Evaluate rules on a copy of X whose rows carry wrong labels and prior outputs
        X_copy = X.copy()
        X_copy[LABEL_COLUMN] = fake_labels.values
        X_copy["Correct"] = False
        X_copy["Predicted Voucher Category"] = y.values
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
            "Item Rejected": "Panels",
        })
        pred, _, applied = evaluate_transaction_rules(rej_out)
        self.assertEqual(pred, "Rejection Out")
        self.assertTrue(applied)

    def test_11_metric_calculation(self):
        """Metrics match hand-computed values; no accuracy target is asserted."""
        m = compute_metrics(["A", "A", "B", "C"], ["A", "B", "B", "C"])
        self.assertEqual(m["correct"], 3)
        self.assertAlmostEqual(m["accuracy"], 0.75)
        # F1: A = 2/3, B = 2/3, C = 1
        self.assertAlmostEqual(m["macro_f1"], (2 / 3 + 2 / 3 + 1) / 3)
        self.assertAlmostEqual(m["weighted_f1"], (2 * 2 / 3 + 1 * 2 / 3 + 1 * 1) / 4)

        # A predicted label absent from the truth counts in the macro average with F1 = 0.
        m = compute_metrics(["A", "B"], ["A", "X"])
        self.assertAlmostEqual(m["accuracy"], 0.5)
        self.assertAlmostEqual(m["macro_f1"], 1 / 3)
        self.assertAlmostEqual(m["weighted_f1"], 0.5)

        with self.assertRaises(ValueError):
            compute_metrics(["A"], ["A", "B"])

        # The pipeline's reported metrics equal a recomputation from its own output columns.
        with tempfile.TemporaryDirectory() as tmpdir:
            summary, out_df = run_to(tmpdir)
            actual = out_df[LABEL_COLUMN].astype(str).tolist()
            predicted = out_df["Predicted Voucher Category"].astype(str).tolist()
            recomputed = compute_metrics(actual, predicted)
            for key in ("n_samples", "correct", "accuracy", "macro_f1", "weighted_f1"):
                self.assertAlmostEqual(summary["pipeline"][key], recomputed[key])
            self.assertEqual(summary["pipeline"]["correct"], int(out_df["Correct"].sum()))

            side = side_report_paths(Path(tmpdir) / "out.xlsx", Path(tmpdir))
            cm = pd.read_csv(side["confusion"], index_col=0)
            self.assertEqual(int(cm.values.sum()), len(out_df))
            self.assertEqual(int(np.trace(cm.values)), recomputed["correct"])
            per_class = pd.read_csv(side["per_class"], index_col=0)
            labels = sorted(set(actual))
            self.assertEqual(int(per_class.loc[labels, "support"].sum()), len(out_df))

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

    def test_15_rule_status_and_score_kept_separate(self):
        """Prediction, rule status and model score are separate; a rule match carries no probability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _, out_df = run_to(tmpdir)
            self.assertNotIn("Prediction Confidence", out_df.columns)
            for col in DECISION_COLUMNS:
                self.assertIn(col, out_df.columns)
            valid = {"RULE_MATCH", "REVIEW_REQUIRED", "AMBIGUOUS", "NO_RULE"}
            self.assertTrue(set(out_df["Rule Status"]) <= valid)
            is_match = out_df["Rule Status"] == "RULE_MATCH"
            self.assertListEqual((out_df["Decision Source"] == "RULE").tolist(), is_match.tolist())
            # Without a rule match the prediction is the model's own prediction.
            model_rows = out_df[~is_match]
            self.assertListEqual(model_rows["Predicted Voucher Category"].tolist(),
                                 model_rows["Model Prediction"].tolist())
            # Conflicting or insufficient rule evidence is always flagged for review.
            flagged = out_df["Rule Status"].isin(["REVIEW_REQUIRED", "AMBIGUOUS"])
            self.assertTrue(out_df.loc[flagged, "Review Required"].all())
            scores = out_df["Model Score (Uncalibrated)"]
            self.assertTrue(((scores >= 0) & (scores <= 1)).all())
            overrides = is_match & (out_df["Predicted Voucher Category"] != out_df["Model Prediction"])
            self.assertListEqual(out_df["Rule Overrode Model"].tolist(), overrides.tolist())

    def test_16_label_isolation_in_pipeline(self):
        """Predictions are identical with true labels, wrong labels, or no label column."""
        raw = pd.read_excel(WORKBOOK_PATH, sheet_name="Test Cases")
        with tempfile.TemporaryDirectory() as tmpdir:
            wrong = raw.copy()
            wrong[LABEL_COLUMN] = list(raw[LABEL_COLUMN].iloc[1:]) + [raw[LABEL_COLUMN].iloc[0]]
            wrong_path = Path(tmpdir) / "wrong_labels.xlsx"
            wrong.to_excel(wrong_path, sheet_name="Test Cases", index=False)
            blind_path = Path(tmpdir) / "no_labels.xlsx"
            raw.drop(columns=[LABEL_COLUMN]).to_excel(blind_path, sheet_name="Test Cases", index=False)

            _, true_out = run_to(tmpdir, "true.xlsx")
            _, wrong_out = run_to(tmpdir, "wrong.xlsx", input_path=wrong_path)
            _, blind_out = run_to(tmpdir, "blind.xlsx", input_path=blind_path)

            compared = ["Predicted Voucher Category", "Rule Status", "Model Prediction", "Model Score (Uncalibrated)"]
            pd.testing.assert_frame_equal(true_out[compared], wrong_out[compared])
            pd.testing.assert_frame_equal(true_out[compared], blind_out[compared])
            self.assertNotIn(LABEL_COLUMN, blind_out.columns)

    def test_17_output_integrity(self):
        """Every input row appears once, in order, with its fields and label unchanged."""
        X, y = load_evaluation_workbook(WORKBOOK_PATH, sheet_name="Test Cases")
        with tempfile.TemporaryDirectory() as tmpdir:
            _, out_df = run_to(tmpdir)
        self.assertEqual(len(out_df), len(X))
        self.assertListEqual(list(out_df.columns[:len(X.columns)]), list(X.columns))
        self.assertTrue((out_df[list(X.columns)].astype(str).values == X.astype(str).values).all())
        self.assertListEqual(out_df[LABEL_COLUMN].tolist(), y.tolist())
        self.assertListEqual(out_df["Correct"].tolist(),
                             (out_df["Predicted Voucher Category"] == out_df[LABEL_COLUMN]).tolist())
        self.assertEqual(int(out_df[list(X.columns)].duplicated().sum()), int(X.duplicated().sum()))

    def test_18_pipeline_deterministic(self):
        """Two runs on the same input produce identical decision columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _, first = run_to(tmpdir, "first.xlsx")
            _, second = run_to(tmpdir, "second.xlsx")
        pd.testing.assert_frame_equal(first[DECISION_COLUMNS], second[DECISION_COLUMNS])

    def test_19_never_overwrites_reports(self):
        """Existing outputs and side-reports are refused unless overwrite is requested."""
        self.assertIsNone(inspect.signature(run_pipeline).parameters["output_path"].default)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            first = unique_output_path(tmp)
            self.assertFalse(first.exists())
            first.touch()
            self.assertNotEqual(unique_output_path(tmp), first)

            out_file = tmp / "kept.xlsx"
            run_to(tmpdir, "kept.xlsx")
            before = out_file.read_bytes()
            with self.assertRaises(FileExistsError):
                run_to(tmpdir, "kept.xlsx")
            self.assertEqual(out_file.read_bytes(), before)

            # A side-report collision alone is also refused, before anything is written.
            fresh = tmp / "fresh.xlsx"
            side_report_paths(fresh, tmp)["per_class"].write_text("existing")
            with self.assertRaises(FileExistsError):
                run_to(tmpdir, "fresh.xlsx")
            self.assertFalse(fresh.exists())

            run_to(tmpdir, "kept.xlsx", overwrite=True)
            self.assertTrue(out_file.exists())

if __name__ == "__main__":
    unittest.main()
