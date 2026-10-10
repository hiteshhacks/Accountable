
"""Analyze errors made by the VYOM+ TF-IDF baseline."""

from pathlib import Path
import pickle

import pandas as pd
import numpy as np

from sklearn.metrics import classification_report

from vyom.dual_encoder import load_data, split_data


ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = ROOT / "models/vyom_plus_tfidf_baseline_model.pkl"
OUTPUT_DIR = ROOT / "reports"

ALL_OUTPUT = OUTPUT_DIR / "baseline_test_predictions.xlsx"
ERROR_OUTPUT = OUTPUT_DIR / "baseline_errors.xlsx"
SUMMARY_OUTPUT = OUTPUT_DIR / "baseline_error_summary.csv"


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Baseline model not found: {MODEL_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Recreate the same group-based split used in the comparison.
    df = load_data()
    train, val, test = split_data(df)

    training_classes = set(train["target"])

    # Match the comparison's evaluation rule:
    # evaluate only records whose actual labels occur in training.
    test = test[
        test["target"].isin(training_classes)
    ].reset_index(drop=True)

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    texts = test["text_input"].tolist()
    actual = test["target"].astype(str).to_numpy()
    predicted = np.asarray(model.predict(texts)).astype(str)

    if len(actual) != len(predicted):
        raise ValueError("Prediction count does not match test row count.")

    result = test.copy()
    result["actual_voucher_type"] = actual
    result["predicted_voucher_type"] = predicted
    result["correct"] = actual == predicted

    # Save prediction probabilities when supported by the model.
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(texts)
        classes = model.classes_

        result["predicted_score"] = probabilities.max(axis=1)

        top_k = min(3, probabilities.shape[1])
        top_indices = np.argsort(probabilities, axis=1)[:, -top_k:][:, ::-1]

        result["top_alternatives"] = [
            " | ".join(
                f"{classes[j]} ({probabilities[i, j]:.3f})"
                for j in row
            )
            for i, row in enumerate(top_indices)
        ]

    # Save full test results and only the incorrect records.
    result.to_excel(ALL_OUTPUT, index=False)

    errors = result[~result["correct"]].copy()
    errors.to_excel(ERROR_OUTPUT, index=False)

    report = classification_report(
        actual,
        predicted,
        output_dict=True,
        zero_division=0,
    )

    pd.DataFrame(report).T.to_csv(SUMMARY_OUTPUT)

    print("\n=== BASELINE ERROR ANALYSIS ===")
    print(f"Evaluated records: {len(result)}")
    print(f"Correct predictions: {result['correct'].sum()}")
    print(f"Incorrect predictions: {len(errors)}")
    print(f"Accuracy: {result['correct'].mean():.4f}")

    print("\nActual -> Predicted errors:")
    if errors.empty:
        print("No errors found.")
    else:
        print(
            errors[
                ["actual_voucher_type", "predicted_voucher_type"]
            ].value_counts().to_string()
        )

    print("\nSaved files:")
    print(ALL_OUTPUT)
    print(ERROR_OUTPUT)
    print(SUMMARY_OUTPUT)


if __name__ == "__main__":
    main()
