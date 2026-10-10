import { useMemo, useState, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertTriangle, Download, FileText, Sparkles, Table2, Upload } from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { MarkdownReport } from '../components/workspace/MarkdownReport';
import { UploadTransactionsModal } from '../components/workspace/UploadTransactionsModal';
import { ReportStatusChip, RowGstStatus, formatDate, formatINR } from '../components/workspace/format';
import { useWorkspace } from '../context/WorkspaceContext';
import type { Severity } from '../api/vyom';

const PAGE = 100;
const SEVERITY_CHIP: Record<Severity, string> = { HIGH: 'ws-chip-bad', MEDIUM: 'ws-chip-warn', LOW: 'ws-chip-info', INFO: 'ws-chip-info' };
const READINESS: Record<string, { label: string; cls: string }> = {
  NOT_READY: { label: 'Not ready', cls: 'ws-chip-bad' },
  REVIEW_REQUIRED: { label: 'Review required', cls: 'ws-chip-warn' },
  PREPARED_FOR_PROFESSIONAL_REVIEW: { label: 'Prepared for review', cls: 'ws-chip-ok' },
};

function SummaryCard({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="ws-card px-5 py-4">
      <p className="text-[12px] font-bold tracking-[0.06em] uppercase" style={{ color: 'var(--ws-text-2)' }}>{label}</p>
      <div className="mt-3">{children}</div>
    </div>
  );
}

export function GstIntelligencePage() {
  const { analysis: saved } = useWorkspace();
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') === 'report' ? 'report' : 'breakdown';
  const [limit, setLimit] = useState(PAGE);
  const [showUpload, setShowUpload] = useState(false);

  const a = saved?.analysis;
  const rows = a?.summary.classification?.rows ?? [];
  const net = a?.summary.gst_summary?.calculations.find((c) => c.name === 'potential_net_gst_liability');
  const counts = useMemo(() => {
    const c: Record<Severity, number> = { HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0 };
    a?.discrepancies.forEach((d) => { c[d.severity] += 1; });
    return c;
  }, [a]);

  const downloadReport = () => {
    if (!a) return;
    const blob = new Blob([a.report], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `gst_report_${a.request_id.slice(0, 8)}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const setTab = (t: 'breakdown' | 'report') => setParams(t === 'report' ? { tab: 'report' } : {}, { replace: true });

  return (
    <AppLayout>
      <div className="mb-7 flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="ws-eyebrow">GST Intelligence</p>
          <h1 className="mt-2 text-[44px] leading-tight">GST Analysis &amp; Compliance Review</h1>
          {saved && (
            <p className="mt-1 text-sm" style={{ color: 'var(--ws-text-2)' }}>
              {saved.sourceLabel} · analysed {formatDate(saved.createdAt)} · request <span className="ws-mono">{a?.request_id.slice(0, 8)}</span>
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-3">
          {a && <button type="button" className="ws-btn-outline" onClick={downloadReport}><Download className="size-4" /> Download report (.md)</button>}
          <button type="button" className="ws-btn-gold" onClick={() => setShowUpload(true)}><Upload className="size-4" /> Analyze a file</button>
        </div>
      </div>

      {!a ? (
        <div className="ws-card flex flex-col items-center px-6 py-16 text-center">
          <Sparkles className="size-10" style={{ color: 'var(--ws-gold)' }} />
          <h2 className="mt-4 text-[30px]">No GST analysis yet</h2>
          <p className="mt-2 max-w-xl text-sm" style={{ color: 'var(--ws-text-2)' }}>
            Upload a workbook (or create an invoice) and choose “Run GST analysis”. VYOM computes every figure in Python,
            checks it, and an LLM writes the narrative; the report appears here.
          </p>
          <button type="button" className="ws-btn-gold mt-6" onClick={() => setShowUpload(true)}><Upload className="size-4" /> Upload Transactions</button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <SummaryCard label="Report Status"><ReportStatusChip status={a.status} /></SummaryCard>
            <SummaryCard label="Filing Readiness">
              {a.summary.filing_readiness ? (
                <span className={`ws-chip ${READINESS[a.summary.filing_readiness.level]?.cls ?? 'ws-chip-info'}`}>
                  {READINESS[a.summary.filing_readiness.level]?.label ?? a.summary.filing_readiness.level}
                </span>
              ) : '—'}
              <p className="mt-2 text-[11px]" style={{ color: 'var(--ws-muted)' }}>Prepared for review only; nothing is filed.</p>
            </SummaryCard>
            <SummaryCard label="Findings">
              <div className="flex flex-wrap gap-1.5">
                <span className="ws-chip ws-chip-bad">{counts.HIGH} high</span>
                <span className="ws-chip ws-chip-warn">{counts.MEDIUM} medium</span>
                <span className="ws-chip ws-chip-info">{counts.LOW + counts.INFO} low/info</span>
              </div>
            </SummaryCard>
            <SummaryCard label="Potential Net GST Liability">
              <p className="ws-serif text-[28px] leading-none">{formatINR(net?.value ?? null)}</p>
              <p className="mt-1.5 text-[11px]" style={{ color: 'var(--ws-muted)' }}>
                {net ? `${net.status.toLowerCase().replace('_', ' ')} · before eligibility checks and GSTR-2B` : 'Not computed'}
              </p>
            </SummaryCard>
          </div>

          {(a.warnings.length > 0 || a.summary.narrative) && (
            <div className="ws-card mt-4 px-5 py-3.5 text-[13px]" style={{ boxShadow: 'none' }}>
              <p>
                <span className="font-semibold">Narrative: </span>
                {a.summary.narrative?.available
                  ? <>generated by <span className="ws-mono">{a.summary.narrative.model}</span> (Groq); every figure comes from the deterministic engine.</>
                  : <>not available, so the report was built from deterministic results only.</>}
              </p>
              {a.warnings.map((w, i) => (
                <p key={i} className="mt-1 flex gap-2" style={{ color: 'var(--ws-text-2)' }}>
                  <AlertTriangle className="mt-0.5 size-3.5 shrink-0" style={{ color: 'var(--ws-warn-text)' }} />{w}
                </p>
              ))}
            </div>
          )}

          <div className="mt-6 flex gap-2">
            <button type="button" onClick={() => setTab('breakdown')} className={tab === 'breakdown' ? 'ws-btn-gold' : 'ws-btn-outline'}>
              <Table2 className="size-4" /> Tax breakdown &amp; findings
            </button>
            <button type="button" onClick={() => setTab('report')} className={tab === 'report' ? 'ws-btn-gold' : 'ws-btn-outline'}>
              <FileText className="size-4" /> Full report
            </button>
          </div>

          {tab === 'report' ? (
            <section className="ws-card mt-4 px-7 py-7 lg:px-10">
              <MarkdownReport markdown={a.report} />
            </section>
          ) : (
            <>
              <section className="ws-card mt-4 px-6 py-5">
                <div className="flex items-center justify-between">
                  <h3 className="text-[26px]">GST Validation &amp; Tax Breakdown Table</h3>
                  <Sparkles className="size-5" style={{ color: 'var(--ws-gold)' }} />
                </div>
                <div className="mt-3 overflow-x-auto">
                  <table className="ws-table">
                    <thead>
                      <tr>
                        <th>Invoice No</th><th>Party</th><th>GSTIN</th><th>Taxable Value</th>
                        <th>GST Amount</th><th>Category</th><th>GST Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.slice(0, limit).map((r) => (
                        <tr key={r.source_ref}>
                          <td className="whitespace-nowrap">
                            <span className="ws-mono font-semibold">{r.invoice_number ?? '—'}</span>
                            <div className="ws-mono text-[11px]" style={{ color: 'var(--ws-muted)' }}>{r.source_ref}</div>
                          </td>
                          <td className="max-w-[220px] truncate font-medium" title={r.party ?? ''}>{r.party ?? '—'}</td>
                          <td className="ws-mono text-xs whitespace-nowrap" style={{ color: 'var(--ws-gold)' }}>{r.counterparty_gstin ?? '—'}</td>
                          <td className="whitespace-nowrap">{formatINR(r.taxable_value)}</td>
                          <td className="whitespace-nowrap" style={{ color: 'var(--ws-gold)' }}>{formatINR(r.tax)}</td>
                          <td className="whitespace-nowrap text-[13px]">{r.category}</td>
                          <td><RowGstStatus findings={r.findings} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {rows.length > limit && (
                  <div className="pt-4 text-center">
                    <button type="button" className="ws-btn-outline" onClick={() => setLimit((l) => l + PAGE)}>Show more ({rows.length - limit} remaining)</button>
                  </div>
                )}
                <p className="mt-3 text-xs" style={{ color: 'var(--ws-muted)' }}>
                  “No issues found” means no configured check flagged the row. It is not a verification against the GST portal or GSTR-2B.
                </p>
              </section>

              <section className="ws-card mt-5 px-6 py-5">
                <h3 className="text-[26px]">Findings</h3>
                {a.discrepancies.length === 0 ? (
                  <p className="mt-3 text-sm" style={{ color: 'var(--ws-text-2)' }}>No findings from the configured checks.</p>
                ) : (
                  <ul className="mt-3 space-y-3">
                    {a.discrepancies.map((d, i) => (
                      <li key={`${d.code}-${i}`} className="rounded-xl border px-4 py-3" style={{ borderColor: 'var(--ws-border)', background: 'var(--ws-bg)' }}>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="ws-mono text-[13px] font-semibold">{d.code}</span>
                          <span className={`ws-chip ${SEVERITY_CHIP[d.severity]}`}>{d.severity}</span>
                          <span className="ws-chip ws-chip-gold">{d.status}</span>
                          {d.origin === 'llm' && <span className="ws-chip ws-chip-info">flagged by LLM</span>}
                          <span className="text-xs" style={{ color: 'var(--ws-muted)' }}>
                            {Number(d.evidence.affected_rows ?? d.source_rows.length)} rows
                          </span>
                        </div>
                        <p className="mt-1.5 text-sm">{d.message}</p>
                        <p className="mt-1 text-[13px]" style={{ color: 'var(--ws-text-2)' }}>Action: {d.recommended_action}</p>
                        {d.source_rows.length > 0 && (
                          <p className="ws-mono mt-1 truncate text-[11px]" style={{ color: 'var(--ws-muted)' }} title={d.source_rows.join(', ')}>
                            {d.source_rows.slice(0, 8).join(', ')}{d.source_rows.length > 8 ? ' …' : ''}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </>
          )}
        </>
      )}

      {showUpload && <UploadTransactionsModal onClose={() => setShowUpload(false)} />}
    </AppLayout>
  );
}
