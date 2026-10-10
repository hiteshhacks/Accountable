# VYOM+ Model V3: Data Audit and Feasibility Result

**Date:** 2026-10-10
**Outcome: no V3 model artifact was produced.** The training data contains structured fields, so a schema-aligned feature contract could be built and tested. But every split of that data leaves the generator's vocabulary shared between training and test. A saved classifier would therefore have no defensible performance estimate. This report gives the evidence, the exact data gap, and the smallest next step.

**Evidence files:**
- [v3_cv_metrics.csv](v3_cv_metrics.csv)
- [v3_experiment_details.xlsx](v3_experiment_details.xlsx), with sheets `Audit`, `CV_Metrics`, `Class_Status`, `Label_Quality`, `Per_Class`, `Confusion_Primary` and `Split_Groups`
- produced by `python -m vyom.train_v3`

The evaluation workbook (`Voucher_Classification_Test_Cases_v2.xlsx`) was not read, trained on or used for any design decision.

---

## 1. What training data was used

| Item | Value |
|---|---|
| File | `data/synthetic/synthetic_voucher_dataset_v5_review_ready.xlsx` (sha256 `1865fba9…d30d`) |
| Inputs | Sheet `model_inputs_no_label`: 5,400 rows × 30 canonical fields. The dataset itself excludes `document_type`, labels and audit columns. |
| Labels | `labelled_data_review.voucher_type`. **All 5,400 are `UNVERIFIED_SYNTHETIC_LABEL`**, and the dataset README states "no human gold labels". |
| Classes | 27, with 200 rows each |
| Used for experiments | 5,200 rows, 26 classes (`Other / Miscellaneous` excluded; see §4) |
| Human review | 540 rows (20 per class) were labelled by two reviewers. Cohen's kappa was 0.84 and 429 rows reached "provisional consensus" (explicitly *NOT GOLD*). |

The existing models trained on those 429 consensus rows. They add no corrections: the consensus label equals the synthetic label on 429 of 429 rows. They only remove the 111 disputed rows.

## 2. Structured fields, or only narratives?

**Structured fields.** The records use the canonical schema:
- **Always filled:** narration, item and date.
- **About 95% filled:** party fields.
- **Partly filled:** amounts, rates and quantities (53–63%), plus status, method, reason, warehouse and account-side fields.

So the schema gap is not that the data is narrative-only. The problem is what the values are:

| Finding | Evidence |
|---|---|
| Values come from small vocabularies chosen per class | Only **238 distinct narration sentences** once the generated reference/date suffix is removed (3–15 per class). `item_description` has 118 values, and a value predicts its class 96.8% of the time. `payment_status` has 35 values, which predict the class 60.4% of the time. |
| Narrations explain the label | 58% of narrations contain a distinctive word from their own label (100% for 11 classes), e.g. "…are classified as Import because…". |
| `document_type` is the label | It is filled in for 15 classes, and each value maps 1:1 to a class. The existing baseline's `make_text` includes it: that recipe scores **1.000** with it and 0.967 without it. |
| Split groups leak | 138 narration sentences appear in more than one `split_group`, the grouping the existing training scripts split on. Both recipes score **1.000** under that split. |
| No split can withhold the vocabulary | When rows that share a sentence, status or item are linked, **all 27 classes form a single connected group**. No class can have test rows whose narration, status and item are all unseen. |
| No identifier-prefix leak | `invoice_number` is `DOC-…` for every class. |
| Labels contradict the guideline | The guideline says Rejection Out means a customer rejection. Every synthetic Rejection Out narration says customer, yet 96 of 200 rows have status "Returned to supplier". |

### Training fields compared with the evaluation adapter

- **Mapping coverage:** `adapter.CANONICAL_MAPPING` maps wide-workbook columns onto 20 of the 30 training fields. These 10 training fields cannot be reached from the wide schema at all: `invoice_number`, `gst_rate_percent`, `discount_amount`, `employee_count`, `attendance_days`, `import_export_reference`, `warehouse_from`, `warehouse_to`, `movement_reason`, `deductions_amount`.
- **The mapping is unvalidated.** The evaluation pipeline imports it but never uses it.
- **Several mapped fields mean something different.** For example:
  - `Status`, an expense-approval status, maps to `payment_status`;
  - `Payer Organization` maps to `seller_supplier`;
  - a stock-adjustment `Reason` maps to `transaction_narration`.
- **Category definitions differ.** The training guideline defines Material In and Material Out as internal movements, but in the evaluation workbook they are subcontracting records. Job Work In and Job Work Out are marked provisional in the guideline.
- **Conclusion: the schema mismatch with the wide evaluation format has not been solved,** and nothing here claims it has.

## 3. Which model was trained

**No model was saved.** I used 5-fold cross-validation to compare feature sets, fitting each fold in memory. The primary candidate was fixed before any results were seen.

| Name | Model |
|---|---|
| `v1_recipe_*` | The existing TF-IDF recipe (word and character TF-IDF + logistic regression), refitted, with and without `document_type` |
| **`v3_field_tfidf_all` (primary)** | Field-aware TF-IDF + logistic regression over the V3 contract: every token is tagged with its field |
| `v3_field_tfidf_narration_only` / `_no_narration` | Ablations of the primary |
| `v3_tabular_structured(_item)` | HistGradientBoosting on categorical, numeric, presence and relationship features, with and without `item_description` |
| `v3_numeric_presence_only`, `v3_presence_only` | Numeric plus field-presence flags, and field-presence flags only (a layout baseline) |

- **Model choice:** scikit-learn's HistGradientBoosting stands in for CatBoost. CatBoost is not installed, and scikit-learn's model needs no new dependency.
- **The V3 contract** (`src/vyom/features_v3.py`) is one preprocessing step shared by training and inference:
  - identifier and party values contribute presence only;
  - text has identifier tokens and digits masked;
  - date, `document_type`, labels and outputs are excluded.

## 4. Which categories are learnable

On this data, "learnable" can only mean that the **synthetic label is recovered for rows whose narration sentence was not seen in training**. No category has been shown to be learnable from real transactions.

| Group | Classes |
|---|---|
| Synthetic labels recovered (primary recall ≥ 0.8 on unseen sentences) | 23 classes |
| Not reliably recovered (recall 0.665–0.675) | Export, Import, Job Work Out Order |
| Recovered, but a reviewer disputed the synthetic label | Rejection In (reviewer 1 agreed on 8/20), Rejection Out (6/20), Purchase Return / Debit Note (9/20), Contra (12/20), Advance / Prepayment (13/20), Journal (14/20), Sales Return / Credit Note (reviewer 2 agreed on 11/20) |
| Not trained | **Other / Miscellaneous** |

- **Rejection In** has 200 synthetic rows and is recovered at recall 1.0. But both its reviewed-label support (8/20 from reviewer 1) and its definition (physical rejection vs debit note) are disputed. A model would learn the generator's version of the class, not a verified one.
- **Other / Miscellaneous** is defined as abstain-and-review. Both reviewers left all 20 reviewed rows unresolved ("NEEDS_ADJUDICATION"). Learning it would only learn generator markers such as status "Pending review". It should be a review route, not a class.

## 5. Training and validation method

- **Splits:** `StratifiedGroupKFold`, 5 folds with seed 42, **grouped by narration sentence**. Every prediction is made out-of-fold, so all 5,200 records are scored once.
- **Diagnostic splits:**
  - the same splitter grouped by `payment_status` value, so test rows have an unseen status;
  - grouped by `item_description` value, so test rows have an unseen item;
  - `GroupKFold` by `split_group`, which is how the existing scripts split.
- **Existing artifact:** `models/vyom_plus_tfidf_baseline_model.pkl` was scored as saved on the 4,860 rows outside the 540-row review queue. It never trained on those rows, but it saw the same templates.
- **Rules only, and model plus rules: not technically valid on this data.** The rule engine needs wide-schema fields, and it returns `NO_RULE` for all 5,400 canonical records. Model plus rules is therefore identical to model only, so rule overrides and ambiguous outcomes are both zero.

## 6. Metrics and sample counts

Macro-F1 is computed over the 26 training classes; weighted-F1 equals macro-F1 because the classes are balanced. The CV rows use 5,200 out-of-fold records, the artifact row 4,860 records.

| Model | Unseen narration sentences | Unseen status values | Unseen item values | Split by `split_group` |
|---|---|---|---|---|
| v1 recipe **with** `document_type` | 1.000 | – | – | 1.000 |
| v1 recipe without `document_type` | 0.967 | 1.000 | 0.999 | – |
| **v3 field-aware TF-IDF (primary)** | **0.954** (acc 0.955) | 1.000 | 1.000 | 1.000 |
| v3 narration only | 0.637 (acc 0.680) | – | – | – |
| v3 without narration | 0.966 | – | – | – |
| v3 structured fields, no text | 0.982 | **0.341** (acc 0.380) | 0.944 | – |
| v3 structured fields + item | 0.943 | 0.962 | **0.251** (acc 0.289) | – |
| v3 numeric + presence only | 0.917 | – | – | – |
| v3 presence only (layout) | 0.657 | – | – | – |
| Existing TF-IDF artifact (25 classes), 4,860 unseen rows, 27 classes | acc 0.885, macro-F1 0.855; recall 0 for Rejection In and Other / Misc | | | |

**What the numbers show:**
- **Each model collapses when the vocabulary it relies on is withheld.** Narration alone drops to 0.64 on unseen sentences. The structured model drops to 0.34 on unseen statuses. Structured plus item drops to 0.25 on unseen items.
- **The text models stay near 1.0 under the status and item splits** only because their narration sentences are still seen.
- **Every number above measures recall of this generator's vocabulary,** not an understanding of transactions.
- **Field presence alone reaches 0.66,** so layout signal also exists in this data.
- **None of these figures predicts real-world accuracy, and no accuracy target is implied.**

Per-class metrics and the confusion matrix of the primary model are in `v3_experiment_details.xlsx`.

## 7. Files created or modified

| File | Change |
|---|---|
| `src/vyom/features_v3.py` | **New.** The V3 feature contract plus the `ContractTokens` and `ContractTabular` transformers |
| `src/vyom/train_v3.py` | **New.** Data loading, label-quality table, cross-validation experiments, reports. Writes reports only and refuses to overwrite them |
| `tests/test_features_v3.py` | **New.** 16 tests covering label isolation, feature consistency, missing fields, deterministic training, supported categories and inference compatibility. Models are fitted in memory and nothing is saved |
| `reports/v3_cv_metrics.csv`, `reports/v3_experiment_details.xlsx`, `reports/v3_experiment_summary.md` | **New** |

No model, report, workbook or existing source file was modified.

## 8. What labelled data is required

**The gap, precisely:**
- there are no verified labels;
- every value comes from a small synthetic vocabulary;
- the records are not in any real export format;
- the category definitions are unresolved for returns versus rejections, Contra, Advance, Journal, Job Work, Material In/Out and Other.

**Smallest defensible next step**, in order:

1. **Freeze the label policy and adjudicate the 111 queued rows.** This costs no new data. The disputed definitions (Rejection In/Out vs Debit/Credit Note, Contra, Advance / Prepayment, Journal, Job Work and Material In/Out, Other as abstention) have to be settled before any label can be trusted, synthetic or real.
2. **Build a small independent development pilot of real structured records.**
   - Export them from 2–3 organisations' accounting systems.
   - Map them into the canonical fields, and record the mapping.
   - Have two accountants label them under the frozen policy, following [independent_evaluation_design.md](independent_evaluation_design.md) §4.
   - About 30 records per class (around 800) is enough to measure whether any V3 feature set transfers, to validate the column mapping, and to estimate a learning curve.
   - This is a **development** set. The ≥60-per-class locked test set in the design document must be a separate, later collection.
3. **Train V3 on real labelled records only after step 2,** sized from the pilot's learning curve. Expect several hundred labelled records per class across several organisations, but don't commit to a number before the pilot.
   - Synthetic rows may be used for pre-training or augmentation.
   - Results must always be reported on real held-out records.

Until then, the contract and tests in this change are the reusable output, and no V3 performance should be claimed.
