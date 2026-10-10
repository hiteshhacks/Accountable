
def apply_rules(row, original_prediction):
    """Return a corrected prediction and an explanation."""

    import re
    import pandas as pd

    def clean(value):
        if pd.isna(value):
            return ""
        return re.sub(r"\s+", " ", str(value)).strip().lower()

    document_type = clean(row.get("document_type"))
    item_description = clean(row.get("item_description"))
    narration = clean(row.get("transaction_narration"))
    payment_status = clean(row.get("payment_status"))
    debit_credit_info = clean(row.get("debit_credit_info"))
    buyer_customer = clean(row.get("buyer_customer"))
    seller_supplier = clean(row.get("seller_supplier"))
    combined = " ".join([
        item_description,
        narration,
        debit_credit_info,
    ])

    # Rule 1: Explicit order documents.
    if document_type in {"sales order", "sales order form"}:
        return "Sales Order", "Explicit document_type: sales order"

    if document_type in {"purchase order", "purchase order form"}:
        return "Purchase Order", "Explicit document_type: purchase order"

    # Preserve explicit documents belonging to other transaction types.
    explicit_other_documents = {
        "delivery note",
        "receipt note",
        "sales invoice",
        "purchase invoice",
        "tax invoice",
    }

    if document_type in explicit_other_documents:
        return (
            original_prediction,
            "Preserved explicit non-order document type",
        )

    # Rule 2: Strong evidence for Advance / Prepayment.
    advance_item = bool(
        re.search(r"\b(advance|prepayment|prepaid)\b", item_description)
    )

    advance_narration = bool(
        re.search(r"\b(advance|prepayment|prepaid)\b", narration)
    )

    advance_status = bool(
        re.search(
            r"\b(prepaid|prepayment|advance|received in advance)\b",
            payment_status,
        )
    )

    if sum([
        advance_item,
        advance_narration,
        advance_status,
    ]) >= 2:
        return (
            "Advance / Prepayment",
            "Advance evidence in at least two fields",
        )

    # Rule 3: Distinguish sales returns from purchase returns.
    # Require explicit credit/debit note evidence AND corroborating
    # evidence identifying the customer-side or supplier-side return.
    sales_note = bool(
        re.search(
            r"\b(credit note|sales return|customer credit note)\b",
            combined,
        )
    )

    purchase_note = bool(
        re.search(
            r"\b(debit note|purchase return|supplier debit note)\b",
            combined,
        )
    )

    customer_return = bool(
        re.search(
            r"\b(customer|buyer|sold goods|previously booked sale|sales invoice)\b",
            combined,
        )
    ) or bool(buyer_customer)

    supplier_return = bool(
        re.search(
            r"\b(supplier|vendor|goods returned to supplier|purchase invoice)\b",
            combined,
        )
    ) or bool(seller_supplier)

    if sales_note and customer_return and not purchase_note:
        return (
            "Sales Return / Credit Note",
            "Explicit sales credit-note evidence with customer-side context",
        )

    if purchase_note and supplier_return and not sales_note:
        return (
            "Purchase Return / Debit Note",
            "Explicit purchase debit-note evidence with supplier-side context",
        )

    return original_prediction, "No correction rule matched"
