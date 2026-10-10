# VYOM+ Rule-Engine Audit: Is the 100% Result Trustworthy?

**Date:** 2026-10-10
**Scope:** `Voucher_Classification_Test_Cases_v2.xlsx`, sheet `Test Cases`. It has 120 records, 168 feature columns and 24 categories with 5 records each.
**Evidence:** [rule_engine_audit.xlsx](rule_engine_audit.xlsx) (13 sheets), [rule_ablation_metrics.csv](rule_ablation_metrics.csv), and [vyom_plus_evaluation_predictions_decision_status.xlsx](vyom_plus_evaluation_predictions_decision_status.xlsx), the corrected prediction report.

## Verdict

The 100% figure reproduces exactly and involves no label leakage. However, it does not measure transaction understanding.

- **The rules decide every record.** They matched all 120 records, so the TF-IDF and Dual Encoder V2 predictions were never used.
- **A third of records need an identifier code.** 40 of 120 are classified only through ID prefix codes (`PO…`, `DBN-…`, `EXP…`, `PUR-…`).
- **The rest rely on the form, not the content.** The other 80 also match a field-presence clause, but each category in this workbook is a separate form with its own columns. That clause therefore identifies which form a record came from, not what the transaction does. Looking only at which columns are filled in classifies 120/120 records with no rules at all.
- **Accuracy falls once ID prefixes are gone.** Without them, the best configuration reaches 75.0–78.3%, and none of the conflicting records in the stress tests are flagged.
- **The confidence of 1.0 was a constant,** not a probability.

---

## 1. Was the 100% score independently reproduced?

**Yes.** I re-ran the evaluation pipeline and recomputed every metric with my own counting code, independent of sklearn.

| Configuration | Correct | Accuracy | Macro-F1 | Weighted-F1 |
|---|---|---|---|---|
| TF-IDF baseline alone | 54 / 120 | 45.0% | 0.3832 | 0.3832 |
| Dual Encoder V2 alone | 45 / 120 | 37.5% | 0.2745 | 0.2745 |
| TF-IDF + semantic rules | 120 / 120 | 100% | 1.0000 | 1.0000 |
| Dual Encoder V2 + semantic rules | 120 / 120 | 100% | 1.0000 | 1.0000 |

All 28 verification checks pass (sheet `Metric_Verification`):

- **Completeness:** all 120 records are present, with no duplicates, and every category has support of exactly 5.
- **Row alignment:** the original report's 168 feature columns match the workbook cell for cell, with 0 differences, so predictions sit on the correct rows.
- **Predictions are genuinely generated:** the report's `Predicted Voucher Category` equals a fresh prediction made without labels on 120/120 rows.
- **The `Correct` column is consistent:** it equals `prediction == ground truth` on 120/120 rows.
- **Predictions are not copied from labels:** with ablations, the same code produces 23–40 wrong predictions.
- **The original reports reproduce exactly.** The four comparison rows, the per-class report and the confusion matrix match recomputation, with a maximum difference of 0.
  - Re-running the fixed pipeline also regenerated `evaluation_per_class_report.csv`, `evaluation_confusion_matrix.csv` and `evaluation_model_comparison.csv/.json`. They are identical to the originals apart from line endings.

## 2. Which rules produced the correct predictions?

- **Every rule fires exactly 5 times.** All 24 rules in `rule_engine.py` fire, each on the 5 records of its own category and nowhere else.
- **No record matched more than one rule.**
- **The model fallback (`rule_engine.py:257-260`) was used 0 times.** "TF-IDF + rules" and "DE V2 + rules" are therefore the same rule-only result, and which model is attached makes no difference.
- **The rules overrode the TF-IDF prediction on 66 records and the DE V2 prediction on 75.**

Sheet `Rule_Inventory` lists each rule's exact source condition, the fields it reads, its evidence type, its precedence and how many records it fired on. Sheet `Rule_Trace` gives, for every record:

- the triggering fields and values;
- whether it depends on a prefix;
- whether it overrode each model;
- whether it is correct.

### Exact code path of the evaluation

`python -m vyom.evaluate_workbook` → `run_pipeline` (`evaluate_workbook.py`):

1. `adapter.load_evaluation_workbook` (`adapter.py:142-174`) separates `Voucher Category` into `y` and leaves 168 feature columns in `X`.
2. `evaluate_baseline_model` (`evaluate_workbook.py:41-56` at HEAD):
   - `X.apply(adapter.serialize_wide_row)` (`adapter.py:190-203`) turns each record into `Field: value | …` for its non-empty fields, skipping the label.
   - The pickled TF-IDF pipeline (25 classes) then runs `predict` and `predict_proba`.
3. For each record, `rule_engine.evaluate_transaction_rules(row, base_prediction=<TF-IDF prediction>)` (`rule_engine.py:22-260`) runs. The first matching rule wins; otherwise the model prediction is returned.
4. Confidence is set to `conf = 1.0 if applied else b_score` (`evaluate_workbook.py:152` at HEAD), with status `RULE_VERIFIED`.
5. Metrics are computed with sklearn from `y` and the final predictions.
6. For the comparison, `evaluate_dual_encoder_model` (`evaluate_workbook.py:59-96`):
   - serializes the same text;
   - encodes it with MiniLM (`sentence-transformers/all-MiniLM-L6-v2`) through `dual_encoder.encode_texts`;
   - applies the `DualEncoder` head from `models/vyom_dual_encoder_v2.pt`, then the same rule engine with DE V2 as the fallback.

These are not on the evaluation path:
- `adapter.map_wide_to_canonical` / `CANONICAL_MAPPING` (imported but unused);
- `rule_correction.py`, `evaluate_rule_correlation.py` and `predict.py`.

### What the rules actually test

- **Only three kinds of test.** Every clause is one of:
  - a `startswith` test on an identifier;
  - a non-empty test on a column;
  - an empty test on a column.
- **No rule reads a field's meaning.** None interprets narration text, amounts, signs, or debit/credit sides.
- **Matching is case-sensitive.** For example, `"po9634122"` would not match `PO`.

| Evidence type | Rules |
|---|---|
| Identifier prefix required, with no prefix-free path | R07 Purchase Order (`PO`), R08 Sales Order (`SO`), R15 Expense (`EXP`), R16 Export (`EXP`); R03 Debit Note (`DBN`, or reference `PUR`), R04 Credit Note (`CRN`, or reference `SAL`), R05 Purchase (`PUR-`, or reference `PO`), R06 Sales (`SAL-`, or reference `DN`) |
| Identifier prefix **OR** a field-presence pattern | R01, R02, R09–R14, R17–R24 |

- **A matching rule always replaces the model prediction.** Among rules, the first match wins, so rule order resolves conflicts silently (see §8).
- **No rule reads the ground-truth label,** directly or indirectly, at run time (see §6).

## 3. How many predictions rely mainly on identifier prefixes?

| Records | Share | How they were matched |
|---|---|---|
| 23 | 19.2% | **Own-ID prefix only**: Purchase Order 5, Sales Order 5, Expense 5, Export 5, Purchase 3 |
| 17 | 14.2% | **Own-ID prefix or a reference-ID prefix**: Debit Note 5 (via `PUR-`), Credit Note 5 (via `SAL-`), Sales 5 (via `DN`), Purchase 2 (via `PO`) |
| 80 | 66.7% | **Own-ID prefix and a field-presence clause both matched**, so the prefix was redundant |

**40 of 120 records (33.3%) have no prefix-free path to the correct answer.** All 120 records also matched an own-ID prefix.

## 4. Accuracy with identifier-prefix rules disabled

| Configuration | Rules fire | Rules correct | Rules only* | TF-IDF + rules | DE V2 + rules |
|---|---|---|---|---|---|
| A. All rules enabled | 120 | 120 | 120 (100%) | 120 (100%) | 120 (100%) |
| **B. Own-ID prefix clauses disabled** | 97 | 97 | 97 (80.8%) | **102 (85.0%)** | **104 (86.7%)** |
| E. Only field-presence clauses (all prefix clauses disabled) | 80 | 80 | 80 (66.7%) | 90 (75.0%) | 93 (77.5%) |

\* "Rules only" counts records with no matching rule as wrong.

- **Macro-F1 values:**
  - B: 0.828 (TF-IDF) and 0.836 (DE V2);
  - E: 0.700 and 0.718.
- **Configuration B keeps the reference-ID prefix clauses** (`PUR-`, `SAL-`, `PO`, `DN`). That is why the Debit Note, Credit Note and Sales rules still fire there.
- **The models recover few of the records the rules give up.** On the 23 records left to them in B, TF-IDF recovers 5 and DE V2 recovers 7.

## 5. Accuracy with identifier values removed or neutralised

Identifier columns are listed in the workbook's `README` sheet. They are 20 own-document ID columns and 15 reference-ID columns. "Neutralised" means `RJN-IN-516405` becomes `DOC-516405`: the field is still filled in, but the prefix is gone.

| Configuration | Rules fire | Rules only | TF-IDF + rules | DE V2 + rules | TF-IDF alone | DE V2 alone |
|---|---|---|---|---|---|---|
| C. Identifier values removed | 80 | 80 (66.7%) | **92 (76.7%)** | **94 (78.3%)** | 58 (48.3%) | 43 (35.8%) |
| D. Identifier prefixes neutralised | 80 | 80 (66.7%) | **90 (75.0%)** | **94 (78.3%)** | 53 (44.2%) | 45 (37.5%) |

- **Rule outcomes in C, D and E are identical:** the same 80 records, all correct. Those 80 survive only because of field-presence clauses.
- **On the 40 records that need an identifier, the models are weak fallbacks.** They recover only 10–14.
- **Removing identifiers slightly helps TF-IDF on its own** (54 → 58 correct). The workbook's ID codes are noise to a model trained on another schema.

## 6. Was any leakage found?

**No run-time leakage.** All nine checks on sheet `Leakage_Checks` pass:

- **Static scan:** a syntax-tree scan finds 80 field names referenced in `rule_engine.py`. None of them is `Voucher Category`, `Correct` or an output column. There is no file input/output, no row-position access and no global state.
- **Dynamic read check:** I ran all 120 records through a wrapper that records every field read and raises an error if row position is accessed. 49 distinct fields were read, all among the 80, and position was never accessed.
- **Injection test:** I added wrong labels as `Voucher Category`, `Correct=False`, and the true labels as `Predicted Voucher Category`. 0 of 120 rule predictions changed.
- **Shuffle test:** after shuffling the rows and re-aligning, 0 rule or TF-IDF predictions changed.
- **No lookup tables:** none of the workbook's identifier values appears anywhere in `src/` or `tests/`.
- **No answer-encoding columns:** no column name carries category, label or test-case wording.
- **Pipeline inputs:** with `run_pipeline` wrapped, none of the 120 rule-engine calls or 120 serializer calls received a label or output column.
- **Test fixtures:** with the full test file wrapped, the only test that passes label columns to the rules is `test_04`, and it does so on purpose.

**However, the evaluation design does not support a claim of generalisation:**

- **The test set appears to have been the development set.**
  - `rule_engine.py`, `evaluate_workbook.py`, the tests and the 100% reports were all added in one commit (`0c42d89 first plan`).
  - Every one of the 80 fields the engine references exists in this workbook.
  - Each rule fires on exactly its own category's 5 records.
  - The prefix codes tested (`RJN-IN`, `JWIO`, `MIW`, `MOW`, `IBL`, `SA`, `SC`…) are this workbook's numbering scheme.
  - Git history cannot prove the workbook was viewed while the rules were written, but the fit is exact. Treat 100% as an in-sample result.
- **The form layout encodes the label.** The workbook has 25 distinct sets of filled-in columns, and each set belongs to exactly one category. A leave-one-out lookup on that column set alone, with no rules, classifies 120/120 records (sheet `Schema_Signatures`). This is not label leakage, because the column layout is legitimately available at prediction time. But it does make this workbook unable to tell understanding apart from form detection.
- **`test_04` was vacuous.** It built `fake_labels` but never used them, so it compared two identical copies of `X`. I fixed it (see "Changes made").
- **`test_11` asserts accuracy above 0.95 on the evaluation workbook.** This turns the test set into a regression target. I left it unchanged; see §9.

## 7. Were the confidence scores misleading?

**Yes.**

- **The 1.0 was hard-coded.** `conf = 1.0 if applied else b_score` assigned 1.0 to every rule match: all 120 records, with status `RULE_VERIFIED`. It was not estimated from anything, and "verified" overstates what is only a prefix or field-presence match.
- **The 1.0 hid disagreement.** The TF-IDF model agreed with the rule on only 54 of 120 records. On the records the rules overrode, its mean score was 0.10. It cannot predict `Rejection In` at all (5 records).
- **Rule precision of 120/120 holds only on this workbook.** On the modified records, rules decided 7 conflicting or ambiguous cases without any flag. Six of these were decided by an identifier prefix or by rule order rather than by the field evidence: M07, M11, M12, M13, M14, M21. Each would have been reported at 1.0.
- **The model scores are not calibrated either.**
  - TF-IDF: mean top score 0.13 against an accuracy of 0.45.
  - DE V2: mean top score 0.43 against an accuracy of 0.375.

**Correction made.** The original report is untouched. The fixed pipeline wrote [vyom_plus_evaluation_predictions_decision_status.xlsx](vyom_plus_evaluation_predictions_decision_status.xlsx). Its predictions are identical (120/120), and `Prediction Confidence` is replaced by:

- `Decision Source` (`RULE` / `MODEL`);
- `Rule Matched`;
- `Decision Status` (`RULE_MATCH`, `MODEL_PREDICTION`, `MODEL_LOW_SCORE` below 0.60, or `MODEL_NO_SCORE`);
- `Model Prediction`;
- `Model Score (Uncalibrated)`, which is the model's score for its own prediction;
- `Rule Overrode Model`.

No probability is given for a rule decision. A model without `predict_proba` now gets an empty score instead of 1.0.

## 8. Which rules look semantically robust, and which depend on the template?

None of the rules has been tested outside this template. The ranking below is about how much a rule depends on this workbook's specific conventions.

| Group | Rules | Why |
|---|---|---|
| **Depends on identifiers** (fails when ID formats change) | R03, R04, R05, R06, R07, R08, R15, R16 | They have no prefix-free path. M16–M18, M22 and M23 keep every order or claim field but remove or neutralise the ID; no rule fires. TF-IDF then gets all 5 wrong and DE V2 gets 3 wrong. |
| **Field-presence rules based on real accounting distinctions** (plausibly transferable if a column-mapping layer supplies these fields) | R14 Salary (gross, net, payroll period), R20 Physical Stock (book vs counted quantity), R17 Import (origin country plus customs duty or units imported), R11 Contra (source and destination account plus transfer amount; does not check that both are the company's own accounts), R01/R02 Rejection In/Out (receiving company or goods-receipt reference vs customer or delivery-note reference) | They responded to the remaining evidence in M09, M19, M20 and M27. But R01/R02 settle conflicting evidence by rule order with no flag (M11–M15). In particular, an `RJN-IN` prefix beats outward evidence (M14), yet an `RJN-OUT` prefix loses to inward evidence (M15), purely because of rule order. |
| **Field-presence rules based on this workbook's column names** | R09, R10, R12/R13, R18, R19, R21/R22, R23/R24 | Paired categories are separated by column-name conventions, not by what the transaction does: <br>• Payment vs Receipt: `Payment Amount` vs `Received Amount`. <br>• Job work in vs out: `Processing Rate` vs `Service Charge` (both forms carry `Processor` and `Principal`). <br>• Material In vs Out: the "In" rule keys on `Quantity Sent` and `Date of Dispatch`. <br>• Stock Journal: `Storage Facility`, where Physical Stock uses `Storage Area`. <br>A generic export with one shared column set gives these rules nothing to match. |

These rules score 80/80 here because each form's columns are exclusive to it.

**Controlled modifications** (sheet `Modified_Records`, 27 cases built from copies of records):

- **Correct, following the remaining field evidence:**
  - M09: a rejection with its goods-receipt reference removed and its prefix neutralised;
  - M19: a goods-receipt note without its GRN Number;
  - M20: a contra record carrying a `PMT-` ID;
  - M27: a stock count carrying an `SA` ID.
- **Correct, but only through a reference-ID prefix:**
  - M01, M02: the `DBN-` ID changed or removed, but the original purchase-invoice reference `PUR-…` remains;
  - M04, M05: the same for credit notes, via `SAL-…`;
  - M25: sales, via the delivery-note reference.
- **No rule fired even though the evidence was intact:** M16, M17 (Purchase Order), M18 (Sales Order), M22 (Expense), M23 (Export). TF-IDF then predicted Delivery Note or Import.
- **Ambiguous records were decided by the model with no review flag:** M03, M06, M10, M24, M26. For M03 and M06, each model gives the same answer whatever the true return direction, so at least one of the pair is always wrong.
- **Conflicts were decided by prefix or rule order and never flagged:** M07, M11, M12, M13, M14, M21. For example, in M21 a stray `CTR-` Contra ID turns a complete payment record into Contra.

## 9. What testing is needed before claiming real-world performance?

1. **Test on a held-out set nobody looked at.** The rules should be frozen first, by recording the `rule_engine.py` commit hash. The data should be expert-labelled and come from real client exports (for example Tally or ERP). Report results without any further rule changes.
2. **Test on uniform-schema inputs**, where every voucher type shares the same columns (date, voucher number, party, ledgers, amount, narration). This is the realistic case. Today's rules would fire on none of those records, so the column-mapping layer needs to be evaluated as well.
3. **Test client-defined numbering schemes**, such as shared series across voucher types, `2024-25/0193`, lower-case codes and no prefixes.
4. **Test conflicts and abstention.** Add explicit conflict detection with a "needs review" outcome, and test it with conflicting and ambiguous records. The 27 modified cases here are a starting set.
5. **Use enough data per class to bound performance.** Even on this template, 5/5 per class only shows recall of at least 48% (95% Clopper-Pearson interval). The 120/120 overall result shows at least 97.0%.
6. **Calibrate on held-out labelled data before showing any probability.** Model-decided and rule-decided records should be calibrated separately.
7. **Fix the fallback models' coverage.** TF-IDF cannot predict `Rejection In`, and both models recover only 10–14 of the 40 records that need identifiers.
8. **Use consistent values if value-level reasoning is to be tested.** This workbook cannot test it:
   - stock discrepancy never equals counted minus book (0/5);
   - Net Payable exceeds Gross Salary in 4 of 5 payroll records;
   - PO total never equals quantity × rate (0/5);
   - payments reference `SAL-` invoices and receipts reference `PUR-` invoices, the reverse of the usual convention.
9. **Separate test-suite checks from performance targets.** Replace `test_11`'s threshold on the evaluation workbook with a check of how metrics are computed, and keep benchmark scores out of the unit tests.

---

## Changes made

- **`src/vyom/evaluate_workbook.py`:**
  - Rule matches no longer get a confidence of 1.0. The new columns are listed in §7.
  - A model without `predict_proba` gets an empty score instead of 1.0.
  - `run_pipeline` takes a new `reports_dir` argument, and the CLI has a matching `--reports-dir` flag. Side-reports now default to the output file's folder. Before this, the unit tests (`test_07`, `test_11`) overwrote `reports/evaluation_*.csv/xlsx` on every run.
  - Predictions and metrics are unchanged.
- **`tests/test_evaluation_adapter.py`:**
  - `test_04` now really injects wrong labels, `Correct` and prior predictions.
  - Added `test_15`, which checks that rule matches carry a decision status and no probability.
- **`src/vyom/rule_audit.py` (new):** the audit itself. Its clause-level mirror of the rules is checked to give the same prediction as `rule_engine.py` on:
  - the workbook;
  - configurations C and D;
  - the modified records;
  - configurations B and E, through equivalent neutralised inputs.
- **New reports:**
  - `rule_engine_audit.xlsx`
  - `rule_ablation_metrics.csv`
  - `vyom_plus_evaluation_predictions_decision_status.xlsx`
  - this summary
- **Preserved without changes:** all 28 earlier files (22 reports, 3 models, `sample_transactions.xlsx` and both copies of the workbook), checked by sha256 before and after.
- **Not changed:**
  - the rules, the models and the workbook;
  - `DEFAULT_OUTPUT`. Running `python -m vyom.evaluate_workbook` with default arguments would therefore overwrite `vyom_plus_evaluation_predictions.xlsx`; use `--output`.
- **Workbook location:** the evaluation workbook was not in the repository (`data/input/` is gitignored). I copied it unchanged from `D:\downloads_new\` (sha256 `81b11e61…a1dc`). It matches the original prediction report cell for cell.

**Environment:** Python 3.12.10 with pandas 2.3.3, scikit-learn 1.8.0 (the version the pickle was built with), torch 2.14.1+cpu and transformers 4.57.6. The MiniLM backbone came from Hugging Face. **Tests:** 16 passed.

**To reproduce** (from `VYOM_PLUS_project`, with `PYTHONPATH=src`):

```
python -m vyom.evaluate_workbook --output reports/vyom_plus_evaluation_predictions_decision_status.xlsx --reports-dir <folder outside reports/>
python -m vyom.rule_audit
python -m pytest tests
```
