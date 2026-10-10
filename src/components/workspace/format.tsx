import { AlertTriangle, CheckCircle2, CircleHelp, XCircle } from 'lucide-react';
import type { ReportStatus, RowFinding } from '../../api/vyom';

export function formatINR(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  const n = typeof value === 'number' ? value : Number(String(value).replace(/[^0-9.-]/g, ''));
  if (!Number.isFinite(n)) return String(value);
  return `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

export function formatScore(score: number | null | undefined): string {
  return score === null || score === undefined ? '—' : score.toFixed(2);
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

const STATUS_STYLE: Record<ReportStatus, { cls: string; label: string }> = {
  ANALYSIS_COMPLETE: { cls: 'ws-chip-ok', label: 'Analysis complete' },
  REVIEW_REQUIRED: { cls: 'ws-chip-warn', label: 'Review required' },
  INSUFFICIENT_DATA: { cls: 'ws-chip-info', label: 'Insufficient data' },
  PROCESSING_FAILED: { cls: 'ws-chip-bad', label: 'Processing failed' },
};

export function ReportStatusChip({ status }: { status: ReportStatus }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.REVIEW_REQUIRED;
  return <span className={`ws-chip ${s.cls}`}>{s.label}</span>;
}

/** Row status from the backend's own findings: never claims "verified". */
export function RowGstStatus({ findings }: { findings: RowFinding[] }) {
  const relevant = findings.filter((f) => f.severity !== 'INFO');
  if (relevant.some((f) => f.severity === 'HIGH')) {
    return (
      <span className="ws-chip ws-chip-bad" title={relevant.map((f) => `${f.code} (${f.status})`).join('\n')}>
        <XCircle className="size-3.5" /> Issues found
      </span>
    );
  }
  if (relevant.length) {
    return (
      <span className="ws-chip ws-chip-warn" title={relevant.map((f) => `${f.code} (${f.status})`).join('\n')}>
        <AlertTriangle className="size-3.5" /> Needs review
      </span>
    );
  }
  return (
    <span className="ws-chip ws-chip-ok" title="No configured check flagged this row. This is not a certification.">
      <CheckCircle2 className="size-3.5" /> No issues found
    </span>
  );
}

export function ScoreChip({ score }: { score: number | null }) {
  if (score === null) return <span className="ws-chip ws-chip-info"><CircleHelp className="size-3.5" /> No score</span>;
  const low = score < 0.5;
  return (
    <span className={`ws-chip ${low ? 'ws-chip-warn' : 'ws-chip-gold'}`} title="Uncalibrated model score, not a probability of being correct">
      {score.toFixed(2)}{low ? ' · review' : ''}
    </span>
  );
}
