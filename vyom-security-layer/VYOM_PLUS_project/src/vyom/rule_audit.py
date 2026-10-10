"""VYOM+ rule-engine audit.

Checks whether the reported 100% rule-based accuracy on the evaluation
workbook reflects transaction understanding or the workbook's template:

- rule inventory and a per-row rule trace for all records,
- identifier-dependence ablations (configurations A-E),
- static and dynamic label-leakage checks,
- independent recomputation of the reported metrics,
- an audit of the reported rule "confidence",
- controlled modifications of selected records.

Predictions are generated from transaction fields only. Ground-truth labels
are joined afterwards, solely to score them. Models, the workbook and the
existing reports are read, never written.

The audited engine is the first-match engine frozen in vyom.legacy_rule_engine.
The pipeline and test-fixture leakage checks exercise the current pipeline
(vyom.rule_engine.assess_transaction). Outputs that already exist are refused.
"""

from dataclasses import dataclass
from pathlib import Path
import argparse
import ast
import contextlib
import importlib.util
import io
import json
import pickle
import re
import unittest

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from vyom import adapter, legacy_rule_engine, rule_engine
from vyom import evaluate_workbook as ew
from vyom.adapter import LABEL_COLUMN, load_evaluation_workbook
from vyom.legacy_rule_engine import _clean, evaluate_transaction_rules


ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "reports"

ORIGINAL_PREDICTIONS = REPORTS_DIR / "vyom_plus_evaluation_predictions.xlsx"
ORIGINAL_COMPARISON = REPORTS_DIR / "evaluation_model_comparison.csv"
ORIGINAL_PER_CLASS = REPORTS_DIR / "evaluation_per_class_report.csv"
ORIGINAL_CONFUSION = REPORTS_DIR / "evaluation_confusion_matrix.csv"
DECISION_STATUS_PREDICTIONS = REPORTS_DIR / "vyom_plus_evaluation_predictions_decision_status.xlsx"

AUDIT_XLSX_NAME = "rule_engine_audit.xlsx"
ABLATION_CSV_NAME = "rule_ablation_metrics.csv"

TESTS_FILE = ROOT / "tests/test_evaluation_adapter.py"

NO_RULE = "No rule matched"
UNCLASSIFIED = "Unclassified"


# ==========================================
# IDENTIFIER COLUMNS
# ==========================================

# The record's own document number. Every record in the workbook has one.
OWN_ID_COLUMNS = [
    "PO Number", "SO Number", "Rejection Note No", "Document Number",
    "GRN Number", "Delivery Challan No", "Outward Job Work No",
    "Inward Job Work No", "Contra ID", "Payment ID", "Receipt ID",
    "Employee Code", "Expense Claim No", "Export Invoice No", "Import Bill No",
    "Journal ID", "Stock Adj ID", "Stock Count ID", "JWIO Ref", "JWOO Ref",
]

# Pointers to another document (invoice, order, delivery or receipt number).
REFERENCE_ID_COLUMNS = [
    "PO Ref", "PO Reference", "Reference PO", "SO Reference", "DN Reference",
    "Delivery Ref", "GRN Reference", "Original Doc Ref", "Original Invoice Ref",
    "Against Invoice", "Buyer Invoice", "Consignment Invoice",
    "Transaction Ref", "Reference Number", "Supporting Doc",
]

IDENTIFIER_COLUMNS = OWN_ID_COLUMNS + REFERENCE_ID_COLUMNS

# Looks like a document code, e.g. "PO9634122", "RJN-IN-516405", "HDFC0001234".
ID_LIKE = re.compile(r"^[A-Z]{2,}[A-Z-]*-?\d{3,}$")


def neutral_identifier(value) -> str:
    """Replace an identifier's prefix with a neutral one, keeping its digits."""
    digits = re.findall(r"\d+", str(value))
    return "DOC-" + "-".join(digits) if digits else "DOC"


def transform_identifiers(X: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Return a copy of X with identifier values removed or neutralized."""
    out = X.copy().astype(object)
    for col in IDENTIFIER_COLUMNS:
        if col not in out.columns:
            continue
        present = out[col].map(lambda v: bool(_clean(v)))
        if mode == "removed":
            out.loc[present, col] = np.nan
        elif mode == "neutralized":
            out.loc[present, col] = out.loc[present, col].map(neutral_identifier)
        else:
            raise ValueError(mode)
    return out


def transform_own_identifiers_neutralized(X: pd.DataFrame) -> pd.DataFrame:
    """Neutralize only the record's own identifiers (cross-check for configuration B)."""
    out = X.copy().astype(object)
    for col in OWN_ID_COLUMNS:
        present = out[col].map(lambda v: bool(_clean(v)))
        out.loc[present, col] = out.loc[present, col].map(neutral_identifier)
    return out


def primary_identifier(row: pd.Series):
    for col in OWN_ID_COLUMNS:
        value = _clean(row.get(col))
        if value:
            return col, value
    return "", ""


# ==========================================
# CLAUSE-LEVEL MIRROR OF rule_engine.py
# ==========================================

OWN, REF, PRESENT, ANY, ABSENT = "own_prefix", "ref_prefix", "present", "any_present", "absent"
PREFIX_KINDS = frozenset({OWN, REF})


@dataclass(frozen=True)
class Atom:
    kind: str
    fields: tuple
    prefix: str = ""

    def evaluate(self, row, disabled):
        """Return (truth, evidence) using the engine's own field cleaning."""
        if self.kind in disabled:
            return False, {}
        values = {f: _clean(row.get(f)) for f in self.fields}
        if self.kind in PREFIX_KINDS:
            value = values[self.fields[0]]
            return value.startswith(self.prefix), {self.fields[0]: value}
        if self.kind == PRESENT:
            value = values[self.fields[0]]
            return bool(value), {self.fields[0]: value}
        if self.kind == ANY:
            hits = {f: v for f, v in values.items() if v}
            return bool(hits), hits
        if self.kind == ABSENT:
            return not any(values.values()), {f: "(empty)" for f in self.fields}
        raise ValueError(self.kind)

    def describe(self) -> str:
        if self.kind == OWN:
            return f"'{self.fields[0]}' starts with '{self.prefix}' [own-ID prefix]"
        if self.kind == REF:
            return f"'{self.fields[0]}' starts with '{self.prefix}' [reference-ID prefix]"
        if self.kind == PRESENT:
            return f"'{self.fields[0]}' present"
        if self.kind == ANY:
            return "any of (" + ", ".join(f"'{f}'" for f in self.fields) + ") present"
        return " and ".join(f"'{f}' empty" for f in self.fields)


def own(field, prefix):
    return Atom(OWN, (field,), prefix)


def ref(field, prefix):
    return Atom(REF, (field,), prefix)


def present(field):
    return Atom(PRESENT, (field,))


def any_of(*fields):
    return Atom(ANY, tuple(fields))


def absent(*fields):
    return Atom(ABSENT, tuple(fields))


REJECTION_DATA = any_of("Item Rejected", "Quantity Rejected", "Rejection Reason")
RETURN_DATA = any_of("Units Returned", "Reason for Return")


@dataclass(frozen=True)
class Rule:
    rid: str
    category: str
    block: tuple        # first/last line of the rule block in rule_engine.py
    condition: tuple    # first/last line of the if-condition in rule_engine.py
    clauses: tuple      # OR of clauses; each clause is an AND of atoms
    guard: tuple = ()

    def satisfied_clauses(self, row, disabled=frozenset()):
        for atom in self.guard:
            if not atom.evaluate(row, disabled)[0]:
                return []
        satisfied = []
        for clause in self.clauses:
            evidence = {}
            for atom in clause:
                ok, ev = atom.evaluate(row, disabled)
                if not ok:
                    break
                evidence.update(ev)
            else:
                satisfied.append((clause, evidence))
        return satisfied


RULES = [
    Rule("R01", "Rejection In", (43, 51), (43, 46), (
        (own("Rejection Note No", "RJN-IN"),),
        (REJECTION_DATA, any_of("GRN Reference", "Receiving Company"), absent("Customer"), absent("DN Reference")),
    )),
    Rule("R02", "Rejection Out", (53, 60), (53, 55), (
        (own("Rejection Note No", "RJN-OUT"),),
        (REJECTION_DATA, any_of("DN Reference", "Customer")),
    )),
    Rule("R03", "Purchase Return / Debit Note", (70, 75), (70, 70), (
        (own("Document Number", "DBN"),),
        (RETURN_DATA, ref("Original Doc Ref", "PUR")),
    )),
    Rule("R04", "Sales Return / Credit Note", (77, 82), (77, 77), (
        (own("Document Number", "CRN"),),
        (RETURN_DATA, ref("Original Invoice Ref", "SAL")),
    )),
    Rule("R05", "Purchase", (85, 91), (85, 86), (
        (own("Document Number", "PUR-"),),
        (ref("PO Ref", "PO"), present("Vendor Name")),
    ), guard=(absent("Units Returned", "Reason for Return"),)),
    Rule("R06", "Sales", (85, 97), (92, 92), (
        (own("Document Number", "SAL-"),),
        (ref("Delivery Ref", "DN"), present("Product")),
    ), guard=(absent("Units Returned", "Reason for Return"),)),
    Rule("R07", "Purchase Order", (100, 107), (102, 102), (
        (own("PO Number", "PO"), any_of("Quantity Required", "Supplier", "Promised Delivery")),
    )),
    Rule("R08", "Sales Order", (109, 116), (111, 111), (
        (own("SO Number", "SO"), any_of("Quantity Ordered", "Selling Company", "Customer")),
    )),
    Rule("R09", "Delivery Note", (119, 125), (120, 120), (
        (own("Delivery Challan No", "DC"),),
        (present("Item Dispatched"), present("Quantity Shipped")),
    )),
    Rule("R10", "Receipt Note", (127, 133), (128, 128), (
        (own("GRN Number", "GRN"),),
        (present("Item Received"), present("Quantity Received"), absent("Outward Job Work No")),
    )),
    Rule("R11", "Contra", (136, 144), (139, 139), (
        (own("Contra ID", "CTR"),),
        (present("Source Account"), present("Destination Account"), present("Transfer Amount")),
    )),
    Rule("R12", "Payment", (146, 152), (147, 147), (
        (own("Payment ID", "PMT"),),
        (present("Payment Amount"), any_of("Payer Organization", "Payee Organization")),
    )),
    Rule("R13", "Receipt", (154, 160), (155, 155), (
        (own("Receipt ID", "RCP"),),
        (present("Received Amount"), any_of("Receipt Nature", "Receiving Organization")),
    )),
    Rule("R14", "Salary / Payroll", (163, 169), (164, 164), (
        (own("Employee Code", "EMP"),),
        (present("Gross Salary"), present("Net Payable"), present("Payroll Period")),
    )),
    Rule("R15", "Expense", (172, 178), (173, 173), (
        (own("Expense Claim No", "EXP"), any_of("Expense Type", "Amount Claimed")),
    )),
    Rule("R16", "Export", (181, 187), (182, 182), (
        (own("Export Invoice No", "EXP"), any_of("Destination Country", "Units Exported", "Free on Board Value")),
    )),
    Rule("R17", "Import", (189, 195), (190, 190), (
        (own("Import Bill No", "IBL"),),
        (present("Originating Country"), any_of("Units Imported", "Customs Duty")),
    )),
    Rule("R18", "Journal", (198, 204), (199, 199), (
        (own("Journal ID", "JNL"),),
        (present("Debit Side"), present("Credit Side"), present("Journal Type")),
    )),
    Rule("R19", "Stock Journal", (207, 213), (208, 208), (
        (own("Stock Adj ID", "SA"),),
        (present("Adjustment Qty"), present("Storage Facility")),
    )),
    Rule("R20", "Physical Stock", (215, 221), (216, 216), (
        (own("Stock Count ID", "SC"),),
        (present("Book Quantity"), present("Counted Quantity")),
    )),
    Rule("R21", "Job Work In Order", (224, 230), (225, 225), (
        (own("JWIO Ref", "JWIO"),),
        (present("Processing Rate"), present("Processor"), absent("Service Charge")),
    )),
    Rule("R22", "Job Work Out Order", (232, 238), (233, 233), (
        (own("JWOO Ref", "JWOO"),),
        (present("Service Charge"), present("Agreement Terms")),
    )),
    Rule("R23", "Material In", (241, 247), (242, 242), (
        (own("Inward Job Work No", "MIW"),),
        (present("Subcontractor"), present("Quantity Sent"), present("Date of Dispatch")),
    )),
    Rule("R24", "Material Out", (249, 255), (250, 250), (
        (own("Outward Job Work No", "MOW"),),
        (present("Contractor"), present("Quantity Received"), present("Date of Receipt")),
    )),
]

RULE_MODES = {
    "all": frozenset(),
    "no_own_prefix": frozenset({OWN}),
    "presence_only": PREFIX_KINDS,
}


def clause_type(clause) -> str:
    kinds = {a.kind for a in clause}
    if OWN in kinds:
        return "own-ID prefix" + (" + field presence" if kinds - {OWN} else "")
    if REF in kinds:
        return "reference-ID prefix + field presence"
    return "field presence only"


def match_rules(row, disabled=frozenset()):
    """All rules whose condition holds, in engine order: [(rule, satisfied_clauses)]."""
    matches = []
    for rule in RULES:
        satisfied = rule.satisfied_clauses(row, disabled)
        if satisfied:
            matches.append((rule, satisfied))
    return matches


def mirror_predictions(X: pd.DataFrame, mode: str = "all"):
    disabled = RULE_MODES[mode]
    out = []
    for i in range(len(X)):
        matches = match_rules(X.iloc[i], disabled)
        out.append(matches[0][0].category if matches else None)
    return out


def engine_predictions(X: pd.DataFrame):
    """Run the real rule engine; None where no rule fired."""
    out = []
    for i in range(len(X)):
        pred, _, applied = evaluate_transaction_rules(X.iloc[i])
        out.append(pred if applied else None)
    return out


def assert_parity(mirror, engine, what):
    mismatches = [i for i, (a, b) in enumerate(zip(mirror, engine)) if a != b]
    if mismatches:
        raise AssertionError(f"Rule mirror diverges from rule_engine.py on {what}: rows {mismatches[:10]}")


def combine(rule_preds, fallback_preds):
    if fallback_preds is None:
        return [r if r is not None else UNCLASSIFIED for r in rule_preds]
    return [r if r is not None else f for r, f in zip(rule_preds, fallback_preds)]


# ==========================================
# MODELS (exact evaluation code paths)
# ==========================================

def load_tfidf():
    with open(ew.DEFAULT_BASELINE, "rb") as f:
        return pickle.load(f)


def run_models(X: pd.DataFrame, tfidf_model) -> dict:
    tf_preds, tf_scores = ew.evaluate_baseline_model(tfidf_model, X)
    de_preds, de_scores = ew.evaluate_dual_encoder_model(ew.DEFAULT_DUAL_ENCODER, X)
    return {"tfidf": tf_preds, "tfidf_score": tf_scores, "de": de_preds, "de_score": de_scores}


# ==========================================
# METRICS (independent of sklearn)
# ==========================================

def score(y_true, y_pred, labels=None) -> dict:
    """Accuracy, macro-F1 and weighted-F1 by direct counting.

    labels defaults to the union of true and predicted labels, the same
    convention sklearn uses in the original evaluation.
    """
    y_true, y_pred = list(y_true), list(y_pred)
    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))
    per_class = {}
    for c in labels:
        tp = sum(t == c and p == c for t, p in zip(y_true, y_pred))
        fp = sum(t != c and p == c for t, p in zip(y_true, y_pred))
        fn = sum(t == c and p != c for t, p in zip(y_true, y_pred))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[c] = {"precision": precision, "recall": recall, "f1-score": f1, "support": tp + fn}
    total_support = sum(v["support"] for v in per_class.values())
    correct = sum(t == p for t, p in zip(y_true, y_pred))
    return {
        "n": len(y_true),
        "correct": correct,
        "accuracy": correct / len(y_true),
        "macro_f1": float(np.mean([v["f1-score"] for v in per_class.values()])),
        "weighted_f1": sum(v["f1-score"] * v["support"] for v in per_class.values()) / total_support,
        "per_class": per_class,
        "labels": labels,
    }


def confusion(y_true, y_pred, labels):
    m = pd.DataFrame(0, index=labels, columns=labels)
    for t, p in zip(y_true, y_pred):
        m.loc[t, p] += 1
    return m


# ==========================================
# 1-2. RULE INVENTORY AND RULE TRACE
# ==========================================

def engine_source_lines():
    return Path(legacy_rule_engine.__file__).read_text(encoding="utf-8").splitlines()


def rule_inventory(src_lines, fired_counts) -> pd.DataFrame:
    rows = []
    for rule in RULES:
        first, last = rule.condition
        condition_src = " ".join(line.strip() for line in src_lines[first - 1:last])
        for clause in rule.clauses:
            for atom in clause:
                if atom.kind in PREFIX_KINDS:
                    assert f'"{atom.prefix}"' in condition_src, (rule.rid, atom.prefix, condition_src)
        fields = []
        for atom in rule.guard + tuple(a for c in rule.clauses for a in c):
            fields.extend(f for f in atom.fields if f not in fields)
        clause_kinds = [clause_type(c) for c in rule.clauses]
        if all("prefix" in k for k in clause_kinds):
            reliance = "Identifier prefix required (no prefix-free path)"
        else:
            reliance = "Identifier prefix OR field-presence pattern"
        conflict_guard = {
            "R01": "Field clause requires Customer and DN Reference empty; the RJN-IN prefix clause has no guard.",
            "R05": "Skipped when Units Returned / Reason for Return present.",
            "R06": "Skipped when Units Returned / Reason for Return present.",
            "R10": "Field clause requires Outward Job Work No empty; the GRN prefix clause has no guard.",
            "R21": "Field clause requires Service Charge empty; the JWIO prefix clause has no guard.",
        }.get(rule.rid, "None")
        rows.append({
            "Rule ID": rule.rid,
            "Predicts": rule.category,
            "Engine Lines": f"rule_engine.py:{rule.block[0]}-{rule.block[1]}",
            "Exact Condition (source)": condition_src,
            "Clauses (OR of AND)": " OR ".join("(" + " AND ".join(a.describe() for a in c) + ")" for c in rule.clauses),
            "Guard": " AND ".join(a.describe() for a in rule.guard) or "",
            "Input Fields Read": ", ".join(fields),
            "Clause Evidence Types": " | ".join(clause_kinds),
            "Identifier Reliance": reliance,
            "Reads Field Values Beyond Prefix/Presence": "No",
            "Conflict Guard": conflict_guard,
            "Overrides Model Prediction": "Yes - a match always replaces the model prediction (rule_engine.py:258-259 only used when no rule matches)",
            "Precedence": f"First match wins; evaluated after {', '.join(r.rid for r in RULES[:RULES.index(rule)]) or 'no other rule'}",
            "Uses Ground-Truth Label": "No (static + dynamic checks, see Leakage_Checks)",
            "Rows Fired (A, workbook)": fired_counts.get(rule.rid, 0),
        })
    rows.append({
        "Rule ID": "FALLBACK",
        "Predicts": "Model prediction (base_prediction) or 'Unclassified'",
        "Engine Lines": "rule_engine.py:257-260",
        "Exact Condition (source)": " ".join(l.strip() for l in src_lines[256:260]),
        "Clauses (OR of AND)": "No rule matched",
        "Input Fields Read": "",
        "Overrides Model Prediction": "No",
        "Uses Ground-Truth Label": "No",
        "Rows Fired (A, workbook)": fired_counts.get("FALLBACK", 0),
    })
    return pd.DataFrame(rows)


def format_evidence(evidence: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in evidence.items())


def trace_row(row, disabled=frozenset()) -> dict:
    matches = match_rules(row, disabled)
    if not matches:
        return {"rule": None, "matches": [], "satisfied": []}
    rule, satisfied = matches[0]
    return {"rule": rule, "matches": matches, "satisfied": satisfied}


# ==========================================
# 4. LEAKAGE CHECKS
# ==========================================

class FieldRecorder(dict):
    """Row stand-in that records every field the rule engine reads.

    It is a plain dict, so any access to Series-only attributes such as
    .name, .index or .iloc (row position) raises instead of passing silently.
    """

    def __init__(self, data, log):
        super().__init__(data)
        self._log = log

    def get(self, key, default=None):
        self._log.add(key)
        return super().get(key, default)

    def __getitem__(self, key):
        self._log.add(key)
        return super().__getitem__(key)


def static_rule_fields(path: Path):
    """String literals passed to row.get(...) and file/IO calls in a module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fields, io_calls, globals_ = set(), set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name == "get" and isinstance(func, ast.Attribute) and getattr(func.value, "id", "") == "row":
                if node.args and isinstance(node.args[0], ast.Constant):
                    fields.add(node.args[0].value)
            if name in {"open", "read_excel", "read_csv", "read_json", "load", "loads", "read_text", "ExcelFile"}:
                io_calls.add(name)
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            globals_.update(node.names)
        if isinstance(node, ast.Attribute) and node.attr in {"name", "index", "iloc", "loc"}:
            if getattr(node.value, "id", "") == "row":
                io_calls.add(f"row.{node.attr}")
    return fields, io_calls, globals_


def leakage_checks(X, y, tfidf_model):
    checks = []

    def add(check, method, result, status):
        checks.append({"Check": check, "Method": method, "Result": result, "Status": status})

    forbidden = {LABEL_COLUMN, "Correct", "Predicted Voucher Category", "Prediction Confidence",
                 "Prediction Status", "Applied Rule", "Prediction Explanation"}

    # Static: which fields the engine can read, and whether it touches files or row metadata.
    engine_path = Path(legacy_rule_engine.__file__)
    fields, io_calls, globals_ = static_rule_fields(engine_path)
    add("Rule engine field references (static)",
        "AST scan of every row.get('<field>') literal in rule_engine.py",
        f"{len(fields)} fields referenced; label/output columns referenced: {sorted(fields & forbidden) or 'none'}; "
        f"file/IO or row-position access: {sorted(io_calls) or 'none'}; global statements: {sorted(globals_) or 'none'}",
        "PASS" if not (fields & forbidden) and not io_calls and not globals_ else "FAIL")
    unmapped = sorted(f for f in fields if f not in X.columns)
    add("Engine fields exist in workbook",
        "Compare engine field literals with workbook columns",
        f"Fields referenced by the engine but absent from the workbook: {unmapped or 'none'}",
        "PASS" if not unmapped else "NOTE")

    # Dynamic: record every field actually read across all rows.
    log = set()
    for i in range(len(X)):
        evaluate_transaction_rules(FieldRecorder(X.iloc[i].to_dict(), log), base_prediction="__model__")
    add("Rule engine field reads (dynamic)",
        "Ran the engine on all rows through a recording dict (no .name/.index/.iloc available)",
        f"{len(log)} distinct fields read; label/output columns read: {sorted(log & forbidden) or 'none'}; "
        f"no row-position attribute accessed (would have raised)",
        "PASS" if not (log & forbidden) and log <= fields else "FAIL")

    # Injection: put the truth and previous outputs into the row; predictions must not move.
    base = engine_predictions(X)
    injected = X.copy()
    shifted = list(y.iloc[1:]) + [y.iloc[0]]
    injected[LABEL_COLUMN] = shifted
    injected["Correct"] = False
    injected["Predicted Voucher Category"] = list(y)
    injected["Prediction Confidence"] = 0.0
    changed = sum(a != b for a, b in zip(base, engine_predictions(injected)))
    add("Label / previous-output injection",
        "Added Voucher Category (wrong labels), Correct=False and Predicted Voucher Category=ground truth to every row",
        f"Rule predictions changed on {changed} of {len(X)} rows",
        "PASS" if changed == 0 else "FAIL")

    # Row order: shuffling must not change any row's prediction.
    perm = np.random.default_rng(0).permutation(len(X))
    shuffled_rules = engine_predictions(X.iloc[perm])
    restored = [None] * len(X)
    for new_pos, old_pos in enumerate(perm):
        restored[old_pos] = shuffled_rules[new_pos]
    tf_base, _ = ew.evaluate_baseline_model(tfidf_model, X)
    tf_shuf, _ = ew.evaluate_baseline_model(tfidf_model, X.iloc[perm])
    tf_restored = [None] * len(X)
    for new_pos, old_pos in enumerate(perm):
        tf_restored[old_pos] = tf_shuf[new_pos]
    moved = sum(a != b for a, b in zip(base, restored)) + sum(a != b for a, b in zip(tf_base, tf_restored))
    add("Row position / category ordering",
        "Shuffled rows (seed 0), re-ran rules and TF-IDF, re-aligned by original position",
        f"{moved} predictions changed after re-alignment",
        "PASS" if moved == 0 else "FAIL")

    # Hard-coded lookups: search the code for any identifier value from the workbook.
    id_values = set()
    for col in IDENTIFIER_COLUMNS:
        id_values.update(v for v in X[col].map(_clean) if v)
    code_files = sorted((ROOT / "src/vyom").glob("*.py")) + sorted((ROOT / "tests").glob("*.py"))
    hits = []
    for path in code_files:
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        hits.extend(f"{path.name}:{v}" for v in id_values if v in text)
    engine_tree = ast.parse(engine_path.read_text(encoding="utf-8"))
    containers = [n for n in ast.walk(engine_tree) if isinstance(n, (ast.Dict, ast.List, ast.Set))
                  and any(isinstance(e, ast.Constant) and isinstance(e.value, str)
                          for e in (n.keys if isinstance(n, ast.Dict) else n.elts) if e is not None)]
    add("Lookup table of record IDs / labels",
        f"Searched {len(code_files) - 1} source and test files for all {len(id_values)} identifier values in the workbook; "
        "AST scan of rule_engine.py for dict/list/set literals of strings",
        f"Identifier values found in code: {hits or 'none'}; string container literals in rule engine: "
        f"{len(containers)} (only the {{'nan','none','nat'}} cleaning set)" ,
        "PASS" if not hits and len(containers) <= 1 else "FAIL")

    # Metadata columns that could encode the answer.
    answer_like = r"categor|voucher|label|\bclass|test ?case|scenario|expected (category|label|class|voucher|answer)"
    suspicious = [c for c in X.columns if re.search(answer_like, c, re.I)]
    add("Answer-encoding metadata columns",
        "Searched feature column names for category/voucher/label/class/test-case/expected-answer wording",
        f"Suspicious columns: {suspicious or 'none'} ('Expected Arrival' is a delivery date). Note: the "
        "populated-column pattern itself identifies the category 1:1 in this workbook (see Schema_Signatures) - "
        "a template property, not label leakage.",
        "PASS" if not suspicious else "FAIL")

    # Evaluation path: what run_pipeline passes to the rule engine and the serializer.
    calls = audit_pipeline_inputs()
    add("Evaluation pipeline inputs (dynamic)",
        "Ran run_pipeline on the workbook (labeled mode, output to a temporary folder) with the rule engine and "
        "serializer wrapped to record the columns of every row they receive",
        f"Rule-engine calls: {calls['rules']}, serializer calls: {calls['serialize']}; calls receiving label or "
        f"output columns: {calls['leaky'] or 'none'}",
        "PASS" if not calls["leaky"] else "FAIL")

    tests = audit_test_fixtures()
    deliberate = {t for t in tests["leaky_tests"] if "label_exclusion" in t}
    accidental = sorted(set(tests["leaky_tests"]) - deliberate)
    add("Unit-test fixtures (dynamic)",
        "Ran tests/test_evaluation_adapter.py with the rule engine and serializer wrapped; recorded which tests "
        "pass rows containing label/output columns",
        f"Tests run: {tests['run']}, failures: {tests['failures']}, errors: {tests['errors']}. Rows with label columns "
        f"supplied by: {sorted(tests['leaky_tests']) or 'none'} (deliberate invariance test: {sorted(deliberate) or 'none'}); "
        f"accidental: {accidental or 'none'}",
        "PASS" if not accidental and not tests["failures"] and not tests["errors"] else "FAIL")
    return pd.DataFrame(checks)


@contextlib.contextmanager
def recording_wrappers():
    """Wrap the rule engine and serializer everywhere the pipeline and tests bind them."""
    calls = {"rules": 0, "serialize": 0, "leaky": [], "leaky_tests": set()}
    forbidden = {LABEL_COLUMN, "Correct", "Predicted Voucher Category"}
    original_rules = rule_engine.evaluate_transaction_rules
    original_assess = rule_engine.assess_transaction
    original_serialize = adapter.serialize_wide_row

    def current_test():
        import inspect
        for frame in inspect.stack():
            if frame.function.startswith("test_"):
                return frame.function
        return "pipeline"

    def keys_of(row):
        return set(row.index) if hasattr(row, "index") and not isinstance(row, dict) else set(row.keys())

    def rules_wrapper(row, base_prediction=None):
        calls["rules"] += 1
        leaked = keys_of(row) & forbidden
        if leaked:
            calls["leaky"].append(f"rules:{sorted(leaked)}")
            calls["leaky_tests"].add(current_test())
        return original_rules(row, base_prediction=base_prediction)

    def assess_wrapper(row):
        calls["rules"] += 1
        leaked = keys_of(row) & forbidden
        if leaked:
            calls["leaky"].append(f"rules:{sorted(leaked)}")
            calls["leaky_tests"].add(current_test())
        return original_assess(row)

    def serialize_wrapper(row):
        calls["serialize"] += 1
        leaked = keys_of(row) & forbidden
        if leaked:
            calls["leaky"].append(f"serialize:{sorted(leaked)}")
            calls["leaky_tests"].add(current_test())
        return original_serialize(row)

    rule_engine.evaluate_transaction_rules = rules_wrapper
    rule_engine.assess_transaction = assess_wrapper
    ew.assess_transaction = assess_wrapper
    adapter.serialize_wide_row = serialize_wrapper
    ew.serialize_wide_row = serialize_wrapper
    try:
        yield calls
    finally:
        rule_engine.evaluate_transaction_rules = original_rules
        rule_engine.assess_transaction = original_assess
        ew.assess_transaction = original_assess
        adapter.serialize_wide_row = original_serialize
        ew.serialize_wide_row = original_serialize


def audit_pipeline_inputs():
    import tempfile
    with recording_wrappers() as calls, tempfile.TemporaryDirectory() as tmp:
        with contextlib.redirect_stdout(io.StringIO()):
            ew.run_pipeline(
                input_path=ew.DEFAULT_INPUT,
                output_path=Path(tmp) / "pipeline_audit.xlsx",
                run_comparison=False,
            )
    return calls


def audit_test_fixtures():
    with recording_wrappers() as calls:
        spec = importlib.util.spec_from_file_location("vyom_audit_tests", TESTS_FILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        with contextlib.redirect_stdout(io.StringIO()):
            result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    calls.update(run=result.testsRun, failures=len(result.failures), errors=len(result.errors))
    return calls


# ==========================================
# 7. CONTROLLED RECORD MODIFICATIONS
# ==========================================

def digits_of(value) -> str:
    return "".join(re.findall(r"\d+", str(value)))


# (case id, base Excel row, required own-ID prefix of base row, edits, description, expectation, basis)
# Edits: {field: value | callable(row) | None}; None blanks the field.
CASES = [
    ("M01", 4, ("Document Number", "DBN"), {"Document Number": lambda r: neutral_identifier(r["Document Number"])},
     "DBN identifier neutralized; supplier-return evidence kept",
     "Purchase Return / Debit Note", "Units Returned, Reason for Return and an Original Doc Ref to a purchase invoice remain"),
    ("M02", 4, ("Document Number", "DBN"), {"Document Number": None},
     "DBN identifier removed; supplier-return evidence kept",
     "Purchase Return / Debit Note", "Units Returned, Reason for Return and Original Doc Ref (PUR-) remain"),
    ("M03", 4, ("Document Number", "DBN"),
     {"Document Number": lambda r: neutral_identifier(r["Document Number"]),
      "Original Doc Ref": lambda r: neutral_identifier(r["Original Doc Ref"])},
     "DBN identifier and purchase-invoice reference both neutralized",
     "AMBIGUOUS", "Return evidence remains, but supplier vs customer direction was carried only by identifiers; "
                  "purchase- and sales-return records both carry Vendor Name and Company in this workbook"),
    ("M04", 9, ("Document Number", "CRN"), {"Document Number": lambda r: neutral_identifier(r["Document Number"])},
     "CRN identifier neutralized; customer-return evidence kept",
     "Sales Return / Credit Note", "Units Returned, Reason for Return and an Original Invoice Ref to a sales invoice remain"),
    ("M05", 9, ("Document Number", "CRN"), {"Document Number": None},
     "CRN identifier removed; customer-return evidence kept",
     "Sales Return / Credit Note", "Units Returned, Reason for Return and Original Invoice Ref (SAL-) remain"),
    ("M06", 9, ("Document Number", "CRN"),
     {"Document Number": lambda r: neutral_identifier(r["Document Number"]),
      "Original Invoice Ref": lambda r: neutral_identifier(r["Original Invoice Ref"])},
     "CRN identifier and sales-invoice reference both neutralized",
     "AMBIGUOUS", "Return evidence remains, but direction was carried only by identifiers"),
    ("M07", 9, ("Document Number", "CRN"), {"Document Number": lambda r: "DBN-" + digits_of(r["Document Number"])},
     "Credit-note record given a DBN- identifier (conflicts with its SAL- original invoice)",
     "CONFLICT", "Identifier says debit note; Original Invoice Ref (SAL-) says sales return"),
    ("M08", 25, ("Rejection Note No", "RJN-IN"), {"GRN Reference": None},
     "GRN Reference removed from an inward rejection",
     "Rejection In", "RJN-IN note, Receiving Company and rejection details remain"),
    ("M09", 25, ("Rejection Note No", "RJN-IN"),
     {"GRN Reference": None, "Rejection Note No": lambda r: neutral_identifier(r["Rejection Note No"])},
     "GRN Reference removed and RJN-IN identifier neutralized",
     "Rejection In", "Receiving Company and rejection details remain (weak inward evidence)"),
    ("M10", 25, ("Rejection Note No", "RJN-IN"),
     {"GRN Reference": None, "Receiving Company": None,
      "Rejection Note No": lambda r: neutral_identifier(r["Rejection Note No"])},
     "GRN Reference and Receiving Company removed, RJN-IN identifier neutralized",
     "AMBIGUOUS", "Only Supplier and rejection details remain; outward rejections also carry Supplier"),
    ("M11", 25, ("Rejection Note No", "RJN-IN"),
     {"Customer": "Retail Networks Inc", "DN Reference": "DC7129709"},
     "Inward rejection given outward evidence (Customer, DN Reference); RJN-IN kept",
     "CONFLICT", "Inward (RJN-IN, GRN Reference, Receiving Company) and outward (Customer, DN Reference) evidence both present"),
    ("M12", 25, ("Rejection Note No", "RJN-IN"),
     {"Customer": "Retail Networks Inc", "DN Reference": "DC7129709",
      "Rejection Note No": lambda r: neutral_identifier(r["Rejection Note No"])},
     "Same conflict as M11 with the rejection identifier neutralized",
     "CONFLICT", "Inward and outward evidence both present; no identifier"),
    ("M13", 3, ("Rejection Note No", "RJN-OUT"),
     {"GRN Reference": "GRN2009152", "Receiving Company": "Corporate Services Ltd"},
     "Outward rejection given inward evidence (GRN Reference, Receiving Company); RJN-OUT kept",
     "CONFLICT", "Outward (RJN-OUT, Customer, DN Reference) and inward (GRN Reference, Receiving Company) evidence both present"),
    ("M14", 3, ("Rejection Note No", "RJN-OUT"), {"Rejection Note No": lambda r: "RJN-IN-" + digits_of(r["Rejection Note No"])},
     "Outward rejection given an RJN-IN identifier; Customer and DN Reference kept",
     "CONFLICT (fields: Rejection Out)", "Identifier says inward; Customer and DN Reference say outward"),
    ("M15", 25, ("Rejection Note No", "RJN-IN"), {"Rejection Note No": lambda r: "RJN-OUT-" + digits_of(r["Rejection Note No"])},
     "Inward rejection given an RJN-OUT identifier; GRN Reference and Receiving Company kept",
     "CONFLICT (fields: Rejection In)", "Identifier says outward; GRN Reference and Receiving Company say inward"),
    ("M16", 2, ("PO Number", "PO"), {"PO Number": None},
     "PO Number removed; Supplier, Ordering Company, Quantity Required, Promised Delivery kept",
     "Purchase Order", "Order fields (supplier, ordering company, required quantity, promised delivery) remain"),
    ("M17", 2, ("PO Number", "PO"), {"PO Number": lambda r: neutral_identifier(r["PO Number"])},
     "PO Number neutralized; order fields kept",
     "Purchase Order", "Order fields remain"),
    ("M18", 54, ("SO Number", "SO"), {"SO Number": None},
     "SO Number removed; Customer, Selling Company, Quantity Ordered kept",
     "Sales Order", "Order fields (customer, selling company, ordered quantity) remain"),
    ("M19", 6, ("GRN Number", "GRN"), {"GRN Number": None, "PO Reference": None},
     "GRN Number and PO Reference removed from a receipt note",
     "Receipt Note", "Item Received, Quantity Received, Receiving Company, Quality Status remain"),
    ("M20", 10, ("Contra ID", "CTR"), {"Contra ID": lambda r: "PMT-" + digits_of(r["Contra ID"])},
     "Contra record given a PMT- identifier; account-transfer fields kept",
     "Contra", "Source Account, Destination Account and Transfer Amount remain"),
    ("M21", 11, ("Payment ID", "PMT"), {"Contra ID": lambda r: "CTR-" + digits_of(r["Payment ID"])},
     "Payment record given an extra Contra ID (CTR-); payment fields kept",
     "CONFLICT (fields: Payment)", "Payer/Payee organizations, Payment Amount and PMT- identifier say payment; stray CTR- identifier says contra"),
    ("M22", 30, ("Expense Claim No", "EXP"), {"Expense Claim No": lambda r: neutral_identifier(r["Expense Claim No"])},
     "Expense Claim No neutralized; claim fields kept",
     "Expense", "Expense Type, Amount Claimed, Department, Approved By remain"),
    ("M23", 16, ("Export Invoice No", "EXP"), {"Export Invoice No": lambda r: neutral_identifier(r["Export Invoice No"])},
     "Export Invoice No neutralized; export fields kept",
     "Export", "Destination Country, Exporter, Units Exported, Free on Board Value remain"),
    ("M24", 14, ("Document Number", "PUR-"), {"Document Number": lambda r: neutral_identifier(r["Document Number"])},
     "Purchase invoice identifier neutralized",
     "AMBIGUOUS", "Purchase and sales invoice records share Vendor Name, Company, Product and amount fields in this workbook"),
    ("M25", 5, ("Document Number", "SAL-"), {"Document Number": lambda r: neutral_identifier(r["Document Number"])},
     "Sales invoice identifier neutralized; Delivery Ref kept",
     "Sales", "Delivery Ref to a delivery note remains (weak sales evidence)"),
    ("M26", 5, ("Document Number", "SAL-"),
     {"Document Number": lambda r: neutral_identifier(r["Document Number"]),
      "Delivery Ref": lambda r: neutral_identifier(r["Delivery Ref"])},
     "Sales invoice identifier and Delivery Ref neutralized",
     "AMBIGUOUS", "Only fields shared with purchase invoices remain (Delivery Ref column is still present)"),
    ("M27", 35, ("Stock Count ID", "SC"), {"Stock Count ID": lambda r: "SA" + digits_of(r["Stock Count ID"])},
     "Physical-stock record given a stock-adjustment style identifier (SA...)",
     "Physical Stock", "Book Quantity and Counted Quantity remain"),
]


def build_modified_records(X: pd.DataFrame):
    rows, meta = [], []
    for cid, excel_row, (id_col, id_prefix), edits, description, expectation, basis in CASES:
        base = X.iloc[excel_row - 2].copy().astype(object)
        assert _clean(base[id_col]).startswith(id_prefix), (cid, base[id_col])
        changes = []
        for field, new in edits.items():
            old = _clean(base.get(field)) or "(empty)"
            value = new(base) if callable(new) else new
            base[field] = np.nan if value is None else value
            changes.append(f"{field}: {old} -> {value if value is not None else '(removed)'}")
        rows.append(base)
        meta.append({"Case": cid, "Base Excel Row": excel_row, "Modification": description,
                     "Field Changes": "; ".join(changes), "Auditor Expectation": expectation,
                     "Basis For Expectation": basis})
    return pd.DataFrame(rows).reset_index(drop=True), meta


def assess_case(expectation, rule, clause_kinds, rule_pred, final_tf):
    if rule is None:
        if expectation.startswith(("AMBIGUOUS", "CONFLICT")):
            return f"No rule fired; model decided ({final_tf}) without a review flag"
        return f"No rule fired despite remaining evidence; model decided ({final_tf})"
    via = " / ".join(clause_kinds)
    if expectation == "AMBIGUOUS":
        return f"Rule resolved an ambiguous record via {via}"
    if expectation == "CONFLICT":
        return f"Conflict not detected; rule chose {rule_pred} via {via}"
    if expectation.startswith("CONFLICT (fields: "):
        field_side = expectation[len("CONFLICT (fields: "):-1]
        if rule_pred == field_side:
            return f"Followed field evidence ({via}); conflict not flagged"
        return f"Followed identifier prefix against field evidence ({via})"
    if rule_pred == expectation:
        if "prefix" in via:
            return f"Correct, via {via}"
        return "Correct, via remaining field evidence"
    return f"Contradicted remaining evidence via {via}"


# ==========================================
# SCHEMA AND IDENTIFIER PATTERNS (audit only)
# ==========================================

def schema_signatures(X, y):
    sig = X.notna().apply(lambda r: tuple(c for c in X.columns if r[c]), axis=1)
    frame = pd.DataFrame({"sig": sig, "y": y.values})
    # Leave-one-out: label of other rows sharing the identical populated-column set.
    loo_correct = 0
    for i in range(len(frame)):
        others = frame[(frame.sig == frame.sig.iloc[i]) & (frame.index != i)]
        if len(others) and others.y.mode().iloc[0] == frame.y.iloc[i]:
            loo_correct += 1
    rows = []
    for cat, sub in frame.groupby("y"):
        sigs = sub.sig.unique()
        rows.append({
            "Category (ground truth, audit only)": cat,
            "Records": len(sub),
            "Distinct Populated-Column Sets": len(sigs),
            "Shared With Other Categories": "No" if frame[frame.sig.isin(sigs)].y.nunique() == 1 else "Yes",
            "Populated Columns": " | ".join(", ".join(s) for s in sigs),
        })
    return pd.DataFrame(rows), {"distinct_signatures": int(frame.sig.nunique()),
                                "max_categories_per_signature": int(frame.groupby("sig").y.nunique().max()),
                                "loo_signature_correct": loo_correct}


def identifier_patterns(X, y):
    rows = []
    for col in IDENTIFIER_COLUMNS:
        values = X[col].map(_clean)
        mask = values != ""
        prefixes = values[mask].map(lambda v: re.match(r"^[A-Z-]*[A-Z]", v).group(0) if re.match(r"^[A-Z]", v) else "")
        by_prefix = pd.DataFrame({"p": prefixes, "y": y[mask]})
        rows.append({
            "Identifier Column": col,
            "Kind": "own document ID" if col in OWN_ID_COLUMNS else "reference to another document",
            "Records With Value": int(mask.sum()),
            "Prefix -> Categories (ground truth, audit only)": "; ".join(
                f"{p}: {', '.join(sorted(g.y.unique()))}" for p, g in by_prefix.groupby("p")),
            "Prefix Identifies One Category": "Yes" if by_prefix.groupby("p").y.nunique().max() == 1 else "No",
            "Read By Rule Engine": "prefix test" if any(a.fields[0] == col and a.kind in PREFIX_KINDS
                                                        for r in RULES for c in r.clauses for a in c)
            else ("presence test" if any(col in a.fields for r in RULES for c in r.clauses + (r.guard,) for a in c)
                  else "No"),
        })
    other_id_like = [c for c in X.columns if c not in IDENTIFIER_COLUMNS
                     and X[c].map(lambda v: bool(ID_LIKE.match(_clean(v)))).any()]
    return pd.DataFrame(rows), other_id_like


# ==========================================
# MAIN
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Audit the VYOM+ rule engine on the evaluation workbook.")
    parser.add_argument("--input", default=str(ew.DEFAULT_INPUT), help="Evaluation workbook")
    parser.add_argument("--sheet", default="Test Cases")
    parser.add_argument("--facts", default=None, help="Optional JSON path for key audit figures")
    parser.add_argument("--output-dir", default=str(REPORTS_DIR), help="Folder for the audit workbook and CSV")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    AUDIT_XLSX, ABLATION_CSV = output_dir / AUDIT_XLSX_NAME, output_dir / ABLATION_CSV_NAME
    existing = [str(p) for p in (AUDIT_XLSX, ABLATION_CSV) if p.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing audit output(s): {', '.join(existing)}. "
                              "Pass a different --output-dir.")
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Inputs. y is held back until all predictions exist. ---
    X, y_holdout = load_evaluation_workbook(args.input, sheet_name=args.sheet)
    assert LABEL_COLUMN not in X.columns
    tfidf_model = load_tfidf()

    X_removed = transform_identifiers(X, "removed")
    X_neutral = transform_identifiers(X, "neutralized")

    # --- Predictions (transaction fields only) ---
    print("Running models on original, identifiers-removed and identifiers-neutralized inputs...")
    models = {"original": run_models(X, tfidf_model),
              "removed": run_models(X_removed, tfidf_model),
              "neutralized": run_models(X_neutral, tfidf_model)}

    rules = {
        "A": mirror_predictions(X, "all"),
        "B": mirror_predictions(X, "no_own_prefix"),
        "C": mirror_predictions(X_removed, "all"),
        "D": mirror_predictions(X_neutral, "all"),
        "E": mirror_predictions(X, "presence_only"),
    }
    # The mirror must reproduce the real engine wherever the engine can run.
    assert_parity(rules["A"], engine_predictions(X), "original workbook")
    assert_parity(rules["C"], engine_predictions(X_removed), "identifiers removed")
    assert_parity(rules["D"], engine_predictions(X_neutral), "identifiers neutralized")
    assert_parity(rules["B"], engine_predictions(transform_own_identifiers_neutralized(X)),
                  "configuration B vs engine on own-ID-neutralized input")
    assert_parity(rules["E"], rules["D"], "configuration E vs engine on fully neutralized input")

    configs = [
        ("A", "All rules enabled", "original", "all"),
        ("B", "Own-identifier prefix clauses disabled; all other clauses unchanged", "original", "no_own_prefix"),
        ("C", "Identifier values removed (own and reference IDs blanked)", "removed", "all"),
        ("D", "Identifier prefixes neutralized to DOC-<digits> (presence kept)", "neutralized", "all"),
        ("E", "Field-presence clauses only (all own- and reference-ID prefix clauses disabled)", "original", "presence_only"),
    ]
    finals = {}
    for cid, _, variant, _ in configs:
        m = models[variant]
        finals[(cid, "none")] = combine(rules[cid], None)
        finals[(cid, "tfidf")] = combine(rules[cid], m["tfidf"])
        finals[(cid, "de")] = combine(rules[cid], m["de"])

    modified, case_meta = build_modified_records(X)
    mod_models = run_models(modified, tfidf_model)
    mod_rules = mirror_predictions(modified, "all")
    assert_parity(mod_rules, engine_predictions(modified), "modified records")

    # --- Ground truth joined only from here on ---
    y = y_holdout.astype(str).tolist()
    n = len(y)

    # Ablation metrics.
    ablation_rows = []

    def add_metrics(config_id, description, variant, rule_mode, fallback, preds, rule_preds=None):
        s = score(y, preds)
        row = {"config_id": config_id, "configuration": description, "input_variant": variant,
               "rule_clauses": rule_mode, "fallback_model": fallback, "n_records": n}
        if rule_preds is not None:
            fired = [i for i, r in enumerate(rule_preds) if r is not None]
            fired_ok = sum(rule_preds[i] == y[i] for i in fired)
            fb = [i for i, r in enumerate(rule_preds) if r is None]
            row.update(rules_fired=len(fired), rules_fired_correct=fired_ok,
                       rule_precision=round(fired_ok / len(fired), 4) if fired else None,
                       fallback_records=len(fb),
                       fallback_correct=sum(preds[i] == y[i] for i in fb) if fallback != "none" else 0)
        else:
            row.update(rules_fired=0, rules_fired_correct=0, rule_precision=None,
                       fallback_records=n, fallback_correct=s["correct"])
        row.update(correct=s["correct"], accuracy=round(s["accuracy"], 4),
                   macro_f1=round(s["macro_f1"], 4), weighted_f1=round(s["weighted_f1"], 4))
        ablation_rows.append(row)
        return s

    model_names = {"tfidf": "TF-IDF baseline", "de": "Dual Encoder V2", "none": "none (unmatched = Unclassified)"}
    for variant, label in [("original", "MODEL_ONLY_original"), ("removed", "MODEL_ONLY_identifiers_removed"),
                           ("neutralized", "MODEL_ONLY_identifiers_neutralized")]:
        for key in ("tfidf", "de"):
            add_metrics(label, "Model alone, no rules", variant, "none", model_names[key], models[variant][key])
    config_scores = {}
    for cid, description, variant, mode in configs:
        for fb in ("none", "tfidf", "de"):
            config_scores[(cid, fb)] = add_metrics(cid, description, variant, mode, model_names[fb],
                                                   finals[(cid, fb)], rules[cid])
    ablation = pd.DataFrame(ablation_rows)
    for i, row in ablation.iterrows():
        if row.config_id in {c[0] for c in configs}:
            fb = {v: k for k, v in model_names.items()}[row.fallback_model]
            ablation.loc[i, "changed_vs_A"] = sum(a != b for a, b in zip(finals[(row.config_id, fb)], finals[("A", fb)]))
    ablation["changed_vs_A"] = ablation["changed_vs_A"].astype("Int64")
    ablation.to_csv(ABLATION_CSV, index=False)

    # Rule trace (configuration A).
    src_lines = engine_source_lines()
    trace_rows, fired_counts = [], {}
    prefix_only_rows, own_only_rows = 0, 0
    m0 = models["original"]
    for i in range(n):
        row = X.iloc[i]
        t = trace_row(row)
        id_col, id_val = primary_identifier(row)
        rule = t["rule"]
        if rule is None:
            fired_counts["FALLBACK"] = fired_counts.get("FALLBACK", 0) + 1
            kinds, evidence, prefix_dep, presence_ok, prefix_hit = [], "", "n/a", "n/a", ""
        else:
            fired_counts[rule.rid] = fired_counts.get(rule.rid, 0) + 1
            kinds = [clause_type(c) for c, _ in t["satisfied"]]
            evidence = " || ".join(f"[{clause_type(c)}] {format_evidence(ev)}" for c, ev in t["satisfied"])
            presence_ok = "Yes" if any(k == "field presence only" for k in kinds) else "No"
            prefix_dep = "No" if presence_ok == "Yes" else "Yes"
            prefix_hit = "; ".join(format_evidence({a.fields[0]: _clean(row.get(a.fields[0]))})
                                   for c, _ in t["satisfied"] for a in c if a.kind in PREFIX_KINDS)
            if prefix_dep == "Yes":
                prefix_only_rows += 1
                if all(not any(a.kind == REF for a in c) for c, _ in t["satisfied"]):
                    own_only_rows += 1
        rule_pred = rule.category if rule else NO_RULE
        trace_rows.append({
            "Excel Row": i + 2,
            "Row Position": i,
            "Identifier Field": id_col,
            "Identifier Value": id_val,
            "TF-IDF Raw Prediction": m0["tfidf"][i],
            "TF-IDF Score (Uncalibrated)": round(m0["tfidf_score"][i], 4),
            "Dual Encoder V2 Raw Prediction": m0["de"][i],
            "Dual Encoder V2 Score (Uncalibrated)": round(m0["de_score"][i], 4),
            "Rule-Based Prediction": rule_pred,
            "Final Prediction (TF-IDF + Rules)": finals[("A", "tfidf")][i],
            "Final Prediction (DE V2 + Rules)": finals[("A", "de")][i],
            "Rule ID": rule.rid if rule else "",
            "Rule Name": f"{rule.rid} {rule.category} (rule_engine.py:{rule.block[0]}-{rule.block[1]})" if rule else "",
            "Satisfied Clause Types": " | ".join(kinds),
            "Triggering Fields And Values": evidence,
            "Identifier Prefix Matched": prefix_hit,
            "Depends On Identifier Prefix": prefix_dep,
            "Field-Presence Evidence Alone Sufficient": presence_ok,
            "Rules Matched (all)": ", ".join(r.rid for r, _ in t["matches"]),
            "Multiple Rules Matched": "Yes" if len(t["matches"]) > 1 else "No",
            "Overrode TF-IDF Prediction": "Yes" if rule and rule.category != m0["tfidf"][i] else "No",
            "Overrode DE V2 Prediction": "Yes" if rule and rule.category != m0["de"][i] else "No",
            # Ground truth is attached only after every prediction above was produced.
            "Ground Truth (audit only)": y[i],
            "Rule-Based Correct": (rule_pred == y[i]) if rule else None,
            "Correct (TF-IDF + Rules)": finals[("A", "tfidf")][i] == y[i],
            "Correct (DE V2 + Rules)": finals[("A", "de")][i] == y[i],
            "TF-IDF Raw Correct": m0["tfidf"][i] == y[i],
            "DE V2 Raw Correct": m0["de"][i] == y[i],
        })
    trace = pd.DataFrame(trace_rows)
    inventory = rule_inventory(src_lines, fired_counts)
    for cid in ("B", "E"):
        counts = {}
        for i in range(n):
            matches = match_rules(X.iloc[i], RULE_MODES[{"B": "no_own_prefix", "E": "presence_only"}[cid]])
            if matches:
                counts[matches[0][0].rid] = counts.get(matches[0][0].rid, 0) + 1
        inventory[f"Rows Fired ({cid})"] = inventory["Rule ID"].map(
            lambda r: counts.get(r, 0) if r != "FALLBACK" else None).astype("Int64")

    # Row-level ablation predictions.
    row_ablation = trace[["Excel Row", "Identifier Value"]].copy()
    for cid, _, variant, _ in configs:
        row_ablation[f"{cid}: Rule"] = [r if r is not None else NO_RULE for r in rules[cid]]
        row_ablation[f"{cid}: TF-IDF + Rules"] = finals[(cid, "tfidf")]
        row_ablation[f"{cid}: DE V2 + Rules"] = finals[(cid, "de")]
    for variant, label in [("removed", "IDs removed"), ("neutralized", "IDs neutralized")]:
        row_ablation[f"TF-IDF alone ({label})"] = models[variant]["tfidf"]
        row_ablation[f"DE V2 alone ({label})"] = models[variant]["de"]
    row_ablation["Ground Truth (audit only)"] = y
    for cid, _, _, _ in configs:
        row_ablation[f"{cid}: TF-IDF + Rules Correct"] = [p == t for p, t in zip(finals[(cid, "tfidf")], y)]
        row_ablation[f"{cid}: DE V2 + Rules Correct"] = [p == t for p, t in zip(finals[(cid, "de")], y)]

    # Modified records.
    case_rows = []
    for j, meta in enumerate(case_meta):
        t = trace_row(modified.iloc[j])
        rule = t["rule"]
        kinds = [clause_type(c) for c, _ in t["satisfied"]] if rule else []
        final_tf = mod_rules[j] or mod_models["tfidf"][j]
        final_de = mod_rules[j] or mod_models["de"][j]
        case_rows.append({
            **meta,
            "Rule Fired": f"{rule.rid} {rule.category}" if rule else NO_RULE,
            "Satisfied Clause Types": " | ".join(kinds),
            "Triggering Fields And Values": " || ".join(format_evidence(ev) for _, ev in t["satisfied"]),
            "Rules Matched (all)": ", ".join(r.rid for r, _ in t["matches"]),
            "TF-IDF Raw": mod_models["tfidf"][j],
            "DE V2 Raw": mod_models["de"][j],
            "Final (TF-IDF + Rules)": final_tf,
            "Final (DE V2 + Rules)": final_de,
            "Former Reported Confidence": 1.0 if rule else round(mod_models["tfidf_score"][j], 4),
            "Assessment": assess_case(meta["Auditor Expectation"], rule, kinds, rule.category if rule else None, final_tf),
        })
    cases = pd.DataFrame(case_rows)

    # --- 6. Metric verification against the existing reports ---
    report = pd.read_excel(ORIGINAL_PREDICTIONS)
    verification = []

    def check(item, expected, observed, ok=None):
        ok = (expected == observed) if ok is None else ok
        verification.append({"Check": item, "Expected": str(expected), "Observed": str(observed),
                             "Status": "PASS" if ok else "FAIL"})

    raw = pd.read_excel(args.input, sheet_name=args.sheet)
    check("Workbook records", 120, len(X))
    check("Duplicate records in workbook", 0, int(raw.duplicated().sum()))
    support = pd.Series(y).value_counts()
    check("Categories in workbook", 24, int(support.size))
    check("Support per category", "5 for every category", f"min {support.min()}, max {support.max()}",
          ok=support.min() == support.max() == 5)
    check("Report records", len(X), len(report))
    feature_mismatch = int((report[list(X.columns)].astype(str).values != X.astype(str).values).sum())
    check("Report feature cells differing from workbook (row alignment)", 0, feature_mismatch)
    check("Report ground-truth cells differing from workbook", 0,
          int((report[LABEL_COLUMN].astype(str).values != np.array(y)).sum()))
    regenerated = finals[("A", "tfidf")]
    check("Report predictions equal to label-free regeneration (TF-IDF + rules)", len(X),
          int((report["Predicted Voucher Category"].astype(str).values == np.array(regenerated)).sum()))
    check("Report 'Correct' equal to (prediction == ground truth)", len(X),
          int((report["Correct"].astype(bool).values == (report["Predicted Voucher Category"] == report[LABEL_COLUMN]).values).sum()))
    check("Rule-engine predictions differing from ground truth under ablations (not copied from labels)",
          "> 0 for B-E rules-only", ", ".join(f"{c}:{sum(p != t for p, t in zip(finals[(c, 'none')], y))}" for c in "BCDE"),
          ok=all(sum(p != t for p, t in zip(finals[(c, "none")], y)) > 0 for c in "BCDE"))

    reported = pd.read_csv(ORIGINAL_COMPARISON)
    mapping = {"TF-IDF Baseline Alone": score(y, models["original"]["tfidf"]),
               "TF-IDF Baseline + Semantic Rules": config_scores[("A", "tfidf")],
               "Dual Encoder V2 Alone": score(y, models["original"]["de"]),
               "Dual Encoder V2 + Semantic Rules": config_scores[("A", "de")]}
    for _, r in reported.iterrows():
        s = mapping[r["model"]]
        for metric in ("accuracy", "macro_f1", "weighted_f1"):
            check(f"{r['model']}: {metric} (reported vs recomputed)", round(float(r[metric]), 6),
                  round(s[metric], 6), ok=abs(float(r[metric]) - s[metric]) < 1e-9)
        check(f"{r['model']}: correct predictions (recomputed)", f"{r['accuracy'] * n:.0f}", s["correct"],
              ok=round(r["accuracy"] * n) == s["correct"])

    per_class_reported = pd.read_csv(ORIGINAL_PER_CLASS, index_col=0)
    s_a = config_scores[("A", "tfidf")]
    diffs = []
    for c, v in s_a["per_class"].items():
        for metric in ("precision", "recall", "f1-score", "support"):
            diffs.append(abs(float(per_class_reported.loc[c, metric]) - v[metric]))
    check("Per-class report (TF-IDF + rules): max abs difference", 0.0, max(diffs), ok=max(diffs) < 1e-9)
    cm_reported = pd.read_csv(ORIGINAL_CONFUSION, index_col=0)
    cm_recomputed = confusion(y, regenerated, s_a["labels"])
    check("Confusion matrix (TF-IDF + rules) identical to report", True,
          bool(cm_reported.loc[s_a["labels"], s_a["labels"]].values.tolist() == cm_recomputed.values.tolist()))
    verification = pd.DataFrame(verification)

    per_class = pd.DataFrame([
        {"Configuration": name, "Category": c, **{k: round(v[k], 4) for k in ("precision", "recall", "f1-score")},
         "Support": v["support"]}
        for name, s in [("A: TF-IDF + Rules", config_scores[("A", "tfidf")]),
                        ("TF-IDF alone", mapping["TF-IDF Baseline Alone"]),
                        ("DE V2 alone", mapping["Dual Encoder V2 Alone"]),
                        ("B: TF-IDF + Rules", config_scores[("B", "tfidf")]),
                        ("E: TF-IDF + Rules", config_scores[("E", "tfidf")])]
        for c, v in s["per_class"].items()])
    cm_out = cm_recomputed.copy()
    cm_out.insert(0, "Ground Truth \\ Predicted", cm_out.index)

    # --- 5. Confidence audit ---
    agreement = sum(r == t for r, t in zip(rules["A"], m0["tfidf"]))
    override_scores = [m0["tfidf_score"][i] for i in range(n) if rules["A"][i] != m0["tfidf"][i]]
    tfidf_classes = set(tfidf_model.classes_)
    missing_class_rows = [r for r in rules["A"] if r not in tfidf_classes]
    mod_fired = [(c, r) for c, r in zip(case_rows, mod_rules) if r is not None]
    mod_bad = [c["Case"] for c in case_rows if c["Rule Fired"] != NO_RULE
               and c["Auditor Expectation"].startswith(("CONFLICT", "AMBIGUOUS"))
               and not c["Assessment"].startswith("Followed field evidence")]
    mod_unflagged = [c["Case"] for c in case_rows if c["Rule Fired"] != NO_RULE
                     and c["Auditor Expectation"].startswith(("CONFLICT", "AMBIGUOUS"))]
    confidence_items = [
        ("Original rule confidence assignment",
         "evaluate_workbook.py (HEAD) line 152: conf = 1.0 if applied else b_score",
         "A constant assigned whenever any rule matches; not estimated from data."),
        ("Original rows with Prediction Confidence = 1.0",
         int((report["Prediction Confidence"] == 1.0).sum()), "All of them have Applied Rule = True / RULE_VERIFIED."),
        ("Original rows with Prediction Status = RULE_VERIFIED",
         int((report["Prediction Status"] == "RULE_VERIFIED").sum()), "'Verified' overstates a prefix/field-presence match."),
        ("Rule matches where TF-IDF predicted the same category", f"{agreement} of {n}",
         "The model and the rule disagree on most rows; the 1.0 hid this."),
        ("TF-IDF uncalibrated score on rows the rules overrode (mean)",
         round(float(np.mean(override_scores)), 4) if override_scores else None, "Max class probability, not calibrated."),
        ("Rule categories absent from the TF-IDF class list",
         f"{', '.join(sorted(set(missing_class_rows))) or 'none'} ({len(missing_class_rows)} rows)",
         "The model can never assign this category, so no model probability exists for these rule decisions."),
        ("Rule precision on the workbook (A)", f"{config_scores[('A', 'none')]['correct']} of {sum(r is not None for r in rules['A'])}",
         "Measured on the template the rules were written alongside; not a probability for new data."),
        ("Rule matches on modified records", f"{len(mod_fired)} of {len(case_rows)} cases",
         f"Conflicting or ambiguous records decided by a rule without any flag: {', '.join(mod_unflagged) or 'none'}; "
         f"of these, decided by an identifier prefix or by rule order rather than by the field evidence: "
         f"{', '.join(mod_bad) or 'none'}. "
         "Each would have been reported with confidence 1.0 / RULE_VERIFIED."),
        ("TF-IDF mean uncalibrated score vs accuracy (workbook)",
         f"{np.mean(m0['tfidf_score']):.4f} vs {mapping['TF-IDF Baseline Alone']['accuracy']:.4f}",
         "Mean score far below accuracy: the scores are not calibrated to this data."),
        ("DE V2 mean uncalibrated score vs accuracy (workbook)",
         f"{np.mean(m0['de_score']):.4f} vs {mapping['Dual Encoder V2 Alone']['accuracy']:.4f}",
         "Mean score above accuracy: over-confident on this data; also not calibrated."),
        ("Corrected representation",
         "Decision Source, Rule Matched, Decision Status (RULE_MATCH / MODEL_PREDICTION / MODEL_LOW_SCORE / MODEL_NO_SCORE), "
         "Model Prediction, Model Score (Uncalibrated), Rule Overrode Model",
         "No probability is reported for rule decisions; the model's own score is kept and labelled uncalibrated."),
    ]
    if DECISION_STATUS_PREDICTIONS.exists():
        corrected = pd.read_excel(DECISION_STATUS_PREDICTIONS)
        same = int((corrected["Predicted Voucher Category"].astype(str).values
                    == report["Predicted Voucher Category"].astype(str).values).sum())
        confidence_items.append((
            "Corrected report", DECISION_STATUS_PREDICTIONS.name,
            f"Predictions identical to original report on {same} of {n} rows; 'Prediction Confidence' column present: "
            f"{'Prediction Confidence' in corrected.columns}; Decision Status counts: "
            f"{corrected['Decision Status'].value_counts().to_dict()}"))
    confidence = pd.DataFrame(confidence_items, columns=["Item", "Value", "Interpretation"])

    # --- 4. Leakage and template analysis ---
    leakage = leakage_checks(X, y_holdout, tfidf_model)
    signatures, sig_stats = schema_signatures(X, y_holdout)
    id_patterns, other_id_like = identifier_patterns(X, y_holdout)

    readme = pd.DataFrame([
        ("Purpose", "Audit of the reported 100% rule-based accuracy on Voucher_Classification_Test_Cases_v2.xlsx."),
        ("Generated by", "python -m vyom.rule_audit (src/vyom/rule_audit.py). Models, workbook and existing reports are read only."),
        ("Label handling", "All predictions are generated from transaction fields only (Voucher Category removed by "
                           "load_evaluation_workbook). Ground truth is joined afterwards, for scoring only."),
        ("Rule trace fidelity", "Rules are traced with a clause-level mirror of rule_engine.py. The mirror's prediction "
                                "is asserted equal to evaluate_transaction_rules on the workbook, on configurations C and D, "
                                "on the modified records, and (for B and E) on equivalently neutralized inputs."),
        ("Own-ID columns", ", ".join(OWN_ID_COLUMNS)),
        ("Reference-ID columns", ", ".join(REFERENCE_ID_COLUMNS)),
        ("Other ID-like columns (not altered)", ", ".join(other_id_like) or "none"),
        ("Neutralization", "Identifier value -> 'DOC-' + its digit groups (e.g. RJN-IN-516405 -> DOC-516405). "
                           "'DOC-' matches none of the prefixes tested by the engine."),
        ("Macro-F1 convention", "Average over the union of true and predicted labels (sklearn default, as in the "
                                "original evaluation). 'Unclassified' counts as a label in rules-only rows."),
        ("Rule_Inventory", "Every rule: exact condition, fields read, evidence type, override behaviour, firing counts."),
        ("Rule_Trace", "All 120 records under configuration A with model outputs, rule, triggering evidence and correctness."),
        ("Ablation_Metrics", "Configurations A-E and model-only baselines (same as rule_ablation_metrics.csv)."),
        ("Ablation_Rows", "Per-record predictions under every configuration."),
        ("Modified_Records", "Controlled edits of selected records and how the rules respond."),
        ("Leakage_Checks", "Static and dynamic checks for label, output, ordering and lookup leakage."),
        ("Metric_Verification", "Independent recomputation of the reported metrics and alignment checks."),
        ("Per_Class", "Per-class precision/recall/F1 for key configurations."),
        ("Confusion_A", "Confusion matrix of the reported pipeline (TF-IDF + rules), recomputed."),
        ("Confidence_Audit", "What the reported 1.0 confidence means and the corrected representation."),
        ("Schema_Signatures", "Populated-column sets per category in the workbook."),
        ("Identifier_Patterns", "Identifier prefixes per column and which categories they occur in."),
    ], columns=["Item", "Detail"])

    sheets = [
        ("README", readme), ("Rule_Inventory", inventory), ("Rule_Trace", trace),
        ("Ablation_Metrics", ablation), ("Ablation_Rows", row_ablation), ("Modified_Records", cases),
        ("Leakage_Checks", leakage), ("Metric_Verification", verification), ("Per_Class", per_class),
        ("Confusion_A", cm_out), ("Confidence_Audit", confidence), ("Schema_Signatures", signatures),
        ("Identifier_Patterns", id_patterns),
    ]
    write_audit_workbook(AUDIT_XLSX, sheets)

    facts = {
        "records": n,
        "reported_vs_recomputed_pass": bool((verification.Status == "PASS").all()),
        "rules_fired_A": sum(r is not None for r in rules["A"]),
        "prefix_dependent_rows_A": prefix_only_rows,
        "own_prefix_only_rows_A": own_only_rows,
        "multiple_rule_matches_A": int((trace["Multiple Rules Matched"] == "Yes").sum()),
        "tfidf_overridden_A": int((trace["Overrode TF-IDF Prediction"] == "Yes").sum()),
        "de_overridden_A": int((trace["Overrode DE V2 Prediction"] == "Yes").sum()),
        "fired_counts_A": fired_counts,
        "signatures": sig_stats,
        "other_id_like_columns": other_id_like,
        "leakage_status": leakage.set_index("Check")["Status"].to_dict(),
        "verification_fail": verification[verification.Status != "PASS"].to_dict("records"),
        "ablation": ablation[["config_id", "fallback_model", "rules_fired", "rules_fired_correct", "correct",
                              "accuracy", "macro_f1", "weighted_f1", "changed_vs_A"]].to_dict("records"),
        "cases": cases[["Case", "Auditor Expectation", "Rule Fired", "Satisfied Clause Types",
                        "Final (TF-IDF + Rules)", "Final (DE V2 + Rules)", "Assessment"]].to_dict("records"),
        "confidence": confidence.to_dict("records"),
    }
    if args.facts:
        Path(args.facts).write_text(json.dumps(facts, indent=2, default=str), encoding="utf-8")

    print(ablation.to_string(index=False))
    print(f"\nSaved {AUDIT_XLSX}\nSaved {ABLATION_CSV}")


def write_audit_workbook(path: Path, sheets):
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, frame in sheets:
            frame.to_excel(writer, sheet_name=name, index=False)
    wb = load_workbook(path)
    header_fill = PatternFill("solid", fgColor="1F3864")
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                cell.font = Font(name="Arial", size=10, bold=cell.row == 1, color="FFFFFF" if cell.row == 1 else "000000")
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        for cell in ws[1]:
            cell.fill = header_fill
        for idx, col in enumerate(ws.columns, start=1):
            longest = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[get_column_letter(idx)].width = max(10, min(longest + 2, 70))
        ws.freeze_panes = "A2"
        if ws.max_row > 1:
            ws.auto_filter.ref = ws.dimensions
    wb.save(path)


if __name__ == "__main__":
    main()
