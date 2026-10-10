import { useState } from 'react';
import { X, Check, ArrowRight } from 'lucide-react';
import { Transaction, VoucherType } from '../../types';
import { useApp } from '../../context/AppContext';

interface TransactionDrawerProps {
  transaction: Transaction | null;
  onClose: () => void;
}

export function TransactionDrawer({
  transaction,
  onClose,
}: TransactionDrawerProps) {
  const { verifyTransaction, updateVoucher } = useApp();
  const [activeTab, setActiveTab] = useState<'overview' | 'ai'>('overview');
  const [isChangingVoucher, setIsChangingVoucher] = useState(false);

  if (!transaction) return null;

  const voucherTypes: VoucherType[] = ['Purchase', 'Sales', 'Payment', 'Expense', 'Journal'];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-xs transition-opacity animate-in fade-in duration-200">
      <div
        className="flex h-full w-full max-w-[500px] flex-col border-l border-[rgba(200,168,90,0.3)] bg-[#17130D] shadow-[0_0_80px_rgba(0,0,0,0.95)] animate-in slide-in-from-right duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between border-b border-[rgba(200,168,90,0.18)] bg-[#1D1810]/80 px-7 py-6">
          <div className="flex items-center gap-3">
            <h2 className="font-mono text-2xl font-medium text-[#F0E5CA]">
              {transaction.invoiceNo}
            </h2>
            <span
              className={`rounded-full px-3 py-0.5 text-xs font-semibold ${
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
            className="flex size-9 items-center justify-center rounded-lg text-[#756B58] transition-colors hover:bg-[#1D1810] hover:text-[#F0E5CA]"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Tab Headers */}
        <div className="flex border-b border-[rgba(200,168,90,0.15)] px-7">
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className={`py-3.5 text-xs font-semibold tracking-wider uppercase transition-colors ${
              activeTab === 'overview'
                ? 'border-b-2 border-[#C8A85A] text-[#F0E5CA]'
                : 'text-[#756B58] hover:text-[#B9AD92]'
            }`}
          >
            Overview
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('ai')}
            className={`ml-8 py-3.5 text-xs font-semibold tracking-wider uppercase transition-colors ${
              activeTab === 'ai'
                ? 'border-b-2 border-[#C8A85A] text-[#F0E5CA]'
                : 'text-[#756B58] hover:text-[#B9AD92]'
            }`}
          >
            AI Analysis
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-7 space-y-6">
          {activeTab === 'overview' ? (
            <>
              {/* Field Grid */}
              <div className="grid grid-cols-2 gap-y-4 gap-x-5 rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#100D08]/70 p-5 text-xs sm:text-sm">
                <div>
                  <span className="text-[#756B58] font-medium">Date</span>
                  <p className="mt-1 font-medium text-[#F0E5CA]">{transaction.date}</p>
                </div>
                <div>
                  <span className="text-[#756B58] font-medium">Party</span>
                  <p className="mt-1 font-medium text-[#F0E5CA]">{transaction.party}</p>
                </div>
                <div>
                  <span className="text-[#756B58] font-medium">Amount</span>
                  <p className="mt-1 font-mono font-medium text-[#F0E5CA]">{transaction.amount}</p>
                </div>
                <div>
                  <span className="text-[#756B58] font-medium">Payment Mode</span>
                  <p className="mt-1 font-medium text-[#F0E5CA]">{transaction.paymentMode}</p>
                </div>
                <div>
                  <span className="text-[#756B58] font-medium">Taxable Value</span>
                  <p className="mt-1 font-mono text-[#B9AD92]">{transaction.taxableValue}</p>
                </div>
                <div>
                  <span className="text-[#756B58] font-medium">GST Amount</span>
                  <p className="mt-1 font-mono text-[#B9AD92]">{transaction.gstAmount}</p>
                </div>
                <div className="col-span-2">
                  <span className="text-[#756B58] font-medium">GSTIN</span>
                  <p className="mt-1 font-mono text-[#B9AD92]">{transaction.gstin}</p>
                </div>
                <div className="col-span-2">
                  <span className="text-[#756B58] font-medium">Description</span>
                  <p className="mt-1 text-[#B9AD92] leading-relaxed">{transaction.description}</p>
                </div>
                <div className="col-span-2">
                  <span className="text-[#756B58] font-medium">Source File</span>
                  <p className="mt-1 font-mono text-[#756B58]">{transaction.sourceFile}</p>
                </div>
              </div>

              {/* Prediction Panel */}
              <div className="rounded-2xl border border-[rgba(200,168,90,0.25)] bg-[#1D1810] p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs text-[#756B58] uppercase tracking-wider font-medium">
                      Predicted Voucher
                    </span>
                    <h3 className="font-serif text-2xl font-normal text-[#F0E5CA]">
                      {transaction.predictedVoucher}
                    </h3>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-[#756B58] uppercase tracking-wider font-medium">
                      Confidence
                    </span>
                    <p className="font-serif text-2xl font-normal text-[#C8A85A]">
                      {transaction.confidence}%
                    </p>
                  </div>
                </div>

                {/* Candidate Breakdown */}
                <div className="mt-6 space-y-3 pt-5 border-t border-[rgba(200,168,90,0.15)]">
                  <span className="text-xs text-[#756B58] uppercase tracking-wider block mb-2 font-medium">
                    Top Candidates
                  </span>
                  {transaction.topCandidates.map((candidate, idx) => (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-xs sm:text-sm">
                        <span className="text-[#F0E5CA]">
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

              {/* Change Voucher Selection UI */}
              {isChangingVoucher && (
                <div className="rounded-2xl border border-[rgba(200,168,90,0.3)] bg-[#100D08] p-5 animate-in fade-in duration-200">
                  <span className="text-xs text-[#C8A85A] uppercase tracking-wider font-medium block mb-3">
                    Select New Voucher Type
                  </span>
                  <div className="grid grid-cols-2 gap-2">
                    {voucherTypes.map((v) => (
                      <button
                        key={v}
                        type="button"
                        onClick={() => {
                          updateVoucher(transaction.id, v);
                          setIsChangingVoucher(false);
                        }}
                        className={`rounded-xl px-3.5 py-2 text-xs font-medium transition-all ${
                          transaction.predictedVoucher === v
                            ? 'bg-[#C8A85A] text-[#090704] font-semibold'
                            : 'border border-[rgba(200,168,90,0.2)] bg-[#17130D] text-[#F0E5CA] hover:border-[#C8A85A]'
                        }`}
                      >
                        {v}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="space-y-5 text-xs sm:text-sm">
              <div className="rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#100D08]/70 p-5">
                <span className="text-xs text-[#C8A85A] uppercase tracking-wider font-semibold block mb-2">
                  Classification Basis
                </span>
                <p className="text-[#B9AD92] leading-relaxed">
                  {transaction.aiAnalysis.classificationBasis}
                </p>
              </div>

              <div className="rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#100D08]/70 p-5">
                <span className="text-xs text-[#C8A85A] uppercase tracking-wider font-semibold block mb-2">
                  Candidate Comparison
                </span>
                <p className="text-[#B9AD92] leading-relaxed">
                  {transaction.aiAnalysis.candidateComparison}
                </p>
              </div>

              <div className="rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#100D08]/70 p-5">
                <span className="text-xs text-[#C8A85A] uppercase tracking-wider font-semibold block mb-2.5">
                  Confidence Factors
                </span>
                <div className="flex flex-wrap gap-2">
                  {transaction.aiAnalysis.confidenceFactors.map((f, i) => (
                    <span
                      key={i}
                      className="rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#17130D] px-3 py-1.5 text-xs text-[#F0E5CA]"
                    >
                      {f}
                    </span>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#100D08]/70 p-5">
                <span className="text-xs text-[#C8A85A] uppercase tracking-wider font-semibold block mb-2.5">
                  Detected Signals
                </span>
                <div className="flex flex-wrap gap-2">
                  {transaction.aiAnalysis.detectedSignals.map((s, i) => (
                    <span
                      key={i}
                      className="rounded-lg border border-[rgba(200,168,90,0.2)] bg-[#17130D] px-3 py-1.5 text-xs text-[#D8BC78]"
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
        <div className="flex items-center gap-3 border-t border-[rgba(200,168,90,0.18)] bg-[#1D1810]/80 p-6">
          <button
            type="button"
            onClick={() => {
              verifyTransaction(transaction.id);
              onClose();
            }}
            className="flex flex-1 h-[48px] items-center justify-center gap-2 rounded-xl bg-[#D8BC78] text-sm font-semibold tracking-wide text-[#090704] shadow-[0_4px_20px_rgba(200,168,90,0.25)] transition-all hover:bg-[#E8D29A]"
          >
            <Check className="size-4" />
            <span>Mark as correct</span>
          </button>

          <button
            type="button"
            onClick={() => setIsChangingVoucher(!isChangingVoucher)}
            className="flex h-[48px] items-center justify-center gap-1.5 rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#100D08] px-5 text-sm font-medium text-[#E8D29A] transition-colors hover:border-[#C8A85A] hover:bg-[#17130D]"
          >
            <span>Change voucher</span>
            <ArrowRight className="size-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
