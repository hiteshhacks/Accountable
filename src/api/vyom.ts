// Typed client for the VYOM+ FastAPI server (VYOM_PLUS_project/src/vyom/serve_v2.py).

const API_BASE = ((import.meta.env.VITE_API_BASE as string | undefined) ?? '/api').replace(/\/$/, '');

export type RecordValue = string | number | boolean | null;
export type InputRecord = Record<string, RecordValue>;

export interface ClassScore {
  label: string;
  score_uncalibrated: number;
}

export interface Prediction {
  predicted_voucher_category: string;
  top_predictions: ClassScore[];
  serialized_input: string;
  ignored_fields: string[];
}

export interface PredictResponse {
  model: string;
  status: string;
  predictions: Prediction[];
}

export type Severity = 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

export interface Discrepancy {
  code: string;
  severity: Severity;
  message: string;
  source_rows: string[];
  evidence: Record<string, unknown>;
  recommended_action: string;
  status: 'CONFIRMED' | 'POSSIBLE';
  origin: 'validation' | 'classification' | 'llm';
}

export interface RowFinding {
  code: string;
  severity: Severity;
  status: 'CONFIRMED' | 'POSSIBLE';
}

export interface AnalysisRow {
  source_ref: string;
  category: string;
  score_uncalibrated: number | null;
  ambiguous: boolean;
  review_flags: string[];
  group: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  party: string | null;
  counterparty_gstin: string | null;
  taxable_value: string | null;
  tax: string | null;
  currency: string | null;
  findings: RowFinding[];
}

export interface Calculation {
  name: string;
  value: string | null;
  status: 'COMPLETE' | 'INCOMPLETE' | 'UNRESOLVED' | 'NOT_APPLICABLE';
  rows_included: number;
  rows_missing: number;
  currency: string;
}

export type ReportStatus = 'ANALYSIS_COMPLETE' | 'REVIEW_REQUIRED' | 'INSUFFICIENT_DATA' | 'PROCESSING_FAILED';

export interface GstAnalysis {
  success: boolean;
  report: string;
  status: ReportStatus;
  warnings: string[];
  discrepancies: Discrepancy[];
  request_id: string;
  errors: string[];
  summary: {
    accounting_summary?: { transaction_count: number; calculations: Calculation[]; base_currency: string };
    gst_summary?: { calculations: Calculation[] };
    filing_readiness?: { level: string; reasons: string[]; note: string };
    classification?: { rows: AnalysisRow[]; ambiguous_rows: number; taxonomy_categories_not_predictable: string[] };
    narrative?: { available: boolean; status: string | null; model: string | null; error_kind: string | null; message: string | null };
    duration_ms?: number;
  };
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function call(path: string, init: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(
      `Cannot reach the VYOM API (${API_BASE}). Start it from VYOM_PLUS_project with: ` +
        'uvicorn vyom.serve_v2:app --app-dir src --port 8000',
      0,
    );
  }
  if (res.ok) return res;
  let message = res.statusText || `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (Array.isArray(body?.errors) && body.errors.length) message = body.errors.join(' ');
    else if (typeof body?.detail === 'string') message = body.detail;
    else if (Array.isArray(body?.detail)) {
      message = body.detail.map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).join('.')}: ${d.msg}`).join('; ');
    }
  } catch {
    /* non-JSON error body: keep the status text */
  }
  throw new ApiError(message, res.status);
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

/** POST /predict - classify records entered by hand. */
export async function predictRecords(records: InputRecord[]): Promise<PredictResponse> {
  return (await call('/predict', json({ records }))).json();
}

/** POST /predict/file - classify an uploaded workbook; returns the classified .xlsx. */
export async function predictFile(file: File): Promise<Blob> {
  const form = new FormData();
  form.append('file', file);
  return (await call('/predict/file', { method: 'POST', body: form })).blob();
}

/** POST /gst/analyze - GST analysis of JSON records. */
export async function analyzeRecords(records: InputRecord[], businessGstin?: string): Promise<GstAnalysis> {
  return (await call('/gst/analyze', json({ records, business_gstin: businessGstin || null }))).json();
}

/** POST /gst/analyze/file - GST analysis of an uploaded workbook (all sheets). */
export async function analyzeFile(file: File, businessGstin?: string): Promise<GstAnalysis> {
  const form = new FormData();
  form.append('file', file);
  if (businessGstin) form.append('business_gstin', businessGstin);
  return (await call('/gst/analyze/file', { method: 'POST', body: form })).json();
}

export async function health(): Promise<boolean> {
  try {
    await call('/health', { method: 'GET' });
    return true;
  } catch {
    return false;
  }
}
