import { useNavigate } from 'react-router-dom';
import {
  FileSpreadsheet,
  Check,
  AlertTriangle,
  ArrowRight,
} from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { MOCK_VALIDATION_CHECKS } from '../mockData';

export function ValidationPage() {
  const navigate = useNavigate();

  return (
    <AppLayout>
      <div className="mx-auto max-w-[760px] py-4">
        {/* Page Heading */}
        <div className="text-center">
          <h1 className="font-serif text-3xl font-normal text-[#F1E7CF] sm:text-4xl">
            Validating your file
          </h1>
          <p className="mt-2 text-sm text-[#B9AD92]">
            We've checked your file for common issues.
          </p>
        </div>

        {/* Central Validation Card */}
        <div className="mt-8 overflow-hidden rounded-2xl border border-[rgba(200,168,90,0.22)] bg-[#17130D] shadow-[0_20px_60px_rgba(0,0,0,0.5)]">
          {/* File Header */}
          <div className="flex items-center gap-4 border-b border-[rgba(200,168,90,0.15)] bg-[#1D1810]/70 px-6 py-5">
            <div className="flex size-11 items-center justify-center rounded-lg border border-[rgba(200,168,90,0.3)] bg-[#100D08] text-[#C8A85A]">
              <FileSpreadsheet className="size-5" />
            </div>
            <div>
              <h2 className="font-mono text-base font-medium text-[#F1E7CF]">
                October_Transactions.xlsx
              </h2>
              <p className="mt-0.5 text-xs text-[#B9AD92]">
                12,450 rows • 18 columns
              </p>
            </div>
          </div>

          {/* Validation Checklist */}
          <div className="divide-y divide-[rgba(200,168,90,0.08)] px-6">
            {MOCK_VALIDATION_CHECKS.map((check) => (
              <div key={check.id} className="flex items-center justify-between py-3.5">
                <div className="flex items-center gap-3.5">
                  <span className="text-sm text-[#F1E7CF]">
                    {check.label}
                  </span>
                </div>

                <div>
                  {check.status === 'passed' ? (
                    <div className="flex size-6 items-center justify-center rounded-full bg-[rgba(78,122,88,0.2)] text-[#78A882]">
                      <Check className="size-3.5" />
                    </div>
                  ) : (
                    <div className="flex size-6 items-center justify-center rounded-full bg-[rgba(200,168,90,0.2)] text-[#D8BC78]">
                      <AlertTriangle className="size-3.5" />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="mt-8 flex items-center justify-between">
          <p className="text-xs text-[#756B58]">
            Warnings will be flagged for human review in the results stage.
          </p>

          <button
            type="button"
            onClick={() => navigate('/processing/job-1024')}
            className="inline-flex min-w-[200px] items-center justify-center gap-2 rounded-lg bg-[#C8A85A] px-6 py-3 text-sm font-semibold tracking-wide text-[#0A0805] shadow-[0_4px_20px_rgba(200,168,90,0.22)] transition-all hover:bg-[#D8BC78]"
          >
            <span>Continue Processing</span>
            <ArrowRight className="size-4" />
          </button>
        </div>
      </div>
    </AppLayout>
  );
}
