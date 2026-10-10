
"""
VYOM+ Dual Encoder V2

General encoder:
    Frozen MiniLM semantic embeddings.

Boundary encoder:
    Trainable projection using supervised contrastive learning.

Training:
    Cross-entropy + supervised contrastive loss.
    Class-balanced sampling.

Evaluation:
    Group-based split, accuracy, macro-F1,
    per-class report, confusion matrix.

NOTE: Experimental model trained on provisional synthetic-derived labels.
"""

from pathlib import Path
from collections import Counter
import copy
import json
import random

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from torch import nn
from torch.utils.data import (
    DataLoader,
    TensorDataset,
    WeightedRandomSampler,
)
from transformers import AutoTokenizer, AutoModel

from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

from vyom.preprocessing import make_text


# ==========================================
# CONFIGURATION
# ==========================================

ROOT = Path(__file__).resolve().parents[2]

DATASET = (
    ROOT / "data/synthetic/"
    "synthetic_voucher_dataset_v5_review_ready.xlsx"
)

COMPARISON = (
    ROOT / "data/synthetic/"
    "VYOM_plus_reviewer_comparison_adjudication.xlsx"
)

MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"

BACKBONE = "sentence-transformers/all-MiniLM-L6-v2"

SEED = 42
BATCH_SIZE = 32
EPOCHS = 35
LR = 0.0005
CONTRASTIVE_WEIGHT = 0.15
TEMPERATURE = 0.15
PATIENCE = 6


# ==========================================
# REPRODUCIBILITY
# ==========================================

def set_seed():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)


# ==========================================
# LOAD DATA
# ==========================================

def load_data():

    queue = pd.read_excel(
        DATASET,
        sheet_name="human_review_queue",
    )

    consensus = pd.read_excel(
        COMPARISON,
        sheet_name="Provisional_Consensus",
    )

    consensus["queue_row_index"] = (
        consensus["review_case_id"]
        .str.extract(r"HR-(\d+)")[0]
        .astype(int) - 1
    )

    metadata = (
        queue.reset_index()
        .rename(columns={"index": "queue_row_index"})
    )

    # Keep the same join logic used by V1.
    df = consensus.merge(
        metadata[["queue_row_index", "split_group"]],
        on="queue_row_index",
        how="left",
        validate="one_to_one",
    )

    df["text_input"] = df.apply(make_text, axis=1)

    df["target"] = (
        df["provisional_consensus_label"]
        .astype(str)
        .str.strip()
    )

    df = df[
        df["split_group"].notna()
        & df["target"].notna()
        & df["target"].ne("")
        & df["target"].ne("nan")
        & df["text_input"].str.len().gt(0)
    ].copy()

    return df.reset_index(drop=True)


# ==========================================
# GROUP-BASED SPLITTING
# ==========================================

def split_data(df):

    indices = np.arange(len(df))
    groups = df["split_group"].astype(str)

    train_val_idx, test_idx = next(
        GroupShuffleSplit(
            n_splits=1,
            test_size=0.20,
            random_state=42,
        ).split(indices, df["target"], groups)
    )

    train_val = df.iloc[train_val_idx].reset_index(drop=True)
    test = df.iloc[test_idx].reset_index(drop=True)

    train_idx, val_idx = next(
        GroupShuffleSplit(
            n_splits=1,
            test_size=0.20,
            random_state=43,
        ).split(
            np.arange(len(train_val)),
            train_val["target"],
            train_val["split_group"].astype(str),
        )
    )

    train = train_val.iloc[train_idx].reset_index(drop=True)
    val = train_val.iloc[val_idx].reset_index(drop=True)

    return train, val, test


# ==========================================
# GENERAL ENCODER
# ==========================================

def encode_texts(texts, tokenizer, backbone, device):

    embeddings = []

    backbone.eval()

    with torch.no_grad():

        for start in range(0, len(texts), BATCH_SIZE):

            batch = texts[start:start + BATCH_SIZE]

            tokens = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            )

            tokens = {
                key: value.to(device)
                for key, value in tokens.items()
            }

            output = backbone(**tokens)

            hidden = output.last_hidden_state

            mask = (
                tokens["attention_mask"]
                .unsqueeze(-1)
                .float()
            )

            pooled = (
                (hidden * mask).sum(dim=1)
                / mask.sum(dim=1).clamp(min=1e-9)
            )

            pooled = F.normalize(pooled, dim=1)

            embeddings.append(pooled.cpu())

    return torch.cat(embeddings, dim=0)


# ==========================================
# DUAL ENCODER
# ==========================================

class DualEncoder(nn.Module):

    def __init__(self, embedding_dim, num_classes):
        super().__init__()

        self.general_encoder = nn.Identity()

        self.boundary_encoder = nn.Sequential(
            nn.Linear(embedding_dim, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(256, 128),
        )

        self.classifier = nn.Sequential(
            nn.Linear(embedding_dim + 128, 256),
            nn.ReLU(),
            nn.Dropout(0.20),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):

        general = self.general_encoder(x)

        boundary = self.boundary_encoder(x)

        boundary = F.normalize(boundary, dim=1)

        combined = torch.cat(
            [general, boundary],
            dim=1,
        )

        logits = self.classifier(combined)

        return logits, boundary


# ==========================================
# SUPERVISED CONTRASTIVE LOSS
# ==========================================

def contrastive_loss(embeddings, labels):

    """
    Pull same-class examples closer.
    Push different-class examples apart.

    Only anchors with a positive partner contribute.
    """

    embeddings = F.normalize(embeddings, dim=1)

    similarities = (
        embeddings @ embeddings.T
    ) / TEMPERATURE

    batch_size = labels.shape[0]

    identity = torch.eye(
        batch_size,
        device=labels.device,
        dtype=torch.bool,
    )

    positive_mask = (
        labels.unsqueeze(0) == labels.unsqueeze(1)
    ) & ~identity

    valid_anchors = positive_mask.any(dim=1)

    if not valid_anchors.any():
        return embeddings.sum() * 0.0

    similarities = similarities.masked_fill(
        identity,
        -1e9,
    )

    log_prob = F.log_softmax(
        similarities,
        dim=1,
    )

    positive_count = positive_mask.sum(dim=1).clamp(min=1)

    positive_log_prob = (
        log_prob.masked_fill(~positive_mask, 0.0)
        .sum(dim=1)
        / positive_count
    )

    return -positive_log_prob[valid_anchors].mean()


# ==========================================
# CLASS-BALANCED SAMPLER
# ==========================================

def create_sampler(labels):

    counts = Counter(labels.tolist())

    sample_weights = [
        1.0 / counts[int(label)]
        for label in labels
    ]

    return WeightedRandomSampler(
        weights=torch.tensor(
            sample_weights,
            dtype=torch.double,
        ),
        num_samples=len(labels),
        replacement=True,
    )


# ==========================================
# EVALUATION
# ==========================================

def evaluate(model, x, y, device):

    model.eval()

    with torch.no_grad():
        logits, _ = model(x.to(device))

        predictions = logits.argmax(dim=1).cpu().numpy()

        loss = F.cross_entropy(
            logits,
            torch.tensor(
                y,
                dtype=torch.long,
                device=device,
            ),
        ).item()

    return predictions, loss


# ==========================================
# TRAINING
# ==========================================

def main():

    set_seed()

    MODEL_DIR.mkdir(exist_ok=True, parents=True)
    REPORT_DIR.mkdir(exist_ok=True, parents=True)

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)

    print("\nLoading dataset...")

    df = load_data()

    train, val, test = split_data(df)

    label_encoder = LabelEncoder()
    label_encoder.fit(train["target"])

    known_classes = set(label_encoder.classes_)

    # V1 excluded examples whose labels were absent from training.
    # Retain this behavior for the experimental comparison,
    # but report exclusions explicitly.
    val_unknown = ~val["target"].isin(known_classes)
    test_unknown = ~test["target"].isin(known_classes)

    print("Train:", len(train))
    print("Validation:", len(val))
    print("Test total:", len(test))
    print("Training classes:", len(known_classes))
    print("Unseen validation labels:", int(val_unknown.sum()))
    print("Unseen test labels:", int(test_unknown.sum()))

    val = val[~val_unknown].reset_index(drop=True)
    test = test[~test_unknown].reset_index(drop=True)

    if len(val) == 0 or len(test) == 0:
        raise ValueError(
            "No evaluable validation/test examples. "
            "Revise the split before training."
        )

    train_y = label_encoder.transform(train["target"])
    val_y = label_encoder.transform(val["target"])
    test_y = label_encoder.transform(test["target"])

    print("\nLoading MiniLM backbone...")

    tokenizer = AutoTokenizer.from_pretrained(BACKBONE)
    backbone = AutoModel.from_pretrained(BACKBONE).to(device)

    for parameter in backbone.parameters():
        parameter.requires_grad = False

    print("Generating embeddings...")

    train_x = encode_texts(
        train["text_input"].tolist(),
        tokenizer,
        backbone,
        device,
    )

    val_x = encode_texts(
        val["text_input"].tolist(),
        tokenizer,
        backbone,
        device,
    )

    test_x = encode_texts(
        test["text_input"].tolist(),
        tokenizer,
        backbone,
        device,
    )

    model = DualEncoder(
        embedding_dim=train_x.shape[1],
        num_classes=len(label_encoder.classes_),
    ).to(device)

    train_labels = torch.tensor(
        train_y,
        dtype=torch.long,
    )

    sampler = create_sampler(train_labels)

    loader = DataLoader(
        TensorDataset(train_x, train_labels),
        batch_size=BATCH_SIZE,
        sampler=sampler,
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LR,
        weight_decay=0.01,
    )

    best_loss = float("inf")
    best_weights = None
    patience_counter = 0

    print("\nTraining Dual Encoder V2...\n")

    for epoch in range(EPOCHS):

        model.train()

        total_loss = 0.0

        for batch_x, batch_y in loader:

            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad()

            logits, boundary = model(batch_x)

            classification_loss = F.cross_entropy(
                logits,
                batch_y,
            )

            boundary_loss = contrastive_loss(
                boundary,
                batch_y,
            )

            loss = (
                classification_loss
                + CONTRASTIVE_WEIGHT * boundary_loss
            )

            loss.backward()

            optimizer.step()

            total_loss += loss.item() * len(batch_y)

        _, val_loss = evaluate(
            model,
            val_x,
            val_y,
            device,
        )

        train_loss = total_loss / len(train)

        print(
            f"Epoch {epoch + 1:02d}/{EPOCHS} | "
            f"Train: {train_loss:.4f} | "
            f"Validation: {val_loss:.4f}"
        )

        if val_loss < best_loss:

            best_loss = val_loss
            best_weights = copy.deepcopy(
                model.state_dict()
            )

            patience_counter = 0

        else:
            patience_counter += 1

        if patience_counter >= PATIENCE:
            print("Early stopping.")
            break

    if best_weights is None:
        raise RuntimeError("No valid model checkpoint was created.")

    model.load_state_dict(best_weights)

    print("\nEvaluating on held-out test data...")

    predictions, _ = evaluate(
        model,
        test_x,
        test_y,
        device,
    )

    accuracy = accuracy_score(
        test_y,
        predictions,
    )

    # Use the complete trained label set for the main macro-F1.
    all_label_ids = np.arange(len(label_encoder.classes_))

    macro_f1 = f1_score(
        test_y,
        predictions,
        labels=all_label_ids,
        average="macro",
        zero_division=0,
    )

    observed_ids = sorted(
        set(test_y.tolist()) | set(predictions.tolist())
    )

    observed_macro_f1 = f1_score(
        test_y,
        predictions,
        labels=observed_ids,
        average="macro",
        zero_division=0,
    )

    print("\n========== RESULTS ==========")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro-F1 (all trained classes): {macro_f1:.4f}")
    print(f"Macro-F1 (observed classes): {observed_macro_f1:.4f}")

    actual_names = label_encoder.inverse_transform(test_y)
    predicted_names = label_encoder.inverse_transform(predictions)

    # Save model without overwriting V1.
    torch.save(
        {
            "state_dict": model.cpu().state_dict(),
            "classes": label_encoder.classes_.tolist(),
            "backbone": BACKBONE,
            "embedding_dim": int(train_x.shape[1]),
            "architecture": "dual_branch_supervised_contrastive_v2",
        },
        MODEL_DIR / "vyom_dual_encoder_v2.pt",
    )

    metrics = {
        "model": "dual_encoder_v2",
        "train": len(train),
        "validation_evaluable": len(val),
        "test_total": int(len(test) + test_unknown.sum()),
        "test_evaluable": len(test),
        "test_excluded_unseen_labels": int(test_unknown.sum()),
        "training_classes": len(label_encoder.classes_),
        "accuracy": float(accuracy),
        "macro_f1_all_trained_classes": float(macro_f1),
        "macro_f1_observed_classes": float(observed_macro_f1),
        "warning": (
            "Provisional synthetic-derived labels. "
            "Missing classes and excluded test labels limit evaluation. "
            "Not a real-world accuracy estimate."
        ),
    }

    (REPORT_DIR / "dual_encoder_v2_metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    report = classification_report(
        test_y,
        predictions,
        labels=all_label_ids,
        target_names=label_encoder.classes_,
        output_dict=True,
        zero_division=0,
    )

    pd.DataFrame(report).T.to_csv(
        REPORT_DIR / "dual_encoder_v2_classification_report.csv"
    )

    cm = confusion_matrix(
        test_y,
        predictions,
        labels=all_label_ids,
    )

    pd.DataFrame(
        cm,
        index=label_encoder.classes_,
        columns=label_encoder.classes_,
    ).to_csv(
        REPORT_DIR / "dual_encoder_v2_confusion_matrix.csv"
    )

    # Include identifiers to simplify error analysis.
    output = pd.DataFrame({
        "actual": actual_names,
        "predicted": predicted_names,
        "correct": actual_names == predicted_names,
        "transaction_text": test["text_input"].to_numpy(),
        "split_group": test["split_group"].to_numpy(),
    })

    if "review_case_id" in test.columns:
        output.insert(
            0,
            "review_case_id",
            test["review_case_id"].to_numpy(),
        )

    output.to_excel(
        REPORT_DIR / "dual_encoder_v2_predictions.xlsx",
        index=False,
    )

    print("\nFiles saved successfully!")
    print("Model: models/vyom_dual_encoder_v2.pt")
    print("Metrics: reports/dual_encoder_v2_metrics.json")
    print("Predictions: reports/dual_encoder_v2_predictions.xlsx")
    print("Confusion matrix: reports/dual_encoder_v2_confusion_matrix.csv")


if __name__ == "__main__":
    main()
