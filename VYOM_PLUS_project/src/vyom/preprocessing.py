"""Shared input normalization and field-labelled text creation."""
import pandas as pd

FEATURES = [
    'seller_supplier','buyer_customer','invoice_number','transaction_date',
    'item_description','transaction_narration','quantity','unit_price',
    'taxable_value','gst_rate_percent','gst_amount','discount_amount',
    'freight_amount','currency','payment_method','payment_status',
    'order_reference','return_reason','debit_credit_info','payroll_period',
    'employee_count','attendance_days','import_export_reference',
    'customs_duty_amount','warehouse_from','warehouse_to','movement_reason',
    'document_type','gross_pay_amount','deductions_amount','net_pay_amount'
]

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim headers; match common header variants to canonical names."""
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(' ', '_').replace('-', '_') for c in out.columns]
    aliases = {
        'supplier':'seller_supplier', 'vendor':'seller_supplier',
        'customer':'buyer_customer', 'narration':'transaction_narration',
        'description':'item_description', 'date':'transaction_date',
        'invoice_no':'invoice_number', 'gst_rate':'gst_rate_percent',
        'gst':'gst_amount', 'voucher':'voucher_type',
    }
    for old, new in aliases.items():
        if old in out.columns and new not in out.columns:
            out = out.rename(columns={old:new})
    return out

def make_text(row) -> str:
    parts = []
    for col in FEATURES:
        if col not in row.index:
            continue
        value = row.get(col)
        if pd.isna(value) or str(value).strip() == '':
            continue
        if col == 'transaction_date':
            try:
                value = pd.to_datetime(value).date().isoformat()
            except (ValueError, TypeError):
                pass
        parts.append(f"{col.replace('_', ' ')}: {str(value).strip()}")
    return ' | '.join(parts)
