"""API tests for the GST endpoints (real classifier, mocked Groq) plus an optional live Groq test."""

from dataclasses import replace
import json
import os
import unittest

from vyom.serve_v2 import MODEL_PATH

from gst_fixtures import BUSINESS, ScriptedRunnable, analysis, clean_records, settings, workbook

KEY = "gsk_test_secret_value_123"


@unittest.skipUnless(MODEL_PATH.exists(), "models/voucher_classifier.pkl not present")
class TestGstApi(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from vyom import serve_v2
        from vyom.gst.llm import GstLLMService
        from vyom.gst.service import GstAnalysisService
        s = settings(KEY)
        s = replace(s, limits=replace(s.limits, max_upload_bytes=200_000, max_json_bytes=100_000))
        cls.runnable = ScriptedRunnable(analysis())
        llm = GstLLMService(s.groq, runnable=cls.runnable, sleep=lambda _: None)
        cls.serve = serve_v2
        cls.previous = serve_v2._gst_service
        serve_v2._gst_service = GstAnalysisService(serve_v2.predict_frame, list(serve_v2.MODEL.classes_), settings=s, llm=llm)
        cls.client = TestClient(serve_v2.app)

    @classmethod
    def tearDownClass(cls):
        cls.serve._gst_service = cls.previous

    def assertReport(self, body):
        self.assertIsInstance(body["report"], str)
        self.assertTrue(body["report"].startswith("# GST Intelligence Report"))
        self.assertIn(body["status"], ("ANALYSIS_COMPLETE", "REVIEW_REQUIRED", "INSUFFICIENT_DATA"))
        self.assertTrue(body["request_id"])
        self.assertNotIn(KEY, json.dumps(body))

    def test_json_records(self):
        resp = self.client.post("/gst/analyze", json={"records": clean_records(), "business_gstin": BUSINESS})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertReport(body)
        self.assertTrue(body["success"])
        rows = body["summary"]["classification"]["rows"]
        self.assertEqual([r["source_ref"] for r in rows], ["records[0]", "records[1]"])
        self.assertIn("scores", body["summary"]["classification"])

    def test_json_string(self):
        resp = self.client.post("/gst/analyze", json={"json_string": json.dumps({"records": clean_records()})})
        self.assertEqual(resp.status_code, 200)
        self.assertReport(resp.json())

    def test_invalid_json_inputs(self):
        resp = self.client.post("/gst/analyze", json={"json_string": "{oops"})
        self.assertEqual(resp.status_code, 422)
        body = resp.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["status"], "PROCESSING_FAILED")
        self.assertIn("Malformed JSON", body["errors"][0])
        self.assertEqual(self.client.post("/gst/analyze", json={}).status_code, 422)
        self.assertEqual(self.client.post("/gst/analyze", json={"records": []}).status_code, 422)

    def test_oversized_json_rejected(self):
        big = {"records": [{"Notes": "x" * 1000}] * 200}
        self.assertEqual(self.client.post("/gst/analyze", json=big).status_code, 413)

    def test_excel_upload_multiple_sheets(self):
        content = workbook(Sales=clean_records()[:1], Purchases=clean_records()[1:], Notes=[])
        resp = self.client.post("/gst/analyze/file", files={"file": ("books.xlsx", content)},
                                data={"business_gstin": BUSINESS})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertReport(body)
        refs = [r["source_ref"] for r in body["summary"]["classification"]["rows"]]
        self.assertEqual(refs, ["Sales!R2", "Purchases!R2"])
        self.assertTrue(any("Notes" in w for w in body["warnings"]))

    def test_bad_uploads(self):
        empty = self.client.post("/gst/analyze/file", files={"file": ("e.xlsx", workbook(Blank=[]))})
        self.assertEqual(empty.status_code, 422)
        self.assertEqual(self.client.post("/gst/analyze/file", files={"file": ("x.pdf", b"%PDF")}).status_code, 422)
        self.assertEqual(self.client.post("/gst/analyze/file", files={"file": ("x.xlsx", b"garbage")}).status_code, 422)
        self.assertEqual(self.client.post("/gst/analyze/file", files={"file": ("big.xlsx", b"0" * 200_001)}).status_code, 413)

    def test_existing_classifier_endpoints_unchanged(self):
        record = {"PO Number": "PO1234567", "Supplier": "Digital Solutions Corp", "Quantity Required": 5}
        pred = self.client.post("/predict", json={"records": [record]})
        self.assertEqual(pred.status_code, 200)
        self.assertIn("predicted_voucher_category", pred.json()["predictions"][0])
        self.assertEqual(self.client.get("/health").json()["status"], "ok")


@unittest.skipUnless(os.environ.get("GROQ_API_KEY") and MODEL_PATH.exists(),
                     "optional live test: set GROQ_API_KEY to run against Groq")
class TestLiveGroq(unittest.TestCase):

    def test_live_analysis(self):
        from vyom import serve_v2
        from vyom.gst.schemas import GstJsonRequest
        from vyom.gst.service import GstAnalysisService
        svc = GstAnalysisService(serve_v2.predict_frame, list(serve_v2.MODEL.classes_))
        resp, code = svc.analyze_json(GstJsonRequest(records=clean_records(), business_gstin=BUSINESS))
        self.assertEqual(code, 200)
        narrative = resp.summary["narrative"]
        if not narrative["available"]:
            # Free-tier limits or model changes can legitimately prevent a narrative; it must fail safely.
            self.assertIn(narrative["error_kind"], ("rate_limited", "timeout", "connection_error", "provider_error",
                                                    "model_unavailable", "structured_output_invalid"))
        self.assertNotIn(os.environ["GROQ_API_KEY"], resp.model_dump_json())


if __name__ == "__main__":
    unittest.main()
