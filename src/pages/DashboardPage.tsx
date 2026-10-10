import { useNavigate } from 'react-router-dom';
import {
  FileSpreadsheet, CheckCircle2, Clock, Upload,
  ArrowRight, MoreHorizontal, FolderOpen,
} from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { useApp } from '../context/AppContext';

export function DashboardPage() {
  const navigate = useNavigate();
  const { uploads, transactions } = useApp();

  const totalTransactions = transactions.length;
  const processedTransactions = transactions.filter((t) => t.status === 'High').length;
  const lastUploadDate = uploads.length > 0 ? uploads[0].date : 'None';

  const card = {
    borderColor: 'var(--border)',
    background: 'var(--surface)',
    boxShadow: 'var(--shadow-card)',
  };

  return (
    <AppLayout>
      {/* Greeting */}
      <div className="mb-9">
        <p className="text-xs font-semibold tracking-widest uppercase" style={{ color: 'var(--accent)' }}>
          Dashboard Overview
        </p>
        <h1 className="mt-1.5 font-serif text-3xl font-normal sm:text-4xl lg:text-5xl" style={{ color: 'var(--text)' }}>
          Let's process your financial data.
        </h1>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        {[
          { Icon: FileSpreadsheet, value: totalTransactions.toLocaleString(),        label: 'Total transactions' },
          { Icon: CheckCircle2,    value: processedTransactions.toLocaleString(),    label: 'Processed' },
          { Icon: Clock,           value: lastUploadDate,                             label: 'Last uploaded', small: true },
        ].map(({ Icon, value, label, small }) => (
          <div key={label} className="rounded-2xl border p-7 transition-all hover:border-opacity-80" style={card}>
            <div className="flex items-center gap-5">
              <div
                className="flex size-14 items-center justify-center rounded-2xl border"
                style={{ borderColor: 'var(--border-strong)', background: 'var(--surface-elevated)', color: 'var(--accent)' }}
              >
                <Icon className="size-7" />
              </div>
              <div>
                <p
                  className={`font-serif font-normal ${small ? 'text-2xl sm:text-3xl' : 'text-3xl sm:text-4xl'}`}
                  style={{ color: 'var(--text)' }}
                >
                  {value}
                </p>
                <p className="mt-1 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>{label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Upload CTA Banner */}
      <div
        onClick={() => navigate('/upload')}
        className="group mt-9 cursor-pointer rounded-2xl border p-8 transition-all duration-300 sm:p-9"
        style={{
          borderColor: 'var(--border)',
          background: `linear-gradient(to right, var(--surface), var(--surface-elevated))`,
          boxShadow: 'var(--shadow-card)',
        }}
        onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.borderColor = 'var(--accent)')}
        onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.borderColor = 'var(--border)')}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div
              className="flex size-16 items-center justify-center rounded-2xl border transition-colors group-hover:border-[var(--accent)]"
              style={{ borderColor: 'var(--border)', background: 'var(--bg-elevated)', color: 'var(--accent)' }}
            >
              <Upload className="size-8" />
            </div>
            <div>
              <h2 className="font-serif text-2xl font-normal sm:text-3xl" style={{ color: 'var(--text)' }}>
                Upload Transactions
              </h2>
              <p className="mt-1.5 text-base" style={{ color: 'var(--text-secondary)' }}>
                Upload your Excel or CSV file to begin intelligent voucher classification.
              </p>
            </div>
          </div>
          <div
            className="flex size-14 items-center justify-center rounded-full border transition-all"
            style={{ borderColor: 'var(--border)', background: 'var(--bg-elevated)', color: 'var(--accent)' }}
          >
            <ArrowRight className="size-6" />
          </div>
        </div>
      </div>

      {/* Recent Uploads */}
      <div className="mt-12">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="font-serif text-2xl font-normal" style={{ color: 'var(--text)' }}>Recent uploads</h3>
          {uploads.length > 0 && (
            <button
              type="button"
              onClick={() => navigate('/results/job-latest')}
              className="flex items-center gap-2 text-sm font-medium transition-colors"
              style={{ color: 'var(--text-secondary)' }}
            >
              <span>View classification results</span>
              <ArrowRight className="size-4" />
            </button>
          )}
        </div>

        {uploads.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center rounded-2xl border px-6 py-16 text-center"
            style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface) 90%, transparent)' }}
          >
            <div
              className="flex size-16 items-center justify-center rounded-2xl border"
              style={{ borderColor: 'var(--border)', background: 'var(--bg-elevated)', color: 'var(--accent)' }}
            >
              <FolderOpen className="size-8" />
            </div>
            <h4 className="mt-6 font-serif text-2xl font-normal sm:text-3xl" style={{ color: 'var(--text)' }}>
              No transactions yet.
            </h4>
            <p className="mt-2.5 max-w-lg text-base" style={{ color: 'var(--text-secondary)' }}>
              Upload your first transaction file to begin intelligent voucher classification and GST intelligence.
            </p>
            <button
              type="button"
              onClick={() => navigate('/upload')}
              className="mt-7 inline-flex items-center gap-2.5 rounded-xl px-7 py-3.5 text-base font-semibold transition-all"
              style={{ background: 'var(--accent-warm)', color: 'var(--accent-contrast)' }}
            >
              <Upload className="size-5" />
              <span>Upload Transactions →</span>
            </button>
          </div>
        ) : (
          <div
            className="overflow-hidden rounded-2xl border"
            style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}
          >
            {uploads.map((item, index) => (
              <div
                key={item.id}
                onClick={() => navigate('/results/job-latest')}
                className="flex cursor-pointer items-center justify-between px-8 py-5 transition-colors"
                style={{
                  borderBottom: index !== uploads.length - 1 ? `1px solid var(--border)` : 'none',
                }}
                onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = 'var(--surface-elevated)')}
                onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
              >
                <div className="flex items-center gap-5">
                  <FileSpreadsheet className="size-6" style={{ color: 'var(--accent)' }} />
                  <span className="font-mono text-base font-medium" style={{ color: 'var(--text)' }}>
                    {item.filename}
                  </span>
                </div>
                <div className="flex items-center gap-9">
                  <span className="font-mono text-base" style={{ color: 'var(--text-secondary)' }}>{item.rows}</span>
                  <span
                    className="inline-flex items-center gap-2 rounded-full border px-3.5 py-1 text-xs font-semibold"
                    style={{
                      borderColor: 'rgba(78,122,88,0.40)',
                      background: 'rgba(78,122,88,0.20)',
                      color: 'var(--status-success-text)',
                    }}
                  >
                    <span className="size-2 rounded-full" style={{ background: 'var(--status-success-text)' }} />
                    {item.status}
                  </span>
                  <span className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>{item.date}</span>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); navigate('/results/job-latest'); }}
                    className="transition-colors"
                    style={{ color: 'var(--text-faint)' }}
                  >
                    <MoreHorizontal className="size-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
