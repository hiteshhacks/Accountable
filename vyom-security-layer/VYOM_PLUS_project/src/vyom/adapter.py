"""Safe Excel Input Adapter for wide-schema voucher classification workbooks.

Handles schema loading, missing value cleanup, field-aware serialization,
and strict label/feature separation.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


LABEL_COLUMN = "Voucher Category"

# Mapping wide evaluation schema columns to canonical features where semantics match
CANONICAL_MAPPING: Dict[str, str] = {
    # Parties
    "Supplier": "seller_supplier",
    "Vendor Name": "seller_supplier",
    "Exporter": "seller_supplier",
    "Selling Company": "seller_supplier",
    "Subcontractor": "seller_supplier",
    "Payer Organization": "seller_supplier",
    "Customer": "buyer_customer",
    "Ordering Company": "buyer_customer",
    "Receiving Company": "buyer_customer",
    "Importer": "buyer_customer",
    "Contractor": "buyer_customer",
    "Payee Organization": "buyer_customer",
    "Company": "buyer_customer",
    
    # Dates
    "PO Date": "transaction_date",
    "Rejection Date": "transaction_date",
    "Document Date": "transaction_date",
    "Receipt Date": "transaction_date",
    "Transaction Date": "transaction_date",
    "Payment Date": "transaction_date",
    "Order Date": "transaction_date",
    "Dispatch Date": "transaction_date",
    "Entry Date": "transaction_date",
    "Claim Date": "transaction_date",
    "Adjustment Date": "transaction_date",
    "Count Date": "transaction_date",
    "SO Date": "transaction_date",
    "Date of Dispatch": "transaction_date",
    "Date of Receipt": "transaction_date",
    
    # Items & Descriptions
    "Item": "item_description",
    "Product": "item_description",
    "Item Rejected": "item_description",
    "Item Received": "item_description",
    "Item Dispatched": "item_description",
    "Material Description": "item_description",
    "Material": "item_description",
    "Export Item": "item_description",
    "Import Item": "item_description",
    "Item Name": "item_description",
    "Description": "item_description",
    
    # Narrations & Details
    "Narration": "transaction_narration",
    "Transaction Details": "transaction_narration",
    "Transfer Purpose": "transaction_narration",
    "Notes": "transaction_narration",
    "Reason": "transaction_narration",
    
    # Quantities
    "Quantity Required": "quantity",
    "Quantity Received": "quantity",
    "Quantity Shipped": "quantity",
    "Quantity Ordered": "quantity",
    "Quantity Sent": "quantity",
    "Quantity": "quantity",
    "Units": "quantity",
    "Book Quantity": "quantity",
    "Counted Quantity": "quantity",
    
    # Rates & Prices
    "Unit Rate": "unit_price",
    "Unit Cost": "unit_price",
    "Processing Rate": "unit_price",
    
    # Values & Amounts
    "Total Value": "taxable_value",
    "Base Amount": "taxable_value",
    "Transfer Amount": "taxable_value",
    "Payment Amount": "taxable_value",
    "Received Amount": "taxable_value",
    "Amount": "taxable_value",
    "Amount Claimed": "taxable_value",
    "Free on Board Value": "taxable_value",
    "Cost Insurance Freight": "taxable_value",
    
    # Taxes
    "Tax Amount": "gst_amount",
    "Import GST": "gst_amount",
    "Customs Duty": "customs_duty_amount",
    
    # Freight & Charges
    "Freight Charges": "freight_amount",
    "Transport Cost": "freight_amount",
    
    # Currency
    "Currency Code": "currency",
    "Payment Currency": "currency",
    "Original Currency": "currency",
    
    # Payment method & status
    "Mode of Payment": "payment_method",
    "Payment Method": "payment_method",
    "Payment Type": "payment_method",
    "Bank Details": "payment_method",
    "Status": "payment_status",
    
    # References
    "PO Reference": "order_reference",
    "SO Reference": "order_reference",
    "Reference PO": "order_reference",
    "Reference Number": "order_reference",
    "Supporting Doc": "order_reference",
    "Delivery Ref": "order_reference",
    "GRN Reference": "order_reference",
    "DN Reference": "order_reference",
    
    # Return reasons
    "Reason for Return": "return_reason",
    "Rejection Reason": "return_reason",
    
    # Accounting sides
    "Debit Side": "debit_credit_info",
    "Credit Side": "debit_credit_info",
    
    # Payroll
    "Payroll Period": "payroll_period",
    "Gross Salary": "gross_pay_amount",
    "Net Payable": "net_pay_amount",
}


def load_evaluation_workbook(
    file_path: Union[str, Path],
    sheet_name: str = "Test Cases",
) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
    """
    Safely load an evaluation workbook.
    
    Returns:
        (X, y):
          X: DataFrame of transaction fields only (Voucher Category excluded).
          y: Series of ground-truth labels if Voucher Category is present, else None.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation workbook not found: {path}")
    
    try:
        df = pd.read_excel(path, sheet_name=sheet_name)
    except Exception as e:
        raise ValueError(f"Could not read sheet '{sheet_name}' from {path}: {e}")
        
    if df.empty:
        raise ValueError(f"Worksheet '{sheet_name}' is empty.")
        
    y: Optional[pd.Series] = None
    if LABEL_COLUMN in df.columns:
        # Separate ground-truth target strictly
        y = df[LABEL_COLUMN].copy()
        X = df.drop(columns=[LABEL_COLUMN]).copy()
    else:
        X = df.copy()
        
    return X, y


def format_field_value(val: any) -> Optional[str]:
    """Format an Excel cell value cleanly, avoiding 'nan', 'None', or 'NaT' strings."""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() in {"nan", "none", "nat"}:
        return None
    # Clean trailing .0 from integer-like floats if representation was pure number
    if isinstance(val, float) and val.is_integer():
        val_str = str(int(val))
    return val_str


def serialize_wide_row(row: pd.Series) -> str:
    """
    Serialize a wide row by preserving field names and populated values.
    Empty fields are strictly omitted.
    Does NOT include target labels.
    """
    parts = []
    for col, val in row.items():
        if col == LABEL_COLUMN:
            continue
        cleaned = format_field_value(val)
        if cleaned is not None:
            parts.append(f"{col}: {cleaned}")
    return " | ".join(parts)


def map_wide_to_canonical(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map wide transaction fields to canonical features used by VYOM+ baseline.
    Only maps fields when meanings genuinely match.
    """
    canonical_df = pd.DataFrame(index=df.index)
    
    for wide_col, can_col in CANONICAL_MAPPING.items():
        if wide_col in df.columns:
            # If canonical column already exists, combine non-null values
            if can_col in canonical_df.columns:
                canonical_df[can_col] = canonical_df[can_col].combine_first(df[wide_col])
            else:
                canonical_df[can_col] = df[wide_col]
                
    return canonical_df
