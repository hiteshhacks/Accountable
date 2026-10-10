
"""VYOM+ rule-correction experiment.

Evaluates the existing TF-IDF baseline against a small,
explainable rule layer on the validation split only.

The original model is never modified.
"""

from pathlib import Path
import pickle
import re

import numpy as np
import pandas as pd

from sklearn.metrics import accuracy_score, f1_score

from vyom.dual_encoder import load_data, split_data


ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = ROOT / "models/vyom_plus_tfidf_baseline_model.pkl"
REPORT_DIR = ROOT / "reports"

PREDICTIONS_PATH = REPORT_DIR / "baseline_rule_validation_predictions.xlsx"
METRICS_PATH = REPORT_DIR / "baseline_rule_validation_metrics.csv"


def clean(value):
    """Normalize a field safely."""
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def apply_rules(row, original_prediction):
    """Return (prediction, reason); preserve the model by default."""

    document_type = clean(row.get("document_type"))
    item_description = clean(row.get("item_description"))
    narration = clean(row.get("transaction_narration"))
    payment_status = clean(row.get("payment_status"))

    # Rule 1: Trust an explicit, recognized order document type.
    # This distinguishes customer sales orders from supplier purchase orders.
    if document_type in {"sales order", "sales order form"}:
        return "Sales Order", "Explicit document_type: sales order"

    if document_type in {"purchase order", "purchase order form"}:
        return "Purchase Order", "Explicit document_type: purchase order"

    # Do not override an explicit document type that identifies another
    # transaction document, such as a delivery note or invoice.
    explicit_other_documents = {
        "delivery note",
        "receipt note",
        "sales invoice",
        "purchase invoice",
        "tax invoice",
        "credit note",
        "debit note",
    }

    if document_type in explicit_other_documents:
        return original_prediction, "Preserved explicit non-order document type"

    # Rule 2: Require evidence from at least two separate fields
    # before correcting to Advance / Prepayment.
    advance_item = bool(
        re.search(r"\b(advance|prepayment|prepaid)\b", item_description)
    )

    advance_narration = bool(
        re.search(
            r"\b(advance|prepayment|prepaid)\b",
            narration,
        )
    )

    advance_status = bool(
        re.search(
            r"\b(prepaid|prepayment|advance|received in advance)\b",
            payment_status,
        )
    )

    evidence_count = sum(
        [advance_item, advance_narration, advance_status]
    )

    if evidence_count >= 2:
        return (
            "Advance / Prepayment",
            f"Advance evidence in {evidence_count} fields",
        )

    return original_prediction, "No correction rule matched"


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Baseline model not found: {MODEL_PATH}"
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()
    train, validation, _test = split_data(df)

    # Evaluate only labels represented in the training split.
    known_classes = set(train["target"])

    validation = validation[
        validation["target"].isin(known_classes)
    ].reset_index(drop=True)

    with open(MODEL_PATH, "rb") as file:
        model = pickle.load(file)

    actual = validation["target"].astype(str).to_numpy()

    original = np.asarray(
        model.predict(validation["text_input"].tolist())
    ).astype(str)

    corrected = []
    reasons = []

    for _, row in validation.iterrows():
        prediction, reason = apply_rules(
            row,
            original[len(corrected)],
        )
        corrected.append(prediction)
        reasons.append(reason)

    corrected = np.asarray(corrected)

    results = validation.copy()
    results["actual_voucher_type"] = actual
    results["baseline_prediction"] = original
    results["rule_corrected_prediction"] = corrected
    results["correction_applied"] = original != corrected
    results["correction_reason"] = reasons
    results["baseline_correct"] = original == actual
    results["corrected_correct"] = corrected == actual

    # Overall accuracy and macro-F1 using the same validation records.
    labels = sorted(known_classes)

    rows = []

    for name, predictions in [
        ("TF-IDF baseline", original),
        ("Baseline + rules", corrected),
    ]:
        rows.append({
            "model": name,
            "validation_records": len(actual),
            "accuracy": accuracy_score(actual, predictions),
            "macro_f1_all_training_classes": f1_score(
                actual,
                predictions,
                labels=labels,
                average="macro",
                zero_division=0,
            ),
            "corrections_applied": int(
                np.sum(original != corrected)
                if name == "Baseline + rules"
                else 0
            ),
        })

    results.to_excel(PREDICTIONS_PATH, index=False)
    pd.DataFrame(rows).to_csv(METRICS_PATH, index=False)

    print("\n=== VALIDATION RESULTS ===")
    print(pd.DataFrame(rows).to_string(index=False))

    print("\nCorrection breakdown:")
    print(
        results.loc[
            results["correction_applied"],
            ["actual_voucher_type",
             "baseline_prediction",
             "rule_corrected_prediction",
             "correction_reason"],
        ].to_string(index=False)
    )

    print("\nSaved:")
    print(PREDICTIONS_PATH)
    print(METRICS_PATH)


if __name__ == "__main__":
    main()
