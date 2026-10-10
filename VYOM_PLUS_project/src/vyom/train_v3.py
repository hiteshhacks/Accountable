"""VYOM+ V3 experimental training and evaluation (synthetic data only).

Trains on data/synthetic/synthetic_voucher_dataset_v5_review_ready.xlsx
(sheet model_inputs_no_label, labels from labelled_data_review). The labels are
unverified synthetic labels. The evaluation workbook is never read.

Evaluation is 5-fold StratifiedGroupKFold grouped by narration sentence (the
narration with its generated reference/date suffix removed), so every test row
has a narration sentence never seen in training. Item descriptions and other
categorical vocabularies cannot be held out at the same time; results describe
recovery of synthetic labels from this generator, not real-world accuracy.

Outputs go to new report files and are refused if they already exist. No model
artifact is saved: every available split leaves some generator vocabulary shared
between train and test (see reports/v3_experiment_summary.md), so a saved
classifier would have no defensible performance estimate.
"""

from pathlib import Path
import argparse
import hashlib
import pickle
import re

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline

from vyom.features_v3 import (
    CONTRACT_FIELDS,
    CONTRACT_VERSION,
    EXCLUDED_FIELDS,
    ContractTabular,
    ContractTokens,
)
from vyom.preprocessing import make_text
from vyom.rule_engine import assess_transaction


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data/synthetic/synthetic_voucher_dataset_v5_review_ready.xlsx"
COMPARISON = ROOT / "data/synthetic/VYOM_plus_reviewer_comparison_adjudication.xlsx"
EXISTING_TFIDF = ROOT / "models/vyom_plus_tfidf_baseline_model.pkl"

METRICS_CSV = ROOT / "reports/v3_cv_metrics.csv"
DETAILS_XLSX = ROOT / "reports/v3_experiment_details.xlsx"

SEED = 42
N_FOLDS = 5
PRIMARY = "v3_field_tfidf_all"

# Classes kept out of training, with the reason. Decided from the label
# guidelines and the reviewer study, not from any evaluation labels.
EXCLUDED_CLASSES = {
    "Other / Miscellaneous": "Guideline defines it as abstention/manual review; 0/20 reviewed rows supported "
                             "by either reviewer. Not learned as a class; route to review instead.",
}

ALL_GROUPS = ("narration", "item", "categorical", "presence", "relationships")


# ==========================================
# DATA
# ==========================================

def narration_core(text) -> str:
    """Narration without its generated reference/date sentence, digits masked."""
    s = str(text)
    m = re.search(r"TXN-\d+", s)
    if m:
        s = s[:s.rfind(".", 0, m.start()) + 1]
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", s)).strip().lower()


def load_training_data():
    """Model inputs, synthetic labels and split groups; inputs never contain label columns."""
    inputs = pd.read_excel(DATASET, sheet_name="model_inputs_no_label")
    labelled = pd.read_excel(DATASET, sheet_name="labelled_data_review")
    if not (inputs.astype(str).values == labelled[list(inputs.columns)].astype(str).values).all():
        raise ValueError("model_inputs_no_label is not row-aligned with labelled_data_review")
    # transaction_date is present but ignored by the contract; label-bearing fields must be absent.
    leaked = set(inputs.columns) & (set(EXCLUDED_FIELDS) - {"transaction_date"})
    if leaked:
        raise ValueError(f"Label-bearing fields present in model inputs: {sorted(leaked)}")
    meta = pd.DataFrame({
        "record_id": labelled["record_id"],
        "split_group": labelled["split_group"],
        "core": labelled["transaction_narration"].map(narration_core),
        "label": labelled["voucher_type"].astype(str).str.strip(),
        "document_type": labelled["document_type"],
    })
    meta["core_id"] = meta["core"].astype("category").cat.codes
    return inputs, meta


def shared_vocabulary_components(inputs: pd.DataFrame, meta: pd.DataFrame) -> pd.Series:
    """Rows linked by a shared narration sentence, payment_status or item_description.

    One component per class means no split can give a class test rows whose
    narration, status and item are all unseen in training.
    """
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    keys = list(zip(meta["core"], inputs["payment_status"].astype(str).str.strip().str.lower(),
                    inputs["item_description"].astype(str).str.strip().str.lower()))
    for core, status, item in keys:
        root = find(("core", core))
        parent[find(("status", status))] = root
        parent[find(("item", item))] = root
    return pd.Series([find(("core", core)) for core, _, _ in keys], index=meta.index)


def label_quality(meta: pd.DataFrame) -> pd.DataFrame:
    """Per-class agreement of the two reviewers with the synthetic label (540 reviewed rows)."""
    queue = pd.read_excel(DATASET, sheet_name="human_review_queue")
    consensus = pd.read_excel(COMPARISON, sheet_name="Provisional_Consensus")
    reviewed = pd.concat([consensus, pd.read_excel(COMPARISON, sheet_name="Adjudication_Queue")], ignore_index=True)
    for frame in (consensus, reviewed):
        frame["qi"] = frame["review_case_id"].str.extract(r"HR-(\d+)")[0].astype(int) - 1
        frame["synthetic"] = queue["voucher_type"].iloc[frame["qi"]].values
    reviewed["r1"] = reviewed["reviewer_1_label"] == reviewed["synthetic"]
    reviewed["r2"] = reviewed["reviewer_2_label"] == reviewed["synthetic"]
    table = reviewed.groupby("synthetic").agg(reviewed=("qi", "size"), reviewer_1_agrees=("r1", "sum"),
                                              reviewer_2_agrees=("r2", "sum"))
    table["provisional_consensus"] = consensus.groupby("synthetic").size().reindex(table.index).fillna(0).astype(int)
    table["synthetic_rows"] = meta["label"].value_counts().reindex(table.index).fillna(0).astype(int)
    return table.reset_index().rename(columns={"synthetic": "class"})


# ==========================================
# MODELS
# ==========================================

def v1_recipe():
    """The existing TF-IDF baseline recipe (train_baseline.py), refitted per fold."""
    return Pipeline([
        ("features", FeatureUnion([
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, max_features=100000)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, max_features=100000)),
        ])),
        ("clf", LogisticRegression(max_iter=3000, class_weight="balanced", C=2.0, random_state=SEED)),
    ])


def field_tfidf(groups=ALL_GROUPS):
    return Pipeline([
        ("contract", ContractTokens(groups=tuple(groups))),
        ("tfidf", TfidfVectorizer(token_pattern=r"\S+", ngram_range=(1, 2), sublinear_tf=True, min_df=2)),
        ("clf", LogisticRegression(max_iter=3000, class_weight="balanced", C=2.0, random_state=SEED)),
    ])


def tabular(include_item=False, categorical=True, numeric=True, relationships=True):
    features = ContractTabular(include_item=include_item, categorical=categorical, numeric=numeric,
                               relationships=relationships)
    return Pipeline([
        ("contract", features),
        ("clf", HistGradientBoostingClassifier(categorical_features=features.categorical_mask(),
                                               class_weight="balanced", early_stopping=False,
                                               max_iter=200, random_state=SEED)),
    ])


def presence_only():
    features = ContractTabular(include_item=False, categorical=False, numeric=False, relationships=False)
    return Pipeline([
        ("contract", features),
        ("clf", HistGradientBoostingClassifier(class_weight="balanced", early_stopping=False,
                                               max_iter=200, random_state=SEED)),
    ])


# (name, description, builder, input view). Views: "contract" = model_inputs_no_label;
# "v1_text" / "v1_text_no_doc_type" = make_text over canonical fields as in train_baseline.py.
EXPERIMENTS = [
    ("v1_recipe_with_document_type", "Existing TF-IDF recipe, inputs as in train_baseline.py (includes document_type)",
     v1_recipe, "v1_text"),
    ("v1_recipe_without_document_type", "Existing TF-IDF recipe without the document_type label proxy",
     v1_recipe, "v1_text_no_doc_type"),
    (PRIMARY, "Field-aware TF-IDF + LR, all contract groups (pre-specified primary)",
     lambda: field_tfidf(ALL_GROUPS), "contract"),
    ("v3_field_tfidf_narration_only", "Field-aware TF-IDF + LR, narration only",
     lambda: field_tfidf(("narration",)), "contract"),
    ("v3_field_tfidf_no_narration", "Field-aware TF-IDF + LR without narration",
     lambda: field_tfidf(("item", "categorical", "presence", "relationships")), "contract"),
    ("v3_tabular_structured", "HistGradientBoosting: categorical + numeric + presence + relationships, no text",
     lambda: tabular(include_item=False), "contract"),
    ("v3_tabular_structured_item", "HistGradientBoosting: structured fields + item_description",
     lambda: tabular(include_item=True), "contract"),
    ("v3_numeric_presence_only", "HistGradientBoosting: numeric + presence + relationships (no categorical, no text)",
     lambda: tabular(include_item=False, categorical=False), "contract"),
    ("v3_presence_only", "HistGradientBoosting: field-presence flags only (layout baseline)",
     presence_only, "contract"),
]


def view(name, inputs, meta):
    if name == "contract":
        return inputs
    frame = inputs.copy()
    if name == "v1_text":
        frame["document_type"] = meta["document_type"].values
    return frame.apply(make_text, axis=1)


def cross_validate(build, X, y, groups, splitter):
    oof = np.empty(len(y), dtype=object)
    for train_idx, test_idx in splitter.split(np.zeros(len(y)), y, groups):
        model = build()
        model.fit(X.iloc[train_idx], y[train_idx])
        oof[test_idx] = model.predict(X.iloc[test_idx])
    return oof


def summarise(name, scheme, y, pred, description=""):
    labels = sorted(set(y))
    rep = classification_report(y, pred, labels=labels, output_dict=True, zero_division=0)
    recalls = [rep[c]["recall"] for c in labels]
    return {
        "model": name, "split": scheme, "description": description, "n_records": len(y),
        "n_classes": len(labels), "correct": int((np.asarray(pred) == np.asarray(y)).sum()),
        "accuracy": round(accuracy_score(y, pred), 4),
        "macro_f1": round(f1_score(y, pred, labels=labels, average="macro", zero_division=0), 4),
        "weighted_f1": round(f1_score(y, pred, labels=labels, average="weighted", zero_division=0), 4),
        "classes_recall_ge_0_8": int(sum(r >= 0.8 for r in recalls)),
        "classes_recall_eq_0": int(sum(r == 0 for r in recalls)),
    }


# ==========================================
# MAIN
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Evaluate experimental VYOM+ V3 feature sets on synthetic data (reports only).")
    parser.parse_args()

    existing = [str(p) for p in (METRICS_CSV, DETAILS_XLSX) if p.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite: {', '.join(existing)}")

    inputs, meta = load_training_data()
    keep = ~meta["label"].isin(EXCLUDED_CLASSES)
    X_all, meta_all = inputs, meta
    X, m = inputs[keep].reset_index(drop=True), meta[keep].reset_index(drop=True)
    y = m["label"].to_numpy()
    print(f"Training rows: {len(X)} of {len(inputs)} ({len(set(y))} classes); excluded: {sorted(EXCLUDED_CLASSES)}")

    sgkf = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    schemes = {"narration_sentence_grouped": (sgkf, m["core_id"].to_numpy())}
    # The split used by the existing training scripts, for comparison only.
    schemes["split_group_grouped"] = (GroupKFold(n_splits=N_FOLDS), m["split_group"].to_numpy())
    # Diagnostics: test rows carry a status value / item description never seen in training.
    schemes["status_value_grouped"] = (sgkf, X["payment_status"].astype(str).str.strip().str.lower().to_numpy())
    schemes["item_value_grouped"] = (sgkf, X["item_description"].astype(str).str.strip().str.lower().to_numpy())
    diagnostic_models = {PRIMARY, "v1_recipe_without_document_type", "v3_tabular_structured", "v3_tabular_structured_item"}

    rows, oof_store = [], {}
    for name, description, build, view_name in EXPERIMENTS:
        Xv = view(view_name, X, m)
        for scheme, (splitter, groups) in schemes.items():
            if scheme == "split_group_grouped" and name not in (PRIMARY, "v1_recipe_with_document_type"):
                continue
            if scheme in ("status_value_grouped", "item_value_grouped") and name not in diagnostic_models:
                continue
            pred = cross_validate(build, Xv, y, groups, splitter)
            oof_store[(name, scheme)] = pred
            rows.append(summarise(name, scheme, y, pred, description))
            print(f"{name:34s} {scheme:28s} acc={rows[-1]['accuracy']:.4f} macroF1={rows[-1]['macro_f1']:.4f}")

    # Existing artifact on rows it never trained on (outside the 540-row review queue).
    queue_ids = set(pd.read_excel(DATASET, sheet_name="human_review_queue")["record_id"])
    outside = ~meta_all["record_id"].isin(queue_ids)
    with open(EXISTING_TFIDF, "rb") as f:
        existing_model = pickle.load(f)
    text_v1 = view("v1_text", X_all[outside].reset_index(drop=True), meta_all[outside].reset_index(drop=True))
    y_out = meta_all.loc[outside, "label"].to_numpy()
    pred_existing = existing_model.predict(text_v1)
    rows.append(summarise("existing_tfidf_artifact", "rows_outside_review_queue", y_out, pred_existing,
                          "models/vyom_plus_tfidf_baseline_model.pkl as saved (25 classes); includes Other / Miscellaneous rows"))

    metrics = pd.DataFrame(rows)

    # Rule engine on canonical records: technical applicability check.
    statuses = pd.Series([assess_transaction(X_all.iloc[i]).status for i in range(len(X_all))]).value_counts()

    # Per-class results.
    primary_pred = oof_store[(PRIMARY, "narration_sentence_grouped")]
    labels = sorted(set(y))
    per_class_rows = []
    for name, _, _, _ in EXPERIMENTS:
        rep = classification_report(y, oof_store[(name, "narration_sentence_grouped")], labels=labels,
                                    output_dict=True, zero_division=0)
        for c in labels:
            per_class_rows.append({"model": name, "class": c, **{k: round(rep[c][k], 4) for k in ("precision", "recall", "f1-score")},
                                   "support": int(rep[c]["support"])})
    per_class = pd.DataFrame(per_class_rows)
    cm = pd.DataFrame(confusion_matrix(y, primary_pred, labels=labels), index=labels, columns=labels)
    cm.insert(0, "true \\ predicted", cm.index)

    quality = label_quality(meta_all)
    prim = per_class[per_class.model == PRIMARY].set_index("class")
    struct = per_class[per_class.model == "v3_tabular_structured"].set_index("class")
    status_rows = []
    for _, q in quality.iterrows():
        c = q["class"]
        disputed = min(q.reviewer_1_agrees, q.reviewer_2_agrees) < 0.75 * q.reviewed
        if c in EXCLUDED_CLASSES:
            status, note = "Not trained", EXCLUDED_CLASSES[c]
        elif prim.loc[c, "recall"] >= 0.8:
            status = "Recovered on unseen synthetic sentences" + (" (label disputed by a reviewer)" if disputed else "")
            note = ""
        else:
            status = "Not reliably recovered" + (" (label disputed by a reviewer)" if disputed else "")
            note = ""
        status_rows.append({
            "class": c, "synthetic_rows": q.synthetic_rows, "reviewed": q.reviewed,
            "reviewer_1_agrees": q.reviewer_1_agrees, "reviewer_2_agrees": q.reviewer_2_agrees,
            "provisional_consensus": q.provisional_consensus,
            "primary_recall": None if c in EXCLUDED_CLASSES else prim.loc[c, "recall"],
            "primary_f1": None if c in EXCLUDED_CLASSES else prim.loc[c, "f1-score"],
            "structured_only_f1": None if c in EXCLUDED_CLASSES else struct.loc[c, "f1-score"],
            "status": status, "note": note,
        })
    class_status = pd.DataFrame(status_rows).sort_values("class")

    groups_per_class = m.groupby("label").agg(narration_sentences=("core_id", "nunique"),
                                              split_groups=("split_group", "nunique")).reset_index()
    audit = pd.DataFrame([
        ("Training file", str(DATASET.relative_to(ROOT))),
        ("Training file sha256", hashlib.sha256(DATASET.read_bytes()).hexdigest()),
        ("Input sheet", "model_inputs_no_label (30 canonical fields; document_type and audit columns excluded by the dataset)"),
        ("Label source", "labelled_data_review.voucher_type - UNVERIFIED_SYNTHETIC_LABEL on all 5,400 rows"),
        ("Rows / classes", f"{len(X_all)} rows, {meta_all['label'].nunique()} classes, 200 per class"),
        ("Rows used for training", f"{len(X)} ({len(set(y))} classes; excluded {sorted(EXCLUDED_CLASSES)})"),
        ("Distinct narration sentences (suffix removed)", int(meta_all["core"].nunique())),
        ("Narration sentences shared across split_groups", int(meta_all.groupby("core")["split_group"].nunique().gt(1).sum())),
        ("Classes forming a single shared-vocabulary component (sentence/status/item)",
         f"{int(shared_vocabulary_components(X_all, meta_all).groupby(meta_all['label']).nunique().eq(1).sum())} of "
         f"{meta_all['label'].nunique()}"),
        ("Rule engine statuses on canonical records", statuses.to_dict()),
        ("Contract version", CONTRACT_VERSION),
        ("Contract fields", ", ".join(CONTRACT_FIELDS)),
        ("Excluded fields", ", ".join(EXCLUDED_FIELDS)),
        ("Evaluation workbook", "Not read by this script"),
    ], columns=["Item", "Value"])

    metrics.to_csv(METRICS_CSV, index=False)
    with pd.ExcelWriter(DETAILS_XLSX, engine="openpyxl") as writer:
        audit.to_excel(writer, sheet_name="Audit", index=False)
        metrics.to_excel(writer, sheet_name="CV_Metrics", index=False)
        class_status.to_excel(writer, sheet_name="Class_Status", index=False)
        quality.to_excel(writer, sheet_name="Label_Quality", index=False)
        per_class.to_excel(writer, sheet_name="Per_Class", index=False)
        cm.to_excel(writer, sheet_name="Confusion_Primary", index=False)
        groups_per_class.to_excel(writer, sheet_name="Split_Groups", index=False)
    print(f"Saved {METRICS_CSV}\nSaved {DETAILS_XLSX}")
    print(class_status[["class", "primary_recall", "structured_only_f1", "status"]].to_string(index=False))
    print("Rule statuses on canonical records:", statuses.to_dict())


if __name__ == "__main__":
    main()
