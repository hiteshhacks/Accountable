import { useMemo, useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  FileText,
  CheckCircle2,
  Clock,
  Gauge,
  FileWarning,
  ListChecks,
  ShieldCheck,
  FolderUp,
  Plus,
  Upload,
  ArrowRight,
  FileSpreadsheet,
  type LucideIcon,
} from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { BarChart, DonutChart, ScoreGauge, foldSlices } from '../components/workspace/Charts';
import { CreateInvoiceModal } from '../components/workspace/CreateInvoiceModal';
import { UploadTransactionsModal } from '../components/workspace/UploadTransactionsModal';
import { ReportStatusChip, formatDate } from '../components/workspace/format';
import { REVIEW_SCORE_THRESHOLD, useWorkspace } from '../context/WorkspaceContext';

const READINESS_LABEL: Record<string, string> = {
  NOT_READY: 'Not ready',
  REVIEW_REQUIRED: 'Review',
  PREPARED_FOR_PROFESSIONAL_REVIEW: 'Prepared',
};

function StatCard({ label, value, icon: Icon, hint }: { label: string; value: string | number; icon: LucideIcon; hint?: string }) {
  return (
    <div className="ws-card flex min-h-[108px] flex-col justify-between px-5 py-4" title={hint}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-[12px] font-bold tracking-[0.06em] uppercase" style={{ color: 'var(--ws-text-2)' }}>{label}</p>
        <Icon className="size-[18px] shrink-0" style={{ color: 'var(--ws-gold)' }} />
      </div>
      <div>
        <p className="ws-serif text-[30px] leading-none">{value}</p>
        {hint && <p className="mt-1 text-[11px]" style={{ color: 'var(--ws-muted)' }}>{hint}</p>}
      </div>
    </div>
  );
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <section className="ws-card flex flex-col px-6 py-5">
      <h3 className="text-[24px] leading-tight">{title}</h3>
      <p className="mt-0.5 text-[12.5px]" style={{ color: 'var(--ws-text-2)' }}>{subtitle}</p>
      <div className="my-4 h-px" style={{ background: 'var(--ws-border)' }} />
      <div className="flex flex-1 flex-col justify-center">{children}</div>
    </section>
  );
}

export function DashboardPage() {
  const { rows, uploads, analysis } = useWorkspace();
  const [params, setParams] = useSearchParams();
  const [modal, setModal] = useState<'invoice' | 'upload' | null>(params.get('upload') ? 'upload' : null);

  const stats = useMemo(() => {
    const today = new Date().toDateString();
    const scored = rows.filter((r) => r.score !== null);
    const avg = scored.length ? scored.reduce((s, r) => s + (r.score ?? 0), 0) / scored.length : null;
    const counts: Record<string, number> = {};
    rows.forEach((r) => { counts[r.category] = (counts[r.category] ?? 0) + 1; });
    const days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (6 - i));
      return d;
    });
    const perDay = days.map((d) => {
      const n = rows.filter((r) => new Date(r.createdAt).toDateString() === d.toDateString()).length;
      return { label: d.toLocaleDateString('en-IN', { weekday: 'short' }), value: n,
        title: `${d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}: ${n} rows classified` };
    });
    const a = analysis?.analysis;
    const findingsRows = a?.summary.classification?.rows.filter((r) => r.findings.some((f) => f.severity !== 'INFO')).length;
    return {
      total: rows.length,
      today: rows.filter((r) => new Date(r.createdAt).toDateString() === today).length,
      review: rows.filter((r) => r.score === null || r.score < REVIEW_SCORE_THRESHOLD).length,
      avg,
      slices: foldSlices(counts),
      perDay,
      gstExceptions: a ? a.discrepancies.filter((d) => d.severity === 'HIGH' || d.severity === 'MEDIUM').length : null,
      findingsRows: findingsRows ?? null,
      readiness: a?.summary.filing_readiness?.level ?? null,
    };
  }, [rows, analysis]);

  const closeModal = () => {
    setModal(null);
    if (params.get('upload')) setParams({}, { replace: true });
  };

  return (
    <AppLayout>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="ws-eyebrow">Administrative Governance Console</p>
          <h1 className="mt-2 text-[44px] leading-[1.05] lg:text-[52px]">System Analytics &amp; Governance Controls</h1>
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" className="ws-btn-outline" onClick={() => setModal('invoice')}>
            <Plus className="size-4" /> Create Invoice
          </button>
          <button type="button" className="ws-btn-gold" onClick={() => setModal('upload')}>
            <Upload className="size-4" /> Upload Transactions
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Transactions" value={stats.total} icon={FileText} />
        <StatCard label="Processed Today" value={stats.today} icon={CheckCircle2} />
        <StatCard label="Pending Reviews" value={stats.review} icon={Clock} hint={`Model score below ${REVIEW_SCORE_THRESHOLD}`} />
        <StatCard label="Avg. Model Score" value={stats.avg === null ? '—' : stats.avg.toFixed(2)} icon={Gauge}
          hint="Uncalibrated; not accuracy" />
        <StatCard label="GST Exceptions" value={stats.gstExceptions ?? '—'} icon={FileWarning}
          hint={stats.gstExceptions === null ? 'Run a GST analysis' : 'High/medium finding groups'} />
        <StatCard label="Rows With GST Findings" value={stats.findingsRows ?? '—'} icon={ListChecks}
          hint={stats.findingsRows === null ? 'Run a GST analysis' : 'In the latest analysis'} />
        <StatCard label="Filing Readiness" value={stats.readiness ? READINESS_LABEL[stats.readiness] ?? stats.readiness : '—'}
          icon={ShieldCheck} hint="Prepared for review only; never filed" />
        <StatCard label="Files Uploaded" value={uploads.length} icon={FolderUp} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <ChartCard title="Voucher Classification" subtitle="Distribution by predicted voucher category">
          {stats.total ? <DonutChart slices={stats.slices} centerLabel="Vouchers" /> : <EmptyChart />}
        </ChartCard>
        <ChartCard title="Daily Classification Volume" subtitle="Rows classified per day, last 7 days">
          <BarChart data={stats.perDay} />
        </ChartCard>
        <ChartCard title="Model Score Gauge" subtitle="Average top-category score across classified rows">
          <ScoreGauge value={stats.avg} label="Avg. score (uncalibrated)"
            sublabel="Classifier scores are not calibrated probabilities and do not measure accuracy; that needs independently labelled data." />
        </ChartCard>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-[1.4fr_1fr]">
        <section className="ws-card px-6 py-5">
          <div className="flex items-center justify-between">
            <h3 className="text-[24px]">Recent Uploads</h3>
            <Link to="/transactions" className="ws-btn-ghost text-sm">View transactions <ArrowRight className="size-4" /></Link>
          </div>
          {uploads.length === 0 ? (
            <p className="mt-4 text-sm" style={{ color: 'var(--ws-text-2)' }}>No files uploaded yet. Use “Upload Transactions” to classify a workbook.</p>
          ) : (
            <ul className="mt-3 divide-y" style={{ borderColor: 'var(--ws-border)' }}>
              {uploads.slice(0, 6).map((u) => (
                <li key={u.id} className="flex items-center gap-3 py-3 text-sm" style={{ borderColor: 'var(--ws-border)' }}>
                  <FileSpreadsheet className="size-5 shrink-0" style={{ color: 'var(--ws-gold)' }} />
                  <span className="min-w-0 flex-1 truncate font-medium">{u.fileName}</span>
                  <span className="tabular-nums" style={{ color: 'var(--ws-text-2)' }}>{u.rows} rows</span>
                  <span className="text-xs" style={{ color: 'var(--ws-muted)' }}>{formatDate(u.createdAt)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="ws-card px-6 py-5">
          <h3 className="text-[24px]">Latest GST Analysis</h3>
          {analysis ? (
            <div className="mt-3 space-y-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <ReportStatusChip status={analysis.analysis.status} />
                <span style={{ color: 'var(--ws-text-2)' }}>{analysis.sourceLabel}</span>
              </div>
              <p style={{ color: 'var(--ws-text-2)' }}>
                {analysis.analysis.discrepancies.length} finding groups · analysed {formatDate(analysis.createdAt)}
              </p>
              <Link to="/gst" className="ws-btn-gold">Open GST Intelligence <ArrowRight className="size-4" /></Link>
            </div>
          ) : (
            <p className="mt-4 text-sm" style={{ color: 'var(--ws-text-2)' }}>
              No analysis yet. Upload a file or create an invoice, then choose “Run GST analysis”.
            </p>
          )}
        </section>
      </div>

      {modal === 'invoice' && <CreateInvoiceModal onClose={closeModal} />}
      {modal === 'upload' && <UploadTransactionsModal onClose={closeModal} />}
    </AppLayout>
  );
}

function EmptyChart() {
  return (
    <p className="py-10 text-center text-sm" style={{ color: 'var(--ws-text-2)' }}>
      No classified transactions yet.
    </p>
  );
}
