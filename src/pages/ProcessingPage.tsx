import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Check, ArrowRight } from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';

export function ProcessingPage() {
  const navigate = useNavigate();
  const { jobId = 'job-1024' } = useParams();

  const [progress, setProgress] = useState(72);
  const [processedCount, setProcessedCount] = useState(8984);
  const totalCount = 12450;

  useEffect(() => {
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(timer);
          return 100;
        }
        const next = Math.min(100, prev + 1);
        setProcessedCount(Math.min(totalCount, Math.round((next / 100) * totalCount)));
        return next;
      });
    }, 450);

    return () => clearInterval(timer);
  }, [totalCount]);

  const steps = [
    { label: 'Reading transaction data', state: 'done' },
    { label: 'Normalizing fields', state: 'done' },
    { label: 'Generating transaction representations', state: 'done' },
    { label: 'Identifying voucher candidates', state: 'done' },
    {
      label: 'Resolving ambiguous classifications',
      state: progress >= 85 ? 'done' : 'active',
    },
    {
      label: 'Calibrating confidence',
      state: progress >= 95 ? 'done' : progress >= 85 ? 'active' : 'pending',
    },
    {
      label: 'Finalizing results',
      state: progress === 100 ? 'done' : progress >= 95 ? 'active' : 'pending',
    },
  ];

  return (
    <AppLayout>
      <div className="mx-auto max-w-[940px] py-4">
        {/* Page Heading */}
        <div>
          <h1 className="font-serif text-3xl font-normal text-[#F1E7CF] sm:text-4xl">
            Processing your transactions
          </h1>
          <p className="mt-2 text-sm text-[#B9AD92]">
            This may take a few minutes. We'll notify you when it's complete.
          </p>
        </div>

        {/* Processing Layout: Pipeline (Left) & Circular Progress (Right) */}
        <div className="mt-10 grid grid-cols-1 items-center gap-10 rounded-2xl border border-[rgba(200,168,90,0.2)] bg-[#17130D] p-8 shadow-[0_20px_60px_rgba(0,0,0,0.5)] md:grid-cols-2 md:p-12">
          {/* Left: Step Pipeline */}
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
                      ? 'text-[#F1E7CF]'
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

          {/* Right: Circular Progress Ring */}
          <div className="flex flex-col items-center justify-center text-center">
            <div className="relative flex size-56 items-center justify-center">
              {/* SVG Ring */}
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
                  className="transition-all duration-300"
                />
              </svg>

              {/* Inside Metrics */}
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-serif text-5xl font-normal text-[#F1E7CF]">
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

            {/* Quick action button when completed or to skip ahead */}
            <button
              type="button"
              onClick={() => navigate(`/results/${jobId}`)}
              className="mt-8 inline-flex items-center gap-2 rounded-lg border border-[rgba(200,168,90,0.3)] bg-[#1D1810] px-5 py-2.5 text-xs font-semibold tracking-wide text-[#E8D29A] transition-all hover:border-[#C8A85A] hover:bg-[#C8A85A] hover:text-[#0A0805]"
            >
              <span>{progress === 100 ? 'View Classification Results' : 'Fast-forward to Results'}</span>
              <ArrowRight className="size-3.5" />
            </button>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
