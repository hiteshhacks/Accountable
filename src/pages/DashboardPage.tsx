import { useNavigate } from 'react-router-dom';
import {
  FileSpreadsheet,
  CheckCircle2,
  Clock,
  Upload,
  ArrowRight,
  MoreHorizontal,
} from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { MOCK_UPLOADS } from '../mockData';

export function DashboardPage() {
  const navigate = useNavigate();

  return (
    <AppLayout>
      {/* Top Greeting */}
      <div className="mb-8">
        <p className="text-xs font-medium tracking-wider text-[#B9AD92] uppercase">
          Good morning,
        </p>
        <h1 className="mt-1 font-serif text-3xl font-normal text-[#F1E7CF] sm:text-4xl">
          Let's process your financial data.
        </h1>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Card 1 */}
        <div className="rounded-xl border border-[rgba(200,168,90,0.18)] bg-[#17130D] p-5 shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg border border-[rgba(200,168,90,0.25)] bg-[#1D1810] text-[#C8A85A]">
              <FileSpreadsheet className="size-4" />
            </div>
            <div>
              <p className="font-serif text-2xl font-normal text-[#F1E7CF]">12,450</p>
              <p className="text-xs text-[#B9AD92]">Total transactions</p>
            </div>
          </div>
        </div>

        {/* Card 2 */}
        <div className="rounded-xl border border-[rgba(200,168,90,0.18)] bg-[#17130D] p-5 shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg border border-[rgba(200,168,90,0.25)] bg-[#1D1810] text-[#C8A85A]">
              <CheckCircle2 className="size-4" />
            </div>
            <div>
              <p className="font-serif text-2xl font-normal text-[#F1E7CF]">11,982</p>
              <p className="text-xs text-[#B9AD92]">Processed</p>
            </div>
          </div>
        </div>

        {/* Card 3 */}
        <div className="rounded-xl border border-[rgba(200,168,90,0.18)] bg-[#17130D] p-5 shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg border border-[rgba(200,168,90,0.25)] bg-[#1D1810] text-[#C8A85A]">
              <Clock className="size-4" />
            </div>
            <div>
              <p className="font-serif text-2xl font-normal text-[#F1E7CF]">468</p>
              <p className="text-xs text-[#B9AD92]">Last uploaded</p>
            </div>
          </div>
        </div>
      </div>

      {/* Primary Action Horizontal Card */}
      <div
        onClick={() => navigate('/upload')}
        className="group mt-6 cursor-pointer rounded-2xl border border-[rgba(200,168,90,0.25)] bg-gradient-to-r from-[#17130D] to-[#1D1810] p-6 shadow-[0_6px_30px_rgba(0,0,0,0.5)] transition-all duration-300 hover:border-[#C8A85A] hover:shadow-[0_8px_36px_rgba(200,168,90,0.12)] sm:p-7"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-5">
            <div className="flex size-14 items-center justify-center rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#100D08] text-[#C8A85A] transition-colors group-hover:border-[#C8A85A] group-hover:bg-[#C8A85A] group-hover:text-[#0A0805]">
              <Upload className="size-6" />
            </div>
            <div>
              <h2 className="font-serif text-xl font-normal text-[#F1E7CF] sm:text-2xl">
                Upload Transactions
              </h2>
              <p className="mt-1 text-xs text-[#B9AD92] sm:text-sm">
                Upload your Excel or CSV file to get started
              </p>
            </div>
          </div>

          <div className="flex size-10 items-center justify-center rounded-full border border-[rgba(200,168,90,0.3)] bg-[#100D08] text-[#C8A85A] transition-all group-hover:border-[#C8A85A] group-hover:bg-[#C8A85A] group-hover:text-[#0A0805]">
            <ArrowRight className="size-4" />
          </div>
        </div>
      </div>

      {/* Recent Uploads Section */}
      <div className="mt-10">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-serif text-lg font-normal text-[#F1E7CF]">
            Recent uploads
          </h3>
          <button
            type="button"
            onClick={() => navigate('/upload')}
            className="flex items-center gap-1.5 text-xs text-[#B9AD92] transition-colors hover:text-[#C8A85A]"
          >
            <span>View all</span>
            <ArrowRight className="size-3" />
          </button>
        </div>

        <div className="overflow-hidden rounded-xl border border-[rgba(200,168,90,0.18)] bg-[#17130D]">
          {MOCK_UPLOADS.map((item, index) => (
            <div
              key={item.id}
              onClick={() => {
                if (item.status === 'Completed') navigate('/results/job-1024');
                else if (item.status === 'Processing') navigate('/processing/job-1024');
                else navigate('/upload');
              }}
              className={`flex cursor-pointer items-center justify-between px-6 py-4 transition-colors hover:bg-[#1D1810] ${
                index !== MOCK_UPLOADS.length - 1 ? 'border-b border-[rgba(200,168,90,0.1)]' : ''
              }`}
            >
              <div className="flex items-center gap-4">
                <FileSpreadsheet className="size-4 text-[#8F7742]" />
                <span className="font-mono text-sm text-[#F1E7CF]">
                  {item.filename}
                </span>
              </div>

              <div className="flex items-center gap-8">
                <span className="text-xs text-[#B9AD92]">
                  {item.rows}
                </span>

                {/* Status indicator */}
                <div className="w-28">
                  {item.status === 'Completed' && (
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-[#4E7A58]/40 bg-[#4E7A58]/15 px-2.5 py-0.5 text-[11px] font-medium text-[#78A882]">
                      <span className="size-1.5 rounded-full bg-[#78A882]" />
                      Completed
                    </span>
                  )}
                  {item.status === 'Processing' && (
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-[#C8A85A]/40 bg-[#C8A85A]/15 px-2.5 py-0.5 text-[11px] font-medium text-[#D8BC78]">
                      <span className="size-1.5 rounded-full bg-[#D8BC78] animate-pulse" />
                      Processing
                    </span>
                  )}
                  {item.status === 'Failed' && (
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-[#8B3A3A]/40 bg-[#8B3A3A]/15 px-2.5 py-0.5 text-[11px] font-medium text-[#D48080]">
                      <span className="size-1.5 rounded-full bg-[#D48080]" />
                      Failed
                    </span>
                  )}
                </div>

                <span className="text-xs text-[#756B58]">
                  {item.date}
                </span>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate('/results/job-1024');
                  }}
                  className="text-[#756B58] transition-colors hover:text-[#C8A85A]"
                >
                  <MoreHorizontal className="size-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
