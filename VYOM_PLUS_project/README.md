# VYOM+ — local project scaffold

## What this project does
Accepts structured transaction rows from an Excel workbook and predicts a voucher category. This is **not OCR**. The current model is an exploratory TF-IDF + Logistic Regression baseline trained from a small provisional-consensus subset of synthetic-derived records.

## Important current limitations
- The included model predicts **25 categories**, not all 27 planned categories. `Rejection In` and `Other / Miscellaneous` are absent from its learned class list. Do not present it as a complete 27-class model.
- The current benchmark used provisional reviewer consensus, synthetic-derived data and a small split. It is not a reliable estimate of client performance.
- `model_score_uncalibrated` is the maximum classifier probability, not a calibrated confidence. All rows must be treated as provisional; review flags are aids, not guarantees.
- Do not retrain using predictions as if they were ground-truth labels. For trustworthy client evaluation, get an expert-labelled representative holdout.

## Folder map
```text
VYOM_PLUS_project/
├── data/
│   ├── input/                  # Put new client .xlsx files here
│   ├── output/                 # Generated prediction workbooks
│   └── synthetic/              # Synthetic data + provisional review workbook
├── models/                     # Current baseline model (.pkl)
├── reports/                   # Existing evaluation report and retraining metrics
├── src/vyom/
│   ├── preprocessing.py        # Shared feature normalization/text builder
│   ├── predict.py              # Excel inference CLI
│   └── train_baseline.py       # Rebuild exploratory baseline
├── tests/
├── requirements.txt
└── pyproject.toml
```

## Windows setup (PowerShell)
Use Python 3.10–3.12. From inside the `VYOM_PLUS_project` folder:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

If PowerShell blocks activation, use ` .venv\Scripts\python.exe ` directly in commands instead of activating the environment.

## Run the included sample
```powershell
python -m vyom.predict
```
Output: `data/output/classified_transactions.xlsx`

## Run a new Excel workbook
1. Copy the client's structured Excel file into `data/input/`, e.g. `client_transactions.xlsx`.
2. Ensure one transaction is represented per row and the workbook has a header row. Columns may be absent; missing fields are ignored. Use canonical field names when possible (see `src/vyom/preprocessing.py`).
3. Run:

```powershell
python -m vyom.predict --input data/input/client_transactions.xlsx --output data/output/client_transactions_classified.xlsx
```

The output retains input columns and adds `predicted_voucher_type`, `model_score_uncalibrated`, `top_3_predictions`, and `review_status`. Do not overwrite the original client file.

## Evaluate a labelled wide-schema workbook
```powershell
python -m vyom.evaluate_workbook --input data/input/<workbook>.xlsx --output reports/<new_name>.xlsx
```
Without `--output`, a new timestamped file is created in `reports/`. Existing outputs and their side-reports are never overwritten unless `--overwrite` is passed. The output keeps these separate:
- the prediction (`Predicted Voucher Category`);
- the rule status: `RULE_MATCH`, `REVIEW_REQUIRED` for conflicting evidence, `AMBIGUOUS` for insufficient evidence, or `NO_RULE`;
- the model's uncalibrated score.

Rule matches are not probabilities. Results on the supplied 120-record workbook are development results; see `reports/rule_audit_summary.md` and `reports/independent_evaluation_design.md`.

## Rebuild the exploratory baseline
This requires the included synthetic workbook and provisional comparison/adjudication workbook:

```powershell
python -m vyom.train_baseline
```

The retrained model overwrites `models/vyom_plus_tfidf_baseline_model.pkl`; metrics are written to `reports/retrained_baseline_metrics.json`. Keep a copy of the prior model if you want to compare versions. The train script reproduces the exploratory setup, not a final gold-label evaluation.

## GST Intelligence Layer (API)
The FastAPI server (`src/vyom/serve_v2.py`) adds GST analysis on top of the existing voucher classifier.

- **Python** normalises the input, calculates every total with `Decimal`, and runs the GST checks.
- **LangGraph** orchestrates the workflow (`src/vyom/gst/graph.py`).
- **A Groq-hosted model via LangChain** (`ChatGroq`) only *explains* the computed results, in a structured, validated format.

If Groq is not configured or fails, the API still returns a complete report built from the deterministic results.

**Workflow:**
1. START → validate input → normalise (Excel or JSON) → classify vouchers (existing classifier) → extract features → calculate → validate GST → check evidence.
2. The evidence check routes to either *analysis* (sufficient evidence) or *review analysis* (missing or conflicting evidence).
3. Either way, the LLM result goes to the report if it succeeded, or to a *deterministic fallback* first if it failed. Then: format report → END.
4. Invalid input goes straight to a *validation error* → END.

**Modules (`src/vyom/gst/`):**

| Module | Responsibility |
|---|---|
| `config.py` | Settings from environment variables |
| `rules.py` | Configurable GST assumptions and GSTIN validation |
| `normalize.py` | Shared Excel/JSON input adapter |
| `accounting.py` | Totals with provenance |
| `validation.py` | Discrepancies and filing readiness |
| `prompts.py`, `llm.py` | Groq service: retries, backoff, schema repair, redaction |
| `report.py` | Markdown report |
| `graph.py` | LangGraph state graph |
| `service.py` | Shared entry point used by both endpoints |

### Setup
```powershell
pip install -r requirements.txt
copy .env.example .env      # then put your key in .env (git-ignored)
uvicorn vyom.serve_v2:app --app-dir src --port 8000
```

**Environment variables** (see `.env.example`):

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Groq API key |
| `GROQ_MODEL` | Model ID; default `openai/gpt-oss-120b`, any current Groq chat model ID works |
| `GROQ_TEMPERATURE` | Sampling temperature; default 0 |
| `GROQ_MAX_TOKENS` | Maximum tokens in the narrative response |
| `GROQ_TIMEOUT` | Seconds per request |
| `GROQ_MAX_RETRIES` | Retries for transient errors, 0–5 |
| `GROQ_STRUCTURED_METHOD` | `json_schema` by default; use `function_calling` for models without JSON-schema output |
| `GST_MAX_*` | Size and row limits |
| `GST_ANALYSIS_DEADLINE_SECONDS` | Time budget for one analysis |
| `GST_RULES_PATH` | Optional JSON file overriding rates and tolerances |

**Model and quota notes:**
- Groq's model list and free-tier limits change. Check https://console.groq.com/docs/models before choosing a model.
- Rate-limit (429), timeout and 5xx errors are retried a bounded number of times with exponential backoff.
- An unavailable model or a rejected key fails fast, with a clear message in `summary.narrative`.

### Endpoints
`/predict` and `/predict/file` (classification) are unchanged. GST analysis uses two new endpoints, one per input mode, and both call the same service:

| Method | Path | Input |
|---|---|---|
| POST | `/gst/analyze` | JSON: `{"records": [...], "business_gstin": "...", "period": "..."}`, where `records` has the same shape as `/predict`. Alternatively `{"json_string": "<JSON text of that list or object>"}`. |
| POST | `/gst/analyze/file` | Multipart: `file` (`.xlsx` / `.xlsm` / `.csv`; every sheet is read) and an optional `business_gstin` form field |

Columns are matched by common names, case-insensitively, for example:
- **Document details:** `Invoice No`, `Invoice Date`, `Document Number`.
- **GSTINs:** `Supplier GSTIN`, `Customer GSTIN`.
- **Values and tax:** `Taxable Value` / `Base Amount`, `GST Rate`, `CGST`, `SGST`, `IGST`, `Cess`, `Tax Amount`, `Invoice Value`.
- **Notes and currency:** `Original Invoice Ref`, `Currency`.
- **Ledgers:** `Ledger`, `Opening Balance`, `Closing Balance`.

Label and prediction columns such as `Voucher Category` are ignored.

**Example request:**
```bash
curl -X POST http://127.0.0.1:8000/gst/analyze -H "Content-Type: application/json" -d '{
  "business_gstin": "27AAACB1234C1ZF",
  "records": [
    {"Invoice No": "S-001", "Invoice Date": "2026-09-05", "Customer GSTIN": "27AABCC5678D1ZQ",
     "Taxable Value": 10000, "GST Rate": 18, "CGST": 900, "SGST": 900, "Invoice Value": 11800}
  ]}'
curl -X POST http://127.0.0.1:8000/gst/analyze/file -F "file=@books.xlsx" -F "business_gstin=27AAACB1234C1ZF"
```

**Example response** (abridged):
```json
{
  "success": true,
  "status": "REVIEW_REQUIRED",
  "report": "# GST Intelligence Report\n\n**Status:** REVIEW_REQUIRED ...\n## Executive Summary\n...",
  "warnings": ["Narrative analysis unavailable: GROQ_API_KEY is not configured. The report was built from deterministic results only."],
  "summary": {
    "accounting_summary": {"transaction_count": 1, "calculations": [{"name": "outward_taxable_value", "value": "10000.00", "status": "COMPLETE", "method": "...", "source_refs": ["records[0]"]}]},
    "gst_summary": {"calculations": ["..."]},
    "filing_preparation": {"outward_b2b": {"rows": 1, "status": "PREPARED_FOR_REVIEW"}},
    "filing_readiness": {"level": "REVIEW_REQUIRED", "not_filed": true},
    "classification": {"rows": [{"source_ref": "records[0]", "category": "Sales", "score_uncalibrated": 0.27, "ambiguous": true}]},
    "narrative": {"available": false, "error_kind": "not_configured", "model": "openai/gpt-oss-120b"}
  },
  "discrepancies": [{"code": "AMBIGUOUS_CLASSIFICATION", "severity": "MEDIUM", "status": "POSSIBLE",
                     "message": "...", "source_rows": ["records[0]"], "evidence": {"affected_rows": 1},
                     "recommended_action": "Confirm the voucher type before using the row in GST totals.", "origin": "validation"}],
  "request_id": "ee20...",
  "errors": []
}
```

**Report status:** `ANALYSIS_COMPLETE`, `REVIEW_REQUIRED`, `INSUFFICIENT_DATA` or `PROCESSING_FAILED`.

**HTTP codes:**

| Code | When |
|---|---|
| 200 | Analysis ran (with or without a narrative) |
| 413 | Request too large |
| 422 | Invalid input, with a clear message in `errors` |
| 500 | Internal error, with a generic message; quote the `request_id` |

### What it does not do
- **It does not determine legal ITC eligibility or the correct rate for any supply.** ITC and net liability are *potential* figures with basic evidence only.
- **It does not reconcile with GSTR-2B or the GST portal.** No such data is fetched.
- **It does not file anything.** "Filing readiness" means data prepared for professional review; filing would need a separate, authorised integration.
- **It does not produce a balance sheet from transactions.** A ledger summary appears only when ledger opening and closing balances are supplied.
- **It does not ensure the category is right.** Classification comes from the existing classifier, which is trained on the development workbook and predicts 24 of the 27 categories. Categories are treated as evidence:
  - totals that depend on ambiguous classifications are marked `INCOMPLETE`;
  - the LLM can only flag a possible mismatch, never relabel.
- **Rates, tolerances and category groupings are configurable assumptions** (`src/vyom/gst/rules.py`), not GST law.

### Tests
```powershell
python -m pytest tests                      # Groq is mocked; no key or quota needed
$env:GROQ_API_KEY="..."; python -m pytest tests/test_gst_api.py -k Live   # optional live check
```

## Next development sequence
1. Finish project structure and confirm local inference runs.
2. Resolve adjudication and improve verified class coverage.
3. Add a leakage-controlled dual-encoder implementation and compare it to this baseline on the same held-out groups.
4. Build client-specific column mapping and a reviewed, expert-labelled evaluation set.
