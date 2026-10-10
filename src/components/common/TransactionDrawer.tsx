import { useState } from 'react';
import { X, Check, ArrowRight } from 'lucide-react';
import { Transaction } from '../../types';

interface TransactionDrawerProps {
  transaction: Transaction | null;
  onClose: () => void;
  onVerify: (id: string) => void;
}

export function TransactionDrawer({
  transaction,
  onClose,
  onVerify,
}: TransactionDrawerProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'ai'>('overview');

  if (!transaction) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs transition-opacity animate-in fade-in duration-200">
      <div
        className="flex h-full w-full max-w-[480px] flex-col border-l border-[rgba(200,168,90,0.25)] bg-[#17130D] shadow-[0_0_80px_rgba(0,0,0,0.9)] animate-in slide-in-from-right duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between border-b border-[rgba(200,168,90,0.15)] bg-[#1D1810]/70 px-6 py-5">
          <div className="flex items-center gap-3">
            <h2 className="font-mono text-xl font-medium text-[#F1E7CF]">
              {transaction.invoiceNo}
            </h2>
            <span
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
                transaction.status === 'High'
                  ? 'border border-[#4E7A58]/40 bg-[#4E7A58]/20 text-[#78A882]'
                  : transaction.status === 'Review'
                  ? 'border border-[#C8A85A]/40 bg-[#C8A85A]/20 text-[#D8BC78]'
                  : 'border border-[#8B3A3A]/40 bg-[#8B3A3A]/20 text-[#D48080]'
              }`}
            >
              {transaction.status === 'High' ? 'High' : transaction.status === 'Review' ? 'Review' : 'Exception'}
            </span>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="flex size-8 items-center justify-center rounded-lg text-[#756B58] transition-colors hover:bg-[#1D1810] hover:text-[#F1E7CF]"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Tab Headers */}
        <div className="flex border-b border-[rgba(200,168,90,0.12)] px-6">
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className={`py-3 text-xs font-semibold tracking-wider uppercase transition-colors ${
              activeTab === 'overview'
                ? 'border-b-2 border-[#C8A85A] text-[#F1E7CF]'
                : 'text-[#756B58] hover:text-[#B9AD92]'
            }`}
          >
            Overview
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('ai')}
            className={`ml-8 py-3 text-xs font-semibold tracking-wider uppercase transition-colors ${
              activeTab === 'ai'
                ? 'border-b-2 border-[#C8A85A] text-[#F1E7CF]'
                : 'text-[#756B58] hover:text-[#B9AD92]'
            }`}
          >
            AI Analysis
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {activeTab === 'overview' ? (
            <>
              {/* Field Grid */}
              <div className="grid grid-cols-2 gap-y-3.5 gap-x-4 rounded-xl border border-[rgba(200,168,90,0.12)] bg-[#100D08]/60 p-4.5 text-xs">
                <div>
                  <span className="text-[#756B58]">Date</span>
                  <p className="mt-0.5 font-medium text-[#F1E7CF]">{transaction.date}</p>
                </div>
                <div>
                  <span className="text-[#756B58]">Party</span>
                  <p className="mt-0.5 font-medium text-[#F1E7CF]">{transaction.party}</p>
                </div>
                <div>
                  <span className="text-[#756B58]">Amount</span>
                  <p className="mt-0.5 font-mono font-medium text-[#F1E7CF]">{transaction.amount}</p>
                </div>
                <div>
                  <span className="text-[#756B58]">Payment Mode</span>
                  <p className="mt-0.5 font-medium text-[#F1E7CF]">{transaction.paymentMode}</p>
                </div>
                <div>
                  <span className="text-[#756B58]">Taxable Value</span>
                  <p className="mt-0.5 font-mono text-[#B9AD92]">{transaction.taxableValue}</p>
                </div>
                <div>
                  <span className="text-[#756B58]">GST Amount</span>
                  <p className="mt-0.5 font-mono text-[#B9AD92]">{transaction.gstAmount}</p>
                </div>
                <div className="col-span-2">
                  <span className="text-[#756B58]">GSTIN</span>
                  <p className="mt-0.5 font-mono text-[#B9AD92]">{transaction.gstin}</p>
                </div>
                <div className="col-span-2">
                  <span className="text-[#756B58]">Description</span>
                  <p className="mt-0.5 text-[#B9AD92]">{transaction.description}</p>
                </div>
                <div className="col-span-2">
                  <span className="text-[#756B58]">Source File</span>
                  <p className="mt-0.5 font-mono text-[#756B58]">{transaction.sourceFile}</p>
                </div>
              </div>

              {/* Prediction Panel */}
              <div className="rounded-xl border border-[rgba(200,168,90,0.2)] bg-[#1D1810] p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-[11px] text-[#756B58] uppercase tracking-wider">
                      Predicted Voucher
                    </span>
                    <h3 className="font-serif text-2xl font-normal text-[#F1E7CF]">
                      {transaction.predictedVoucher}
                    </h3>
                  </div>
                  <div className="text-right">
                    <span className="text-[11px] text-[#756B58] uppercase tracking-wider">
                      Confidence
                    </span>
                    <p className="font-serif text-2xl font-normal text-[#C8A85A]">
                      {transaction.confidence}%
                    </p>
                  </div>
                </div>

                {/* Candidate Breakdown */}
                <div className="mt-5 space-y-2.5 pt-4 border-t border-[rgba(200,168,90,0.1)]">
                  <span className="text-[11px] text-[#756B58] uppercase tracking-wider block mb-2">
                    Top Candidates
                  </span>
                  {transaction.topCandidates.map((candidate, idx) => (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-[#F1E7CF]">
                          {idx + 1}. {candidate.voucher}
                        </span>
                        <span className="font-mono text-[#C8A85A]">{candidate.confidence}%</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-[#100D08]">
                        <div
                          className="h-full rounded-full bg-[#C8A85A]"
                          style={{ width: `${candidate.confidence}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="space-y-5 text-xs">
              <div className="rounded-xl border border-[rgba(200,168,90,0.15)] bg-[#100D08]/60 p-4.5">
                <span className="text-[11px] text-[#C8A85A] uppercase tracking-wider font-semibold block mb-1.5">
                  Classification Basis
                </span>
                <p className="text-[#B9AD92] leading-relaxed">
                  {transaction.aiAnalysis.classificationBasis}
                </p>
              </div>

              <div className="rounded-xl border border-[rgba(200,168,90,0.15)] bg-[#100D08]/60 p-4.5">
                <span className="text-[11px] text-[#C8A85A] uppercase tracking-wider font-semibold block mb-1.5">
                  Candidate Comparison
                </span>
                <p className="text-[#B9AD92] leading-relaxed">
                  {transaction.aiAnalysis.candidateComparison}
                </p>
              </div>

              <div className="rounded-xl border border-[rgba(200,168,90,0.15)] bg-[#100D08]/60 p-4.5">
                <span className="text-[11px] text-[#C8A85A] uppercase tracking-wider font-semibold block mb-2">
                  Confidence Factors
                </span>
                <div className="flex flex-wrap gap-2">
                  {transaction.aiAnalysis.confidenceFactors.map((f, i) => (
                    <span
                      key={i}
                      className="rounded-md border border-[rgba(200,168,90,0.2)] bg-[#17130D] px-2.5 py-1 text-[11px] text-[#F1E7CF]"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-[rgba(200,168,90,0.15)] bg-[#100D08]/60 p-4.5">
                <span className="text-[11px] text-[#C8A85A] uppercase tracking-wider font-semibold block mb-2">
                  Detected Signals
                </span>
                <div className="flex flex-wrap gap-2">
                  {transaction.aiAnalysis.detectedSignals.map((s, i) => (
                    <span
                      key={i}
                      className="rounded-md border border-[rgba(200,168,90,0.2)] bg-[#17130D] px-2.5 py-1 text-[11px] text-[#D8BC78]"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Bottom Actions */}
        <div className="flex items-center gap-3 border-t border-[rgba(200,168,90,0.15)] bg-[#1D1810]/70 p-5">
          <button
            type="button"
            onClick={() => {
              onVerify(transaction.id);
              onClose();
            }}
            className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#C8A85A] py-2.5 text-xs font-semibold tracking-wide text-[#0A0805] shadow-[0_4px_16px_rgba(200,168,90,0.2)] transition-colors hover:bg-[#D8BC78]"
          >
            <Check className="size-3.5" />
            <span>Mark as correct</span>
          </button>

          <button
            type="button"
            onClick={() => alert(`Change voucher for ${transaction.invoiceNo}`)}
            className="flex items-center justify-center gap-1.5 rounded-lg border border-[rgba(200,168,90,0.25)] bg-[#100D08] px-4 py-2.5 text-xs font-medium text-[#E8D29A] transition-colors hover:border-[#C8A85A] hover:bg-[#17130D]"
          >
            <span>Change voucher</span>
            <ArrowRight className="size-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
