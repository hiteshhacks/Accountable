"""VYOM+ Evaluation and Prediction Pipeline for Structured Workbooks.

Supports both Mode A (labeled evaluation) and Mode B (blind prediction)
on the wide-table evaluation workbook. Strictly excludes target labels from
features and prediction logic.
"""

from pathlib import Path
import argparse
import json
import pickle
from typing import Dict, List, Optional, Tuple

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
from vyom.rule_engine import evaluate_transaction_rules


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data/input/Voucher_Classification_Test_Cases_v2.xlsx"
DEFAULT_BASELINE = ROOT / "models/vyom_plus_tfidf_baseline_model.pkl"
DEFAULT_DUAL_ENCODER = ROOT / "models/vyom_dual_encoder_v2.pt"
DEFAULT_OUTPUT = ROOT / "reports/vyom_plus_evaluation_predictions.xlsx"
REPORTS_DIR = ROOT / "reports"


def evaluate_baseline_model(
    model,
    X: pd.DataFrame,
) -> Tuple[List[str], List[float]]:
    """Generate baseline model predictions and uncalibrated confidence scores."""
    serialized_texts = X.apply(serialize_wide_row, axis=1).tolist()
    preds = model.predict(serialized_texts)
    
    scores = []
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(serialized_texts)
        scores = probs.max(axis=1).tolist()
    else:
        scores = [1.0] * len(preds)
        
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
    output_path: Path = DEFAULT_OUTPUT,
    baseline_path: Path = DEFAULT_BASELINE,
    dual_encoder_path: Optional[Path] = None,
    apply_rules: bool = True,
    run_comparison: bool = True,
) -> Dict:
    """Run full evaluation and prediction pipeline."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Safe Load
    print(f"Loading input workbook: {input_path} (sheet: '{sheet_name}')")
    X, y = load_evaluation_workbook(input_path, sheet_name=sheet_name)
    n_samples = len(X)
    print(f"Loaded {n_samples} records and {len(X.columns)} transaction feature columns.")
    
    is_labeled = y is not None
    print(f"Mode: {'Mode A (Labeled Evaluation)' if is_labeled else 'Mode B (Blind Prediction)'}")
    
    # 2. Load Baseline Model
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline model not found: {baseline_path}")
    with open(baseline_path, "rb") as f:
        baseline_model = pickle.load(f)
    baseline_classes = set(baseline_model.classes_)
    print(f"Loaded baseline model ({len(baseline_classes)} classes).")
    
    # 3. Model Predictions on X (strictly no label used)
    base_preds, base_scores = evaluate_baseline_model(baseline_model, X)
    
    # 4. Semantic Rule Application (strictly no label used)
    final_preds = []
    explanations = []
    rules_applied = []
    confidences = []
    statuses = []
    
    for i in range(n_samples):
        row = X.iloc[i]
        b_pred = base_preds[i]
        b_score = base_scores[i]
        
        if apply_rules:
            pred, explanation, applied = evaluate_transaction_rules(row, base_prediction=b_pred)
        else:
            pred, explanation, applied = b_pred, "Model statistical prediction", False
            
        final_preds.append(pred)
        explanations.append(explanation)
        rules_applied.append(applied)
        
        conf = 1.0 if applied else b_score
        confidences.append(round(conf, 4))
        
        status = "RULE_VERIFIED" if applied else ("MODEL_PREDICTION" if conf >= 0.60 else "LOW_CONFIDENCE")
        statuses.append(status)

    # 5. Build Output DataFrame preserving all original columns in X
    out_df = X.copy()
    
    # If labeled, place the ground-truth label alongside predictions for easy comparison
    if is_labeled:
        out_df[LABEL_COLUMN] = y.values
        out_df["Correct"] = [p == act for p, act in zip(final_preds, y.values)]
        
    out_df["Predicted Voucher Category"] = final_preds
    out_df["Prediction Confidence"] = confidences
    out_df["Prediction Status"] = statuses
    out_df["Applied Rule"] = rules_applied
    out_df["Prediction Explanation"] = explanations
    
    # Write output predictions workbook
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_excel(output_path, index=False)
    print(f"Saved evaluation predictions workbook to: {output_path}")

    metrics_summary = {}
    
    # 6. Metrics & Reporting (if labeled)
    if is_labeled:
        actual = y.astype(str).tolist()
        
        # Calculate primary metrics for Final Pipeline (Baseline + Rules)
        acc = accuracy_score(actual, final_preds)
        macro_f1 = f1_score(actual, final_preds, average="macro", zero_division=0)
        weighted_f1 = f1_score(actual, final_preds, average="weighted", zero_division=0)
        
        print("\n" + "="*50)
        print("PIPELINE EVALUATION RESULTS (Baseline + Rules)")
        print("="*50)
        print(f"Total Samples: {n_samples}")
        print(f"Accuracy:    {acc:.4f} ({sum(out_df['Correct'])} / {n_samples})")
        print(f"Macro F1:    {macro_f1:.4f}")
        print(f"Weighted F1: {weighted_f1:.4f}")
        print(f"Rules Applied: {sum(rules_applied)} / {n_samples} ({sum(rules_applied)/n_samples:.1%})")
        
        # Per-class report
        all_unique_labels = sorted(list(set(actual) | set(final_preds)))
        class_rep = classification_report(actual, final_preds, output_dict=True, zero_division=0)
        class_rep_df = pd.DataFrame(class_rep).T
        class_rep_path = REPORTS_DIR / "evaluation_per_class_report.csv"
        class_rep_df.to_csv(class_rep_path)
        print(f"Saved per-class report to: {class_rep_path}")
        
        # Confusion matrix
        cm = confusion_matrix(actual, final_preds, labels=all_unique_labels)
        cm_df = pd.DataFrame(cm, index=all_unique_labels, columns=all_unique_labels)
        cm_path = REPORTS_DIR / "evaluation_confusion_matrix.csv"
        cm_df.to_csv(cm_path)
        print(f"Saved confusion matrix to: {cm_path}")
        
        # Error analysis report
        errors_df = out_df[~out_df["Correct"]].copy()
        err_path = REPORTS_DIR / "evaluation_error_analysis.xlsx"
        errors_df.to_excel(err_path, index=False)
        print(f"Saved error analysis ({len(errors_df)} errors) to: {err_path}")
        
        metrics_summary["pipeline"] = {
            "model": "TF-IDF Baseline + Semantic Rules",
            "n_samples": n_samples,
            "accuracy": float(acc),
            "macro_f1": float(macro_f1),
            "weighted_f1": float(weighted_f1),
            "rules_applied_count": int(sum(rules_applied)),
            "errors_count": int(len(errors_df)),
        }

        # 7. Model Comparisons
        if run_comparison:
            comparison_rows = []
            
            # (a) TF-IDF baseline alone
            acc_base = accuracy_score(actual, base_preds)
            macro_base = f1_score(actual, base_preds, average="macro", zero_division=0)
            weighted_base = f1_score(actual, base_preds, average="weighted", zero_division=0)
            comparison_rows.append({
                "model": "TF-IDF Baseline Alone",
                "n_samples": n_samples,
                "accuracy": float(acc_base),
                "macro_f1": float(macro_base),
                "weighted_f1": float(weighted_base),
                "rule_layer": "No",
            })
            
            # (b) Baseline + Rules
            comparison_rows.append({
                "model": "TF-IDF Baseline + Semantic Rules",
                "n_samples": n_samples,
                "accuracy": float(acc),
                "macro_f1": float(macro_f1),
                "weighted_f1": float(weighted_f1),
                "rule_layer": "Yes",
            })
            
            # (c) Dual Encoder V2 if available
            de_path = dual_encoder_path or DEFAULT_DUAL_ENCODER
            if de_path and de_path.exists():
                try:
                    print("\nEvaluating Dual Encoder V2 for comparison...")
                    de_preds, _ = evaluate_dual_encoder_model(de_path, X)
                    acc_de = accuracy_score(actual, de_preds)
                    macro_de = f1_score(actual, de_preds, average="macro", zero_division=0)
                    weighted_de = f1_score(actual, de_preds, average="weighted", zero_division=0)
                    comparison_rows.append({
                        "model": "Dual Encoder V2 Alone",
                        "n_samples": n_samples,
                        "accuracy": float(acc_de),
                        "macro_f1": float(macro_de),
                        "weighted_f1": float(weighted_de),
                        "rule_layer": "No",
                    })
                    
                    # Dual Encoder V2 + Rules
                    de_rule_preds = []
                    for i in range(n_samples):
                        rp, _, _ = evaluate_transaction_rules(X.iloc[i], base_prediction=de_preds[i])
                        de_rule_preds.append(rp)
                    acc_de_rules = accuracy_score(actual, de_rule_preds)
                    macro_de_rules = f1_score(actual, de_rule_preds, average="macro", zero_division=0)
                    weighted_de_rules = f1_score(actual, de_rule_preds, average="weighted", zero_division=0)
                    comparison_rows.append({
                        "model": "Dual Encoder V2 + Semantic Rules",
                        "n_samples": n_samples,
                        "accuracy": float(acc_de_rules),
                        "macro_f1": float(macro_de_rules),
                        "weighted_f1": float(weighted_de_rules),
                        "rule_layer": "Yes",
                    })
                except Exception as ex:
                    print(f"Could not complete Dual Encoder V2 comparison: {ex}")
                    
            comp_df = pd.DataFrame(comparison_rows)
            comp_csv = REPORTS_DIR / "evaluation_model_comparison.csv"
            comp_json = REPORTS_DIR / "evaluation_model_comparison.json"
            comp_df.to_csv(comp_csv, index=False)
            comp_json.write_text(json.dumps(comparison_rows, indent=2))
            
            print("\n" + "="*50)
            print("MODEL COMPARISON SUMMARY")
            print("="*50)
            print(comp_df.to_string(index=False))
            print(f"\nSaved model comparison to: {comp_csv}")
            metrics_summary["comparison"] = comparison_rows
            
    return metrics_summary


def main():
    parser = argparse.ArgumentParser(description="Evaluate VYOM+ models on wide test cases workbook.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to input workbook")
    parser.add_argument("--sheet", default="Test Cases", help="Worksheet name")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to output predictions workbook")
    parser.add_argument("--model", default=str(DEFAULT_BASELINE), help="Path to TF-IDF baseline model")
    parser.add_argument("--dual-encoder", default=str(DEFAULT_DUAL_ENCODER), help="Path to Dual Encoder V2 model")
    parser.add_argument("--no-rules", action="store_true", help="Disable rule layer")
    parser.add_argument("--skip-comparison", action="store_true", help="Skip running model comparison")
    args = parser.parse_args()
    
    run_pipeline(
        input_path=Path(args.input),
        sheet_name=args.sheet,
        output_path=Path(args.output),
        baseline_path=Path(args.model),
        dual_encoder_path=Path(args.dual_encoder) if not args.skip_comparison else None,
        apply_rules=not args.no_rules,
        run_comparison=not args.skip_comparison,
    )


if __name__ == "__main__":
    main()
