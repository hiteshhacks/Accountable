import { useNavigate } from 'react-router-dom';
import { FileSpreadsheet, Check, AlertTriangle, ArrowRight, FolderOpen } from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { useApp } from '../context/AppContext';

export function ValidationPage() {
  const navigate = useNavigate();
  const { currentJob, startProcessing } = useApp();

  if (!currentJob) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <FolderOpen className="size-12" style={{ color: 'var(--accent-muted)' }} />
          <h2 className="mt-4 font-serif text-2xl font-normal" style={{ color: 'var(--text)' }}>
            No file uploaded for validation
          </h2>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
            Upload a transaction file first to begin validation.
          </p>
          <button
            type="button"
            onClick={() => navigate('/upload')}
            className="mt-6 inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold"
            style={{ background: 'var(--accent-warm)', color: 'var(--accent-contrast)' }}
          >
            <span>Upload Transactions →</span>
          </button>
        </div>
      </AppLayout>
    );
  }

  const handleContinueProcessing = async () => {
    await startProcessing(currentJob.id);
    navigate(`/processing/${currentJob.id}`);
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-[800px] py-4">
        <div className="text-center">
          <h1 className="font-serif text-3xl font-normal sm:text-4xl" style={{ color: 'var(--text)' }}>
            Validating your file
          </h1>
          <p className="mt-2 text-base" style={{ color: 'var(--text-muted)' }}>
            We've checked your file for data structure and compliance issues.
          </p>
        </div>

        {/* Validation Card */}
        <div
          className="mt-8 overflow-hidden rounded-2xl border"
          style={{
            borderColor: 'var(--border)',
            background: 'var(--surface)',
            boxShadow: 'var(--shadow-card)',
          }}
        >
          {/* File Header */}
          <div
            className="flex items-center gap-4 border-b px-7 py-6"
            style={{
              borderColor: 'var(--border)',
              background: 'color-mix(in srgb, var(--surface-elevated) 80%, transparent)',
            }}
          >
            <div
              className="flex size-12 items-center justify-center rounded-xl border"
              style={{ borderColor: 'var(--border)', background: 'var(--bg-elevated)', color: 'var(--accent)' }}
            >
              <FileSpreadsheet className="size-6" />
            </div>
            <div>
              <h2 className="font-mono text-lg font-medium" style={{ color: 'var(--text)' }}>
                {currentJob.filename}
              </h2>
              <p className="mt-0.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                {currentJob.rowCount.toLocaleString()} rows • {currentJob.colCount} columns • {currentJob.fileSize}
              </p>
            </div>
          </div>

          {/* Checklist */}
          <div className="divide-y px-7" style={{ borderColor: 'var(--border)' }}>
            {currentJob.validationChecks.map((check) => (
              <div
                key={check.id}
                className="flex items-center justify-between py-4"
                style={{ borderColor: 'var(--border)' }}
              >
                <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                  {check.label}
                </span>
                <div>
                  {check.status === 'passed' ? (
                    <div
                      className="flex size-6 items-center justify-center rounded-full"
                      style={{ background: 'rgba(78,122,88,0.25)', color: 'var(--status-success-text)' }}
                    >
                      <Check className="size-4" />
                    </div>
                  ) : (
                    <div
                      className="flex size-6 items-center justify-center rounded-full"
                      style={{ background: 'color-mix(in srgb, var(--accent) 25%, transparent)', color: 'var(--accent-warm)' }}
                    >
                      <AlertTriangle className="size-4" />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="mt-8 flex items-center justify-between">
          <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
            Warnings will be flagged for review during results classification.
          </p>
          <button
            type="button"
            onClick={handleContinueProcessing}
            className="inline-flex min-w-[210px] h-[54px] items-center justify-center gap-2.5 rounded-xl px-7 text-base font-semibold tracking-wide transition-all"
            style={{ background: 'var(--accent-warm)', color: 'var(--accent-contrast)', boxShadow: 'var(--shadow-gold)' }}
          >
            <span>Continue Processing</span>
            <ArrowRight className="size-5" />
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
