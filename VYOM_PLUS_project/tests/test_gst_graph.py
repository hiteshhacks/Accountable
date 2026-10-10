"""LangGraph workflow: routing, fallback, report formatting and the shared service."""

import unittest

from vyom.gst.report import esc
from vyom.gst.schemas import ClassificationConcern, DiscrepancyExplanation, GstJsonRequest

from gst_fixtures import BUSINESS, ScriptedRunnable, analysis, clean_records, groq_error, service, workbook

SECTIONS = ["# GST Intelligence Report", "## Executive Summary", "## Accounting Summary", "## GST Summary",
            "## Discrepancy Report", "## Filing Preparation Data", "## Recommended Actions",
            "## Missing Information and Limitations", "## Filing Readiness"]


def stages(resp):
    return [s["stage"] for s in resp.summary["stages"]]


class TestGraphPaths(unittest.TestCase):

    def test_sufficient_evidence_path(self):
        runnable = ScriptedRunnable(analysis())
        resp, code = service(runnable).analyze_json(GstJsonRequest(records=clean_records(), business_gstin=BUSINESS))
        self.assertEqual((code, resp.status, resp.success), (200, "ANALYSIS_COMPLETE", True))
        self.assertIn("generate_analysis", stages(resp))
        self.assertNotIn("deterministic_fallback", stages(resp))
        self.assertEqual(resp.summary["filing_readiness"]["level"], "PREPARED_FOR_PROFESSIONAL_REVIEW")
        self.assertTrue(resp.summary["narrative"]["available"])
        self.assertIn("Two documents reviewed.", resp.report)

    def test_review_path_with_warnings(self):
        records = [dict(clean_records()[1], **{"Supplier GSTIN": None})]
        resp, _ = service(ScriptedRunnable(analysis())).analyze_json(GstJsonRequest(records=records, business_gstin=BUSINESS))
        self.assertEqual(resp.status, "REVIEW_REQUIRED")
        self.assertIn("generate_review_analysis", stages(resp))
        self.assertEqual(resp.summary["filing_readiness"]["level"], "NOT_READY")

    def test_insufficient_data(self):
        resp, code = service(ScriptedRunnable(analysis())).analyze_json(GstJsonRequest(records=[{"Kind": "Journal", "Notes": "x"}]))
        self.assertEqual((code, resp.status), (200, "INSUFFICIENT_DATA"))

    def test_invalid_input_routes_to_validation_error(self):
        resp, code = service().analyze_json(GstJsonRequest(json_string="[1, 2"))
        self.assertEqual((code, resp.success, resp.status), (422, False, "PROCESSING_FAILED"))
        self.assertTrue(resp.errors)
        resp, code = service().analyze_json(GstJsonRequest())
        self.assertEqual(code, 422)

    def test_llm_failure_uses_deterministic_fallback(self):
        runnable = ScriptedRunnable(*([groq_error("RateLimitError", 429)] * 10))
        resp, code = service(runnable).analyze_json(GstJsonRequest(records=clean_records(), business_gstin=BUSINESS))
        self.assertEqual((code, resp.success, resp.status), (200, True, "ANALYSIS_COMPLETE"))
        self.assertIn("deterministic_fallback", stages(resp))
        self.assertFalse(resp.summary["narrative"]["available"])
        self.assertEqual(resp.summary["narrative"]["error_kind"], "rate_limited")
        self.assertIn("deterministic fallback", resp.report)
        self.assertTrue(any("rate limit" in w for w in resp.warnings))

    def test_no_api_key_still_produces_report(self):
        resp, code = service(api_key="").analyze_json(GstJsonRequest(records=clean_records(), business_gstin=BUSINESS))
        self.assertEqual(code, 200)
        self.assertEqual(resp.summary["narrative"]["error_kind"], "not_configured")
        for section in SECTIONS:
            self.assertIn(section, resp.report)

    def test_llm_cannot_change_figures_or_categories(self):
        a = analysis(executive_summary="Net liability is INR 99,999,999.",
                     possible_classification_mismatches=[ClassificationConcern(source_row="records[0]",
                                                                               classifier_category="Sales", concern="Looks like a purchase")])
        resp, _ = service(ScriptedRunnable(a)).analyze_json(GstJsonRequest(records=clean_records(), business_gstin=BUSINESS))
        net = next(c for c in resp.summary["gst_summary"]["calculations"] if c["name"] == "potential_net_gst_liability")
        self.assertEqual(net["value"], "900.00")
        self.assertIn("| Potential net GST liability | INR 900.00 |", resp.report)
        self.assertEqual(resp.summary["classification"]["rows"][0]["category"], "Sales")
        self.assertIn("LLM_CLASSIFICATION_CONCERN", {d.code for d in resp.discrepancies})
        self.assertEqual(resp.status, "REVIEW_REQUIRED")

    def test_untrusted_text_reaching_the_report_is_escaped(self):
        hostile = "[click](http://evil) <script>x</script> | # heading"
        # Generated narrative is untrusted.
        resp, _ = service(ScriptedRunnable(analysis(executive_summary=hostile))).analyze_json(
            GstJsonRequest(records=clean_records(), business_gstin=BUSINESS))
        self.assertNotIn("<script>", resp.report)
        self.assertNotIn("[click](http://evil)", resp.report)
        # Sheet names flow into source references.
        dup = [dict(clean_records()[0], **{"Supplier GSTIN": None})] * 2
        resp, _ = service(api_key="").analyze_workbook(workbook(**{"A_b(1)#|x": dup}), "b.xlsx", BUSINESS)
        self.assertIn("A\\_b\\(1\\)\\#\\|x\\!R2", resp.report)
        self.assertNotIn("A_b(1)#|x!R2", resp.report)
        self.assertEqual(esc("a|b*c"), "a\\|b\\*c")

    def test_excel_and_json_share_the_same_analysis(self):
        svc = service(api_key="")
        json_resp, _ = svc.analyze_json(GstJsonRequest(records=clean_records(), business_gstin=BUSINESS))
        xl_resp, _ = svc.analyze_workbook(workbook(Books=clean_records()), "books.xlsx", BUSINESS)
        for key in ("accounting_summary", "gst_summary"):
            strip = lambda calcs: [{k: v for k, v in c.items() if k != "source_refs"} for c in calcs]  # noqa: E731
            self.assertEqual(strip(json_resp.summary[key]["calculations"]), strip(xl_resp.summary[key]["calculations"]))
        self.assertEqual(xl_resp.summary["classification"]["rows"][0]["source_ref"], "Books!R2")

    def test_discrepancy_explanations_rendered(self):
        records = [dict(clean_records()[1], **{"Supplier GSTIN": None})]
        a = analysis(discrepancy_explanations=[DiscrepancyExplanation(code="SUPPLIER_GSTIN_MISSING",
                                                                      explanation="No GSTIN.", why_it_matters="ITC.")])
        resp, _ = service(ScriptedRunnable(a)).analyze_json(GstJsonRequest(records=records, business_gstin=BUSINESS))
        self.assertIn("Explanation (generated): No GSTIN.", resp.report)


if __name__ == "__main__":
    unittest.main()
