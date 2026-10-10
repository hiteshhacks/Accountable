"""Tests for the experimental V3 feature contract and training setup.

Models are fitted in memory on a small, fixed sample of the synthetic training
data; nothing is saved and the evaluation workbook is never read.
"""

import pickle
import unittest

import numpy as np
import pandas as pd

from vyom.adapter import LABEL_COLUMN, map_wide_to_canonical
from vyom.features_v3 import (
    CONTRACT_FIELDS,
    EXCLUDED_FIELDS,
    PRESENCE_ONLY_FIELDS,
    ContractTabular,
    ContractTokens,
    field_tokens,
    prepare_frame,
)
from vyom.train_v3 import EXCLUDED_CLASSES, field_tfidf, load_training_data, narration_core


ALL_GROUPS = ("narration", "item", "categorical", "presence", "relationships")


class V3TestBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        inputs, meta = load_training_data()
        keep = ~meta["label"].isin(EXCLUDED_CLASSES)
        cls.inputs, cls.meta = inputs[keep].reset_index(drop=True), meta[keep].reset_index(drop=True)
        sample = cls.meta.groupby("label").head(15).index
        cls.X = cls.inputs.loc[sample].reset_index(drop=True)
        cls.y = cls.meta.loc[sample, "label"].to_numpy()


class TestLabelIsolation(V3TestBase):

    def test_training_inputs_carry_no_label_columns(self):
        self.assertFalse(set(self.inputs.columns) & (set(EXCLUDED_FIELDS) - {"transaction_date"}))

    def test_contract_output_excludes_labels_and_outputs(self):
        prepared = prepare_frame(self.X.head(20))
        for field in EXCLUDED_FIELDS:
            self.assertFalse(any(field in col for col in prepared.columns), field)

    def test_injected_label_columns_do_not_change_features(self):
        rows = self.X.head(30)
        injected = rows.assign(**{"voucher_type": "Journal", LABEL_COLUMN: "Journal", "document_type": "Payroll register",
                                  "Correct": True, "Predicted Voucher Category": "Journal"})
        pd.testing.assert_frame_equal(prepare_frame(rows), prepare_frame(injected))
        tokens = ContractTokens()
        self.assertListEqual(tokens.transform(rows), tokens.transform(injected))


class TestFeatureConsistency(V3TestBase):

    def test_features_are_row_wise_and_order_independent(self):
        rows = self.X.head(40)
        shuffled = rows.sample(frac=1.0, random_state=0)
        pd.testing.assert_frame_equal(prepare_frame(rows).loc[shuffled.index], prepare_frame(shuffled))

    def test_identifier_and_party_values_contribute_presence_only(self):
        rows = self.X.head(30)
        changed = rows.copy()
        for field in PRESENCE_ONLY_FIELDS:
            changed[field] = changed[field].map(lambda v: v if pd.isna(v) else "ZZ-999999-OTHER")
        groups = ALL_GROUPS
        self.assertListEqual(field_tokens(prepare_frame(rows), groups).tolist(),
                             field_tokens(prepare_frame(changed), groups).tolist())

    def test_identifier_tokens_and_digits_are_masked_in_text(self):
        prepared = prepare_frame(pd.DataFrame({"transaction_narration": ["Paid PMT-12345 on 05 Mar 2026 ref TXN-7"]}))
        text = prepared.loc[0, "transaction_narration"]
        self.assertNotIn("12345", text)
        self.assertNotIn("pmt", text)
        self.assertIn("idtoken", text)

    def test_training_and_inference_share_one_transform(self):
        model = field_tfidf(ALL_GROUPS).fit(self.X, self.y)
        self.assertIsInstance(model.named_steps["contract"], ContractTokens)
        restored = pickle.loads(pickle.dumps(model))
        np.testing.assert_array_equal(model.predict(self.X), restored.predict(self.X))

    def test_narration_core_drops_generated_reference_sentence(self):
        a = narration_core("Goods were received. Record reference TXN-700001 is dated 01 Jan 2025.")
        b = narration_core("Goods were received. Audit trail: TXN-700999, transaction date 09 Sep 2026.")
        self.assertEqual(a, b)


class TestMissingFields(V3TestBase):

    def test_missing_columns_become_empty_with_presence_zero(self):
        prepared = prepare_frame(pd.DataFrame({"transaction_narration": ["Customer paid the open invoice"]}))
        for field in CONTRACT_FIELDS:
            self.assertIn(f"has_{field}", prepared.columns)
        self.assertEqual(prepared.loc[0, "has_transaction_narration"], 1.0)
        self.assertEqual(prepared.loc[0, "has_quantity"], 0.0)
        self.assertTrue(np.isnan(prepared.loc[0, "taxable_value"]))
        self.assertTrue(np.isnan(prepared.loc[0, "rel_qty_x_price_matches_value"]))

    def test_unknown_categories_become_missing_for_tabular(self):
        tab = ContractTabular(include_item=True).fit(self.X)
        row = self.X.head(1).copy()
        row["payment_status"] = "a status never seen in training"
        matrix = tab.transform(row)
        status_col = ["item_description", "currency", "payment_method", "payment_status"].index("payment_status")
        self.assertTrue(np.isnan(matrix[0, status_col]))
        self.assertEqual(matrix.shape[1], len(tab.categorical_mask()))

    def test_relationship_features(self):
        prepared = prepare_frame(pd.DataFrame({
            "quantity": [10, 10], "unit_price": [5.0, 5.0], "taxable_value": [50.0, 80.0],
            "gst_rate_percent": [18, 18], "gst_amount": [9.0, 1.0],
        }))
        self.assertListEqual(prepared["rel_qty_x_price_matches_value"].tolist(), [1.0, 0.0])
        self.assertEqual(prepared.loc[0, "rel_gst_matches_rate"], 1.0)


class TestDeterministicTraining(V3TestBase):

    def test_two_fits_give_identical_models(self):
        first = field_tfidf(ALL_GROUPS).fit(self.X, self.y)
        second = field_tfidf(ALL_GROUPS).fit(self.X, self.y)
        np.testing.assert_array_equal(first.named_steps["clf"].coef_, second.named_steps["clf"].coef_)
        np.testing.assert_array_equal(first.predict(self.X), second.predict(self.X))


class TestSupportedCategories(V3TestBase):

    def test_training_label_set(self):
        labels = set(self.meta["label"])
        self.assertEqual(len(labels), 26)
        self.assertNotIn("Other / Miscellaneous", labels)
        self.assertIn("Rejection In", labels)
        self.assertEqual(self.meta["label"].value_counts().min(), 200)

    def test_fitted_model_covers_all_training_classes(self):
        model = field_tfidf(ALL_GROUPS).fit(self.X, self.y)
        self.assertSetEqual(set(model.classes_), set(self.meta["label"]))


class TestInferenceCompatibility(V3TestBase):

    def test_predicts_on_sparse_canonical_records(self):
        model = field_tfidf(ALL_GROUPS).fit(self.X, self.y)
        sparse = pd.DataFrame([
            {"transaction_narration": "Bank transfer settles supplier payable", "payment_status": "Paid"},
            {"item_description": "steel sheets", "quantity": 4},
            {},
        ])
        pred = model.predict(sparse)
        self.assertEqual(len(pred), 3)
        self.assertTrue(set(pred) <= set(model.classes_))

    def test_predicts_on_wide_records_mapped_to_canonical(self):
        model = field_tfidf(ALL_GROUPS).fit(self.X, self.y)
        wide = pd.DataFrame([{"Supplier": "Alpha Traders", "Item Received": "bearings", "Quantity Received": 40,
                              "Narration": "Goods received at stores", "Rejection Note No": "RJN-IN-1"}])
        pred = model.predict(map_wide_to_canonical(wide))
        self.assertEqual(len(pred), 1)
        self.assertIn(pred[0], set(model.classes_))


if __name__ == "__main__":
    unittest.main()
