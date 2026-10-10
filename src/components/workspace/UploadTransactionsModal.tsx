import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';
import { Download, FileSpreadsheet, Loader2, Sparkles, Upload } from 'lucide-react';
import { Modal, ErrorNote } from './Modal';
import { ScoreChip } from './format';
import { analyzeFile, predictFile, type ClassScore, type InputRecord } from '../../api/vyom';
import { REVIEW_SCORE_THRESHOLD, useWorkspace, type ClassifiedRow } from '../../context/WorkspaceContext';

const MAX_BYTES = 10 * 1024 * 1024;
const PREVIEW_ROWS = 50;
const RESULT_ROWS = 100;
const OUTPUT_COLUMNS = ['Predicted Voucher Category', 'Model Score (Uncalibrated)', 'Top 3 (Uncalibrated)'];

interface SheetPreview {
  name: string;
  headers: string[];
  rows: string[][];
  totalRows: number;
}

function parseTop3(text: unknown): ClassScore[] {
  return String(text ?? '')
    .split('|')
    .map((part) => part.trim().match(/^(.*)\s+\(([\d.]+)\)$/))
    .filter((m): m is RegExpMatchArray => m !== null)
    .map((m) => ({ label: m[1].trim(), score_uncalibrated: Number(m[2]) }));
}

async function readPreview(file: File): Promise<SheetPreview[]> {
  const wb = XLSX.read(await file.arrayBuffer(), { type: 'array', cellDates: true });
  return wb.SheetNames.map((name) => {
    const grid = XLSX.utils.sheet_to_json<string[]>(wb.Sheets[name], { header: 1, defval: '', raw: false, blankrows: false });
    const [headers = [], ...rows] = grid;
    return { name, headers: headers.map(String), rows: rows.slice(0, PREVIEW_ROWS).map((r) => r.map(String)), totalRows: rows.length };
  });
}

function PreviewTable({ headers, rows, firstRowNumber = 2 }: { headers: string[]; rows: (string | number)[][]; firstRowNumber?: number }) {
  return (
    <div className="max-h-[420px] overflow-auto rounded-xl border" style={{ borderColor: 'var(--ws-border)' }}>
      <table className="ws-table text-[12.5px]">
        <thead className="sticky top-0" style={{ background: 'var(--ws-surface-2)' }}>
          <tr>
            <th>Row</th>
            {headers.map((h, i) => <th key={i}>{h || `Column ${i + 1}`}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td className="ws-mono" style={{ color: 'var(--ws-muted)' }}>{firstRowNumber + i}</td>
              {headers.map((_, j) => <td key={j} className="max-w-[240px] truncate" title={String(r[j] ?? '')}>{String(r[j] ?? '')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function UploadTransactionsModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const { addRows, setAnalysis, businessGstin, setBusinessGstin } = useWorkspace();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [sheets, setSheets] = useState<SheetPreview[]>([]);
  const [activeSheet, setActiveSheet] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState<'read' | 'classify' | 'gst' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [classified, setClassified] = useState<{ rows: ClassifiedRow[]; blob: Blob; sheet: string } | null>(null);

  const choose = async (f: File) => {
    setError(null);
    setClassified(null);
    const ext = f.name.split('.').pop()?.toLowerCase();
    if (!ext || !['xlsx', 'xlsm', 'csv'].includes(ext)) {
      setError('Choose an .xlsx, .xlsm or .csv file.');
      return;
    }
    if (f.size > MAX_BYTES) {
      setError('The file is larger than 10 MB.');
      return;
    }
    setBusy('read');
    try {
      const parsed = await readPreview(f);
      if (!parsed.some((s) => s.totalRows > 0)) throw new Error('The file has no data rows.');
      setFile(f);
      setSheets(parsed);
      setActiveSheet(Math.max(0, parsed.findIndex((s) => s.totalRows > 0)));
    } catch (e) {
      setFile(null);
      setSheets([]);
      setError((e as Error).message || 'The file could not be read.');
    } finally {
      setBusy(null);
    }
  };

  const classify = async () => {
    if (!file) return;
    setBusy('classify');
    setError(null);
    try {
      const blob = await predictFile(file);
      const wb = XLSX.read(await blob.arrayBuffer(), { type: 'array', cellDates: true });
      const sheet = wb.SheetNames[0];
      const objects = XLSX.utils.sheet_to_json<Record<string, unknown>>(wb.Sheets[sheet], { defval: null, raw: true });
      const sourceSheet = file.name.toLowerCase().endsWith('.csv') ? null : sheets[0]?.name ?? null;
      const now = new Date().toISOString();
      const rows: ClassifiedRow[] = objects.map((o, i) => {
        const record: InputRecord = {};
        for (const [k, v] of Object.entries(o)) {
          if (OUTPUT_COLUMNS.includes(k) || v === null || v === '') continue;
          record[k] = v instanceof Date ? v.toISOString().slice(0, 10) : (v as string | number | boolean);
        }
        const score = Number(o['Model Score (Uncalibrated)']);
        return {
          id: `file-${Date.now()}-${i}`,
          source: 'file',
          fileName: file.name,
          sourceRef: sourceSheet ? `${sourceSheet}!R${i + 2}` : `R${i + 2}`,
          createdAt: now,
          record,
          category: String(o['Predicted Voucher Category'] ?? 'Unknown'),
          score: Number.isFinite(score) ? score : null,
          top: parseTop3(o['Top 3 (Uncalibrated)']),
        };
      });
      addRows(rows, { id: `upload-${Date.now()}`, fileName: file.name, rows: rows.length, createdAt: now });
      setClassified({ rows, blob, sheet: sourceSheet ?? 'CSV' });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const download = () => {
    if (!classified || !file) return;
    const url = URL.createObjectURL(classified.blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${file.name.replace(/\.[^.]+$/, '')}_classified.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const runGst = async () => {
    if (!file) return;
    setBusy('gst');
    setError(null);
    try {
      const analysis = await analyzeFile(file, businessGstin.trim() || undefined);
      setAnalysis({ analysis, sourceLabel: file.name, createdAt: new Date().toISOString() });
      onClose();
      navigate('/gst');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const sheet = sheets[activeSheet];
  const reviewCount = classified?.rows.filter((r) => r.score === null || r.score < REVIEW_SCORE_THRESHOLD).length ?? 0;
  const categories = classified ? new Set(classified.rows.map((r) => r.category)).size : 0;
  const shownColumns = classified
    ? Array.from(new Set(classified.rows.slice(0, RESULT_ROWS).flatMap((r) => Object.keys(r.record)))).slice(0, 5)
    : [];

  return (
    <Modal
      title="Upload Transactions"
      subtitle="Preview your workbook, classify it with POST /predict/file, then run GST analysis."
      onClose={onClose}
      wide
      footer={
        <>
          <button type="button" className="ws-btn-outline" onClick={onClose}>Close</button>
          {classified && (
            <button type="button" className="ws-btn-outline" onClick={download}>
              <Download className="size-4" /> Download classified .xlsx
            </button>
          )}
          {file && (
            <button type="button" className={classified ? 'ws-btn-gold' : 'ws-btn-outline'} onClick={runGst} disabled={busy !== null}>
              {busy === 'gst' ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
              Run GST analysis
            </button>
          )}
          {file && !classified && (
            <button type="button" className="ws-btn-gold" onClick={classify} disabled={busy !== null}>
              {busy === 'classify' ? <Loader2 className="size-4 animate-spin" /> : null}
              Classify transactions
            </button>
          )}
        </>
      }
    >
      <input ref={inputRef} type="file" accept=".xlsx,.xlsm,.csv" className="hidden"
        onChange={(e) => e.target.files?.[0] && choose(e.target.files[0])} />

      {!file && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files[0]) choose(e.dataTransfer.files[0]); }}
          onClick={() => inputRef.current?.click()}
          className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-14 text-center transition-colors"
          style={{ borderColor: dragging ? 'var(--ws-gold)' : 'var(--ws-border-strong)', background: dragging ? 'var(--ws-gold-soft)' : 'var(--ws-surface)' }}
        >
          {busy === 'read' ? <Loader2 className="size-10 animate-spin" style={{ color: 'var(--ws-gold)' }} />
            : <Upload className="size-10" style={{ color: 'var(--ws-gold)' }} />}
          <p className="ws-serif mt-4 text-2xl">Drop your transaction file here</p>
          <p className="mt-1 text-sm" style={{ color: 'var(--ws-text-2)' }}>or click to browse · .xlsx, .xlsm or .csv up to 10 MB</p>
        </div>
      )}

      {error && <div className="mt-4"><ErrorNote message={error} /></div>}

      {file && !classified && sheet && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <FileSpreadsheet className="size-6" style={{ color: 'var(--ws-gold)' }} />
              <div>
                <p className="text-sm font-semibold">{file.name}</p>
                <p className="text-xs" style={{ color: 'var(--ws-muted)' }}>
                  {(file.size / 1024).toFixed(0)} KB · {sheets.length} sheet{sheets.length === 1 ? '' : 's'} ·{' '}
                  {sheets.reduce((s, x) => s + x.totalRows, 0)} data rows
                </p>
              </div>
            </div>
            <button type="button" className="ws-btn-ghost text-sm" onClick={() => { setFile(null); setSheets([]); }}>
              Choose another file
            </button>
          </div>

          {sheets.length > 1 && (
            <div className="flex flex-wrap gap-2">
              {sheets.map((s, i) => (
                <button key={s.name} type="button" onClick={() => setActiveSheet(i)}
                  className={`ws-chip ${i === activeSheet ? 'ws-chip-gold' : 'ws-chip-info'} cursor-pointer`}>
                  {s.name} · {s.totalRows}
                </button>
              ))}
            </div>
          )}
          {sheets.length > 1 && (
            <p className="text-xs" style={{ color: 'var(--ws-text-2)' }}>
              Classification (/predict/file) reads the first sheet, “{sheets[0].name}”. GST analysis reads every sheet.
            </p>
          )}

          <PreviewTable headers={sheet.headers} rows={sheet.rows} />
          <p className="text-xs" style={{ color: 'var(--ws-muted)' }}>
            Showing {Math.min(PREVIEW_ROWS, sheet.totalRows)} of {sheet.totalRows} rows in “{sheet.name}”.
          </p>

          <label className="block max-w-sm">
            <span className="ws-label">Business GSTIN (optional, for GST analysis)</span>
            <input className="ws-input ws-mono" placeholder="e.g. 27AAACB1234C1ZF" value={businessGstin}
              onChange={(e) => setBusinessGstin(e.target.value.toUpperCase())} />
          </label>
        </div>
      )}

      {classified && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <span className="ws-chip ws-chip-ok">{classified.rows.length} rows classified · saved to workspace</span>
            <span className="ws-chip ws-chip-gold">{categories} categories</span>
            <span className={`ws-chip ${reviewCount ? 'ws-chip-warn' : 'ws-chip-ok'}`}>
              {reviewCount} with score below {REVIEW_SCORE_THRESHOLD} (review)
            </span>
          </div>
          <div className="max-h-[440px] overflow-auto rounded-xl border" style={{ borderColor: 'var(--ws-border)' }}>
            <table className="ws-table text-[12.5px]">
              <thead className="sticky top-0" style={{ background: 'var(--ws-surface-2)' }}>
                <tr>
                  <th>Source</th>
                  <th>Predicted category</th>
                  <th>Score</th>
                  <th>Runner-up</th>
                  {shownColumns.map((c) => <th key={c}>{c}</th>)}
                </tr>
              </thead>
              <tbody>
                {classified.rows.slice(0, RESULT_ROWS).map((r) => (
                  <tr key={r.id}>
                    <td className="ws-mono whitespace-nowrap" style={{ color: 'var(--ws-muted)' }}>{r.sourceRef}</td>
                    <td className="font-semibold whitespace-nowrap">{r.category}</td>
                    <td><ScoreChip score={r.score} /></td>
                    <td className="whitespace-nowrap" style={{ color: 'var(--ws-text-2)' }}>
                      {r.top[1] ? `${r.top[1].label} (${r.top[1].score_uncalibrated.toFixed(2)})` : '—'}
                    </td>
                    {shownColumns.map((c) => (
                      <td key={c} className="max-w-[200px] truncate" title={String(r.record[c] ?? '')}>{String(r.record[c] ?? '')}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs" style={{ color: 'var(--ws-muted)' }}>
            Showing {Math.min(RESULT_ROWS, classified.rows.length)} of {classified.rows.length} rows from “{classified.sheet}”.
            Scores are uncalibrated, not the probability of being correct.
          </p>
          <label className="block max-w-sm">
            <span className="ws-label">Business GSTIN (optional, for GST analysis)</span>
            <input className="ws-input ws-mono" placeholder="e.g. 27AAACB1234C1ZF" value={businessGstin}
              onChange={(e) => setBusinessGstin(e.target.value.toUpperCase())} />
          </label>
        </div>
      )}
    </Modal>
  );
}
