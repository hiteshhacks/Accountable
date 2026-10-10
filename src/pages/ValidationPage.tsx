import { useNavigate } from 'react-router-dom';
import {
  FileSpreadsheet,
  Check,
  AlertTriangle,
  ArrowRight,
  FolderOpen,
} from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { useApp } from '../context/AppContext';

export function ValidationPage() {
  const navigate = useNavigate();
  const { currentJob, startProcessing } = useApp();

  if (!currentJob) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <FolderOpen className="size-12 text-[#8F7742]" />
          <h2 className="mt-4 font-serif text-2xl font-normal text-[#F0E5CA]">
            No file uploaded for validation
          </h2>
          <p className="mt-2 text-sm text-[#B9AD92]">
            Upload a transaction file first to begin validation.
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

  const handleContinueProcessing = async () => {
    await startProcessing(currentJob.id);
    navigate(`/processing/${currentJob.id}`);
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-[800px] py-4">
        {/* Page Heading */}
        <div className="text-center">
          <h1 className="font-serif text-3xl font-normal text-[#F0E5CA] sm:text-4xl">
            Validating your file
          </h1>
          <p className="mt-2 text-base text-[#B9AD92]">
            We've checked your file for data structure and compliance issues.
          </p>
        </div>

        {/* Central Validation Card with Real Data */}
        <div className="mt-8 overflow-hidden rounded-2xl border border-[rgba(200,168,90,0.25)] bg-[#17130D] shadow-[0_20px_60px_rgba(0,0,0,0.6)]">
          {/* File Header */}
          <div className="flex items-center gap-4 border-b border-[rgba(200,168,90,0.18)] bg-[#1D1810]/80 px-7 py-6">
            <div className="flex size-12 items-center justify-center rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#100D08] text-[#C8A85A]">
              <FileSpreadsheet className="size-6" />
            </div>
            <div>
              <h2 className="font-mono text-lg font-medium text-[#F0E5CA]">
                {currentJob.filename}
              </h2>
              <p className="mt-0.5 text-xs text-[#B9AD92]">
                {currentJob.rowCount.toLocaleString()} rows • {currentJob.colCount} columns • {currentJob.fileSize}
              </p>
            </div>
          </div>

          {/* Real Validation Checklist */}
          <div className="divide-y divide-[rgba(200,168,90,0.1)] px-7">
            {currentJob.validationChecks.map((check) => (
              <div key={check.id} className="flex items-center justify-between py-4">
                <span className="text-sm font-medium text-[#F0E5CA]">
                  {check.label}
                </span>

                <div>
                  {check.status === 'passed' ? (
                    <div className="flex size-6 items-center justify-center rounded-full bg-[rgba(78,122,88,0.25)] text-[#78A882]">
                      <Check className="size-4" />
                    </div>
                  ) : (
                    <div className="flex size-6 items-center justify-center rounded-full bg-[rgba(200,168,90,0.25)] text-[#D8BC78]">
                      <AlertTriangle className="size-4" />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Actions */}
        <div className="mt-8 flex items-center justify-between">
          <p className="text-xs text-[#756B58]">
            Warnings will be flagged for review during results classification.
          </p>

          <button
            type="button"
            onClick={handleContinueProcessing}
            className="inline-flex min-w-[210px] h-[54px] items-center justify-center gap-2.5 rounded-xl bg-[#D8BC78] px-7 text-base font-semibold tracking-wide text-[#090704] shadow-[0_4px_24px_rgba(200,168,90,0.25)] transition-all hover:bg-[#E8D29A]"
          >
            <span>Continue Processing</span>
            <ArrowRight className="size-5" />
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
