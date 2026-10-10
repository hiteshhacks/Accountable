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

## Rebuild the exploratory baseline
This requires the included synthetic workbook and provisional comparison/adjudication workbook:

```powershell
python -m vyom.train_baseline
```

The retrained model overwrites `models/vyom_plus_tfidf_baseline_model.pkl`; metrics are written to `reports/retrained_baseline_metrics.json`. Keep a copy of the prior model if you want to compare versions. The train script reproduces the exploratory setup, not a final gold-label evaluation.

## Next development sequence
1. Finish project structure and confirm local inference runs.
2. Resolve adjudication and improve verified class coverage.
3. Add a leakage-controlled dual-encoder implementation and compare it to this baseline on the same held-out groups.
4. Build client-specific column mapping and a reviewed, expert-labelled evaluation set.
