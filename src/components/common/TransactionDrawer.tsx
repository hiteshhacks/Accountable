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
        className="flex h-full w-full max-w-[500px] flex-col border-l shadow-[0_0_80px_rgba(0,0,0,0.7)] animate-in slide-in-from-right duration-300"
        style={{ borderColor: 'var(--border-strong)', background: 'var(--surface)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div
          className="flex items-center justify-between border-b px-7 py-6"
          style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface-elevated) 80%, transparent)' }}
        >
          <div className="flex items-center gap-3">
            <h2 className="font-mono text-2xl font-medium" style={{ color: 'var(--text)' }}>
              {transaction.invoiceNo}
            </h2>
            <span
              className="rounded-full px-3 py-0.5 text-xs font-semibold border"
              style={{
                borderColor: transaction.status === 'High'
                  ? 'color-mix(in srgb, var(--status-success) 40%, transparent)'
                  : transaction.status === 'Review'
                    ? 'color-mix(in srgb, var(--status-warn) 40%, transparent)'
                    : 'color-mix(in srgb, var(--status-error) 40%, transparent)',
                background: transaction.status === 'High'
                  ? 'color-mix(in srgb, var(--status-success) 20%, transparent)'
                  : transaction.status === 'Review'
                    ? 'color-mix(in srgb, var(--status-warn) 20%, transparent)'
                    : 'color-mix(in srgb, var(--status-error) 20%, transparent)',
                color: transaction.status === 'High'
                  ? 'var(--status-success-text)'
                  : transaction.status === 'Review'
                    ? 'var(--status-warn-text)'
                    : 'var(--status-error-text)',
              }}
            >
              {transaction.status === 'High' ? 'High' : transaction.status === 'Review' ? 'Review' : 'Exception'}
            </span>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="flex size-9 items-center justify-center rounded-lg transition-colors"
            style={{ color: 'var(--text-faint)' }}
            onMouseEnter={(e) => {
              const el = e.currentTarget as HTMLElement;
              el.style.background = 'var(--surface-elevated)';
              el.style.color = 'var(--text)';
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget as HTMLElement;
              el.style.background = 'transparent';
              el.style.color = 'var(--text-faint)';
            }}
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Tab Headers */}
        <div className="flex border-b px-7" style={{ borderColor: 'var(--border)' }}>
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className="py-3.5 text-xs font-semibold tracking-wider uppercase transition-colors cursor-pointer"
            style={{
              borderBottom: activeTab === 'overview' ? '2px solid var(--accent)' : '2px solid transparent',
              color: activeTab === 'overview' ? 'var(--text)' : 'var(--text-faint)',
            }}
            onMouseEnter={(e) => {
              if (activeTab !== 'overview') (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)';
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'overview') (e.currentTarget as HTMLElement).style.color = 'var(--text-faint)';
            }}
          >
            Overview
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('ai')}
            className="ml-8 py-3.5 text-xs font-semibold tracking-wider uppercase transition-colors cursor-pointer"
            style={{
              borderBottom: activeTab === 'ai' ? '2px solid var(--accent)' : '2px solid transparent',
              color: activeTab === 'ai' ? 'var(--text)' : 'var(--text-faint)',
            }}
            onMouseEnter={(e) => {
              if (activeTab !== 'ai') (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)';
            }}
            onMouseLeave={(e) => {
              if (activeTab !== 'ai') (e.currentTarget as HTMLElement).style.color = 'var(--text-faint)';
            }}
          >
            AI Analysis
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-7 space-y-6">
          {activeTab === 'overview' ? (
            <>
              {/* Field Grid */}
              <div
                className="grid grid-cols-2 gap-y-4 gap-x-5 rounded-2xl border p-5 text-xs sm:text-sm"
                style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface-input) 70%, transparent)' }}
              >
                <div>
                  <span className="font-medium" style={{ color: 'var(--text-faint)' }}>Date</span>
                  <p className="mt-1 font-medium" style={{ color: 'var(--text)' }}>{transaction.date}</p>
                </div>
                <div>
                  <span className="font-medium" style={{ color: 'var(--text-faint)' }}>Party</span>
                  <p className="mt-1 font-medium" style={{ color: 'var(--text)' }}>{transaction.party}</p>
                </div>
                <div>
                  <span className="font-medium" style={{ color: 'var(--text-faint)' }}>Amount</span>
                  <p className="mt-1 font-mono font-medium" style={{ color: 'var(--text)' }}>{transaction.amount}</p>
                </div>
                <div>
                  <span className="font-medium" style={{ color: 'var(--text-faint)' }}>Payment Mode</span>
                  <p className="mt-1 font-medium" style={{ color: 'var(--text)' }}>{transaction.paymentMode}</p>
                </div>
                <div>
                  <span className="font-medium" style={{ color: 'var(--text-faint)' }}>Taxable Value</span>
                  <p className="mt-1 font-mono" style={{ color: 'var(--text-muted)' }}>{transaction.taxableValue}</p>
                </div>
                <div>
                  <span className="font-medium" style={{ color: 'var(--text-faint)' }}>GST Amount</span>
                  <p className="mt-1 font-mono" style={{ color: 'var(--text-muted)' }}>{transaction.gstAmount}</p>
                </div>
                <div className="col-span-2">
                  <span className="font-medium" style={{ color: 'var(--text-faint)' }}>GSTIN</span>
                  <p className="mt-1 font-mono" style={{ color: 'var(--text-muted)' }}>{transaction.gstin}</p>
                </div>
                <div className="col-span-2">
                  <span className="font-medium" style={{ color: 'var(--text-faint)' }}>Description</span>
                  <p className="mt-1 leading-relaxed" style={{ color: 'var(--text-muted)' }}>{transaction.description}</p>
                </div>
                <div className="col-span-2">
                  <span className="font-medium" style={{ color: 'var(--text-faint)' }}>Source File</span>
                  <p className="mt-1 font-mono" style={{ color: 'var(--text-faint)' }}>{transaction.sourceFile}</p>
                </div>
              </div>

              {/* Prediction Panel */}
              <div
                className="rounded-2xl border p-6"
                style={{ borderColor: 'var(--border-strong)', background: 'var(--surface-elevated)' }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs uppercase tracking-wider font-medium" style={{ color: 'var(--text-faint)' }}>
                      Predicted Voucher
                    </span>
                    <h3 className="font-serif text-2xl font-normal" style={{ color: 'var(--text)' }}>
                      {transaction.predictedVoucher}
                    </h3>
                  </div>
                  <div className="text-right">
                    <span className="text-xs uppercase tracking-wider font-medium" style={{ color: 'var(--text-faint)' }}>
                      Confidence
                    </span>
                    <p className="font-serif text-2xl font-normal" style={{ color: 'var(--accent)' }}>
                      {transaction.confidence}%
                    </p>
                  </div>
                </div>

                {/* Candidate Breakdown */}
                <div className="mt-6 space-y-3 pt-5 border-t" style={{ borderColor: 'var(--border)' }}>
                  <span className="text-xs uppercase tracking-wider block mb-2 font-medium" style={{ color: 'var(--text-faint)' }}>
                    Top Candidates
                  </span>
                  {transaction.topCandidates.map((candidate, idx) => (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-xs sm:text-sm">
                        <span style={{ color: 'var(--text)' }}>
                          {idx + 1}. {candidate.voucher}
                        </span>
                        <span className="font-mono" style={{ color: 'var(--accent)' }}>{candidate.confidence}%</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full" style={{ background: 'var(--surface-input)' }}>
                        <div
                          className="h-full rounded-full"
                          style={{ background: 'var(--accent)', width: `${candidate.confidence}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Change Voucher Selection UI */}
              {isChangingVoucher && (
                <div
                  className="rounded-2xl border p-5 animate-in fade-in duration-200"
                  style={{ borderColor: 'var(--border-strong)', background: 'var(--surface-input)' }}
                >
                  <span className="text-xs uppercase tracking-wider font-medium block mb-3" style={{ color: 'var(--accent)' }}>
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
                        className="rounded-xl border px-3.5 py-2 text-xs font-medium transition-all cursor-pointer"
                        style={{
                          borderColor: transaction.predictedVoucher === v ? 'var(--accent)' : 'var(--border)',
                          background: transaction.predictedVoucher === v ? 'var(--accent)' : 'var(--surface)',
                          color: transaction.predictedVoucher === v ? 'var(--accent-contrast)' : 'var(--text)',
                        }}
                        onMouseEnter={(e) => {
                          if (transaction.predictedVoucher !== v) (e.currentTarget as HTMLElement).style.borderColor = 'var(--accent)';
                        }}
                        onMouseLeave={(e) => {
                          if (transaction.predictedVoucher !== v) (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
                        }}
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
              <div
                className="rounded-2xl border p-5"
                style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface-input) 70%, transparent)' }}
              >
                <span className="text-xs uppercase tracking-wider font-semibold block mb-2" style={{ color: 'var(--accent)' }}>
                  Classification Basis
                </span>
                <p className="leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                  {transaction.aiAnalysis.classificationBasis}
                </p>
              </div>

              <div
                className="rounded-2xl border p-5"
                style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface-input) 70%, transparent)' }}
              >
                <span className="text-xs uppercase tracking-wider font-semibold block mb-2" style={{ color: 'var(--accent)' }}>
                  Candidate Comparison
                </span>
                <p className="leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                  {transaction.aiAnalysis.candidateComparison}
                </p>
              </div>

              <div
                className="rounded-2xl border p-5"
                style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface-input) 70%, transparent)' }}
              >
                <span className="text-xs uppercase tracking-wider font-semibold block mb-2.5" style={{ color: 'var(--accent)' }}>
                  Confidence Factors
                </span>
                <div className="flex flex-wrap gap-2">
                  {transaction.aiAnalysis.confidenceFactors.map((f, i) => (
                    <span
                      key={i}
                      className="rounded-lg border px-3 py-1.5 text-xs"
                      style={{ borderColor: 'var(--border)', background: 'var(--surface)', color: 'var(--text)' }}
                    >
                      {f}
                    </span>
                  ))}
                </div>
              </div>

              <div
                className="rounded-2xl border p-5"
                style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface-input) 70%, transparent)' }}
              >
                <span className="text-xs uppercase tracking-wider font-semibold block mb-2.5" style={{ color: 'var(--accent)' }}>
                  Detected Signals
                </span>
                <div className="flex flex-wrap gap-2">
                  {transaction.aiAnalysis.detectedSignals.map((s, i) => (
                    <span
                      key={i}
                      className="rounded-lg border px-3 py-1.5 text-xs"
                      style={{ borderColor: 'var(--border)', background: 'var(--surface)', color: 'var(--accent-warm)' }}
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
        <div
          className="flex items-center gap-3 border-t p-6"
          style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface-elevated) 80%, transparent)' }}
        >
          <button
            type="button"
            onClick={() => {
              verifyTransaction(transaction.id);
              onClose();
            }}
            className="flex flex-1 h-[48px] items-center justify-center gap-2 rounded-xl text-sm font-semibold tracking-wide transition-all cursor-pointer"
            style={{ background: 'var(--accent-warm)', color: 'var(--accent-contrast)', boxShadow: 'var(--shadow-gold)' }}
            onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.background = 'var(--accent-light)'}
            onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.background = 'var(--accent-warm)'}
          >
            <Check className="size-4" />
            <span>Mark as correct</span>
          </button>

          <button
            type="button"
            onClick={() => setIsChangingVoucher(!isChangingVoucher)}
            className="flex h-[48px] items-center justify-center gap-1.5 rounded-xl border px-5 text-sm font-medium transition-colors cursor-pointer"
            style={{ borderColor: 'var(--border-strong)', background: 'var(--surface-input)', color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => {
              const el = e.currentTarget as HTMLElement;
              el.style.borderColor = 'var(--accent)';
              el.style.background = 'var(--surface)';
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget as HTMLElement;
              el.style.borderColor = 'var(--border-strong)';
              el.style.background = 'var(--surface-input)';
            }}
          >
            <span>Change voucher</span>
            <ArrowRight className="size-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
