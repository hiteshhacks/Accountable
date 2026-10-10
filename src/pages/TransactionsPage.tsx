import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, Plus, Sparkles, Trash2, Upload } from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { CreateInvoiceModal } from '../components/workspace/CreateInvoiceModal';
import { UploadTransactionsModal } from '../components/workspace/UploadTransactionsModal';
import { ErrorNote } from '../components/workspace/Modal';
import { ScoreChip, formatDate, formatINR } from '../components/workspace/format';
import { analyzeRecords } from '../api/vyom';
import {
  AMOUNT_FIELDS, INVOICE_FIELDS, PARTY_FIELDS, REVIEW_SCORE_THRESHOLD, pickField, useWorkspace,
} from '../context/WorkspaceContext';

const PAGE = 100;

export function TransactionsPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const { rows, clearWorkspace, setAnalysis, businessGstin } = useWorkspace();
  const reviewOnly = params.get('view') === 'review';
  const query = params.get('q') ?? '';
  const [category, setCategory] = useState('all');
  const [limit, setLimit] = useState(PAGE);
  const [modal, setModal] = useState<'invoice' | 'upload' | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const categories = useMemo(() => Array.from(new Set(rows.map((r) => r.category))).sort(), [rows]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (reviewOnly && !(r.score === null || r.score < REVIEW_SCORE_THRESHOLD)) return false;
      if (category !== 'all' && r.category !== category) return false;
      if (!q) return true;
      return [r.category, r.sourceRef, r.fileName ?? '', ...Object.values(r.record).map(String)]
        .some((v) => v.toLowerCase().includes(q));
    });
  }, [rows, reviewOnly, category, query]);

  const setQuery = (q: string) => {
    const next = new URLSearchParams(params);
    if (q) next.set('q', q); else next.delete('q');
    setParams(next, { replace: true });
  };

  const analyzeWorkspace = async () => {
    setBusy(true);
    setError(null);
    try {
      const records = filtered.map((r) => r.record);
      const analysis = await analyzeRecords(records, businessGstin.trim() || undefined);
      setAnalysis({ analysis, sourceLabel: `${records.length} workspace transactions`, createdAt: new Date().toISOString() });
      navigate('/gst');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppLayout>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="ws-eyebrow">{reviewOnly ? 'Review Queue' : 'Transactions'}</p>
          <h1 className="mt-2 text-[44px] leading-tight">{reviewOnly ? 'Rows Needing Review' : 'Classified Transactions'}</h1>
          <p className="mt-1 text-sm" style={{ color: 'var(--ws-text-2)' }}>
            {reviewOnly
              ? `Rows whose top model score is below ${REVIEW_SCORE_THRESHOLD}. Scores are uncalibrated.`
              : 'Every row classified from manual entries and uploaded files, stored in this browser.'}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" className="ws-btn-outline" onClick={() => setModal('invoice')}><Plus className="size-4" /> Create Invoice</button>
          <button type="button" className="ws-btn-gold" onClick={() => setModal('upload')}><Upload className="size-4" /> Upload Transactions</button>
        </div>
      </div>

      <div className="ws-card px-5 py-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="min-w-[220px] flex-1">
            <span className="ws-label">Search</span>
            <input className="ws-input" placeholder="Category, party, invoice no., value…" value={query}
              onChange={(e) => setQuery(e.target.value)} />
          </label>
          <label className="w-[230px]">
            <span className="ws-label">Category</span>
            <select className="ws-input" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="all">All categories</option>
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <button type="button" className="ws-btn-outline" disabled={busy || filtered.length === 0} onClick={analyzeWorkspace}
            title="POST /gst/analyze with the rows shown">
            {busy ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            GST analysis of {filtered.length} rows
          </button>
          {rows.length > 0 && (
            <button type="button" className="ws-btn-ghost" onClick={() => window.confirm('Remove all classified rows and the saved analysis from this browser?') && clearWorkspace()}>
              <Trash2 className="size-4" /> Clear
            </button>
          )}
        </div>
        {error && <div className="mt-3"><ErrorNote message={error} /></div>}
      </div>

      <div className="ws-card mt-5 overflow-hidden">
        {filtered.length === 0 ? (
          <p className="px-6 py-14 text-center text-sm" style={{ color: 'var(--ws-text-2)' }}>
            {rows.length === 0 ? 'No transactions yet. Create an invoice or upload a workbook to get started.' : 'No rows match these filters.'}
          </p>
        ) : (
          <div className="overflow-x-auto px-3 py-2">
            <table className="ws-table">
              <thead>
                <tr>
                  <th>Source</th><th>Invoice / Doc No</th><th>Party</th><th>Amount</th>
                  <th>Predicted Category</th><th>Score</th><th>Runner-up</th><th>Added</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, limit).map((r) => (
                  <tr key={r.id}>
                    <td className="whitespace-nowrap">
                      <span className="ws-mono text-xs" style={{ color: 'var(--ws-muted)' }}>{r.sourceRef}</span>
                      {r.fileName && <div className="max-w-[160px] truncate text-xs" style={{ color: 'var(--ws-text-2)' }} title={r.fileName}>{r.fileName}</div>}
                    </td>
                    <td className="ws-mono font-semibold whitespace-nowrap">{pickField(r.record, INVOICE_FIELDS) ?? '—'}</td>
                    <td className="max-w-[200px] truncate">{pickField(r.record, PARTY_FIELDS) ?? '—'}</td>
                    <td className="whitespace-nowrap">{formatINR(pickField(r.record, AMOUNT_FIELDS))}</td>
                    <td className="font-semibold whitespace-nowrap">{r.category}</td>
                    <td><ScoreChip score={r.score} /></td>
                    <td className="whitespace-nowrap text-xs" style={{ color: 'var(--ws-text-2)' }}>
                      {r.top[1] ? `${r.top[1].label} (${r.top[1].score_uncalibrated.toFixed(2)})` : '—'}
                    </td>
                    <td className="whitespace-nowrap text-xs" style={{ color: 'var(--ws-muted)' }}>{formatDate(r.createdAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length > limit && (
              <div className="py-4 text-center">
                <button type="button" className="ws-btn-outline" onClick={() => setLimit((l) => l + PAGE)}>
                  Show more ({filtered.length - limit} remaining)
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {modal === 'invoice' && <CreateInvoiceModal onClose={() => setModal(null)} />}
      {modal === 'upload' && <UploadTransactionsModal onClose={() => setModal(null)} />}
    </AppLayout>
  );
}
