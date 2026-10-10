# VYOM+ Phase 1: Adjudication Queue Summary

**Date:** 2026-10-10
**Status: queue prepared; no label has been adjudicated.** All 111 records are `PENDING`, with blank final labels and rationales.

**Files:**
- [vyom_adjudication_queue.xlsx](vyom_adjudication_queue.xlsx): the queue, built by `python -m vyom.build_adjudication_queue`
- [vyom_label_definition_gaps.md](vyom_label_definition_gaps.md): the definition questions

## 1. Sources and verification

| Source | Path | Role |
|---|---|---|
| Reviewer comparison workbook | `data/synthetic/VYOM_plus_reviewer_comparison_adjudication.xlsx` | **Authoritative.** `Adjudication_Queue` has 111 rows, every one with `needs_adjudication = True`. `Provisional_Consensus` has 429 rows, all `False`. |
| Synthetic dataset | `data/synthetic/synthetic_voucher_dataset_v5_review_ready.xlsx` | Record IDs and fields come from `human_review_queue` (540 rows), matched by case number (HR-0001 = queue row 1). Definitions come from `label_guidelines_v5`. |

**Counts reconciled with the comparison workbook's `Summary` sheet:**

| Check | Result |
|---|---|
| Records examined (reviewed by both reviewers) | **540**, all unique case IDs |
| Consensus + disputed | 429 + 111 = 540; no overlap |
| Disputed records (`needs_adjudication = True`) | **111**, matching Summary: "Records requiring adjudication: 111" |
| Exact reviewer agreement | 429 consensus + 22 both `NEEDS_ADJUDICATION` + 6 both Rejection In = **457**, matching Summary: "457/540 (84.6%)" |
| Queue fields vs `human_review_queue` | 31 shared columns are identical on all 111 rows |

The queue was taken from the source rows as they are; nothing was reconstructed.

## 2. Disagreement counts

### By kind

| Kind | Records |
|---|---|
| Two concrete labels conflict | 41 |
| One reviewer abstained (`NEEDS_ADJUDICATION`) | 42 |
| Both reviewers abstained | 22 |
| Same label, but a quality flag was raised (both Rejection In) | 6 |
| **Total** | **111** |

### By category pair (all 18 types found in the data)

| Disagreement type | Records | Priority | Definition issue |
|---|---|---|---|
| Both `NEEDS_ADJUDICATION`, generator class Other / Misc | 20 | HIGH | DEF-10 |
| Both `NEEDS_ADJUDICATION`, other records (HR-0085, HR-0190) | 2 | MEDIUM | none |
| Rejection In vs Rejection Out | 11 | HIGH | DEF-01 |
| Payment vs Purchase Return / Debit Note | 10 | HIGH | DEF-04 |
| Purchase Return / Debit Note vs Rejection In | 9 | HIGH | DEF-02, DEF-01 |
| Contra vs `NEEDS_ADJUDICATION` | 8 | MEDIUM | DEF-05 |
| `NEEDS_ADJUDICATION` vs Sales Return / Credit Note | 8 | MEDIUM | DEF-03 |
| Advance / Prepayment vs `NEEDS_ADJUDICATION` | 7 | MEDIUM | DEF-07 |
| Journal vs `NEEDS_ADJUDICATION` | 6 | LOW | none |
| Both Rejection In, with a quality flag | 6 | MEDIUM | DEF-01 |
| `NEEDS_ADJUDICATION` vs Rejection Out | 6 | MEDIUM | DEF-01, DEF-02 |
| Material Out vs Rejection In | 4 | HIGH | DEF-08, DEF-01 |
| Material In vs Rejection In | 3 | HIGH | DEF-08, DEF-01 |
| Sales vs Sales Return / Credit Note | 2 | MEDIUM | none (the guideline already excludes returns from Sales) |
| Rejection Out vs Sales Return / Credit Note | 2 | HIGH | DEF-02 |
| `NEEDS_ADJUDICATION` vs Payment | 2 | MEDIUM | DEF-06 |
| Expense vs `NEEDS_ADJUDICATION` | 2 | MEDIUM | DEF-06 |
| `NEEDS_ADJUDICATION` vs Purchase | 2 | MEDIUM | DEF-06 |
| `NEEDS_ADJUDICATION` vs Rejection In | 1 | MEDIUM | DEF-01, DEF-02 |

**The patterns named in the brief, as found in the data:**
- **Payment vs Debit Note:** 10 records.
- **Debit Note vs Rejection In:** 9.
- **Rejection In vs Rejection Out:** 11.
- **`NEEDS_ADJUDICATION` vs Contra:** 8.
- **`NEEDS_ADJUDICATION` vs Advance:** 7.
- **Rejection In is involved in 34 queued records** (11 + 9 + 6 + 4 + 3 + 1). Only 2 Rejection In rows reached consensus.
- **"Other / Miscellaneous vs a specific category" does not occur.** No reviewer used the label Other / Miscellaneous on any of the 540 records. The 20 generator-labelled "Other" records were left `NEEDS_ADJUDICATION` by both reviewers.

**Systematic patterns:**
- **Reviewer 1 reverses the Rejection In/Out direction on all 11 In-vs-Out disputes.** Customer-rejection narrations are labelled Rejection In, and supplier/inbound rejections Rejection Out. This is opposite to Reviewer 2 and to guideline v5 (DEF-01).
- **Reviewer 1 labels all 10 supplier debit notes "Payment"** at confidence 3/3 (DEF-04).

## 3. Counts by priority

| Priority | Records | Queue ranks | Criteria |
|---|---|---|---|
| HIGH | **59** | 1–59 | Two concrete labels conflict on an open definition issue (39 records), or both reviewers abstained on a record that decides the Other / Misc policy (20). |
| MEDIUM | **46** | 60–105 | Concrete conflict where the definition is not disputed; agreement with a quality flag; one reviewer abstained on an open definition issue; or both abstained on another record. |
| LOW | **6** | 106–111 | One reviewer abstained and no definition issue applies (all 6 are Journal records). |

Within each priority level, larger disagreement groups come first, since one decision settles more records. Field conflicts are listed on every record but do not change its priority.

## 4. Label-definition issues

There are 11 issues; details, representative records and proposals are in `vyom_label_definition_gaps.md`. Counts overlap where a record depends on more than one issue.

| Issue | Queued records that depend on it |
|---|---|
| DEF-01 Rejection In vs Rejection Out direction convention | 40 |
| DEF-10 Other / Miscellaneous: class or review status | 20 |
| DEF-02 Physical rejection vs financial return | 18 |
| DEF-04 Payment vs Purchase Return / Debit Note | 10 |
| DEF-03 Evidence required for a sales return / credit note | 8 |
| DEF-05 Payment vs Receipt vs Contra | 8 |
| DEF-07 Advance / Prepayment direction | 7 |
| DEF-08 Material In / Material Out scope | 7 |
| DEF-06 Payment vs Expense vs Purchase | 6 |
| DEF-09 Job Work In vs Out Order (provisional) | 0 queued, but it governs 40 consensus labels |
| DEF-11 Purchase Return vs Sales Return direction | 0 queued |

**Process issue:** Reviewer 1 cited `document_type` on 60 of the 111 records. In this dataset that field is generated alongside the label, so it is not independent evidence.

## 5. Records that may lack enough evidence for adjudication

**44 records (29 HIGH, 15 MEDIUM)** contain a factual conflict or gap in their own fields that may prevent any label from being supported. An adjudicator may need the status `INSUFFICIENT_EVIDENCE` or `NEEDS_POLICY_DECISION` for these instead of a label.

| Finding | Records | Examples |
|---|---|---|
| Narration itself states the event is unclear or held for review | 20 | HR-0301 to HR-0320 |
| Contra narration, but two different external parties named | 6 | HR-0243, HR-0245, HR-0250 |
| `document_type` (Material inward/outward) contradicts `movement_reason` = "Quality rejection" | 7 | HR-0282, HR-0427 |
| Advance with direction unstated, or item contradicts status | 6 | HR-0404, HR-0410, HR-0417 |
| Customer-rejection narration with status "Returned to supplier" | 5 | HR-0127, HR-0136 |

**Further gaps that don't block a decision on their own:**
- 25 rejection records have a `movement_reason` that doesn't describe a rejection.
- 36 records with account-dependent candidates have an empty `debit_credit_info`.
- 2 Contra records name only one party (HR-0248, HR-0249).

Each record's `Field Conflicts or Gaps` column lists what applies to it.

## 6. Recommended order for human review

1. **Settle the policy questions first, without labelling any records.** In order of how many records each one unblocks:
   - **DEF-01** Rejection In/Out direction (40 records), which must be confirmed against the target accounting software;
   - **DEF-10** Other / Miscellaneous (20);
   - **DEF-02** physical rejection vs financial return (18);
   - **DEF-04** Payment vs Debit Note (10);
   - then DEF-03, DEF-05, DEF-07, DEF-08 and DEF-06.

   Record each decision as a versioned definition. DEF-09 (Job Work) should be settled at the same time, because it governs 40 consensus labels and overlaps DEF-08.
2. **Adjudicate the HIGH records** (ranks 1–59). The 20 Other / Misc records (ranks 1–20) are resolved mechanically once DEF-10 is decided.
3. **Adjudicate the MEDIUM records** (ranks 60–105), then **the LOW records** (ranks 106–111).
4. **For every record:**
   - Fill in `Final Adjudicated Label`, `Adjudicator Rationale`, `Adjudicator` and `Adjudication Date`.
   - Set `Adjudication Status` to `ADJUDICATED`, `NEEDS_POLICY_DECISION` or `INSUFFICIENT_EVIDENCE`.
   - Don't consult the hidden `Generator_Label_AUDIT_ONLY` sheet until a decision has been recorded.
5. **Afterwards, re-check the 429 provisional-consensus labels** in classes affected by any changed definition (DEF-01, DEF-08, DEF-09 in particular). Agreement under the old wording doesn't confirm a label under the new one.

## 7. Missing files and fields

| Missing item | Search performed | Effect |
|---|---|---|
| `VYOM_plus_blind_human_review_batch.xlsx` | Repository, `D:\` and the user's Downloads, Documents, Desktop and OneDrive folders, by name pattern | Not found. The blind batch can't be compared with `human_review_queue`. |
| Reviewer 1 and Reviewer 2 individual workbooks | Same search | Not found. Reviewer labels, confidences, flags and notes are taken from the comparison workbook's copy and **cannot be verified against the reviewers' original files**. |
| `VYOM_voucher_definitions_human_review_protocol.xlsx` | Same search | Not found. The only definitions available are `label_guidelines_v5`. Whatever protocol the reviewers were given is unknown, which matters for DEF-01, where they followed opposite conventions. |

**Fields missing from the source records,** which an adjudicator may need:
- account-level debit/credit lines, or an account master (Contra, Payment, Debit Note);
- original invoice or bill references and note numbers (returns);
- which party is the reporting entity (Contra, Advance, Rejection direction).

**Truncated source text:** the comparison workbook truncated Reviewer 2's evidence strings (at most 333 characters), so some quoted narrations end mid-sentence. The full narration is in the `Field: transaction_narration` column and the `Source_Records` sheet.

**Out of scope:** the dataset's `boundary_case_review` sheet (200 rows, all `PENDING_HUMAN_REVIEW`) is a separate review set and is not part of this queue.

## 8. Validation

`tests/test_adjudication_queue.py` has 20 checks, all passing. Each check runs on both the in-memory build and the saved workbook unless noted.

| Check | Result |
|---|---|
| Queue contains exactly the records with `needs_adjudication = True` in the authoritative workbook (111) | Pass |
| No duplicated case ID or record ID | Pass |
| Reviewer 1 and 2 labels, adjudication reason and consensus label match the source, row by row | Pass |
| Record IDs, source record IDs and transaction fields match the source; `Source_Records` is a verbatim copy of the source sheet | Pass |
| Final label, rationale, adjudicator and date are blank; every status is `PENDING` | Pass |
| Priorities and definition-issue references are valid; field findings never name a category | Pass |
| Counts reconcile with the comparison `Summary` sheet; the build is deterministic | Pass |
| Source workbooks' sha256 unchanged since the build | Pass |
| Models, synthetic data and `rule_engine.py` unchanged against git HEAD | Pass |

Every pre-existing report, model, workbook and source file was also checked by sha256 before and after this work, including `features_v3.py`, which is not in git. All are unchanged.
