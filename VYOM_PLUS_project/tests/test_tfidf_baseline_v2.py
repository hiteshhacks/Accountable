"""Tests for the TF-IDF baseline v2 training pipeline and its saved artifacts."""

from pathlib import Path
import json
import pickle
import shutil
import subprocess
import unittest

import numpy as np
import pandas as pd

from vyom.adapter import LABEL_COLUMN
from vyom.train_tfidf_baseline_v2 import (
    CONFIG_PATH,
    DATASET,
    LABELS_PATH,
    METRICS_PATH,
    MODEL_PATH,
    PREDICTIONS_PATH,
    REVIEW_ROUTE,
    build_model,
    contract_tokens,
    disputed_record_ids,
    load_eligible,
    sha256,
    split,
    taxonomy,
)


class Base(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.X, cls.m, cls.disputed = load_eligible()
        cls.tokens = contract_tokens(cls.X)
        cls.labels = taxonomy()


class TestEligibleData(Base):

    def test_taxonomy_has_27_categories(self):
        self.assertEqual(len(self.labels), 27)
        self.assertEqual(len(set(self.labels)), 27)
        self.assertSetEqual(set(self.m["label"]), set(self.labels))

    def test_disputed_records_are_excluded(self):
        self.assertEqual(len(self.disputed), 111)
        self.assertFalse(self.m["record_id"].isin(self.disputed).any())
        self.assertEqual(len(self.X), 5400 - 111)

    def test_inputs_carry_no_label_columns(self):
        for col in ("voucher_type", LABEL_COLUMN, "document_type", "split_group", "record_id"):
            self.assertNotIn(col, self.X.columns)


class TestSplit(Base):

    def test_split_is_grouped_covering_and_deterministic(self):
        tr, te = split(self.m, self.tokens)
        tr2, te2 = split(self.m, self.tokens)
        np.testing.assert_array_equal(tr, tr2)
        np.testing.assert_array_equal(te, te2)
        self.assertFalse(set(self.m["core_id"].iloc[tr]) & set(self.m["core_id"].iloc[te]))
        self.assertFalse(set(self.tokens.iloc[tr]) & set(self.tokens.iloc[te]))
        y = self.m["label"].to_numpy()
        self.assertSetEqual(set(y[tr]), set(self.labels))
        self.assertSetEqual(set(y[te]), set(self.labels))
        self.assertEqual(len(tr) + len(te), len(self.X))

    def test_other_seed_draws_a_different_split(self):
        _, te = split(self.m, self.tokens)
        _, te_other = split(self.m, self.tokens, seed=101)
        self.assertNotEqual(set(te), set(te_other))


class TestModelBehaviour(Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sample = cls.m.groupby("label").head(12).index
        cls.Xs, cls.ys = cls.X.loc[sample], cls.m.loc[sample, "label"].to_numpy()

    def test_training_is_deterministic(self):
        a = build_model(2.0).fit(self.Xs, self.ys)
        b = build_model(2.0).fit(self.Xs, self.ys)
        np.testing.assert_array_equal(a.named_steps["clf"].coef_, b.named_steps["clf"].coef_)

    def test_label_columns_do_not_change_predictions(self):
        model = build_model(2.0).fit(self.Xs, self.ys)
        injected = self.Xs.assign(**{"voucher_type": "Journal", LABEL_COLUMN: "Journal", "document_type": "Payroll register"})
        np.testing.assert_array_equal(model.predict(self.Xs), model.predict(injected))

    def test_both_representations_build_and_predict(self):
        for rep in ("field_words", "field_words+text_chars"):
            model = build_model(1.0, rep).fit(self.Xs, self.ys)
            self.assertEqual(len(model.classes_), 27)


@unittest.skipUnless(MODEL_PATH.exists(), "baseline v2 has not been trained")
class TestSavedArtifacts(Base):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open(MODEL_PATH, "rb") as f:
            cls.model = pickle.load(f)
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cls.label_map = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
        cls.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        cls.predictions = pd.read_excel(PREDICTIONS_PATH)

    def test_model_covers_full_taxonomy_in_label_map_order(self):
        self.assertListEqual(list(self.model.classes_), sorted(self.labels))
        self.assertListEqual([e["label"] for e in self.label_map["labels"]], list(self.model.classes_))
        self.assertListEqual([e["index"] for e in self.label_map["labels"]], list(range(27)))
        missing_v1 = {e["label"] for e in self.label_map["labels"] if not e["in_existing_v1_artifact"]}
        self.assertSetEqual(missing_v1, {"Rejection In", "Other / Miscellaneous"})
        routed = {e["label"] for e in self.label_map["labels"] if e["review_route"]}
        self.assertSetEqual(routed, REVIEW_ROUTE)

    def test_config_matches_training_data_and_policy(self):
        self.assertEqual(self.config["training_data"]["sha256"], sha256(DATASET))
        self.assertEqual(self.config["excluded_records"]["count"], 111)
        self.assertFalse(self.config["evaluation_workbook_used"])
        self.assertIn("document_type", self.config["preprocessing"]["excluded_fields"])

    def test_predictions_file_is_the_primary_test_split(self):
        _, te = split(self.m, self.tokens)
        self.assertListEqual(sorted(self.predictions["record_id"]), sorted(self.m["record_id"].iloc[te]))
        self.assertFalse(self.predictions["record_id"].isin(disputed_record_ids()).any())

    def test_saved_model_reproduces_saved_predictions_and_metrics(self):
        inputs = self.predictions[list(self.X.columns)]
        pred = self.model.predict(inputs)
        self.assertListEqual(list(pred), self.predictions["Predicted Voucher Category"].tolist())
        correct = int((pred == self.predictions["Synthetic Label (unverified)"]).sum())
        self.assertEqual(correct, self.metrics["test"]["correct"])
        self.assertAlmostEqual(correct / len(pred), self.metrics["test"]["accuracy"], places=4)

    def test_review_route_flags_match_predictions(self):
        expected = self.predictions["Predicted Voucher Category"].isin(REVIEW_ROUTE)
        self.assertListEqual(self.predictions["Review Required"].tolist(), expected.tolist())

    def test_inference_on_sparse_canonical_records(self):
        sparse = pd.DataFrame([{"transaction_narration": "Bank transfer settles a supplier payable", "payment_status": "Paid"},
                               {"item_description": "steel sheets", "quantity": 4}, {}])
        pred = self.model.predict(sparse)
        self.assertEqual(len(pred), 3)
        self.assertTrue(set(pred) <= set(self.labels))
        self.assertEqual(self.model.predict_proba(sparse).shape, (3, 27))


@unittest.skipUnless(shutil.which("git"), "git not available")
class TestExistingArtifactsUnchanged(unittest.TestCase):

    def test_existing_models_and_sources_unchanged(self):
        root = Path(__file__).resolve().parents[1]
        paths = ["models/vyom_plus_tfidf_baseline_model.pkl", "models/vyom_dual_encoder_model.pt",
                 "models/vyom_dual_encoder_v2.pt", "data/synthetic", "src/vyom/rule_engine.py"]
        diff = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", *paths], cwd=root,
                              capture_output=True, text=True)
        self.assertEqual(diff.stdout.strip(), "", diff.stdout)


if __name__ == "__main__":
    unittest.main()
