
"""VYOM+ fair model comparison: baseline, V1 and V2."""

from pathlib import Path
import pickle
import json

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from transformers import AutoTokenizer, AutoModel
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, classification_report

from vyom.dual_encoder import (
    load_data,
    split_data,
    encode_texts,
    DualEncoder,
    BACKBONE,
)


ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"

BASELINE_PATH = MODEL_DIR / "vyom_plus_tfidf_baseline_model.pkl"
V2_PATH = MODEL_DIR / "vyom_dual_encoder_v2.pt"
V1_PREDICTIONS = REPORT_DIR / "vyom_dual_encoder_test_predictions.xlsx"

OUTPUT_JSON = REPORT_DIR / "model_comparison.json"
OUTPUT_CSV = REPORT_DIR / "model_comparison.csv"

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


def metrics_for(name, actual, predicted, labels):
    """Calculate comparable metrics on the same records."""
    return {
        "model": name,
        "n_test": len(actual),
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_f1_all_training_classes": float(
            f1_score(
                actual,
                predicted,
                labels=labels,
                average="macro",
                zero_division=0,
            )
        ),
        "macro_f1_observed_classes": float(
            f1_score(
                actual,
                predicted,
                labels=sorted(set(actual) | set(predicted)),
                average="macro",
                zero_division=0,
            )
        ),
    }


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    for path in [BASELINE_PATH, V2_PATH, V1_PREDICTIONS]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required artifact not found: {path}\n"
                "Check the filename and location in your project."
            )

    # Recreate the split used by the dual-encoder experiments.
    df = load_data()
    train, val, test = split_data(df)

    label_encoder = LabelEncoder()
    label_encoder.fit(train["target"])

    known_classes = set(label_encoder.classes_)

    # Only evaluate labels represented in training.
    test = test[
        test["target"].isin(known_classes)
    ].reset_index(drop=True)

    if test.empty:
        raise ValueError("No eligible test records.")

    actual = label_encoder.transform(test["target"])
    all_labels = np.arange(len(label_encoder.classes_))

    results = []
    prediction_columns = {
        "actual": label_encoder.inverse_transform(actual)
    }

    # ------------------------------------------
    # 1. TF-IDF baseline
    # ------------------------------------------
    print("Evaluating TF-IDF baseline...")

    with open(BASELINE_PATH, "rb") as f:
        baseline = pickle.load(f)

    baseline_predictions = baseline.predict(
        test["text_input"].tolist()
    )

    baseline_predictions = np.asarray(baseline_predictions)

    # Support either string labels or encoded class IDs.
    if len(baseline_predictions) and isinstance(
        baseline_predictions[0], (int, np.integer)
    ):
        baseline_predictions = label_encoder.inverse_transform(
            baseline_predictions.astype(int)
        )

    baseline_predictions = np.asarray(baseline_predictions)

    results.append(
        metrics_for(
            "TF-IDF baseline",
            test["target"].to_numpy(),
            baseline_predictions,
            label_encoder.classes_.tolist(),
        )
    )

    prediction_columns["baseline"] = baseline_predictions

    # ------------------------------------------
    # 2. Dual Encoder V2
    # ------------------------------------------
    print("Evaluating Dual Encoder V2...")

    checkpoint = torch.load(
        V2_PATH,
        map_location="cpu",
        weights_only=False,
    )

    v2_classes = checkpoint["classes"]

    if v2_classes != label_encoder.classes_.tolist():
        raise ValueError(
            "V2 class mapping differs from the recreated training split. "
            "Do not compare until the exact split and class mapping match."
        )

    tokenizer = AutoTokenizer.from_pretrained(BACKBONE)
    backbone = AutoModel.from_pretrained(BACKBONE).to(DEVICE)

    for parameter in backbone.parameters():
        parameter.requires_grad = False

    embeddings = encode_texts(
        test["text_input"].tolist(),
        tokenizer,
        backbone,
        DEVICE,
    )

    model = DualEncoder(
        embedding_dim=checkpoint["embedding_dim"],
        num_classes=len(v2_classes),
    ).to(DEVICE)

    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    with torch.no_grad():
        logits, _ = model(embeddings.to(DEVICE))
        v2_ids = logits.argmax(dim=1).cpu().numpy()

    v2_predictions = label_encoder.inverse_transform(v2_ids)

    results.append(
        metrics_for(
            "Dual Encoder V2",
            test["target"].to_numpy(),
            v2_predictions,
            label_encoder.classes_.tolist(),
        )
    )

    prediction_columns["dual_encoder_v2"] = v2_predictions

    # ------------------------------------------
    # 3. Dual Encoder V1 saved predictions
    # ------------------------------------------
    print("Checking Dual Encoder V1 predictions...")

    v1 = pd.read_excel(V1_PREDICTIONS)

    required = {"actual", "predicted"}
    if not required.issubset(v1.columns):
        raise ValueError(
            f"V1 predictions must contain columns: {required}"
        )

    if len(v1) != len(test):
        print(
            f"V1 has {len(v1)} rows, current eligible test has "
            f"{len(test)} rows. V1 cannot be fairly compared yet."
        )
    elif (
        v1["actual"].astype(str).tolist()
        != test["target"].astype(str).tolist()
    ):
        print(
            "V1 actual labels/order do not match the recreated test set. "
            "Skipping V1 comparison to avoid a misleading result."
        )
    else:
        v1_predictions = v1["predicted"].astype(str).to_numpy()

        results.append(
            metrics_for(
                "Dual Encoder V1",
                test["target"].to_numpy(),
                v1_predictions,
                label_encoder.classes_.tolist(),
            )
        )

        prediction_columns["dual_encoder_v1"] = v1_predictions

    # ------------------------------------------
    # Save results
    # ------------------------------------------
    summary = pd.DataFrame(results)

    summary.to_csv(OUTPUT_CSV, index=False)

    (OUTPUT_JSON).write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    prediction_columns["split_group"] = test["split_group"].to_numpy()

    pd.DataFrame(prediction_columns).to_excel(
        REPORT_DIR / "model_comparison_predictions.xlsx",
        index=False,
    )

    print("\n=== COMPARISON RESULTS ===")
    print(summary.to_string(index=False))

    print("\nSaved:")
    print(OUTPUT_JSON)
    print(OUTPUT_CSV)
    print(REPORT_DIR / "model_comparison_predictions.xlsx")


if __name__ == "__main__":
    main()
