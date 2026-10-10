import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Check, ArrowRight, FolderOpen } from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { useApp } from '../context/AppContext';

export function ProcessingPage() {
  const navigate = useNavigate();
  const { jobId = 'job-latest' } = useParams();
  const { currentJob, transactions } = useApp();

  const totalCount = currentJob ? currentJob.rowCount : transactions.length;

  const [progress, setProgress] = useState(0);
  const [processedCount, setProcessedCount] = useState(0);

  useEffect(() => {
    if (totalCount === 0) return;

    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(timer);
          setTimeout(() => {
            navigate(`/results/${jobId}`);
          }, 800);
          return 100;
        }
        const next = Math.min(100, prev + 5);
        setProcessedCount(Math.min(totalCount, Math.round((next / 100) * totalCount)));
        return next;
      });
    }, 150);

    return () => clearInterval(timer);
  }, [totalCount, jobId, navigate]);

  if (totalCount === 0 && !currentJob) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <FolderOpen className="size-12 text-[#8F7742]" />
          <h2 className="mt-4 font-serif text-2xl font-normal text-[#F0E5CA]">
            No processing job active
          </h2>
          <p className="mt-2 text-sm text-[#B9AD92]">
            Upload a transaction file to begin processing.
          </p>
          <button
            type="button"
            onClick={() => navigate('/upload')}
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-[#D8BC78] px-6 py-3 text-sm font-semibold text-[#090704]"
          >
            <span>Upload Transactions →</span>
          </button>
        </div>
      </AppLayout>
    );
  }

  const steps = [
    { label: 'Reading transaction data', state: progress >= 15 ? 'done' : 'active' },
    { label: 'Normalizing fields & dates', state: progress >= 35 ? 'done' : progress >= 15 ? 'active' : 'pending' },
    { label: 'Generating transaction representations', state: progress >= 55 ? 'done' : progress >= 35 ? 'active' : 'pending' },
    { label: 'Identifying voucher candidates', state: progress >= 75 ? 'done' : progress >= 55 ? 'active' : 'pending' },
    { label: 'Resolving ambiguous classifications', state: progress >= 90 ? 'done' : progress >= 75 ? 'active' : 'pending' },
    { label: 'Calibrating confidence', state: progress >= 98 ? 'done' : progress >= 90 ? 'active' : 'pending' },
    { label: 'Finalizing classification results', state: progress === 100 ? 'done' : progress >= 98 ? 'active' : 'pending' },
  ];

  return (
    <AppLayout>
      <div className="mx-auto max-w-[960px] py-4">
        {/* Page Heading */}
        <div>
          <h1 className="font-serif text-3xl font-normal text-[#F0E5CA] sm:text-4xl">
            Processing your transactions
          </h1>
          <p className="mt-2 text-base text-[#B9AD92]">
            Analyzing context, counterparties, and tax signals for {currentJob ? currentJob.filename : 'your uploaded file'}.
          </p>
        </div>

        {/* Processing Layout */}
        <div className="mt-10 grid grid-cols-1 items-center gap-10 rounded-2xl border border-[rgba(200,168,90,0.25)] bg-[#17130D] p-8 shadow-[0_20px_60px_rgba(0,0,0,0.6)] md:grid-cols-2 md:p-12">
          {/* Step Pipeline */}
          <div className="space-y-5">
            {steps.map((step, idx) => (
              <div key={idx} className="flex items-center gap-4">
                {step.state === 'done' && (
                  <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-[rgba(78,122,88,0.25)] text-[#78A882]">
                    <Check className="size-3.5" />
                  </div>
                )}
                {step.state === 'active' && (
                  <div className="relative flex size-6 shrink-0 items-center justify-center">
                    <span className="absolute inline-flex size-full animate-ping rounded-full bg-[#C8A85A] opacity-40" />
                    <div className="size-3 rounded-full bg-[#C8A85A]" />
                  </div>
                )}
                {step.state === 'pending' && (
                  <div className="size-6 shrink-0 rounded-full border border-[rgba(200,168,90,0.25)] bg-[#100D08]" />
                )}

                <span
                  className={`text-sm tracking-wide ${
                    step.state === 'done'
                      ? 'text-[#F0E5CA]'
                      : step.state === 'active'
                      ? 'font-medium text-[#E8D29A]'
                      : 'text-[#756B58]'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>

          {/* Circular Progress Gauge */}
          <div className="flex flex-col items-center justify-center text-center">
            <div className="relative flex size-56 items-center justify-center">
              <svg className="size-full -rotate-90" viewBox="0 0 120 120">
                <circle
                  cx="60"
                  cy="60"
                  r="52"
                  stroke="rgba(200, 168, 90, 0.15)"
                  strokeWidth="6"
                  fill="transparent"
                />
                <circle
                  cx="60"
                  cy="60"
                  r="52"
                  stroke="#C8A85A"
                  strokeWidth="6"
                  strokeDasharray={2 * Math.PI * 52}
                  strokeDashoffset={2 * Math.PI * 52 * (1 - progress / 100)}
                  strokeLinecap="round"
                  fill="transparent"
                  className="transition-all duration-200"
                />
              </svg>

              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-serif text-5xl font-normal text-[#F0E5CA]">
                  {progress}%
                </span>
                <span className="mt-1 font-mono text-xs text-[#B9AD92]">
                  {processedCount.toLocaleString()} / {totalCount.toLocaleString()}
                </span>
                <span className="text-[10px] text-[#756B58] uppercase tracking-wider mt-0.5">
                  transactions processed
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => navigate(`/results/${jobId}`)}
              className="mt-8 inline-flex items-center gap-2 rounded-xl border border-[rgba(200,168,90,0.35)] bg-[#1D1810] px-6 py-3 text-xs font-semibold tracking-wide text-[#E8D29A] transition-all hover:border-[#C8A85A] hover:bg-[#C8A85A] hover:text-[#090704]"
            >
              <span>{progress === 100 ? 'View Classification Results' : 'Skip directly to Results'}</span>
              <ArrowRight className="size-4" />
            </button>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
