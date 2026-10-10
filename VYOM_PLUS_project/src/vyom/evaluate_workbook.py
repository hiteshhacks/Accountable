"""VYOM+ Evaluation and Prediction Pipeline for Structured Workbooks.

Supports both Mode A (labeled evaluation) and Mode B (blind prediction)
on the wide-table evaluation workbook. Strictly excludes target labels from
features and prediction logic.

Outputs never overwrite existing files: without --output a unique timestamped
file name is generated, and an existing --output (or any of its side-reports)
is refused unless --overwrite is given.
"""

from datetime import datetime
from pathlib import Path
import argparse
import json
import pickle
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

from vyom.adapter import (
    LABEL_COLUMN,
    load_evaluation_workbook,
    serialize_wide_row,
    map_wide_to_canonical,
)
from vyom.rule_engine import AMBIGUOUS, NO_RULE, REVIEW_REQUIRED, RULE_MATCH, assess_transaction


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data/input/Voucher_Classification_Test_Cases_v2.xlsx"
DEFAULT_BASELINE = ROOT / "models/vyom_plus_tfidf_baseline_model.pkl"
DEFAULT_DUAL_ENCODER = ROOT / "models/vyom_dual_encoder_v2.pt"
REPORTS_DIR = ROOT / "reports"
OUTPUT_STEM = "vyom_plus_evaluation_predictions"
LOW_SCORE_THRESHOLD = 0.60


def unique_output_path(directory: Path = REPORTS_DIR, stem: str = OUTPUT_STEM) -> Path:
    """Return a timestamped .xlsx path in ``directory`` that does not exist yet."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = Path(directory) / f"{stem}_{stamp}.xlsx"
    n = 2
    while candidate.exists():
        candidate = Path(directory) / f"{stem}_{stamp}_{n}.xlsx"
        n += 1
    return candidate


def side_report_paths(output_path: Path, reports_dir: Path) -> Dict[str, Path]:
    """Metric side-reports, named after the predictions workbook so runs never collide."""
    stem = Path(output_path).stem
    return {
        "per_class": reports_dir / f"{stem}_per_class_report.csv",
        "confusion": reports_dir / f"{stem}_confusion_matrix.csv",
        "errors": reports_dir / f"{stem}_error_analysis.xlsx",
        "comparison_csv": reports_dir / f"{stem}_model_comparison.csv",
        "comparison_json": reports_dir / f"{stem}_model_comparison.json",
    }


def compute_metrics(actual: Sequence[str], predicted: Sequence[str]) -> Dict:
    """Accuracy, macro-F1 and weighted-F1 over the union of true and predicted labels."""
    if len(actual) != len(predicted):
        raise ValueError(f"Length mismatch: {len(actual)} labels vs {len(predicted)} predictions")
    actual, predicted = list(actual), list(predicted)
    return {
        "n_samples": len(actual),
        "correct": int(sum(a == p for a, p in zip(actual, predicted))),
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(actual, predicted, average="weighted", zero_division=0)),
    }


def evaluate_baseline_model(
    model,
    X: pd.DataFrame,
) -> Tuple[List[str], List[float]]:
    """Generate baseline model predictions and uncalibrated scores (max class probability)."""
    serialized_texts = X.apply(serialize_wide_row, axis=1).tolist()
    preds = model.predict(serialized_texts)
    
    scores = []
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(serialized_texts)
        scores = probs.max(axis=1).tolist()
    else:
        # No score is available; do not substitute a fabricated certainty.
        scores = [float("nan")] * len(preds)
        
    return list(preds), list(scores)


def evaluate_dual_encoder_model(
    checkpoint_path: Path,
    X: pd.DataFrame,
    device: Optional[torch.device] = None,
) -> Tuple[List[str], List[float]]:
    """Generate Dual Encoder V2 predictions and softmax scores."""
    from transformers import AutoTokenizer, AutoModel
    from vyom.dual_encoder import DualEncoder, encode_texts, BACKBONE
    
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    classes = checkpoint["classes"]
    
    tokenizer = AutoTokenizer.from_pretrained(BACKBONE)
    backbone = AutoModel.from_pretrained(BACKBONE).to(device)
    for p in backbone.parameters():
        p.requires_grad = False
        
    serialized_texts = X.apply(serialize_wide_row, axis=1).tolist()
    embeddings = encode_texts(serialized_texts, tokenizer, backbone, device)
    
    model = DualEncoder(
        embedding_dim=checkpoint["embedding_dim"],
        num_classes=len(classes),
    ).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    
    with torch.no_grad():
        logits, _ = model(embeddings.to(device))
        probs = torch.softmax(logits, dim=1).cpu().numpy()
        preds_idx = probs.argmax(axis=1)
        
    predictions = [classes[i] for i in preds_idx]
    scores = probs.max(axis=1).tolist()
    return predictions, scores


def run_pipeline(
    input_path: Path,
    sheet_name: str = "Test Cases",
    output_path: Optional[Path] = None,
    baseline_path: Path = DEFAULT_BASELINE,
    dual_encoder_path: Optional[Path] = None,
    apply_rules: bool = True,
    run_comparison: bool = True,
    reports_dir: Optional[Path] = None,
    overwrite: bool = False,
) -> Dict:
    """Run full evaluation and prediction pipeline.

    ``output_path`` defaults to a new timestamped file in ``REPORTS_DIR``.
    Metric side-reports are named after it and written to ``reports_dir``
    (default: the folder of ``output_path``). Existing files are never replaced
    unless ``overwrite`` is True.
    """
    input_path = Path(input_path)
    output_path = Path(output_path) if output_path is not None else unique_output_path()
    reports_dir = Path(reports_dir) if reports_dir is not None else output_path.parent
    if output_path.resolve() == input_path.resolve():
        raise ValueError("Output path must differ from the input workbook.")

    # 1. Safe Load
    print(f"Loading input workbook: {input_path} (sheet: '{sheet_name}')")
    X, y = load_evaluation_workbook(input_path, sheet_name=sheet_name)
    n_samples = len(X)
    print(f"Loaded {n_samples} records and {len(X.columns)} transaction feature columns.")

    is_labeled = y is not None
    print(f"Mode: {'Mode A (Labeled Evaluation)' if is_labeled else 'Mode B (Blind Prediction)'}")

    side_paths = side_report_paths(output_path, reports_dir)
    targets = [output_path]
    if is_labeled:
        targets += [side_paths["per_class"], side_paths["confusion"], side_paths["errors"]]
        if run_comparison:
            targets += [side_paths["comparison_csv"], side_paths["comparison_json"]]
    existing = [str(p) for p in targets if p.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Refusing to overwrite existing report(s): " + ", ".join(existing)
            + ". Choose a different --output or pass --overwrite."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 2. Load Baseline Model
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline model not found: {baseline_path}")
    with open(baseline_path, "rb") as f:
        baseline_model = pickle.load(f)
    baseline_classes = set(baseline_model.classes_)
    print(f"Loaded baseline model ({len(baseline_classes)} classes).")

    # 3. Model Predictions on X (strictly no label used)
    base_preds, base_scores = evaluate_baseline_model(baseline_model, X)

    # 4. Semantic Rule Assessment (strictly no label used)
    # Prediction, rule status and model score are kept in separate columns.
    # A rule match is a deterministic decision, not a probability; only the
    # model has a score, and it is uncalibrated.
    decisions = [assess_transaction(X.iloc[i]) if apply_rules else None for i in range(n_samples)]
    final_preds = apply_rule_decisions(decisions, base_preds)

    sources, rule_statuses, candidates, review_flags, review_reasons, explanations = [], [], [], [], [], []
    for decision, b_score in zip(decisions, base_scores):
        rule_status = decision.status if decision else "RULES_DISABLED"
        source = "RULE" if rule_status == RULE_MATCH else "MODEL"
        if rule_status == REVIEW_REQUIRED:
            reason = "Conflicting rule evidence"
        elif rule_status == AMBIGUOUS:
            reason = "Insufficient rule evidence"
        elif source == "MODEL" and pd.isna(b_score):
            reason = "No model score"
        elif source == "MODEL" and b_score < LOW_SCORE_THRESHOLD:
            reason = f"Model score below {LOW_SCORE_THRESHOLD:.2f} (uncalibrated)"
        else:
            reason = ""
        sources.append(source)
        rule_statuses.append(rule_status)
        candidates.append(" | ".join(decision.candidates) if decision else "")
        review_flags.append(bool(reason))
        review_reasons.append(reason)
        if decision is None:
            explanations.append("Model statistical prediction (rules disabled)")
        elif rule_status == NO_RULE:
            explanations.append("No rule evidence; model statistical prediction")
        else:
            explanations.append(decision.explanation)

    # 5. Build Output DataFrame preserving all original columns in X
    out_df = X.copy()

    # If labeled, place the ground-truth label alongside predictions for easy comparison
    if is_labeled:
        out_df[LABEL_COLUMN] = y.values
        out_df["Correct"] = [p == act for p, act in zip(final_preds, y.values)]

    out_df["Predicted Voucher Category"] = final_preds
    out_df["Decision Source"] = sources
    out_df["Rule Status"] = rule_statuses
    out_df["Rule Candidates"] = candidates
    out_df["Model Prediction"] = base_preds
    out_df["Model Score (Uncalibrated)"] = [round(s, 4) for s in base_scores]
    out_df["Rule Overrode Model"] = [s == "RULE" and p != b for s, p, b in zip(sources, final_preds, base_preds)]
    out_df["Review Required"] = review_flags
    out_df["Review Reason"] = review_reasons
    out_df["Prediction Explanation"] = explanations

    # Write output predictions workbook
    out_df.to_excel(output_path, index=False)
    print(f"Saved evaluation predictions workbook to: {output_path}")

    status_counts = pd.Series(rule_statuses).value_counts().to_dict()
    metrics_summary = {
        "outputs": {"predictions": str(output_path)},
        "rule_status_counts": {k: int(v) for k, v in status_counts.items()},
        "review_required_count": int(sum(review_flags)),
    }
    print(f"Rule status counts: {metrics_summary['rule_status_counts']}")
    print(f"Review required: {metrics_summary['review_required_count']} / {n_samples}")

    # 6. Metrics & Reporting (if labeled)
    if is_labeled:
        actual = y.astype(str).tolist()

        # Calculate primary metrics for Final Pipeline (Baseline + Rules)
        pipeline_metrics = compute_metrics(actual, final_preds)

        print("\n" + "="*50)
        print("PIPELINE EVALUATION RESULTS (Baseline + Rules)")
        print("="*50)
        print(f"Total Samples: {n_samples}")
        print(f"Accuracy:    {pipeline_metrics['accuracy']:.4f} ({pipeline_metrics['correct']} / {n_samples})")
        print(f"Macro F1:    {pipeline_metrics['macro_f1']:.4f}")
        print(f"Weighted F1: {pipeline_metrics['weighted_f1']:.4f}")

        # Per-class report
        all_unique_labels = sorted(list(set(actual) | set(final_preds)))
        class_rep = classification_report(actual, final_preds, output_dict=True, zero_division=0)
        class_rep_df = pd.DataFrame(class_rep).T
        class_rep_df.to_csv(side_paths["per_class"])
        print(f"Saved per-class report to: {side_paths['per_class']}")

        # Confusion matrix
        cm = confusion_matrix(actual, final_preds, labels=all_unique_labels)
        cm_df = pd.DataFrame(cm, index=all_unique_labels, columns=all_unique_labels)
        cm_df.to_csv(side_paths["confusion"])
        print(f"Saved confusion matrix to: {side_paths['confusion']}")

        # Error analysis report
        errors_df = out_df[~out_df["Correct"]].copy()
        errors_df.to_excel(side_paths["errors"], index=False)
        print(f"Saved error analysis ({len(errors_df)} errors) to: {side_paths['errors']}")
        metrics_summary["outputs"].update(
            per_class=str(side_paths["per_class"]),
            confusion=str(side_paths["confusion"]),
            errors=str(side_paths["errors"]),
        )

        metrics_summary["pipeline"] = {
            "model": "TF-IDF Baseline + Semantic Rules",
            **pipeline_metrics,
            "rule_match_count": int(status_counts.get(RULE_MATCH, 0)),
            "errors_count": int(len(errors_df)),
        }

        # 7. Model Comparisons
        if run_comparison:
            comparison_rows = [
                {"model": "TF-IDF Baseline Alone", **compute_metrics(actual, base_preds), "rule_layer": "No"},
                {"model": "TF-IDF Baseline + Semantic Rules", **pipeline_metrics, "rule_layer": "Yes"},
            ]

            # Dual Encoder V2 if available
            de_path = dual_encoder_path or DEFAULT_DUAL_ENCODER
            if de_path and de_path.exists():
                try:
                    print("\nEvaluating Dual Encoder V2 for comparison...")
                    de_preds, _ = evaluate_dual_encoder_model(de_path, X)
                    comparison_rows.append(
                        {"model": "Dual Encoder V2 Alone", **compute_metrics(actual, de_preds), "rule_layer": "No"})
                    if apply_rules:
                        de_rule_preds = apply_rule_decisions(decisions, de_preds)
                        comparison_rows.append({"model": "Dual Encoder V2 + Semantic Rules",
                                                **compute_metrics(actual, de_rule_preds), "rule_layer": "Yes"})
                except Exception as ex:
                    print(f"Could not complete Dual Encoder V2 comparison: {ex}")

            comp_df = pd.DataFrame(comparison_rows)
            comp_df.to_csv(side_paths["comparison_csv"], index=False)
            side_paths["comparison_json"].write_text(json.dumps(comparison_rows, indent=2))

            print("\n" + "="*50)
            print("MODEL COMPARISON SUMMARY")
            print("="*50)
            print(comp_df.to_string(index=False))
            print(f"\nSaved model comparison to: {side_paths['comparison_csv']}")
            metrics_summary["comparison"] = comparison_rows
            metrics_summary["outputs"].update(
                comparison_csv=str(side_paths["comparison_csv"]),
                comparison_json=str(side_paths["comparison_json"]),
            )

    return metrics_summary


def apply_rule_decisions(decisions, model_preds: Sequence[str]) -> List[str]:
    """Use the rule category only for RULE_MATCH; otherwise keep the model prediction."""
    return [d.category if d is not None and d.status == RULE_MATCH else m
            for d, m in zip(decisions, model_preds)]


def main():
    parser = argparse.ArgumentParser(description="Evaluate VYOM+ models on wide test cases workbook.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to input workbook")
    parser.add_argument("--sheet", default="Test Cases", help="Worksheet name")
    parser.add_argument("--output", default=None,
                        help="Path to output predictions workbook (default: new timestamped file in reports/)")
    parser.add_argument("--model", default=str(DEFAULT_BASELINE), help="Path to TF-IDF baseline model")
    parser.add_argument("--dual-encoder", default=str(DEFAULT_DUAL_ENCODER), help="Path to Dual Encoder V2 model")
    parser.add_argument("--no-rules", action="store_true", help="Disable rule layer")
    parser.add_argument("--skip-comparison", action="store_true", help="Skip running model comparison")
    parser.add_argument("--reports-dir", default=None, help="Folder for metric side-reports (default: folder of --output)")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing existing output files")
    args = parser.parse_args()

    run_pipeline(
        input_path=Path(args.input),
        sheet_name=args.sheet,
        output_path=Path(args.output) if args.output else None,
        baseline_path=Path(args.model),
        dual_encoder_path=Path(args.dual_encoder) if not args.skip_comparison else None,
        apply_rules=not args.no_rules,
        run_comparison=not args.skip_comparison,
        reports_dir=Path(args.reports_dir) if args.reports_dir else None,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
