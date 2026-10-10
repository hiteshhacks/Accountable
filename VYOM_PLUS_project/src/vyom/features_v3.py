"""VYOM+ V3 feature contract (experimental).

One preprocessing contract shared by training and inference. It keeps field
names and meanings, and separates five feature groups:

- text:          narration and item description, normalised (identifier
                 tokens and digits masked)
- categorical:   status / method / reason / account-side / location fields
- numeric:       amounts, rates, quantities
- relationships: presence of party and reference fields, and arithmetic
                 consistency between related amounts
- missingness:   one presence flag per contract field

Identifiers (invoice / order / import-export references) and party names
contribute presence only, never their values. Calendar dates, document_type
(a 1:1 proxy for the label in the synthetic training data), the target label
and every output column are excluded from model inputs.
"""

from typing import Dict, Iterable, List
import re

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from vyom.adapter import LABEL_COLUMN


CONTRACT_VERSION = "v3-experimental-1"

TEXT_FIELDS = ("transaction_narration", "item_description")
CATEGORICAL_FIELDS = (
    "currency", "payment_method", "payment_status", "return_reason",
    "debit_credit_info", "warehouse_from", "warehouse_to", "movement_reason",
)
NUMERIC_FIELDS = (
    "quantity", "unit_price", "taxable_value", "gst_rate_percent", "gst_amount",
    "discount_amount", "freight_amount", "customs_duty_amount", "employee_count",
    "attendance_days", "gross_pay_amount", "deductions_amount", "net_pay_amount",
)
# Values are arbitrary names or numbers; only whether they are present is used.
PRESENCE_ONLY_FIELDS = (
    "seller_supplier", "buyer_customer", "invoice_number", "order_reference",
    "import_export_reference", "payroll_period",
)
CONTRACT_FIELDS = TEXT_FIELDS + CATEGORICAL_FIELDS + NUMERIC_FIELDS + PRESENCE_ONLY_FIELDS

EXCLUDED_FIELDS = (
    "transaction_date",        # random calendar dates in the synthetic data
    "document_type",           # maps 1:1 to the label where present in the synthetic data
    "voucher_type", LABEL_COLUMN, "target", "provisional_consensus_label",
    "Correct", "Predicted Voucher Category",
)

RELATIONSHIP_FEATURES = ("rel_qty_x_price_matches_value", "rel_gst_matches_rate", "rel_net_matches_gross_minus_deductions")

_ID_TOKEN = re.compile(r"\b[A-Za-z]{2,}[-/]?\d[\w-]*\b")
_DIGITS = re.compile(r"\d+")


def normalise_text(value) -> str:
    """Lower-case text with identifier-like tokens and digits masked."""
    if value is None or (isinstance(value, float) and np.isnan(value)) or pd.isna(value):
        return ""
    text = _ID_TOKEN.sub(" idtoken ", str(value))
    text = _DIGITS.sub("#", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _clean_category(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def _close(a, b, tolerance=0.02) -> float:
    """1.0 if a and b agree within a relative tolerance, 0.0 if not, NaN if either is missing."""
    if pd.isna(a) or pd.isna(b):
        return np.nan
    return float(abs(a - b) <= tolerance * max(abs(a), abs(b), 1.0))


def prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the contract to canonical records; extra columns are ignored, missing ones become empty.

    Returns one row per input row, in the same order, with only contract-derived columns.
    """
    src = pd.DataFrame(index=df.index)
    for field in CONTRACT_FIELDS:
        src[field] = df[field] if field in df.columns else np.nan

    out = pd.DataFrame(index=df.index)
    for field in TEXT_FIELDS:
        out[field] = src[field].map(normalise_text)
    for field in CATEGORICAL_FIELDS:
        out[field] = src[field].map(_clean_category)
    for field in NUMERIC_FIELDS:
        out[field] = pd.to_numeric(src[field], errors="coerce")
    for field in CONTRACT_FIELDS:
        out[f"has_{field}"] = src[field].map(lambda v: float(not pd.isna(v) and str(v).strip() != ""))

    out["rel_qty_x_price_matches_value"] = [
        _close(q * p, v) if not (pd.isna(q) or pd.isna(p)) else np.nan
        for q, p, v in zip(out.quantity, out.unit_price, out.taxable_value)]
    out["rel_gst_matches_rate"] = [
        _close(v * r / 100.0, g) if not (pd.isna(v) or pd.isna(r)) else np.nan
        for v, r, g in zip(out.taxable_value, out.gst_rate_percent, out.gst_amount)]
    out["rel_net_matches_gross_minus_deductions"] = [
        _close(gr - de, ne) if not (pd.isna(gr) or pd.isna(de)) else np.nan
        for gr, de, ne in zip(out.gross_pay_amount, out.deductions_amount, out.net_pay_amount)]
    return out


def presence_columns() -> List[str]:
    return [f"has_{f}" for f in CONTRACT_FIELDS]


def field_tokens(prepared: pd.DataFrame, groups: Iterable[str]) -> pd.Series:
    """Field-aware token string: every token carries the name of the field it came from."""
    groups = set(groups)
    parts: Dict[str, pd.Series] = {}
    if "narration" in groups:
        parts["narr"] = prepared["transaction_narration"].map(
            lambda t: " ".join(f"narr_{w}" for w in re.findall(r"[a-z#]+", t)))
    if "item" in groups:
        parts["item"] = prepared["item_description"].map(
            lambda t: " ".join(f"item_{w}" for w in re.findall(r"[a-z#]+", t)))
    if "categorical" in groups:
        for field in CATEGORICAL_FIELDS:
            parts[field] = prepared[field].map(
                lambda v, f=field: f"{f}={v.replace(' ', '_')}" if v else "")
    if "presence" in groups:
        for col in presence_columns():
            parts[col] = prepared[col].map(lambda v, c=col: c if v else f"no_{c[4:]}")
    if "relationships" in groups:
        for col in RELATIONSHIP_FEATURES:
            parts[col] = prepared[col].map(lambda v, c=col: "" if pd.isna(v) else f"{c}={int(v)}")
    if not parts:
        return pd.Series([""] * len(prepared), index=prepared.index)
    return pd.concat(parts, axis=1).apply(lambda r: " ".join(t for t in r if t), axis=1)


class ContractTokens(BaseEstimator, TransformerMixin):
    """Stateless: canonical records -> field-tagged token strings."""

    def __init__(self, groups=("narration", "item", "categorical", "presence", "relationships")):
        self.groups = groups

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return field_tokens(prepare_frame(X), self.groups).tolist()


class ContractTabular(BaseEstimator, TransformerMixin):
    """Canonical records -> numeric matrix for tree models.

    Categorical values are encoded with codes learned in fit; unseen or missing
    values become NaN. Column order: categorical, numeric, presence, relationships.
    """

    def __init__(self, include_item=False, categorical=True, numeric=True, relationships=True):
        self.include_item = include_item
        self.categorical = categorical
        self.numeric = numeric
        self.relationships = relationships

    def _categorical_fields(self) -> List[str]:
        if not self.categorical:
            return []
        return (["item_description"] if self.include_item else []) + list(CATEGORICAL_FIELDS)

    def categorical_mask(self) -> List[bool]:
        n_rest = (len(NUMERIC_FIELDS) if self.numeric else 0) + len(CONTRACT_FIELDS) \
            + (len(RELATIONSHIP_FEATURES) if self.relationships else 0)
        return [True] * len(self._categorical_fields()) + [False] * n_rest

    def fit(self, X, y=None):
        prepared = prepare_frame(X)
        self.categories_ = {f: sorted(v for v in prepared[f].unique() if v) for f in self._categorical_fields()}
        return self

    def transform(self, X):
        prepared = prepare_frame(X)
        cols = []
        for f in self._categorical_fields():
            codes = {v: float(i) for i, v in enumerate(self.categories_[f])}
            cols.append(prepared[f].map(lambda v: codes.get(v, np.nan)).to_numpy(dtype=float))
        if self.numeric:
            cols += [prepared[f].to_numpy(dtype=float) for f in NUMERIC_FIELDS]
        cols += [prepared[c].to_numpy(dtype=float) for c in presence_columns()]
        if self.relationships:
            cols += [prepared[c].to_numpy(dtype=float) for c in RELATIONSHIP_FEATURES]
        return np.column_stack(cols)


class ContractText(BaseEstimator, TransformerMixin):
    """Stateless: canonical records -> normalised narration and item text (identifiers and digits masked)."""

    def __init__(self, fields=TEXT_FIELDS):
        self.fields = fields

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        prepared = prepare_frame(X)
        return prepared[list(self.fields)].agg(" ".join, axis=1).str.strip().tolist()
