"""Predict voucher categories for a structured Excel workbook."""
from pathlib import Path
import argparse
import pickle
import pandas as pd
from vyom.preprocessing import normalize_columns, make_text

DEFAULT_MODEL = Path(__file__).resolve().parents[2] / 'models' / 'vyom_plus_tfidf_baseline_model.pkl'
DEFAULT_INPUT = Path(__file__).resolve().parents[2] / 'data' / 'input' / 'sample_transactions.xlsx'
DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / 'data' / 'output' / 'classified_transactions.xlsx'

def main():
    parser = argparse.ArgumentParser(description='Classify voucher types in a structured Excel file.')
    parser.add_argument('--input', default=str(DEFAULT_INPUT), help='Path to input .xlsx file')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT), help='Path to output .xlsx file')
    parser.add_argument('--model', default=str(DEFAULT_MODEL), help='Path to trained .pkl model')
    parser.add_argument('--review-threshold', type=float, default=0.60, help='Below this uncalibrated score, flag for review')
    args = parser.parse_args()

    input_path, output_path = Path(args.input), Path(args.output)
    if not input_path.exists():
        raise FileNotFoundError(f'Input file not found: {input_path}')
    if not Path(args.model).exists():
        raise FileNotFoundError(f'Model not found: {args.model}')
    df = pd.read_excel(input_path)
    if df.empty:
        raise ValueError('Input Excel contains no transaction rows.')
    df = normalize_columns(df)
    texts = df.apply(make_text, axis=1)
    empty_mask = texts.str.strip().eq('')
    with open(args.model, 'rb') as f:
        model = pickle.load(f)
    predictions = []
    scores = []
    top_three = []
    probs = model.predict_proba(texts.tolist())
    classes = model.classes_
    for i, p in enumerate(probs):
        order = p.argsort()[::-1][:3]
        predictions.append(str(classes[order[0]]))
        scores.append(float(p[order[0]]))
        top_three.append(' | '.join(f'{classes[j]} ({p[j]:.3f})' for j in order))
    df['predicted_voucher_type'] = predictions
    df['model_score_uncalibrated'] = [round(x, 4) for x in scores]
    df['top_3_predictions'] = top_three
    df['review_status'] = [
        'NEEDS_REVIEW_EMPTY_INPUT' if empty_mask.iloc[i] else
        'REVIEW_LOW_SCORE' if scores[i] < args.review_threshold else
        'MODEL_PREDICTION_REVIEW_REQUIRED'
        for i in range(len(df))
    ]
    # All predictions are provisional; even high scores are not verified accounting decisions.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)
    print(f'Input rows: {len(df)}')
    print(f'Model classes available: {len(classes)}')
    print(f'Rows with empty usable input fields: {int(empty_mask.sum())}')
    print(f'Rows below review threshold: {sum(s < args.review_threshold for s in scores)}')
    print(f'Output written to: {output_path.resolve()}')
    print('NOTE: scores are uncalibrated and all predictions require validation before business use.')

if __name__ == '__main__':
    main()
