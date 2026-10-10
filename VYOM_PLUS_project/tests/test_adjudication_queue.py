"""Validation of the adjudication queue against the authoritative source workbooks."""

from pathlib import Path
import hashlib
import shutil
import subprocess
import unittest

import pandas as pd

from vyom.build_adjudication_queue import (
    COMPARISON,
    DATASET,
    DEFINITION_ISSUES,
    OUTPUT,
    STATUSES,
    build_queue,
    narration_core,
)


CATEGORIES = set(pd.read_excel(DATASET, sheet_name="label_guidelines_v5")["voucher_type"])
EDITABLE = ["Final Adjudicated Label", "Adjudicator Rationale", "Adjudicator", "Adjudication Date"]


def authoritative_disputed_ids():
    sheets = pd.read_excel(COMPARISON, sheet_name=["Provisional_Consensus", "Adjudication_Queue"])
    both = pd.concat(sheets.values(), ignore_index=True)
    return set(both.loc[both["needs_adjudication"] == True, "review_case_id"])  # noqa: E712


class QueueChecks:
    """Checks shared by the in-memory queue and the saved workbook."""

    queue: pd.DataFrame

    def test_contains_exactly_the_disputed_records(self):
        expected = authoritative_disputed_ids()
        self.assertEqual(len(expected), 111)
        self.assertSetEqual(set(self.queue["Review Case ID"]), expected)

    def test_no_duplicates(self):
        self.assertEqual(len(self.queue), 111)
        self.assertFalse(self.queue["Review Case ID"].duplicated().any())
        self.assertFalse(self.queue["Record ID"].duplicated().any())

    def test_reviewer_labels_match_source(self):
        src = pd.read_excel(COMPARISON, sheet_name="Adjudication_Queue").set_index("review_case_id")
        q = self.queue.set_index("Review Case ID")
        for col, src_col in [("Reviewer 1 Label", "reviewer_1_label"), ("Reviewer 2 Label", "reviewer_2_label"),
                             ("Original Adjudication Reason", "adjudication_reason")]:
            self.assertListEqual(q[col].tolist(), src.loc[q.index, src_col].tolist(), col)
        consensus = src.loc[q.index, "provisional_consensus_label"].fillna("").tolist()
        self.assertListEqual(q["Existing Provisional Consensus Label"].fillna("").tolist(), consensus)

    def test_ids_and_fields_preserved(self):
        review = pd.read_excel(DATASET, sheet_name="human_review_queue")
        src = pd.read_excel(COMPARISON, sheet_name="Adjudication_Queue").set_index("review_case_id")
        for _, row in self.queue.iterrows():
            qi = int(row["Review Case ID"].split("-")[1]) - 1
            self.assertEqual(row["Record ID"], review.loc[qi, "record_id"])
            self.assertEqual(row["Source Record ID"], review.loc[qi, "source_record_id"])
            s = src.loc[row["Review Case ID"]]
            for field in ("item_description", "payment_status", "return_reason", "debit_credit_info",
                          "movement_reason", "document_type", "seller_supplier", "buyer_customer"):
                expected = "" if pd.isna(s[field]) else str(s[field]).strip()
                got = "" if pd.isna(row[f"Field: {field}"]) else str(row[f"Field: {field}"])
                self.assertEqual(got, expected, (row["Review Case ID"], field))
            self.assertEqual(row["Field: transaction_narration"], narration_core(str(s["transaction_narration"])))

    def test_nothing_is_adjudicated(self):
        for col in EDITABLE:
            values = self.queue[col].fillna("").astype(str).str.strip()
            self.assertTrue((values == "").all(), col)
        self.assertTrue((self.queue["Adjudication Status"] == "PENDING").all())

    def test_priorities_and_definition_links_are_valid(self):
        self.assertTrue(set(self.queue["Adjudication Priority"]) <= {"HIGH", "MEDIUM", "LOW"})
        for refs in self.queue["Definition Issues"].fillna(""):
            for ref in [r.strip() for r in refs.split(",") if r.strip()]:
                self.assertIn(ref, DEFINITION_ISSUES)
        self.assertTrue(self.queue["Disagreement Type"].notna().all())

    def test_findings_never_name_a_category_as_decision(self):
        for text in self.queue["Field Conflicts or Gaps"].fillna(""):
            for category in CATEGORIES:
                self.assertNotIn(category, text)


class TestBuiltQueue(QueueChecks, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result = build_queue()
        cls.queue = cls.result["queue"]

    def test_counts_reconcile_with_comparison_summary(self):
        counts = self.result["counts"]
        self.assertEqual(counts["reviewed_records"], 540)
        self.assertEqual(counts["unique_reviewed_ids"], 540)
        self.assertEqual(counts["consensus_records"], 429)
        summary = {r["VYOM+ Reviewer Comparison & Adjudication"]: r["Result"] for r in counts["summary_sheet"]}
        self.assertEqual(int(summary["Records requiring adjudication"]), len(self.queue))

    def test_build_is_deterministic(self):
        pd.testing.assert_frame_equal(self.queue, build_queue()["queue"])


@unittest.skipUnless(OUTPUT.exists(), "reports/vyom_adjudication_queue.xlsx has not been built")
class TestSavedWorkbook(QueueChecks, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.queue = pd.read_excel(OUTPUT, sheet_name="Adjudication_Queue")
        cls.readme = pd.read_excel(OUTPUT, sheet_name="README").set_index("Item")["Detail"]

    def test_source_records_sheet_is_verbatim(self):
        saved = pd.read_excel(OUTPUT, sheet_name="Source_Records").set_index("review_case_id")
        src = pd.read_excel(COMPARISON, sheet_name="Adjudication_Queue").set_index("review_case_id")
        pd.testing.assert_frame_equal(saved[src.columns].loc[src.index], src, check_dtype=False)

    def test_source_workbooks_unchanged_since_build(self):
        for name, path in (("Source of truth", COMPARISON), ("Record IDs and fields", DATASET)):
            self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), self.readme[name])

    def test_status_values_are_from_the_allowed_list(self):
        self.assertTrue(set(self.queue["Adjudication Status"]) <= set(STATUSES))


@unittest.skipUnless(shutil.which("git"), "git not available")
class TestTrackedArtifactsUnchanged(unittest.TestCase):

    def test_tracked_models_rule_engine_and_sources_unchanged(self):
        root = Path(__file__).resolve().parents[1]
        paths = ["models", "data/synthetic", "src/vyom/rule_engine.py"]
        tracked = subprocess.run(["git", "ls-files", "--", *paths], cwd=root, capture_output=True, text=True).stdout
        if not tracked.strip():
            self.skipTest("artifacts not tracked by git here")
        diff = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", *paths], cwd=root, capture_output=True, text=True)
        self.assertEqual(diff.stdout.strip(), "", diff.stdout)


if __name__ == "__main__":
    unittest.main()
