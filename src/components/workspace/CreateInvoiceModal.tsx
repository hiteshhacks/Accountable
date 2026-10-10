import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Plus, Sparkles, Trash2 } from 'lucide-react';
import { Modal, ErrorNote } from './Modal';
import { ScoreChip } from './format';
import { analyzeRecords, predictRecords, type InputRecord, type Prediction } from '../../api/vyom';
import { useWorkspace } from '../../context/WorkspaceContext';

// Column names follow the classifier's wide workbook schema and the GST layer's aliases.
const FIELDS: { key: string; label: string; type?: string; placeholder?: string }[] = [
  { key: 'Document Number', label: 'Invoice / Document No', placeholder: 'e.g. SAL-1001' },
  { key: 'Document Date', label: 'Invoice Date', type: 'date' },
  { key: 'Vendor Name', label: 'Vendor / Supplier', placeholder: 'Supplier name' },
  { key: 'Customer', label: 'Customer', placeholder: 'Customer name' },
  { key: 'Supplier GSTIN', label: 'Supplier GSTIN', placeholder: '15-character GSTIN' },
  { key: 'Customer GSTIN', label: 'Customer GSTIN', placeholder: '15-character GSTIN' },
  { key: 'Product', label: 'Product / Item', placeholder: 'Goods or service' },
  { key: 'Units', label: 'Quantity', type: 'number' },
  { key: 'Base Amount', label: 'Taxable Value (₹)', type: 'number' },
  { key: 'GST Rate', label: 'GST Rate (%)', type: 'number' },
  { key: 'CGST', label: 'CGST (₹)', type: 'number' },
  { key: 'SGST', label: 'SGST (₹)', type: 'number' },
  { key: 'IGST', label: 'IGST (₹)', type: 'number' },
  { key: 'Invoice Value', label: 'Invoice Total (₹)', type: 'number' },
  { key: 'Mode of Payment', label: 'Mode of Payment', placeholder: 'e.g. NEFT' },
  { key: 'Original Invoice Ref', label: 'Original Invoice Ref (notes)', placeholder: 'For credit/debit notes' },
];

function buildRecord(values: Record<string, string>, custom: { key: string; value: string }[]): InputRecord {
  const record: InputRecord = {};
  for (const f of FIELDS) {
    const v = (values[f.key] ?? '').trim();
    if (!v) continue;
    record[f.key] = f.type === 'number' && Number.isFinite(Number(v)) ? Number(v) : v;
  }
  for (const c of custom) {
    if (c.key.trim() && c.value.trim()) record[c.key.trim()] = c.value.trim();
  }
  return record;
}

export function CreateInvoiceModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const { addRows, setAnalysis, businessGstin } = useWorkspace();
  const [values, setValues] = useState<Record<string, string>>({});
  const [custom, setCustom] = useState<{ key: string; value: string }[]>([]);
  const [busy, setBusy] = useState<'predict' | 'gst' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ record: InputRecord; prediction: Prediction } | null>(null);
  const [saved, setSaved] = useState(false);

  const record = buildRecord(values, custom);
  const empty = Object.keys(record).length === 0;

  const classify = async () => {
    setBusy('predict');
    setError(null);
    setSaved(false);
    try {
      const res = await predictRecords([record]);
      setResult({ record, prediction: res.predictions[0] });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const save = () => {
    if (!result) return;
    const p = result.prediction;
    addRows([{
      id: `manual-${Date.now()}`,
      source: 'manual',
      fileName: null,
      sourceRef: 'Manual entry',
      createdAt: new Date().toISOString(),
      record: result.record,
      category: p.predicted_voucher_category,
      score: p.top_predictions[0]?.score_uncalibrated ?? null,
      top: p.top_predictions,
    }]);
    setSaved(true);
  };

  const runGst = async () => {
    if (!result) return;
    setBusy('gst');
    setError(null);
    try {
      if (!saved) save();
      const analysis = await analyzeRecords([result.record], businessGstin);
      setAnalysis({ analysis, sourceLabel: `Manual entry ${String(result.record['Document Number'] ?? '')}`.trim(),
        createdAt: new Date().toISOString() });
      onClose();
      navigate('/gst');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <Modal
      title="Create Invoice"
      subtitle="Enter a transaction manually. VYOM classifies it with POST /predict; empty fields are left out."
      onClose={onClose}
      wide
      footer={
        <>
          <button type="button" className="ws-btn-outline" onClick={onClose}>Close</button>
          {result && (
            <>
              <button type="button" className="ws-btn-outline" onClick={save} disabled={saved}>
                {saved ? 'Saved to workspace' : 'Save to workspace'}
              </button>
              <button type="button" className="ws-btn-outline" onClick={runGst} disabled={busy !== null}>
                {busy === 'gst' ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                Run GST analysis
              </button>
            </>
          )}
          <button type="button" className="ws-btn-gold" onClick={classify} disabled={empty || busy !== null}>
            {busy === 'predict' ? <Loader2 className="size-4 animate-spin" /> : null}
            Classify voucher
          </button>
        </>
      }
    >
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {FIELDS.map((f) => (
              <label key={f.key} className="block">
                <span className="ws-label">{f.label}</span>
                <input
                  className="ws-input"
                  type={f.type ?? 'text'}
                  step={f.type === 'number' ? 'any' : undefined}
                  placeholder={f.placeholder}
                  value={values[f.key] ?? ''}
                  onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                />
              </label>
            ))}
          </div>

          <div className="mt-5">
            <div className="mb-2 flex items-center justify-between">
              <span className="ws-label mb-0">Additional fields</span>
              <button type="button" className="ws-btn-ghost text-xs" onClick={() => setCustom((c) => [...c, { key: '', value: '' }])}>
                <Plus className="size-3.5" /> Add field
              </button>
            </div>
            {custom.length === 0 && (
              <p className="text-xs" style={{ color: 'var(--ws-muted)' }}>
                Add any other column, e.g. "PO Number", "Narration" or "Delivery Ref".
              </p>
            )}
            <div className="space-y-2">
              {custom.map((c, i) => (
                <div key={i} className="flex gap-2">
                  <input className="ws-input" placeholder="Column name" value={c.key}
                    onChange={(e) => setCustom((all) => all.map((x, j) => (j === i ? { ...x, key: e.target.value } : x)))} />
                  <input className="ws-input" placeholder="Value" value={c.value}
                    onChange={(e) => setCustom((all) => all.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))} />
                  <button type="button" className="ws-btn-ghost" aria-label="Remove field"
                    onClick={() => setCustom((all) => all.filter((_, j) => j !== i))}>
                    <Trash2 className="size-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {error && <ErrorNote message={error} />}
          {!result && !error && (
            <div className="ws-card p-5 text-sm" style={{ boxShadow: 'none', color: 'var(--ws-text-2)' }}>
              The predicted voucher category and the model's top three categories will appear here.
            </div>
          )}
          {result && (
            <div className="ws-card p-5" style={{ boxShadow: 'none' }}>
              <p className="ws-eyebrow">Predicted category</p>
              <p className="ws-serif mt-1 text-[30px] leading-tight">{result.prediction.predicted_voucher_category}</p>
              <div className="mt-2"><ScoreChip score={result.prediction.top_predictions[0]?.score_uncalibrated ?? null} /></div>
              <p className="ws-label mt-5">Top predictions (uncalibrated scores)</p>
              <ul className="space-y-2">
                {result.prediction.top_predictions.map((t) => (
                  <li key={t.label} className="text-sm">
                    <div className="flex justify-between gap-3"><span>{t.label}</span><span className="tabular-nums">{t.score_uncalibrated.toFixed(2)}</span></div>
                    <div className="mt-1 h-1.5 rounded-full" style={{ background: 'var(--viz-track)' }}>
                      <div className="h-1.5 rounded-full" style={{ width: `${Math.round(t.score_uncalibrated * 100)}%`, background: 'var(--ws-gold-btn)' }} />
                    </div>
                  </li>
                ))}
              </ul>
              <p className="ws-label mt-5">Text the model saw</p>
              <p className="ws-mono rounded-lg border p-3 text-xs break-words" style={{ borderColor: 'var(--ws-border)', background: 'var(--ws-bg)' }}>
                {result.prediction.serialized_input || '—'}
              </p>
              <p className="mt-3 text-xs" style={{ color: 'var(--ws-muted)' }}>
                Scores are uncalibrated and are not the probability that the category is correct.
              </p>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
