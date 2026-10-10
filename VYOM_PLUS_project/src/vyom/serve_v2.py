"""FastAPI server for the VYOM+ voucher classifier (models/voucher_classifier.pkl).

Run from the VYOM_PLUS_project folder:

    uvicorn vyom.serve_v2:app --app-dir src --port 8000

Then open http://127.0.0.1:8000/docs to try the endpoints.

The model is a TF-IDF + LogisticRegression pipeline over wide-schema records
(columns such as "PO Number", "Supplier", "Vendor Name"), serialized with
vyom.adapter.serialize_wide_row ("Column: value | ..."). It predicts 24 classes.

Caution: its vocabulary contains identifier values from the 120-record
development workbook (Voucher_Classification_Test_Cases_v2.xlsx), so it was
trained on that workbook; accuracy on it says nothing about new data. Scores are
uncalibrated class probabilities, not confidence. Label or output columns sent
with a record are dropped before prediction.
"""

from io import BytesIO
import pickle
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from vyom.adapter import LABEL_COLUMN, serialize_wide_row


ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "models/voucher_classifier.pkl"
MAX_ROWS = 5000
TOP_K = 3
STATUS = ("Trained on the 120-record development workbook (its identifiers are in the model vocabulary); "
          "not validated on independent data. Scores are uncalibrated.")
# Label-bearing and output columns are never passed to the model.
DROPPED = {LABEL_COLUMN, "voucher_type", "document_type", "target", "Correct", "Predicted Voucher Category",
           "Model Score (Uncalibrated)", "Top 3 (Uncalibrated)", "Review Required"}

EXAMPLE = {"PO Number": "PO1234567", "Supplier": "Digital Solutions Corp", "Ordering Company": "Assembly Line Ltd",
           "Item": "Textiles", "Quantity Required": 815, "Unit Rate": 200.55, "Currency Code": "INR"}


class PredictRequest(BaseModel):
    records: List[Dict[str, Any]] = Field(
        ..., min_length=1, max_length=MAX_ROWS,
        description="Wide-schema records: column name -> value, as in the voucher test-case workbook.",
        json_schema_extra={"example": [EXAMPLE]})


class ClassScore(BaseModel):
    label: str
    score_uncalibrated: float


class Prediction(BaseModel):
    predicted_voucher_category: str
    top_predictions: List[ClassScore]
    serialized_input: str
    ignored_fields: List[str]


class PredictResponse(BaseModel):
    model: str
    status: str
    predictions: List[Prediction]


def load_model():
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model not found: {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


MODEL = load_model()

app = FastAPI(
    title="VYOM+ Voucher Classifier (voucher_classifier.pkl)",
    description=STATUS,
    version="voucher_classifier",
)


def predict_frame(frame: pd.DataFrame) -> List[Prediction]:
    ignored = sorted(c for c in frame.columns if c in DROPPED)
    texts = frame.drop(columns=ignored).apply(serialize_wide_row, axis=1).tolist()
    proba = MODEL.predict_proba(texts)
    classes = list(MODEL.classes_)
    out = []
    for text, row in zip(texts, proba):
        order = row.argsort()[::-1][:TOP_K]
        out.append(Prediction(
            predicted_voucher_category=classes[order[0]],
            top_predictions=[ClassScore(label=classes[i], score_uncalibrated=round(float(row[i]), 4)) for i in order],
            serialized_input=text,
            ignored_fields=ignored,
        ))
    return out


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "model": MODEL_PATH.name}


@app.get("/model")
def model_info() -> Dict:
    vectorizer, classifier = MODEL.steps[0][1], MODEL.steps[-1][1]
    return {
        "model": MODEL_PATH.name,
        "status": STATUS,
        "pipeline": [name for name, _ in MODEL.steps],
        "classifier": type(classifier).__name__,
        "vocabulary_size": len(vectorizer.vocabulary_),
        "labels": list(MODEL.classes_),
        "input": "wide-schema records serialized as 'Column: value | ...' (vyom.adapter.serialize_wide_row)",
    }


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    frame = pd.DataFrame(request.records)
    return PredictResponse(model=MODEL_PATH.name, status=STATUS, predictions=predict_frame(frame))


@app.post("/predict/file")
async def predict_file(file: UploadFile = File(...)):
    """Upload an .xlsx or .csv in the workbook layout; returns it with prediction columns added."""
    content = await file.read()
    name = (file.filename or "").lower()
    try:
        frame = pd.read_csv(BytesIO(content)) if name.endswith(".csv") else pd.read_excel(BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")
    if frame.empty or len(frame) > MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"File must contain 1 to {MAX_ROWS} rows")
    frame.columns = [str(c).strip() for c in frame.columns]
    preds = predict_frame(frame)
    out = frame.copy()
    out["Predicted Voucher Category"] = [p.predicted_voucher_category for p in preds]
    out["Model Score (Uncalibrated)"] = [p.top_predictions[0].score_uncalibrated for p in preds]
    out["Top 3 (Uncalibrated)"] = [" | ".join(f"{s.label} ({s.score_uncalibrated:.3f})" for s in p.top_predictions)
                                   for p in preds]
    buffer = BytesIO()
    out.to_excel(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(
        buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="voucher_classifier_predictions.xlsx"'})
