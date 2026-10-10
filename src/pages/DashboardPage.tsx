import { useNavigate } from 'react-router-dom';
import {
  FileSpreadsheet,
  CheckCircle2,
  Clock,
  Upload,
  ArrowRight,
  MoreHorizontal,
  FolderOpen,
} from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { useApp } from '../context/AppContext';

export function DashboardPage() {
  const navigate = useNavigate();
  const { uploads, transactions } = useApp();

  const totalTransactions = transactions.length;
  const processedTransactions = transactions.filter((t) => t.status === 'High').length;
  const lastUploadDate = uploads.length > 0 ? uploads[0].date : 'None';

  return (
    <AppLayout>
      {/* Top Greeting */}
      <div className="mb-9">
        <p className="text-xs font-semibold tracking-widest text-[#C8A85A] uppercase">
          Dashboard Overview
        </p>
        <h1 className="mt-1.5 font-serif text-3xl font-normal text-[#F0E5CA] sm:text-4xl lg:text-5xl">
          Let's process your financial data.
        </h1>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        {/* Card 1 */}
        <div className="rounded-2xl border border-[rgba(200,168,90,0.25)] bg-[#17130D] p-7 shadow-[0_4px_28px_rgba(0,0,0,0.6)] transition-all hover:border-[rgba(200,168,90,0.45)]">
          <div className="flex items-center gap-5">
            <div className="flex size-14 items-center justify-center rounded-2xl border border-[rgba(200,168,90,0.35)] bg-[#1D1810] text-[#C8A85A]">
              <FileSpreadsheet className="size-7" />
            </div>
            <div>
              <p className="font-serif text-3xl font-normal text-[#F0E5CA] sm:text-4xl">
                {totalTransactions.toLocaleString()}
              </p>
              <p className="mt-1 text-sm font-medium text-[#E8D29A]">Total transactions</p>
            </div>
          </div>
        </div>

        {/* Card 2 */}
        <div className="rounded-2xl border border-[rgba(200,168,90,0.25)] bg-[#17130D] p-7 shadow-[0_4px_28px_rgba(0,0,0,0.6)] transition-all hover:border-[rgba(200,168,90,0.45)]">
          <div className="flex items-center gap-5">
            <div className="flex size-14 items-center justify-center rounded-2xl border border-[rgba(200,168,90,0.35)] bg-[#1D1810] text-[#C8A85A]">
              <CheckCircle2 className="size-7" />
            </div>
            <div>
              <p className="font-serif text-3xl font-normal text-[#F0E5CA] sm:text-4xl">
                {processedTransactions.toLocaleString()}
              </p>
              <p className="mt-1 text-sm font-medium text-[#E8D29A]">Processed</p>
            </div>
          </div>
        </div>

        {/* Card 3 */}
        <div className="rounded-2xl border border-[rgba(200,168,90,0.25)] bg-[#17130D] p-7 shadow-[0_4px_28px_rgba(0,0,0,0.6)] transition-all hover:border-[rgba(200,168,90,0.45)]">
          <div className="flex items-center gap-5">
            <div className="flex size-14 items-center justify-center rounded-2xl border border-[rgba(200,168,90,0.35)] bg-[#1D1810] text-[#C8A85A]">
              <Clock className="size-7" />
            </div>
            <div>
              <p className="font-serif text-2xl font-normal text-[#F0E5CA] sm:text-3xl">
                {lastUploadDate}
              </p>
              <p className="mt-1 text-sm font-medium text-[#E8D29A]">Last uploaded</p>
            </div>
          </div>
        </div>
      </div>

      {/* Primary Action Horizontal Banner */}
      <div
        onClick={() => navigate('/upload')}
        className="group mt-9 cursor-pointer rounded-2xl border border-[rgba(200,168,90,0.35)] bg-gradient-to-r from-[#17130D] to-[#1D1810] p-8 shadow-[0_8px_40px_rgba(0,0,0,0.65)] transition-all duration-300 hover:border-[#C8A85A] hover:shadow-[0_12px_48px_rgba(200,168,90,0.18)] sm:p-9"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex size-16 items-center justify-center rounded-2xl border border-[rgba(200,168,90,0.4)] bg-[#100D08] text-[#C8A85A] transition-colors group-hover:border-[#C8A85A] group-hover:bg-[#C8A85A] group-hover:text-[#090704]">
              <Upload className="size-8" />
            </div>
            <div>
              <h2 className="font-serif text-2xl font-normal text-[#F0E5CA] sm:text-3xl">
                Upload Transactions
              </h2>
              <p className="mt-1.5 text-base text-[#E8D29A]">
                Upload your Excel or CSV file to begin intelligent voucher classification.
              </p>
            </div>
          </div>

          <div className="flex size-14 items-center justify-center rounded-full border border-[rgba(200,168,90,0.4)] bg-[#100D08] text-[#C8A85A] transition-all group-hover:border-[#C8A85A] group-hover:bg-[#C8A85A] group-hover:text-[#090704]">
            <ArrowRight className="size-6" />
          </div>
        </div>
      </div>

      {/* Recent Uploads Section / High-Readability Empty State */}
      <div className="mt-12">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="font-serif text-2xl font-normal text-[#F0E5CA]">
            Recent uploads
          </h3>
          {uploads.length > 0 && (
            <button
              type="button"
              onClick={() => navigate('/results/job-latest')}
              className="flex items-center gap-2 text-sm font-medium text-[#E8D29A] transition-colors hover:text-[#F0E5CA]"
            >
              <span>View classification results</span>
              <ArrowRight className="size-4" />
            </button>
          )}
        </div>

        {uploads.length === 0 ? (
          /* Empty State */
          <div className="flex flex-col items-center justify-center rounded-2xl border border-[rgba(200,168,90,0.25)] bg-[#17130D]/90 px-6 py-16 text-center">
            <div className="flex size-16 items-center justify-center rounded-2xl border border-[rgba(200,168,90,0.3)] bg-[#100D08] text-[#C8A85A]">
              <FolderOpen className="size-8" />
            </div>
            <h4 className="mt-6 font-serif text-2xl font-normal text-[#F0E5CA] sm:text-3xl">
              No transactions yet.
            </h4>
            <p className="mt-2.5 max-w-lg text-base text-[#E8D29A]">
              Upload your first transaction file to begin intelligent voucher classification and GST intelligence.
            </p>
            <button
              type="button"
              onClick={() => navigate('/upload')}
              className="mt-7 inline-flex items-center gap-2.5 rounded-xl bg-[#D8BC78] px-7 py-3.5 text-base font-semibold text-[#090704] transition-all hover:bg-[#E8D29A]"
            >
              <Upload className="size-5" />
              <span>Upload Transactions →</span>
            </button>
          </div>
        ) : (
          /* Uploads Table */
          <div className="overflow-hidden rounded-2xl border border-[rgba(200,168,90,0.22)] bg-[#17130D]">
            {uploads.map((item, index) => (
              <div
                key={item.id}
                onClick={() => navigate('/results/job-latest')}
                className={`flex cursor-pointer items-center justify-between px-8 py-5.5 transition-colors hover:bg-[#1D1810] ${
                  index !== uploads.length - 1 ? 'border-b border-[rgba(200,168,90,0.12)]' : ''
                }`}
              >
                <div className="flex items-center gap-5">
                  <FileSpreadsheet className="size-6 text-[#C8A85A]" />
                  <span className="font-mono text-base font-medium text-[#F0E5CA]">
                    {item.filename}
                  </span>
                </div>

                <div className="flex items-center gap-9">
                  <span className="text-base font-mono text-[#E8D29A]">
                    {item.rows}
                  </span>

                  <span className="inline-flex items-center gap-2 rounded-full border border-[#4E7A58]/40 bg-[#4E7A58]/20 px-3.5 py-1 text-xs font-semibold text-[#78A882]">
                    <span className="size-2 rounded-full bg-[#78A882]" />
                    {item.status}
                  </span>

                  <span className="text-sm font-medium text-[#B9AD92]">
                    {item.date}
                  </span>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate('/results/job-latest');
                    }}
                    className="text-[#756B58] transition-colors hover:text-[#C8A85A]"
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
