"""VYOM+ TF-IDF + Logistic Regression baseline v2 (27 classes, synthetic data).

Training data: data/synthetic/synthetic_voucher_dataset_v5_review_ready.xlsx
(sheet model_inputs_no_label; labels from labelled_data_review, all
UNVERIFIED_SYNTHETIC_LABEL). The 111 records flagged needs_adjudication in
VYOM_plus_reviewer_comparison_adjudication.xlsx are excluded. The evaluation
workbook is never read.

Features: the V3 feature contract (vyom.features_v3): field-tagged tokens from
narration, item, categorical, presence and relationship features, optionally plus
character n-grams of the masked narration and item text; identifiers and party
names contribute presence only; document_type and dates are excluded.

Split: a per-class group holdout. For every class, whole narration-sentence
groups are drawn at random until about 20% of its rows are held out (at least one
group per class), so all 27 classes are tested on narration sentences never seen
in training. The representation and C are chosen by grouped 5-fold CV on the
training part only. The saved model is the one evaluated on the test split.

Every output is a new file; existing files are never overwritten. Metrics measure
recovery of synthetic labels from this generator, not real-world accuracy.
"""

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import pickle
import platform
import subprocess

import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline

from vyom.features_v3 import (
    CONTRACT_FIELDS,
    CONTRACT_VERSION,
    EXCLUDED_FIELDS,
    ContractText,
    ContractTokens,
    field_tokens,
    prepare_frame,
)
from vyom.train_v3 import load_training_data, v1_recipe, view


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data/synthetic/synthetic_voucher_dataset_v5_review_ready.xlsx"
COMPARISON = ROOT / "data/synthetic/VYOM_plus_reviewer_comparison_adjudication.xlsx"
EXISTING_MODEL = ROOT / "models/vyom_plus_tfidf_baseline_model.pkl"

MODEL_PATH = ROOT / "models/vyom_plus_tfidf_baseline_v2.pkl"
CONFIG_PATH = ROOT / "models/vyom_plus_tfidf_baseline_v2_config.json"
LABELS_PATH = ROOT / "models/vyom_plus_tfidf_baseline_v2_labels.json"
METRICS_PATH = ROOT / "reports/tfidf_baseline_v2_metrics.json"
CLASS_REPORT_PATH = ROOT / "reports/tfidf_baseline_v2_classification_report.csv"
CONFUSION_PATH = ROOT / "reports/tfidf_baseline_v2_confusion_matrix.csv"
PREDICTIONS_PATH = ROOT / "reports/tfidf_baseline_v2_predictions.xlsx"
REPORT_PATH = ROOT / "reports/tfidf_baseline_v2_report.md"
OUTPUTS = [MODEL_PATH, CONFIG_PATH, LABELS_PATH, METRICS_PATH, CLASS_REPORT_PATH, CONFUSION_PATH,
           PREDICTIONS_PATH, REPORT_PATH]

SEED = 42
N_FOLDS = 5
TEST_SHARE = 0.2
STABILITY_SEEDS = tuple(range(101, 111))
C_GRID = (0.5, 1.0, 2.0, 4.0, 8.0)
FEATURE_GROUPS = ("narration", "item", "categorical", "presence", "relationships")
REPRESENTATIONS = {
    "field_words": "field-tagged word uni/bi-grams over the contract (narration, item, categorical, presence, relationships)",
    "field_words+text_chars": "field_words plus character 3-5-grams over the masked narration and item text",
}

# Labels whose predictions must go to human review regardless of model score.
REVIEW_ROUTE = {"Other / Miscellaneous"}

# Per-class caveats from the reviewer study and the open definition issues
# (reports/vyom_label_definition_gaps.md). They do not change any label.
CLASS_NOTES = {
    "Other / Miscellaneous": "Policy undecided (DEF-10: voucher class or review status). Kept as a class so the taxonomy "
                             "is complete; its examples are generator records marked unclear / pending review. "
                             "Predictions are routed to human review. Missing from the v1 artifact.",
    "Rejection In": "Direction convention disputed (DEF-01). 18 of its 20 reviewed rows are disputed and excluded; "
                    "trained on synthetic labels that follow guideline v5. Missing from the v1 artifact.",
    "Rejection Out": "Direction convention disputed (DEF-01, DEF-02).",
    "Purchase Return / Debit Note": "Boundary with Payment and Rejection In disputed (DEF-02, DEF-04).",
    "Sales Return / Credit Note": "Evidence requirement disputed (DEF-03).",
    "Contra": "Same-entity evidence rule unresolved (DEF-05).",
    "Advance / Prepayment": "Direction policy unresolved (DEF-07).",
    "Material In": "Scope disputed: internal movement vs subcontracting (DEF-08).",
    "Material Out": "Scope disputed: internal movement vs subcontracting (DEF-08).",
    "Job Work In Order": "Definition provisional (DEF-09).",
    "Job Work Out Order": "Definition provisional (DEF-09).",
    "Payment": "Boundary with Expense / Debit Note unresolved (DEF-04, DEF-06).",
    "Expense": "Boundary with Payment / Purchase unresolved (DEF-06).",
    "Purchase": "Consumables policy unresolved (DEF-06).",
}

CAVEAT = ("Trained and evaluated on unverified synthetic labels from one generator. Test rows have unseen narration "
          "sentences, but item, status and other field vocabularies are shared with training, so these metrics "
          "measure recovery of synthetic labels, not accuracy on real transactions.")

DISCLOSURE = ("A first run (StratifiedGroupKFold fold 0 as the test split, word features only) was discarded because its "
              "test split contained no Job Work In Order or Advance / Prepayment rows. That run's test comparison also "
              "showed character n-grams helping, which is why the field_words+text_chars candidate was added. The final "
              "split was redrawn per class, and the representation and C were chosen by training-part CV only.")


# ==========================================
# DATA
# ==========================================

def taxonomy():
    """The 27 voucher categories, in the order of the official label guidelines."""
    return pd.read_excel(DATASET, sheet_name="label_guidelines_v5")["voucher_type"].astype(str).str.strip().tolist()


def disputed_record_ids():
    """Record IDs of the records flagged needs_adjudication in the reviewer comparison."""
    adj = pd.read_excel(COMPARISON, sheet_name="Adjudication_Queue")
    adj = adj[adj["needs_adjudication"] == True]  # noqa: E712 - explicit boolean column
    queue = pd.read_excel(DATASET, sheet_name="human_review_queue")
    rows = adj["review_case_id"].str.extract(r"HR-(\d+)")[0].astype(int) - 1
    return set(queue["record_id"].iloc[rows])


def reviewed_record_ids():
    return set(pd.read_excel(DATASET, sheet_name="human_review_queue")["record_id"])


def load_eligible():
    """Model inputs and metadata for every labelled row except the disputed records."""
    inputs, meta = load_training_data()
    disputed = disputed_record_ids()
    keep = ~meta["record_id"].isin(disputed)
    X, m = inputs[keep].reset_index(drop=True), meta[keep].reset_index(drop=True)
    unknown = set(m["label"]) - set(taxonomy())
    if unknown:
        raise ValueError(f"Labels outside the 27-category taxonomy: {sorted(unknown)}")
    return X, m, disputed


def contract_tokens(X):
    return field_tokens(prepare_frame(X), FEATURE_GROUPS)


NEAR_DUPLICATE_DROP = ["transaction_date", "invoice_number", "taxable_value", "gst_amount", "unit_price",
                       "quantity", "transaction_narration"]


def audit(X, m, disputed, tokens):
    tok = pd.DataFrame({"tok": tokens.values, "y": m["label"].values})
    near = X.drop(columns=NEAR_DUPLICATE_DROP).astype(str)
    return {
        "eligible_rows": int(len(X)),
        "excluded_disputed_rows": int(len(disputed)),
        "classes": int(m["label"].nunique()),
        "rows_per_class": m["label"].value_counts().sort_index().to_dict(),
        "exact_duplicate_rows": int(X.astype(str).duplicated().sum()),
        "identical_model_inputs_rows": int(tok["tok"].duplicated().sum()),
        "identical_inputs_with_conflicting_labels": int(tok.groupby("tok")["y"].nunique().gt(1).sum()),
        "near_duplicate_rows_except_narration_dates_ids_amounts": int(near.duplicated().sum()),
        "missing_rate_by_field": X.isna().mean().round(3).to_dict(),
        "narration_sentences": int(m["core_id"].nunique()),
        "narration_sentences_per_class_min": int(m.groupby("label")["core_id"].nunique().min()),
        "narration_sentences_shared_across_split_groups": int(m.groupby("core")["split_group"].nunique().gt(1).sum()),
        "label_source": "UNVERIFIED_SYNTHETIC_LABEL",
        "document_type_excluded": "document_type maps 1:1 to the label for 15 classes; not a model input",
    }


def split(m, tokens, seed=SEED):
    """Per-class group holdout by narration sentence; identical inputs never cross the split."""
    if m.groupby("core_id")["label"].nunique().max() > 1:
        raise AssertionError("A narration sentence belongs to more than one class")
    rng = np.random.default_rng(seed)
    test_groups = set()
    for label in sorted(m["label"].unique()):
        sizes = m.loc[m["label"] == label].groupby("core_id").size()
        if len(sizes) < 2:
            raise ValueError(f"{label} has fewer than two narration groups; cannot hold one out")
        held, taken = [], 0
        for group in rng.permutation(sizes.index.to_numpy()):
            if taken >= TEST_SHARE * sizes.sum() or len(held) == len(sizes) - 1:
                break
            held.append(group)
            taken += sizes[group]
        test_groups.update(held)
    is_test = m["core_id"].isin(test_groups).to_numpy()
    train_idx, test_idx = np.flatnonzero(~is_test), np.flatnonzero(is_test)
    if set(m["core_id"].iloc[train_idx]) & set(m["core_id"].iloc[test_idx]):
        raise AssertionError("A narration sentence appears in both train and test")
    if set(tokens.iloc[train_idx]) & set(tokens.iloc[test_idx]):
        raise AssertionError("Identical model inputs appear in both train and test")
    return train_idx, test_idx


# ==========================================
# MODEL
# ==========================================

def build_model(C=2.0, representation="field_words"):
    words = Pipeline([
        ("contract", ContractTokens(groups=FEATURE_GROUPS)),
        ("tfidf", TfidfVectorizer(token_pattern=r"\S+", ngram_range=(1, 2), sublinear_tf=True, min_df=2)),
    ])
    if representation == "field_words":
        features = words
    elif representation == "field_words+text_chars":
        chars = Pipeline([
            ("text", ContractText()),
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=2)),
        ])
        features = FeatureUnion([("field_words", words), ("text_chars", chars)])
    else:
        raise ValueError(representation)
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(C=C, max_iter=3000, class_weight="balanced", random_state=SEED)),
    ])


def select_config(X, y, groups):
    """Grouped 5-fold CV on the training part only; returns ((representation, C), scores)."""
    sgkf = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED + 1)
    folds = list(sgkf.split(np.zeros(len(y)), y, groups))
    scores = {}
    for rep in REPRESENTATIONS:
        for C in C_GRID:
            oof = np.empty(len(y), dtype=object)
            for tr, va in folds:
                oof[va] = build_model(C, rep).fit(X.iloc[tr], y[tr]).predict(X.iloc[va])
            scores[(rep, C)] = round(float(f1_score(y, oof, average="macro", zero_division=0)), 4)
            print(f"  CV {rep:24s} C={C:<4} macro-F1={scores[(rep, C)]}")
    # Ties go to the simpler representation, then the smaller C.
    best = max(scores, key=lambda k: (scores[k], -list(REPRESENTATIONS).index(k[0]), -k[1]))
    return best, scores


def metrics_for(y_true, y_pred, labels):
    present = [c for c in labels if c in set(y_true)]
    return {
        "n": int(len(y_true)),
        "correct": int((np.asarray(y_true) == np.asarray(y_pred)).sum()),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, labels=present, average="macro", zero_division=0)), 4),
        "weighted_f1": round(float(f1_score(y_true, y_pred, labels=present, average="weighted", zero_division=0)), 4),
        "classes_in_test": len(present),
    }


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


# ==========================================
# MAIN
# ==========================================

def main():
    argparse.ArgumentParser(description="Train the VYOM+ TF-IDF baseline v2 (writes new files only).").parse_args()
    existing = [str(p) for p in OUTPUTS if p.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite: {', '.join(existing)}")

    labels = taxonomy()
    X, m, disputed = load_eligible()
    tokens = contract_tokens(X)
    data_audit = audit(X, m, disputed, tokens)
    y = m["label"].to_numpy()
    train_idx, test_idx = split(m, tokens)
    for part, idx in (("training", train_idx), ("test", test_idx)):
        missing = sorted(set(labels) - set(y[idx]))
        if missing:
            raise AssertionError(f"Classes absent from the {part} split: {missing}")
    print(f"Eligible rows {len(X)} (excluded {len(disputed)} disputed); train {len(train_idx)}, test {len(test_idx)}")

    X_train, y_train = X.iloc[train_idx], y[train_idx]
    X_test, y_test = X.iloc[test_idx], y[test_idx]
    (best_rep, best_C), cv_scores = select_config(X_train, y_train, m["core_id"].to_numpy()[train_idx])
    print(f"Selected by train-only CV: representation={best_rep}, C={best_C}")

    model = build_model(best_C, best_rep).fit(X_train, y_train)
    if list(model.classes_) != sorted(labels):
        raise AssertionError("Model classes differ from the 27-category taxonomy")
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test).max(axis=1)

    # Stability: the same configuration on other random group holdouts (no re-tuning).
    stability, stability_recall = [], {c: [] for c in labels}
    for seed in STABILITY_SEEDS:
        tr, te = split(m, tokens, seed=seed)
        p = build_model(best_C, best_rep).fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
        stability.append({"seed": seed, **metrics_for(y[te], p, labels)})
        for c in labels:
            stability_recall[c].append(float((p[y[te] == c] == c).mean()))
    stab = pd.DataFrame(stability)
    stability_summary = {k: {"mean": round(float(stab[k].mean()), 4), "std": round(float(stab[k].std()), 4),
                             "min": round(float(stab[k].min()), 4), "max": round(float(stab[k].max()), 4)}
                         for k in ("accuracy", "macro_f1")}
    print(f"Stability over {len(STABILITY_SEEDS)} other group holdouts: {stability_summary}")

    # Comparisons on the same split.
    comparisons = {"tfidf_baseline_v2 (this model)": metrics_for(y_test, pred, labels)}
    for name, view_name in (("v1 recipe refit, with document_type", "v1_text"),
                            ("v1 recipe refit, without document_type", "v1_text_no_doc_type")):
        text = view(view_name, X, m)
        refit = v1_recipe().fit(text.iloc[train_idx], y_train)
        comparisons[name] = metrics_for(y_test, refit.predict(text.iloc[test_idx]), labels)
    with open(EXISTING_MODEL, "rb") as f:
        existing_model = pickle.load(f)
    unseen = ~m["record_id"].iloc[test_idx].isin(reviewed_record_ids()).to_numpy()
    text_v1 = view("v1_text", X, m)
    existing_pred = existing_model.predict(text_v1.iloc[test_idx[unseen]])
    comparisons["existing v1 artifact as saved (25 classes), test rows outside the 540 reviewed"] = {
        **metrics_for(y_test[unseen], existing_pred, labels),
        "missing_classes": sorted(set(labels) - set(existing_model.classes_)),
    }
    comparisons["tfidf_baseline_v2 on those same rows"] = metrics_for(y_test[unseen], pred[unseen], labels)

    report = classification_report(y_test, pred, labels=labels, output_dict=True, zero_division=0)
    class_rows = []
    for c in labels:
        class_rows.append({
            "class": c, "precision": round(report[c]["precision"], 4), "recall": round(report[c]["recall"], 4),
            "f1": round(report[c]["f1-score"], 4), "test_support": int(report[c]["support"]),
            "train_rows": int((y_train == c).sum()), "eligible_rows": int((y == c).sum()),
            "recall_mean_other_holdouts": round(float(np.mean(stability_recall[c])), 4),
            "recall_min_other_holdouts": round(float(np.min(stability_recall[c])), 4),
            "review_route": c in REVIEW_ROUTE, "note": CLASS_NOTES.get(c, ""),
        })
    class_table = pd.DataFrame(class_rows)
    cm = pd.DataFrame(confusion_matrix(y_test, pred, labels=labels), index=labels, columns=labels)
    top_confusions = [
        {"true": t, "predicted": p, "count": int(cm.loc[t, p])}
        for t, p in sorted(((t, p) for t in labels for p in labels if t != p and cm.loc[t, p] > 0),
                           key=lambda tp: -cm.loc[tp[0], tp[1]])[:10]]

    # Near-duplicates (same non-narration fields) that straddle the split: reported, not removed.
    near_key = X.drop(columns=NEAR_DUPLICATE_DROP).astype(str).agg("|".join, axis=1)
    straddle = int(near_key.iloc[test_idx].isin(set(near_key.iloc[train_idx])).sum())

    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    split_info = {
        "method": f"per-class group holdout: whole narration-sentence groups drawn per class until >= {TEST_SHARE:.0%} "
                  f"of its rows (>= 1 group held out, >= 1 kept), numpy default_rng({SEED})",
        "group": "narration sentence (narration with generated reference/date sentence removed, digits masked)",
        "train_rows": int(len(train_idx)), "test_rows": int(len(test_idx)),
        "train_groups": int(m["core_id"].iloc[train_idx].nunique()),
        "test_groups": int(m["core_id"].iloc[test_idx].nunique()),
        "test_rows_sharing_non_narration_fields_with_train": straddle,
    }
    metrics = {
        "model": MODEL_PATH.name, "created_utc": created, "caveat": CAVEAT, "disclosure": DISCLOSURE,
        "split": split_info, "cv_macro_f1": {f"{r}, C={c}": v for (r, c), v in cv_scores.items()},
        "chosen_representation": best_rep, "chosen_C": best_C,
        "test": comparisons["tfidf_baseline_v2 (this model)"], "comparisons": comparisons,
        "stability_other_holdouts": {"seeds": list(STABILITY_SEEDS), "summary": stability_summary, "runs": stability},
        "classes_with_recall_ge_0_8": int((class_table["recall"] >= 0.8).sum()),
        "classes_with_zero_test_support": class_table.loc[class_table.test_support == 0, "class"].tolist(),
        "top_confusions": top_confusions,
        "review_routed_test_predictions": int(np.isin(pred, list(REVIEW_ROUTE)).sum()),
    }
    config = {
        "model": MODEL_PATH.name, "created_utc": created,
        "status": "EXPERIMENTAL BASELINE - unverified synthetic labels; not validated on real transactions",
        "input_schema": "Canonical fields as in data/synthetic model_inputs_no_label; pass a pandas DataFrame; missing "
                        "fields are allowed; extra columns are ignored",
        "preprocessing": {"contract_version": CONTRACT_VERSION, "feature_groups": list(FEATURE_GROUPS),
                          "contract_fields": list(CONTRACT_FIELDS), "excluded_fields": list(EXCLUDED_FIELDS),
                          "identifiers_and_parties": "presence only",
                          "text_masking": "identifier-like tokens -> 'idtoken', digits -> '#', lower-case"},
        "representation": {"name": best_rep, "description": REPRESENTATIONS[best_rep],
                           "field_words": {"type": "TfidfVectorizer", "token_pattern": r"\S+", "ngram_range": [1, 2],
                                           "sublinear_tf": True, "min_df": 2},
                           "text_chars": ({"type": "TfidfVectorizer", "analyzer": "char_wb", "ngram_range": [3, 5],
                                           "sublinear_tf": True, "min_df": 2,
                                           "fields": ["transaction_narration", "item_description"]}
                                          if best_rep == "field_words+text_chars" else None)},
        "classifier": {"type": "LogisticRegression", "C": best_C, "class_weight": "balanced", "max_iter": 3000,
                       "random_state": SEED},
        "hyperparameter_search": {"representations": list(REPRESENTATIONS), "C_grid": list(C_GRID),
                                  "cv": f"StratifiedGroupKFold({N_FOLDS}) on train part only, grouped by narration "
                                        f"sentence, random_state={SEED + 1}",
                                  "scores": metrics["cv_macro_f1"], "disclosure": DISCLOSURE},
        "training_data": {"file": DATASET.relative_to(ROOT).as_posix(), "sha256": sha256(DATASET),
                          "inputs_sheet": "model_inputs_no_label", "labels": "labelled_data_review.voucher_type",
                          "label_source": "UNVERIFIED_SYNTHETIC_LABEL", "eligible_rows": int(len(X)),
                          "trained_on_rows": int(len(train_idx))},
        "excluded_records": {"source": COMPARISON.relative_to(ROOT).as_posix(), "sha256": sha256(COMPARISON),
                             "rule": "Adjudication_Queue rows with needs_adjudication = True", "count": int(len(disputed))},
        "split": split_info,
        "scores": "predict_proba is uncalibrated; never report it as confidence",
        "review_route_labels": sorted(REVIEW_ROUTE),
        "evaluation_workbook_used": False,
        "environment": {"python": platform.python_version(), "scikit_learn": sklearn.__version__,
                        "pandas": pd.__version__, "numpy": np.__version__, "git_commit": git_commit()},
    }
    by_class = {r["class"]: r for r in class_rows}
    label_map = {
        "taxonomy_source": f"{DATASET.relative_to(ROOT).as_posix()} / label_guidelines_v5 (27 categories)",
        "index_order": "model.classes_ (alphabetical); index i corresponds to predict_proba column i",
        "labels": [{"index": i, "label": c, "train_rows": by_class[c]["train_rows"],
                    "eligible_rows": by_class[c]["eligible_rows"], "review_route": by_class[c]["review_route"],
                    "in_existing_v1_artifact": c in set(existing_model.classes_), "note": by_class[c]["note"]}
                   for i, c in enumerate(model.classes_)],
    }

    predictions = X_test.copy()
    predictions.insert(0, "record_id", m["record_id"].iloc[test_idx].values)
    predictions["Synthetic Label (unverified)"] = y_test
    predictions["Predicted Voucher Category"] = pred
    predictions["Correct"] = pred == y_test
    predictions["Model Score (Uncalibrated)"] = np.round(proba, 4)
    predictions["Review Required"] = np.isin(pred, list(REVIEW_ROUTE))

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    LABELS_PATH.write_text(json.dumps(label_map, indent=2), encoding="utf-8")
    METRICS_PATH.write_text(json.dumps({**metrics, "data_audit": data_audit}, indent=2, default=str), encoding="utf-8")
    class_table.to_csv(CLASS_REPORT_PATH, index=False)
    cm.to_csv(CONFUSION_PATH)
    predictions.to_excel(PREDICTIONS_PATH, index=False)
    REPORT_PATH.write_text(render_report(data_audit, metrics, class_table, config), encoding="utf-8")

    for p in OUTPUTS:
        print(f"Saved {p}")
    print(json.dumps(comparisons, indent=2))


def render_report(data_audit, metrics, class_table, config):
    comp = "\n".join(
        f"| {name} | {r['n']} | {r['correct']} | {r['accuracy']:.4f} | {r['macro_f1']:.4f} | {r['weighted_f1']:.4f} |"
        for name, r in metrics["comparisons"].items())
    per_class = "\n".join(
        f"| {r['class']} | {r['train_rows']} | {r['test_support']} | {r['precision']:.3f} | {r['recall']:.3f} | "
        f"{r['f1']:.3f} | {r['recall_mean_other_holdouts']:.3f} | {r['recall_min_other_holdouts']:.3f} | {r['note']} |"
        for _, r in class_table.sort_values("recall_min_other_holdouts").iterrows())
    confusions = "\n".join(f"| {c['true']} | {c['predicted']} | {c['count']} |" for c in metrics["top_confusions"])
    cv_table = "\n".join(f"| {k} | {v} |" for k, v in metrics["cv_macro_f1"].items())
    s, a = metrics["split"], data_audit
    st = metrics["stability_other_holdouts"]["summary"]
    return f"""# VYOM+ TF-IDF Baseline v2: Experiment Report

**Model:** `models/{MODEL_PATH.name}`, created {metrics['created_utc']} (generated by `python -m vyom.train_tfidf_baseline_v2`).

> **{CAVEAT}** The 120-record development workbook was not used.

## Data

- **Training file:** `{config['training_data']['file']}` (sha256 `{config['training_data']['sha256'][:12]}…`). Inputs come from `model_inputs_no_label`; labels come from `labelled_data_review.voucher_type`, and **every label is unverified synthetic**.
- **Eligible rows:** {a['eligible_rows']}, covering {a['classes']} classes, after excluding **{a['excluded_disputed_rows']} disputed records**. These are the records with `needs_adjudication = True` in `{config['excluded_records']['source']}`; they are left unchanged.
- **Duplicates:**
  - exact duplicate rows: {a['exact_duplicate_rows']};
  - rows whose model inputs are identical: {a['identical_model_inputs_rows']} (identical inputs with conflicting labels: {a['identical_inputs_with_conflicting_labels']});
  - near-duplicates (identical except narration, dates, identifiers and amounts): {a['near_duplicate_rows_except_narration_dates_ids_amounts']}.
- **Narration templates:** {a['narration_sentences']} distinct narration sentences, with at least {a['narration_sentences_per_class_min']} per class. {a['narration_sentences_shared_across_split_groups']} of them are shared across the dataset's `split_group`s, so `split_group` is not used for splitting.
- **Leakage controls:**
  - `document_type` is excluded, because it maps 1:1 to the label for 15 classes;
  - identifiers and party names contribute presence only;
  - dates are excluded;
  - the label and every output column are excluded.

## Split and model selection

- **Test split:** {s['method']}. Groups are {s['group']}. Train has {s['train_rows']} rows ({s['train_groups']} groups); test has {s['test_rows']} rows ({s['test_groups']} groups). All 27 classes appear on both sides.
- **No shared narration sentences or identical inputs** appear on both sides of the split; the script asserts this.
- **{s['test_rows_sharing_non_narration_fields_with_train']} of the {s['test_rows']} test rows share all their non-narration fields with some training row.** The generator's field vocabularies cannot be held out.
- **Model:** TF-IDF + logistic regression with balanced class weights.
- **Selected configuration:** **{metrics['chosen_representation']}** ({REPRESENTATIONS[metrics['chosen_representation']]}) with **C = {metrics['chosen_C']}**. Both were chosen by grouped 5-fold cross-validation on the training part only:

| Representation and C | Cross-validation macro-F1 (training part) |
|---|---|
{cv_table}

**Disclosure:** {DISCLOSURE}

## How stable the test result is

The primary split is one random draw of held-out narration sentences, and each class has only {a['narration_sentences_per_class_min']}–15 of them. So the score depends heavily on which sentences are held out.

The same configuration, refitted with no re-tuning on {len(metrics['stability_other_holdouts']['seeds'])} other random per-class group holdouts, gives:

| Metric | Mean | Std | Min | Max |
|---|---|---|---|---|
| Accuracy | {st['accuracy']['mean']:.4f} | {st['accuracy']['std']:.4f} | {st['accuracy']['min']:.4f} | {st['accuracy']['max']:.4f} |
| Macro-F1 | {st['macro_f1']['mean']:.4f} | {st['macro_f1']['std']:.4f} | {st['macro_f1']['min']:.4f} | {st['macro_f1']['max']:.4f} |

**Quote this range, not the single-split number, when describing the baseline.** It still measures only synthetic-label recovery.

## Results on the primary held-out test split

| Model | Rows | Correct | Accuracy | Macro-F1 | Weighted-F1 |
|---|---|---|---|---|---|
{comp}

**How to read the comparison rows:**
- **"v1 recipe refit"** retrains the existing `train_baseline.py` recipe on this split, with its own inputs. Those inputs include dates, invoice and order numbers and party names, and in the first row `document_type`, which is a label proxy.
- **The v1 artifact** is scored as saved, on test rows it cannot have trained on. It has no `Rejection In` or `Other / Miscellaneous` class, so those rows always count as errors.

## Per-class results

Precision, recall and F1 are from the primary test split. The last two recall columns come from the {len(metrics['stability_other_holdouts']['seeds'])} other group holdouts and show which classes are fragile. Rows are sorted by the minimum recall across those holdouts.

| Class | Train rows | Test rows | Precision | Recall | F1 | Recall, mean (other holdouts) | Recall, min (other holdouts) | Note |
|---|---|---|---|---|---|---|---|---|
{per_class}

### Most frequent confusions (test split)

| True | Predicted | Count |
|---|---|---|
{confusions}

The full confusion matrix is in `reports/{CONFUSION_PATH.name}`.

## Category handling

- **All 27 categories are trained and tested,** and the model's classes match the taxonomy in `label_guidelines_v5`; the script asserts this.
- **`Rejection In` and `Other / Miscellaneous`,** both missing from the v1 artifact, are learned explicitly.
- **Predictions of `Other / Miscellaneous` are flagged `Review Required`.** Its policy (DEF-10) is undecided.
- **Classes whose definitions are disputed carry a note** in `models/{LABELS_PATH.name}`. Their labels follow guideline v5 and may change after adjudication.

## Limitations

- **The labels are unverified synthetic labels.**
- **The vocabularies are small and generator-specific.** In earlier experiments, holding out status or item values dropped macro-F1 to 0.25–0.34 (`reports/v3_experiment_summary.md`).
- **No real or independently labelled data was used.** See `reports/independent_evaluation_design.md` for what is required before any real-world claim.
- **`predict_proba` is uncalibrated.**
- **The model expects canonical fields.** Wide-schema workbooks need a validated column mapping first.
- **The training rows exclude the held-out test split.** The model is not refitted on all eligible rows, so the saved artifact is exactly the model these metrics describe.

## Reproduce

```
python -m vyom.train_tfidf_baseline_v2
```

The script refuses to run if any output already exists.
"""


if __name__ == "__main__":
    main()
