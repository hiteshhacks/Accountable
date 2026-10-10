"""Voucher Semantic Rule Engine.

Applies deterministic, explainable semantic rules based on explicit transaction
evidence present in wide voucher fields. Rules do not use the target label.
"""

from typing import Any, Dict, Optional, Tuple
import re
import pandas as pd


def _clean(val: Any) -> str:
    """Normalize field value to trimmed string."""
    if pd.isna(val):
        return ""
    val_str = str(val).strip()
    if val_str.lower() in {"nan", "none", "nat"}:
        return ""
    return val_str


def evaluate_transaction_rules(
    row: pd.Series,
    base_prediction: Optional[str] = None,
) -> Tuple[str, str, bool]:
    """
    Evaluate explicit transaction-specific evidence.
    
    Args:
        row: Series of transaction fields. MUST NOT contain target label.
        base_prediction: Baseline model prediction to fall back on if no rule fires.
        
    Returns:
        (prediction, explanation, rule_applied)
    """
    # 1. Rejection In vs Rejection Out
    rejection_note = _clean(row.get("Rejection Note No"))
    item_rejected = _clean(row.get("Item Rejected"))
    qty_rejected = _clean(row.get("Quantity Rejected"))
    rejection_reason = _clean(row.get("Rejection Reason"))
    has_rejection_data = bool(item_rejected or qty_rejected or rejection_reason)
    
    if rejection_note.startswith("RJN-IN") or (
        has_rejection_data and (_clean(row.get("GRN Reference")) or _clean(row.get("Receiving Company")))
        and not _clean(row.get("Customer")) and not _clean(row.get("DN Reference"))
    ):
        return (
            "Rejection In",
            f"Explicit inward rejection evidence (Note: {rejection_note or 'GRN linked'})",
            True,
        )
        
    if rejection_note.startswith("RJN-OUT") or (
        has_rejection_data and (_clean(row.get("DN Reference")) or _clean(row.get("Customer")))
    ):
        return (
            "Rejection Out",
            f"Explicit outward rejection evidence (Note: {rejection_note or 'DN linked'})",
            True,
        )

    # 2. Purchase Return / Debit Note vs Sales Return / Credit Note
    doc_num = _clean(row.get("Document Number"))
    units_returned = _clean(row.get("Units Returned"))
    reason_for_return = _clean(row.get("Reason for Return"))
    orig_doc_ref = _clean(row.get("Original Doc Ref"))
    orig_inv_ref = _clean(row.get("Original Invoice Ref"))
    has_return = bool(units_returned or reason_for_return)
    
    if doc_num.startswith("DBN") or (has_return and orig_doc_ref.startswith("PUR")):
        return (
            "Purchase Return / Debit Note",
            f"Explicit debit note / supplier return evidence ({doc_num or orig_doc_ref})",
            True,
        )
        
    if doc_num.startswith("CRN") or (has_return and orig_inv_ref.startswith("SAL")):
        return (
            "Sales Return / Credit Note",
            f"Explicit credit note / customer return evidence ({doc_num or orig_inv_ref})",
            True,
        )

    # 3. Invoices: Purchase vs Sales (only when not a return note)
    if not has_return:
        if doc_num.startswith("PUR-") or (_clean(row.get("PO Ref")).startswith("PO") and _clean(row.get("Vendor Name"))):
            return (
                "Purchase",
                f"Explicit purchase invoice document ({doc_num or 'PO Ref linked'})",
                True,
            )
        if doc_num.startswith("SAL-") or (_clean(row.get("Delivery Ref")).startswith("DN") and _clean(row.get("Product"))):
            return (
                "Sales",
                f"Explicit sales invoice document ({doc_num or 'Delivery Ref linked'})",
                True,
            )

    # 4. Purchase Order vs Sales Order
    po_number = _clean(row.get("PO Number"))
    qty_req = _clean(row.get("Quantity Required"))
    if po_number.startswith("PO") and (qty_req or _clean(row.get("Supplier")) or _clean(row.get("Promised Delivery"))):
        return (
            "Purchase Order",
            f"Explicit purchase order evidence ({po_number})",
            True,
        )
        
    so_number = _clean(row.get("SO Number"))
    qty_ord = _clean(row.get("Quantity Ordered"))
    if so_number.startswith("SO") and (qty_ord or _clean(row.get("Selling Company")) or _clean(row.get("Customer"))):
        return (
            "Sales Order",
            f"Explicit sales order evidence ({so_number})",
            True,
        )

    # 5. Delivery Note vs Receipt Note
    dc_no = _clean(row.get("Delivery Challan No"))
    if dc_no.startswith("DC") or (_clean(row.get("Item Dispatched")) and _clean(row.get("Quantity Shipped"))):
        return (
            "Delivery Note",
            f"Explicit delivery challan evidence ({dc_no or 'dispatched goods'})",
            True,
        )
        
    grn_no = _clean(row.get("GRN Number"))
    if grn_no.startswith("GRN") or (_clean(row.get("Item Received")) and _clean(row.get("Quantity Received")) and not _clean(row.get("Outward Job Work No"))):
        return (
            "Receipt Note",
            f"Explicit goods receipt note evidence ({grn_no or 'received goods'})",
            True,
        )

    # 6. Banking & Cash: Contra vs Payment vs Receipt
    contra_id = _clean(row.get("Contra ID"))
    src_acct = _clean(row.get("Source Account"))
    dst_acct = _clean(row.get("Destination Account"))
    if contra_id.startswith("CTR") or (src_acct and dst_acct and _clean(row.get("Transfer Amount"))):
        return (
            "Contra",
            f"Explicit contra inter-account transfer evidence ({contra_id or src_acct + ' -> ' + dst_acct})",
            True,
        )
        
    pmt_id = _clean(row.get("Payment ID"))
    if pmt_id.startswith("PMT") or (_clean(row.get("Payment Amount")) and (_clean(row.get("Payer Organization")) or _clean(row.get("Payee Organization")))):
        return (
            "Payment",
            f"Explicit disbursement payment evidence ({pmt_id or 'disbursement'})",
            True,
        )
        
    rcp_id = _clean(row.get("Receipt ID"))
    if rcp_id.startswith("RCP") or (_clean(row.get("Received Amount")) and (_clean(row.get("Receipt Nature")) or _clean(row.get("Receiving Organization")))):
        return (
            "Receipt",
            f"Explicit receipt transaction evidence ({rcp_id or 'received amount'})",
            True,
        )

    # 7. Salary / Payroll
    emp_code = _clean(row.get("Employee Code"))
    if emp_code.startswith("EMP") or (_clean(row.get("Gross Salary")) and _clean(row.get("Net Payable")) and _clean(row.get("Payroll Period"))):
        return (
            "Salary / Payroll",
            f"Explicit payroll record with employee code ({emp_code})",
            True,
        )

    # 8. Expense
    exp_claim = _clean(row.get("Expense Claim No"))
    if exp_claim.startswith("EXP") and (_clean(row.get("Expense Type")) or _clean(row.get("Amount Claimed"))):
        return (
            "Expense",
            f"Explicit expense claim record ({exp_claim})",
            True,
        )

    # 9. International Trade: Export vs Import
    exp_inv = _clean(row.get("Export Invoice No"))
    if exp_inv.startswith("EXP") and (_clean(row.get("Destination Country")) or _clean(row.get("Units Exported")) or _clean(row.get("Free on Board Value"))):
        return (
            "Export",
            f"Explicit foreign export transaction ({exp_inv})",
            True,
        )
        
    ibl_no = _clean(row.get("Import Bill No"))
    if ibl_no.startswith("IBL") or (_clean(row.get("Originating Country")) and (_clean(row.get("Units Imported")) or _clean(row.get("Customs Duty")))):
        return (
            "Import",
            f"Explicit customs import bill of entry ({ibl_no})",
            True,
        )

    # 10. General Journal
    jnl_id = _clean(row.get("Journal ID"))
    if jnl_id.startswith("JNL") or (_clean(row.get("Debit Side")) and _clean(row.get("Credit Side")) and _clean(row.get("Journal Type"))):
        return (
            "Journal",
            f"Explicit journal entry ({jnl_id or 'Debit/Credit entries'})",
            True,
        )

    # 11. Inventory: Stock Journal vs Physical Stock
    stock_adj = _clean(row.get("Stock Adj ID"))
    if stock_adj.startswith("SA") or (_clean(row.get("Adjustment Qty")) and _clean(row.get("Storage Facility"))):
        return (
            "Stock Journal",
            f"Explicit stock adjustment journal ({stock_adj})",
            True,
        )
        
    stock_cnt = _clean(row.get("Stock Count ID"))
    if stock_cnt.startswith("SC") or (_clean(row.get("Book Quantity")) and _clean(row.get("Counted Quantity"))):
        return (
            "Physical Stock",
            f"Explicit physical stock count audit ({stock_cnt})",
            True,
        )

    # 12. Job Work Orders: Inward vs Outward
    jwio_ref = _clean(row.get("JWIO Ref"))
    if jwio_ref.startswith("JWIO") or (_clean(row.get("Processing Rate")) and _clean(row.get("Processor")) and not _clean(row.get("Service Charge"))):
        return (
            "Job Work In Order",
            f"Explicit job work inward order ({jwio_ref or 'processing rate'})",
            True,
        )
        
    jwoo_ref = _clean(row.get("JWOO Ref"))
    if jwoo_ref.startswith("JWOO") or (_clean(row.get("Service Charge")) and _clean(row.get("Agreement Terms"))):
        return (
            "Job Work Out Order",
            f"Explicit job work outward order ({jwoo_ref or 'service charge'})",
            True,
        )

    # 13. Material Movement: Inward vs Outward
    miw_no = _clean(row.get("Inward Job Work No"))
    if miw_no.startswith("MIW") or (_clean(row.get("Subcontractor")) and _clean(row.get("Quantity Sent")) and _clean(row.get("Date of Dispatch"))):
        return (
            "Material In",
            f"Explicit material inward record ({miw_no})",
            True,
        )
        
    mow_no = _clean(row.get("Outward Job Work No"))
    if mow_no.startswith("MOW") or (_clean(row.get("Contractor")) and _clean(row.get("Quantity Received")) and _clean(row.get("Date of Receipt"))):
        return (
            "Material Out",
            f"Explicit material outward record ({mow_no})",
            True,
        )

    # Fallback if no specific rule matched
    if base_prediction:
        return (base_prediction, "Model statistical prediction (no rule override)", False)
    return ("Unclassified", "Insufficient evidence for deterministic rule", False)
