# VYOM+ Label-Definition Gaps: Proposed Clarifications

**Status: PROPOSALS ONLY.** Nothing here changes an approved definition.

**Source of the existing definitions.** The only definitions found are the `label_guidelines_v5` sheet of `data/synthetic/synthetic_voucher_dataset_v5_review_ready.xlsx`. `VYOM_voucher_definitions_human_review_protocol.xlsx` was not found anywhere on disk (see the summary).

**Evidence.** Every record ID refers to the queue in [vyom_adjudication_queue.xlsx](vyom_adjudication_queue.xlsx).

**For each issue below, a qualified reviewer (an accountant familiar with the target accounting software) must:**
1. answer the clarification question;
2. approve, amend or reject the proposal;
3. record the approved wording in the official definitions, with a version number, before the affected records are adjudicated.

Records blocked by an open issue should be given the status `NEEDS_POLICY_DECISION`, not a forced label.

| ID | Issue | Records in queue | Representative |
|---|---|---|---|
| DEF-01 | Rejection In vs Rejection Out: direction convention | 40 | HR-0122 |
| DEF-02 | Physical rejection vs financial return | 18 | HR-0342 |
| DEF-03 | Evidence required for a sales return / credit note | 8 | HR-0082 |
| DEF-04 | Payment vs Purchase Return / Debit Note | 10 | HR-0523 |
| DEF-05 | Payment vs Receipt vs Contra | 8 | HR-0243 |
| DEF-06 | Payment vs Expense vs Purchase | 6 | HR-0195 |
| DEF-07 | Advance / Prepayment direction | 7 | HR-0404 |
| DEF-08 | Material In / Material Out scope | 7 | HR-0282 |
| DEF-09 | Job Work In Order vs Job Work Out Order | 0 | none in queue |
| DEF-10 | Other / Miscellaneous: class or review status | 20 | HR-0301 |
| DEF-11 | Purchase Return vs Sales Return direction | 0 | none in queue |

A record can depend on more than one issue, so the counts overlap.

---

## DEF-01: Rejection In vs Rejection Out (direction convention)

**Existing definitions:**
- Rejection In: *"Physical rejection of inbound supplier goods before financial debit-note adjustment."*
- Rejection Out: *"Physical customer rejection before financial credit-note adjustment."*

**Ambiguity or conflict:**
- **The two reviewers apply opposite conventions, consistently.** In all 11 Rejection In-vs-Out disputes, the narration names a customer in 8 and supplier or inbound goods in 3. Reviewer 2 (and the guideline) label customer rejections Rejection Out. Reviewer 1 labels the same 8 records Rejection In and the 3 supplier rejections Rejection Out. This is a naming convention, not random error.
- **"In/Out" can name either of two things:**
  - the supply direction of the original goods: inbound from a supplier = In;
  - the direction the rejected goods now move relative to the entity: goods a customer rejects come back **in**; goods the entity rejects go back **out** to the supplier.

  Some accounting software is commonly documented as using the second convention, e.g. TallyPrime's "Rejections In" and "Rejections Out" voucher types. That is the reverse of guideline v5, and it must be confirmed against the target software's documentation, not assumed.
- **The synthetic data mixes both conventions.** 5 queued records (HR-0127, HR-0129, HR-0133, HR-0136, HR-0138) have a narration in which a customer rejects the goods, yet `payment_status` is "Returned to supplier".
- **Downstream impact:** the 120-record development workbook (`Voucher_Classification_Test_Cases_v2.xlsx`) follows the guideline's convention. If the convention changes, its labels would also need review.

**Clarification question:** In the target accounting software, does "Rejection In" record goods rejected **by our customers** and received back, or goods **we** reject from our suppliers? Which convention will VYOM+ use?

**Proposed clarification (PROPOSAL):** Adopt whichever convention the target software uses, and define both classes by *who rejects* and *where the goods physically go*, for example:

> "Rejection In: goods previously sold/delivered by the entity are rejected by a customer and physically received back by the entity, before any credit note."

Add a note that `payment_status` values such as "Returned to supplier" are not direction evidence unless they agree with the narration.

## DEF-02: Physical rejection vs financial return

**Existing definitions:**
- Rejection In boundary: *"Not Purchase Return/Debit Note, which financially adjusts a booked purchase."*
- Rejection Out boundary: *"Not Sales Return/Credit Note, which financially adjusts a booked sale."*
- Open issues in the guideline: *"Confirm whether supplier goods had already been booked"* and *"Confirm whether sale credit adjustment has been booked."*

**Ambiguity or conflict:**
- **Reviewer 1 labelled 8 supplier-side rejections Purchase Return / Debit Note,** even though their narrations say "no debit note is the primary event" (e.g. HR-0342). In two further records (HR-0084, HR-0090), Reviewer 1 chose Rejection Out where the narration describes a credit to the customer balance.
- **The guideline does not say what to do when the record shows both events,** or neither. It also doesn't say what to do when `movement_reason` contradicts a rejection: 25 queued records describe a rejection but carry `movement_reason` values such as "Internal transfer", "Stock count" or "Job allocation".

**Clarification question:** When a record describes a quality rejection and does not show whether a debit or credit note was raised, is it labelled as the physical rejection, the financial return, or sent to review? Is a return reason alone ever enough to label a financial return?

**Proposed clarification (PROPOSAL):**
- Label the **physical rejection** class only when the record shows a physical rejection or return of goods with no financial adjustment.
- Label the **return / note** class only when the record shows the financial adjustment: a note number, a reversal of tax or revenue, or a debit or credit to the party balance.
- When both events or neither are shown, send the record to review. A `movement_reason` that contradicts the narration is a data-quality flag, not evidence.

## DEF-03: Evidence required for a sales return / credit note

**Existing definition:** Sales Return / Credit Note: *"Financial adjustment/reversal against a previously booked customer sale."* Open issue: *"Requires link to original sale or credit-note evidence."*

**Ambiguity or conflict:** Reviewer 1 abstained on 8 records that Reviewer 2 labelled Sales Return / Credit Note (e.g. HR-0082, whose narration says "The customer balance is credited for a return…"). The guideline says a link to the original sale is "required", but it doesn't say what counts as a link:
- an invoice number;
- an order reference;
- narration wording such as "against an earlier sale".

Several records carry only an `order_reference` or no reference at all.

**Clarification question:** Is narration that explicitly describes a credit against an earlier sale enough, or must a document reference (invoice or credit-note number) be present?

**Proposed clarification (PROPOSAL):** State the minimum evidence explicitly, for example: "an original invoice reference **or** a credit-note number **or** an explicit narration statement that a booked sale is reversed". Records with none of these are sent to review.

## DEF-04: Payment vs Purchase Return / Debit Note

**Existing definitions:**
- Payment: *"Cash/bank outflow settling an existing external obligation…"*
- Purchase Return / Debit Note: *"Financial adjustment/reversal against a previously booked supplier purchase."*

**Ambiguity or conflict:**
- **Reviewer 1 labelled 10 debit-note records "Payment"** (e.g. HR-0523), all with confidence 3/3. The narration says "A supplier-side debit note reduces a previously booked purchase…".
- **The entry contains no cash or bank account.** `debit_credit_info` is "Debit supplier payable; credit purchase/ITC adjustment".
- **The probable trigger** is that a debit to the supplier payable also appears in payment entries. The guideline doesn't say that a Payment requires a cash or bank leg.

**Clarification question:** Must a Payment voucher include a cash or bank account? Is a debit to a supplier payable with no cash or bank movement always a debit note or adjustment?

**Proposed clarification (PROPOSAL):** "Payment requires a credit to a cash or bank account. A reduction of a supplier payable without a cash/bank leg is not a Payment."

## DEF-05: Payment vs Receipt vs Contra

**Existing definitions:**
- Contra: *"Transfer between cash/bank accounts belonging to the same entity."* Open issue: *"Must identify same-entity accounts; otherwise review."*
- Payment: *"Cash/bank outflow settling an existing external obligation…"*
- Receipt: *"Cash/bank inflow settling an existing external receivable…"*

**Ambiguity or conflict:** All 8 Contra disputes are cases where Reviewer 1 abstained (e.g. HR-0243). The narration says "movement between the entity's own cash or bank balances", but:
- **No account is named** and `debit_credit_info` is empty.
- **6 records name two different organisations** in the seller and buyer fields.
- **2 records name only one party** (HR-0248, HR-0249), and it isn't clear whether that party is the entity itself.

The guideline's own rule ("otherwise review") supports abstaining, but it doesn't say which evidence identifies "same-entity accounts".

**Clarification question:** What evidence establishes that both accounts belong to the entity? Account names, an account master, or debit/credit lines? Can narration alone establish it? What should be done when external party fields are filled in?

**Proposed clarification (PROPOSAL):** "Contra requires both the debited and credited accounts to be identified as the entity's own cash/bank accounts (from debit/credit lines or the account master). Narration alone is not sufficient. External counterparty fields on a Contra record are a data-quality flag."

## DEF-06: Payment vs Expense vs Purchase

**Existing definitions:**
- Expense: *"Recognized operating cost or service/overhead… Not Payment (cash outflow only)…"*
- Purchase: *"Completed supplier-billed acquisition of goods/materials…"*
- Open issues in the guideline: *"Purchase vs Expense depends on goods/material acquisition vs service/overhead; confirm chart-of-accounts policy"*, and *"Whether some consumables are Purchase or Expense depends on company accounting policy."*

**Ambiguity or conflict:**
- **Payment vs Expense:** HR-0195 and HR-0197 say "disbursement to an external party for utility bill, not purchase recognition". Reviewer 2 chose Expense; Reviewer 1 abstained.
- **Purchase vs Expense:** HR-0329 and HR-0332 are about "office supplies" procurement. Reviewer 1 chose Purchase; Reviewer 2 abstained. This is the consumables policy the guideline leaves open.

**Clarification question:**
- Is a cash settlement of a service bill a Payment (settlement) or an Expense (cost recognition) when the record does not show a separate bill booking?
- Are office supplies and similar consumables Purchase or Expense?

**Proposed clarification (PROPOSAL):**
- "When the record's primary event is a cash/bank outflow and it does not recognise the cost itself, label Payment."
- Publish a consumables list naming which items count as Purchase and which as Expense, approved by the chart-of-accounts owner.

## DEF-07: Advance / Prepayment direction

**Existing definition:** *"Money paid/received before fulfilment or final invoice, to be adjusted later."* Open issue: *"Direction and context may determine whether a more specific voucher type is needed."*

**Ambiguity or conflict:**
- **The direction isn't stated.** 5 queued records (e.g. HR-0404) say funds are "paid or received in advance".
- **Fields contradict each other.** HR-0404 and HR-0417 have item "customer advance received" while `payment_status` is "Prepaid".
- **The guideline itself leaves open** whether direction matters.

**Clarification question:** Is Advance / Prepayment one class covering both directions? Or should advances be labelled Payment or Receipt, with an advance marker?

**Proposed clarification (PROPOSAL):** Choose one of these two options and record it:
1. **Keep one direction-neutral class,** and require only evidence that the transaction happens before fulfilment.
2. **Split it** into "Advance Paid" and "Advance Received", or label it Payment or Receipt with an advance flag.

Under either option, records whose direction cannot be established are sent to review.

## DEF-08: Material In / Material Out scope

**Existing definitions:**
- Material In: *"Internal inbound material movement, not external purchase and not job-work return."*
- Material Out: *"Internal issue/movement of material to site/project/production, not external sale or subcontract job work."*

**Ambiguity or conflict:**
- **Fields contradict each other.** 7 queued records (e.g. HR-0282, HR-0427) have `document_type` "Material inward record" or "Material outward record" but `movement_reason` "Quality rejection". Reviewer 1 labelled all 7 Rejection In. That includes 4 *outward* material issues, which is directionally inconsistent with any rejection-in reading.
- **The definitions disagree with the development workbook.** In that 120-record workbook, Material In/Out records are subcontracting records (subcontractor or contractor, "Subcontracting Job"), which the guideline explicitly excludes.

**Clarification question:**
- Do Material In/Out cover only internal movements, or also material sent to and received from subcontractors?
- When `document_type` and `movement_reason` disagree, which field governs?

**Proposed clarification (PROPOSAL):**
- Confirm the scope against the target software. If subcontracting moves are Material In/Out, remove the "not subcontract job work" exclusion and redefine Job Work In/Out Order (DEF-09) to match.
- Treat conflicting `movement_reason` values as a data-quality flag, and send the record to review.

## DEF-09: Job Work In Order vs Job Work Out Order

**Existing definitions:**
- Job Work In Order: *"PROVISIONAL: inbound receipt of processed goods back from an external job worker."*
- Job Work Out Order: *"PROVISIONAL: materials/components sent to an external job worker for processing."*
- Open issue: *"Accounting software nomenclature varies. Confirm… before gold labeling."*

**Ambiguity or conflict:**
- **There is no disputed record in the queue,** because all 40 reviewed Job Work records reached consensus.
- **But the definitions are still marked provisional.** They describe goods *movements* while the class names say *Order*, and they overlap with Material In/Out (DEF-08).
- **Reviewer agreement doesn't confirm them,** because both reviewers applied the same provisional text.

**Clarification question:** Are these classes purchase-order-like *orders* placed on or received from a job worker, or the *movements* of goods to and from the job worker? Which side is "In": the principal or the job worker?

**Proposed clarification (PROPOSAL):** Define both classes from the target software's voucher types, and state which party the entity is: principal or job worker. Treat the 40 consensus Job Work labels as provisional until this is done.

## DEF-10: Other / Miscellaneous — voucher class or review status

**Existing definition:** *"Insufficient evidence for a supported specific class; should trigger manual review."* Boundary: *"Not a catch-all for known but confusing categories."* Open issue: *"Prefer abstention/manual review rather than forcing a label."*

**Ambiguity or conflict:**
- **The definition describes a review status,** "should trigger manual review", but it is listed as one of the 27 voucher classes.
- **Every queued "Other" record says it is unclear.** All 20 (HR-0301 to HR-0320) have narrations stating the event is unclear or held for review, status "Pending review", and `document_type` "Unclassified record - review required".
- **Both reviewers abstained (`NEEDS_ADJUDICATION`) on all 20,** and no reviewer used the label "Other / Miscellaneous" on any of the 540 reviewed records.
- **The project has been treating it inconsistently:**
  - the existing TF-IDF model cannot predict it;
  - V3 excluded it from training;
  - the rule engine uses `REVIEW_REQUIRED` and `AMBIGUOUS` statuses instead.

**Clarification question:** Is "Other / Miscellaneous" a real voucher category with its own positive definition (e.g. a named set of miscellaneous voucher types in the target software)? Or is it a review status meaning "no class can be assigned"? If it is a status, should it be removed from the label set and from class-balanced training and evaluation?

**Proposed clarification (PROPOSAL). This policy is deliberately not decided here.** Choose one of these two options:
1. **Keep Other / Miscellaneous as a class,** with a positive definition naming the voucher types it covers. Track records with insufficient evidence separately with the status `NEEDS_REVIEW`.
2. **Remove it from the label set,** and represent insufficient evidence only as a review status (`NEEDS_ADJUDICATION` or `INSUFFICIENT_EVIDENCE`). Then exclude those records from class-based training and metrics, and report them as an abstention rate.

## DEF-11: Purchase Return vs Sales Return direction

**Existing definitions:**
- Purchase Return / Debit Note: *"…against a previously booked supplier purchase."*
- Sales Return / Credit Note: *"…against a previously booked customer sale."*

**Ambiguity or conflict:**
- **There is no direct Purchase-vs-Sales-return dispute in the queue.** The definitions are clear about the counterparty.
- **But the direction often rests on identifiers only.** In other project data, return direction can be determined only from document-number prefixes. Both return templates in the development workbook carry "Vendor Name" and "Company", and the rule-engine audit found that direction could not be recovered once identifiers were neutralised.
- **"Debit note" and "credit note" are named from the issuer's side.** A debit note issued to a supplier and a credit note received from a supplier describe the same event.

**Clarification question:** Is the class determined by the counterparty (supplier vs customer) or by which note was issued? How should a credit note *received from a supplier* be labelled?

**Proposed clarification (PROPOSAL):** "Determine the class by the counterparty of the original transaction: a return against a supplier purchase is Purchase Return / Debit Note, whichever party issued the note. Records whose counterparty cannot be established are sent to review."

---

## Process issue (not a definition)

Reviewer 1 cited `document_type` as evidence on 60 of the 111 queued records. In this synthetic dataset `document_type` was produced by the same generator as the label: for 15 classes each value maps one-to-one to the generator's label. It should be treated as generated metadata, not independent evidence, during adjudication. Note that all 20 "Other" records carry "Unclassified record - review required".
