# VYOM+ Independent Evaluation Design

**Status:** design only. This evaluation has not been run.
**Claim boundary:** until this evaluation has been completed, nothing may be claimed about how VYOM+ performs on new data. That applies to the rules, the models and the full pipeline.

**Why the existing workbook can't show this.** The 120-record workbook (`Voucher_Classification_Test_Cases_v2.xlsx`) has served as the development set. The rules were written alongside it, and each category in it is a separate form with its own columns. See [rule_audit_summary.md](rule_audit_summary.md).

**What changed since the audit.**
- The rule engine (`src/vyom/rule_engine.py`) now:
  - evaluates every rule instead of stopping at the first match;
  - returns `REVIEW_REQUIRED` when evidence supports more than one category;
  - returns `AMBIGUOUS` when the only evidence is an identifier prefix, or when return or rejection details give no direction.
- Rule matches carry a status, never a probability.
- Its result on the development workbook (117 rule matches, 3 `AMBIGUOUS`) is **not** a performance estimate.

---

## 1. Questions this evaluation must answer

1. What is the end-to-end accuracy, and the per-class precision and recall, on transactions from sources nobody looked at during development?
2. When a rule decides (`RULE_MATCH`), how often is it right? Report this separately for each type of evidence: identifier, identifier plus fields, reference plus fields, fields only.
3. Do `REVIEW_REQUIRED` and `AMBIGUOUS` flag the records that are genuinely conflicting, under-specified or likely to be wrong, without flagging too much?
4. How does performance change with document format, column layout and numbering scheme?
5. When the rules don't decide, how good is the model fallback?

## 2. What is frozen before any test data is seen

- **Code and model fingerprints.** Record the commit hash of `src/vyom/` and the sha256 of every model in `models/`. Do the same for any column-mapping configuration.
- **The exact command to be run.** For a wide-schema file:

  ```
  python -m vyom.evaluate_workbook --input <locked file> --output <new path> --reports-dir <new folder>
  ```

  The command refuses to overwrite existing outputs.
- **Pre-registered metrics, sub-groups and acceptance criteria** (§7, §8).

Changing anything after the test data is accessed makes the result a development result. Such a change must be evaluated on a new, unseen test set. Tuning against the locked test set is not allowed. That includes reading its errors and editing rules, mappings or thresholds.

## 3. Data

### 3.1 Sources

- **At least 5–8 different organisations**, outside the people and data used to build the synthetic training set and the 120-record workbook. Ideally they span several industries and accounting systems.
- **No overlap with training data.** Remove exact and near duplicates against `data/synthetic/` before labelling.
- **A custodian holds the locked test set.** Developers receive only aggregate results until the evaluation is closed.

### 3.2 Format and column-pattern groups

Every record is tagged with one group, and every metric is reported per group.

| Group | Description | Why it matters |
|---|---|---|
| F1. Wide, per-form, new author | Form-style workbooks like the current one, written by someone else with their own column names | Tests whether the rules depend on this workbook's column names |
| F2. Uniform schema | Every voucher type shares one column set (date, voucher number, party, ledger debit and credit, amount, narration), as in day-book or general-ledger exports | The realistic client case; today's rules have nothing to match here unless a mapping layer exists |
| F3. Renamed or variant headers | Same content with synonyms, abbreviations, other languages or reordered columns | Tests the mapping layer and how the rules depend on field names |
| F4. Partial records | Missing columns, empty identifiers, missing references | Tests behaviour with missing identifiers and how `AMBIGUOUS` is used |
| F5. Different numbering schemes | Client-defined voucher numbers, number series shared across voucher types, lower-case codes, no prefixes | Tests whether decisions depend on identifier prefixes |

Also tag each record with whether it has an identifier and whether it has a reference to another document. These tags allow ablations on real data.

### 3.3 Natural and stress samples

- **Natural sample:** records as they occur, stratified so that every category is represented (§5). Headline metrics come from this sample.
- **Stress sample** (reported separately and never pooled with the natural sample): genuinely conflicting or under-specified records. Collect real ones where possible, and add controlled edits of locked records written by the custodian. The 27 modified-record cases from the audit show the kinds of edits to make: conflicting identifiers, opposite references, inward plus outward evidence, missing identifiers.

## 4. Labelling protocol

1. **A written labelling guide** defines all categories, including `Other / Miscellaneous`. It also defines direction from the reporting organisation's point of view, which matters for Payment vs Receipt, Rejection In vs Out, Material In vs Out and Job Work In vs Out.
2. **Each record gets three labels from the annotator:**
   - the category;
   - **whether the record contains enough information to decide** (`DETERMINABLE` / `UNDER-SPECIFIED`);
   - **whether its evidence contradicts itself** (`CONSISTENT` / `CONFLICTING`).

   Without the last two, the review statuses cannot be evaluated.
3. **Two independent qualified accountants label every record.** They see no model or rule output. A third resolves disagreements, and both the original and the resolved labels are kept.
4. **Report agreement:** Cohen's kappa overall and per category, and the agreement rate on the determinability label. Any category with low agreement is reported with that caveat.
5. **The label column is kept in a separate file.** It is joined only after predictions have been written, as the current pipeline does when it removes `Voucher Category` before predicting.

## 5. Sample size

- **Per category:** at least 60 natural records for each category that is evaluated. For a true recall near 0.8, 60 records gives a 95% Wilson interval of about ±0.10. With 5 records per category, as in the development workbook, the lower bound for 5/5 is only about 0.48.
- **Overall:** about 1,500 natural records (24–27 categories × 60) or more. Spread them across the organisations in §3.1, with at least 100 records in each format group in §3.2.
- **Stress sample:** at least 30 conflicting and 30 under-specified records per family that has paired directions: returns, rejections, payment/receipt/contra, material in/out, job work in/out.
- **Clustered intervals:** compute confidence intervals with a cluster bootstrap over organisations, because records from one organisation are not independent.

## 6. Leakage controls

- The automated checks already in the test suite must pass on the frozen code:
  - wrong labels injected, label column absent, and label/output columns injected into rule rows (`test_04`, `test_16`, `TestDecisionSeparation`);
  - row-order and determinism checks (`test_07`, `test_18`).
- Locked test files contain no test-case IDs, scenario names or answer-bearing metadata. The custodian checks this before release.
- **Baseline that predicts from column layout alone.** Run a classifier that looks only at which columns are filled in, trained on the development workbook. If it does well on the test set, that set has the same form-per-category layout as the development data. It then cannot measure transaction understanding and must be rebalanced towards F2 and F3.
- **Rule and model scores are not calibrated.** Scores are shown only if they have been calibrated on a separate calibration split (§7.5).

## 7. Metrics (pre-registered)

### 7.1 End to end (natural sample)

Report:
- accuracy, macro-F1 and weighted-F1, each with a 95% cluster-bootstrap interval;
- per-category precision, recall and F1 with intervals, and the confusion matrix.

A record flagged for review counts as wrong for the end-to-end figure. Flagging a record does not make the system right.

### 7.2 By decision source

- **Rule coverage:** the share of records with `RULE_MATCH`.
- **Rule precision:** the accuracy of `RULE_MATCH` records, split by evidence basis (`identifier+fields`, `reference+fields`, `fields`).
- **Model fallback accuracy** on `NO_RULE` records, for TF-IDF and for Dual Encoder V2.
- **Rule overrides:** how often a rule overrode the model, and how often that override was right.

### 7.3 Review flags

- **Review rate:** the share of records that are `REVIEW_REQUIRED` or `AMBIGUOUS`.
- **Flag precision:** the share of flagged records that the annotators marked `CONFLICTING` or `UNDER-SPECIFIED`, or whose unflagged prediction would have been wrong.
- **Flag recall:** the share of `CONFLICTING` or `UNDER-SPECIFIED` records, and of all errors, that were flagged.
- **Accuracy without flagged records:** accuracy on the records that were not flagged. Report it together with the share of records it covers.

### 7.4 Robustness, per group and in ablations

- Every metric in §7.1–7.3 for each format group F1–F5, and for records with and without an identifier.
- Re-run the audit's ablations on the locked set: identifiers removed, identifiers neutralised, prefix clauses disabled.
- Add header renaming and dropping one column at a time.
- Report how much each metric drops relative to the unmodified locked set.

### 7.5 Calibration (only if scores are shown to users)

- Fit calibration on a separate labelled calibration split. Then report reliability diagrams and expected calibration error on the test split.
- Calibrate model-decided records only. Rule matches stay a status, not a probability.

## 8. Comparisons and acceptance criteria

**Comparisons to report:**
- majority class;
- each model alone;
- rules alone, with unmatched records counted as wrong;
- the column-layout baseline (§6);
- the frozen pipeline.

**Acceptance criteria.** The business owner sets them before the test data is released, and records them alongside the code fingerprints (§2). An example is:

> Accuracy on unflagged records of at least A, covering at least C of records, with a review rate of at most R, and per-category recall of at least P for these categories: …

This document deliberately sets no values for A, C, R and P.

## 9. Known gaps to address or measure

- **The rules depend on this workbook's column names.** Uniform-schema data (F2) and renamed headers (F3) need a column-mapping layer before the rules can fire at all. The mapping must be evaluated on its own: per-field mapping accuracy on the locked set.
- **Some categories cannot be decided without their identifier.** There is no prefix-free path for Purchase Order, Sales Order, Expense or Export, and Purchase vs Sales invoice records are ambiguous without their identifier. These records reach the model with `NO_RULE`, or `AMBIGUOUS` when only a prefix is present. Expect lower coverage, and measure it.
- **The TF-IDF model has 25 classes.** It cannot predict `Rejection In` or `Other / Miscellaneous`.
- **The development workbook's values contradict each other** (see the audit), so value-level checks such as amounts, debit and credit, or quantities cannot be validated on it. The locked set must use real values.

## 10. Reporting

The evaluation report must include:
- the code fingerprints;
- a description of the data: sources, groups, counts per category, labelling agreement;
- every pre-registered metric with its intervals, for the natural and stress samples separately;
- per-group results and the ablations;
- a list of failure modes illustrated with records the custodian has approved for release;
- any departure from this design.

Any statement about generalisation must be limited to the groups and organisations that were actually tested.
