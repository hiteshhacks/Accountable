"""Tests for the FastAPI server serving models/voucher_classifier.pkl."""

from io import BytesIO
import unittest

import pandas as pd

from vyom.adapter import serialize_wide_row
from vyom.serve_v2 import MODEL_PATH

RECORD = {"PO Number": "PO1234567", "Supplier": "Digital Solutions Corp", "Item": "Textiles",
          "Quantity Required": 815, "Currency Code": "INR"}


@unittest.skipUnless(MODEL_PATH.exists(), "models/voucher_classifier.pkl not present")
class TestServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from vyom.serve_v2 import app, MODEL
        cls.client = TestClient(app)
        cls.model = MODEL

    def test_health_and_model_info(self):
        self.assertEqual(self.client.get("/health").json()["model"], "voucher_classifier.pkl")
        info = self.client.get("/model").json()
        self.assertListEqual(info["labels"], list(self.model.classes_))

    def test_predict_matches_model_on_serialized_input(self):
        body = self.client.post("/predict", json={"records": [RECORD, {}]}).json()
        self.assertEqual(len(body["predictions"]), 2)
        expected = self.model.predict([serialize_wide_row(pd.Series(RECORD))])[0]
        first = body["predictions"][0]
        self.assertEqual(first["predicted_voucher_category"], expected)
        self.assertEqual(first["serialized_input"], serialize_wide_row(pd.Series(RECORD)))
        self.assertEqual(len(first["top_predictions"]), 3)

    def test_label_columns_are_ignored(self):
        leaky = {**RECORD, "Voucher Category": "Journal", "document_type": "x"}
        plain = self.client.post("/predict", json={"records": [RECORD]}).json()["predictions"][0]
        got = self.client.post("/predict", json={"records": [leaky]}).json()["predictions"][0]
        self.assertEqual(plain["predicted_voucher_category"], got["predicted_voucher_category"])
        self.assertEqual(plain["serialized_input"], got["serialized_input"])
        self.assertIn("Voucher Category", got["ignored_fields"])

    def test_empty_request_rejected(self):
        self.assertEqual(self.client.post("/predict", json={"records": []}).status_code, 422)

    def test_file_upload_returns_workbook(self):
        buf = BytesIO()
        pd.DataFrame([RECORD]).to_excel(buf, index=False)
        resp = self.client.post("/predict/file", files={"file": ("in.xlsx", buf.getvalue())})
        self.assertEqual(resp.status_code, 200)
        out = pd.read_excel(BytesIO(resp.content))
        self.assertIn("Predicted Voucher Category", out.columns)


if __name__ == "__main__":
    unittest.main()
