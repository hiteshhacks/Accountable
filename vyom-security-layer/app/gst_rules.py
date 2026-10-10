from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4


GST_RULE_VERSION = "GST-DEMO-2026-10-10"
GST_RULE_SOURCE_URL = "https://cbic-gst.gov.in/gst-goods-services-rates.html"
GST_RULE_SOURCE_NAME = "CBIC GST Goods and Services Rates"
ALLOWED_GST_RATES = {Decimal("0"), Decimal("5"), Decimal("12"), Decimal("18"), Decimal("28")}
MONEY = Decimal("0.01")


class GSTRuleRejected(ValueError):
    pass


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def evaluate_gst(taxable_value: Decimal, rate_percent: Decimal, supply_type: str) -> dict:
    taxable_value = Decimal(str(taxable_value))
    rate_percent = Decimal(str(rate_percent))
    if taxable_value < 0 or taxable_value > Decimal("1000000000000"):
        raise GSTRuleRejected("taxable_value_out_of_bounds")
    if rate_percent not in ALLOWED_GST_RATES:
        raise GSTRuleRejected("unsupported_gst_rate")
    if supply_type not in {"intra_state", "inter_state"}:
        raise GSTRuleRejected("unsupported_supply_type")

    tax_amount = _money(taxable_value * rate_percent / Decimal("100"))
    if supply_type == "intra_state":
        cgst = _money(tax_amount / Decimal("2"))
        sgst = tax_amount - cgst
        igst = Decimal("0.00")
    else:
        cgst = Decimal("0.00")
        sgst = Decimal("0.00")
        igst = tax_amount

    return {
        "trace_id": str(uuid4()),
        "rule_version": GST_RULE_VERSION,
        "source_name": GST_RULE_SOURCE_NAME,
        "source_url": GST_RULE_SOURCE_URL,
        "taxable_value": str(_money(taxable_value)),
        "rate_percent": str(rate_percent),
        "supply_type": supply_type,
        "cgst": str(_money(cgst)),
        "sgst": str(_money(sgst)),
        "igst": str(_money(igst)),
        "total_tax": str(tax_amount),
        "formula": "taxable_value * rate_percent / 100; intra_state splits total tax equally into CGST and SGST",
    }
