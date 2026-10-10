import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Download,
  Search,
  ChevronDown,
  MoreHorizontal,
  Check,
  FolderOpen,
  Upload,
} from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { TransactionDrawer } from '../components/common/TransactionDrawer';
import { useApp } from '../context/AppContext';
import { Transaction } from '../types';

export function ResultsPage() {
  const navigate = useNavigate();
  const { transactions, exportToExcel, exportToJSON } = useApp();

  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [filterTab, setFilterTab] = useState<'all' | 'high' | 'review' | 'exception'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [voucherFilter, setVoucherFilter] = useState('all');
  const [selectedRowIds, setSelectedRowIds] = useState<string[]>([]);

  // Calculate metrics
  const totalCount = transactions.length;
  const highCount = transactions.filter((t) => t.status === 'High').length;
  const reviewCount = transactions.filter((t) => t.status === 'Review').length;
  const exceptionCount = transactions.filter((t) => t.status === 'Exception').length;

  const highPct = totalCount > 0 ? ((highCount / totalCount) * 100).toFixed(1) : '0.0';
  const reviewPct = totalCount > 0 ? ((reviewCount / totalCount) * 100).toFixed(1) : '0.0';
  const exceptionPct = totalCount > 0 ? ((exceptionCount / totalCount) * 100).toFixed(1) : '0.0';

  const toggleSelectRow = (id: string) => {
    setSelectedRowIds((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedRowIds.length === transactions.length) {
      setSelectedRowIds([]);
    } else {
      setSelectedRowIds(transactions.map((t) => t.id));
    }
  };

  const filteredTransactions = transactions.filter((t) => {
    if (filterTab === 'high' && t.status !== 'High') return false;
    if (filterTab === 'review' && t.status !== 'Review') return false;
    if (filterTab === 'exception' && t.status !== 'Exception') return false;

    if (voucherFilter !== 'all' && t.predictedVoucher !== voucherFilter) return false;

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        t.invoiceNo.toLowerCase().includes(q) ||
        t.party.toLowerCase().includes(q) ||
        t.amount.toLowerCase().includes(q) ||
        t.predictedVoucher.toLowerCase().includes(q)
      );
    }

    return true;
  });

  return (
    <AppLayout>
      <div>
        {/* Header with Title and Download Actions */}
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="font-serif text-3xl font-normal sm:text-4xl lg:text-5xl" style={{ color: 'var(--text)' }}>
              Processing complete
            </h1>
            <p className="mt-2 text-base font-medium" style={{ color: 'var(--text-secondary)' }}>
              {totalCount > 0
                ? `${totalCount.toLocaleString()} transactions analyzed successfully.`
                : 'No classification results available yet.'}
            </p>
          </div>

          {totalCount > 0 && (
            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={exportToExcel}
                className="inline-flex items-center gap-2.5 rounded-xl border px-6 py-3 text-sm font-semibold shadow-xs transition-colors cursor-pointer"
                style={{ borderColor: 'var(--border-strong)', background: 'var(--surface)', color: 'var(--text)' }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget as HTMLElement;
                  el.style.borderColor = 'var(--accent)';
                  el.style.background = 'var(--surface-elevated)';
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget as HTMLElement;
                  el.style.borderColor = 'var(--border-strong)';
                  el.style.background = 'var(--surface)';
                }}
              >
                <Download className="size-4.5" style={{ color: 'var(--accent)' }} />
                <span>Download Excel</span>
              </button>

              <button
                type="button"
                onClick={exportToJSON}
                className="inline-flex items-center gap-2.5 rounded-xl border px-6 py-3 text-sm font-semibold shadow-xs transition-colors cursor-pointer"
                style={{ borderColor: 'var(--border-strong)', background: 'var(--surface)', color: 'var(--text)' }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget as HTMLElement;
                  el.style.borderColor = 'var(--accent)';
                  el.style.background = 'var(--surface-elevated)';
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget as HTMLElement;
                  el.style.borderColor = 'var(--border-strong)';
                  el.style.background = 'var(--surface)';
                }}
              >
                <Download className="size-4.5" style={{ color: 'var(--accent)' }} />
                <span>Download JSON</span>
              </button>
            </div>
          )}
        </div>

        {totalCount === 0 ? (
          /* Empty State */
          <div
            className="mt-12 flex flex-col items-center justify-center rounded-2xl border px-6 py-20 text-center"
            style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface) 90%, transparent)' }}
          >
            <div
              className="flex size-16 items-center justify-center rounded-2xl border"
              style={{ borderColor: 'var(--border-strong)', background: 'var(--bg-elevated)', color: 'var(--accent)' }}
            >
              <FolderOpen className="size-8" />
            </div>
            <h3 className="mt-6 font-serif text-2xl font-normal sm:text-3xl" style={{ color: 'var(--text)' }}>
              No classification results yet.
            </h3>
            <p className="mt-2.5 max-w-lg text-base" style={{ color: 'var(--text-secondary)' }}>
              Upload a transaction file to view AI classification results, confidence scores, and GST intelligence.
            </p>
            <button
              type="button"
              onClick={() => navigate('/upload')}
              className="mt-7 inline-flex items-center gap-2.5 rounded-xl px-8 py-4 text-base font-semibold transition-all hover:opacity-90"
              style={{ background: 'var(--accent-warm)', color: 'var(--accent-contrast)' }}
            >
              <Upload className="size-5" />
              <span>Upload Transactions →</span>
            </button>
          </div>
        ) : (
          <>
            {/* 3 Summary Cards - High Readability */}
            <div className="mt-9 grid grid-cols-1 gap-6 sm:grid-cols-3">
              {/* High Confidence */}
              <div
                onClick={() => setFilterTab('high')}
                className="cursor-pointer rounded-2xl border p-7 transition-all"
                style={{
                  borderColor: filterTab === 'high' ? 'var(--status-success)' : 'var(--border)',
                  background: filterTab === 'high' ? 'var(--surface-elevated)' : 'var(--surface)',
                }}
                onMouseEnter={(e) => {
                  if (filterTab !== 'high') (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-strong)';
                }}
                onMouseLeave={(e) => {
                  if (filterTab !== 'high') (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
                }}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-serif text-4xl font-normal" style={{ color: 'var(--text)' }}>
                      {highCount.toLocaleString()}
                    </p>
                    <p className="mt-1.5 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                      High confidence (≥ 70%)
                    </p>
                  </div>
                  <span
                    className="rounded-full border px-3.5 py-1 text-xs font-semibold"
                    style={{
                      borderColor: 'color-mix(in srgb, var(--status-success) 40%, transparent)',
                      background: 'color-mix(in srgb, var(--status-success) 20%, transparent)',
                      color: 'var(--status-success-text)',
                    }}
                  >
                    {highPct}%
                  </span>
                </div>
              </div>

              {/* Needs Review */}
              <div
                onClick={() => setFilterTab('review')}
                className="cursor-pointer rounded-2xl border p-7 transition-all"
                style={{
                  borderColor: filterTab === 'review' ? 'var(--status-warn)' : 'var(--border)',
                  background: filterTab === 'review' ? 'var(--surface-elevated)' : 'var(--surface)',
                }}
                onMouseEnter={(e) => {
                  if (filterTab !== 'review') (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-strong)';
                }}
                onMouseLeave={(e) => {
                  if (filterTab !== 'review') (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
                }}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-serif text-4xl font-normal" style={{ color: 'var(--text)' }}>
                      {reviewCount.toLocaleString()}
                    </p>
                    <p className="mt-1.5 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                      Needs review (&lt; 70%)
                    </p>
                  </div>
                  <span
                    className="rounded-full border px-3.5 py-1 text-xs font-semibold"
                    style={{
                      borderColor: 'color-mix(in srgb, var(--status-warn) 40%, transparent)',
                      background: 'color-mix(in srgb, var(--status-warn) 20%, transparent)',
                      color: 'var(--status-warn-text)',
                    }}
                  >
                    {reviewPct}%
                  </span>
                </div>
              </div>

              {/* Exceptions */}
              <div
                onClick={() => setFilterTab('exception')}
                className="cursor-pointer rounded-2xl border p-7 transition-all"
                style={{
                  borderColor: filterTab === 'exception' ? 'var(--status-error)' : 'var(--border)',
                  background: filterTab === 'exception' ? 'var(--surface-elevated)' : 'var(--surface)',
                }}
                onMouseEnter={(e) => {
                  if (filterTab !== 'exception') (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-strong)';
                }}
                onMouseLeave={(e) => {
                  if (filterTab !== 'exception') (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
                }}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-serif text-4xl font-normal" style={{ color: 'var(--text)' }}>
                      {exceptionCount.toLocaleString()}
                    </p>
                    <p className="mt-1.5 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                      Exceptions (validation issues)
                    </p>
                  </div>
                  <span
                    className="rounded-full border px-3.5 py-1 text-xs font-semibold"
                    style={{
                      borderColor: 'color-mix(in srgb, var(--status-error) 40%, transparent)',
                      background: 'color-mix(in srgb, var(--status-error) 20%, transparent)',
                      color: 'var(--status-error-text)',
                    }}
                  >
                    {exceptionPct}%
                  </span>
                </div>
              </div>
            </div>

            {/* Filter Tabs & Search Bar */}
            <div className="mt-10 space-y-5">
              <div className="flex border-b pb-px" style={{ borderColor: 'var(--border)' }}>
                {['all', 'high', 'review', 'exception'].map((tab) => {
                  const labels: Record<string, string> = {
                    all: 'All transactions',
                    high: 'High confidence',
                    review: 'Needs review',
                    exception: 'Exceptions'
                  };
                  const counts: Record<string, number> = {
                    all: totalCount,
                    high: highCount,
                    review: reviewCount,
                    exception: exceptionCount
                  };
                  return (
                    <button
                      key={tab}
                      type="button"
                      onClick={() => setFilterTab(tab as any)}
                      className="ml-0 first:ml-0 [&:not(:first-child)]:ml-10 pb-4 text-sm font-semibold tracking-wider transition-colors cursor-pointer"
                      style={{
                        borderBottom: filterTab === tab ? '2px solid var(--accent)' : '2px solid transparent',
                        color: filterTab === tab ? 'var(--text)' : 'var(--text-muted)',
                      }}
                      onMouseEnter={(e) => {
                        if (filterTab !== tab) (e.currentTarget as HTMLElement).style.color = 'var(--text)';
                      }}
                      onMouseLeave={(e) => {
                        if (filterTab !== tab) (e.currentTarget as HTMLElement).style.color = 'var(--text-muted)';
                      }}
                    >
                      {labels[tab]}{' '}
                      <span className="ml-1.5 font-mono font-bold" style={{ color: 'var(--accent)' }}>{counts[tab]}</span>
                    </button>
                  );
                })}
              </div>

              {/* Search Bar + Dropdowns */}
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="relative flex-1 max-w-md">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 size-4.5" style={{ color: 'var(--text-muted)' }} />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by invoice, party, amount..."
                    className="w-full rounded-xl border py-3 pl-11 pr-4 text-sm transition-colors focus:outline-hidden"
                    style={{
                      borderColor: 'var(--border)',
                      background: 'var(--surface)',
                      color: 'var(--text)',
                    }}
                    onFocus={(e) => (e.target.style.borderColor = 'var(--accent)')}
                    onBlur={(e) => (e.target.style.borderColor = 'var(--border)')}
                  />
                </div>

                <div className="flex items-center gap-3">
                  <div className="relative">
                    <select
                      value={voucherFilter}
                      onChange={(e) => setVoucherFilter(e.target.value)}
                      className="appearance-none rounded-xl border py-3 pl-4 pr-10 text-sm font-medium transition-colors focus:outline-hidden"
                      style={{
                        borderColor: 'var(--border)',
                        background: 'var(--surface)',
                        color: 'var(--text)',
                      }}
                      onFocus={(e) => (e.target.style.borderColor = 'var(--accent)')}
                      onBlur={(e) => (e.target.style.borderColor = 'var(--border)')}
                    >
                      <option value="all">Voucher type (All)</option>
                      <option value="Purchase">Purchase</option>
                      <option value="Sales">Sales</option>
                      <option value="Payment">Payment</option>
                      <option value="Expense">Expense</option>
                      <option value="Journal">Journal</option>
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 size-4" style={{ color: 'var(--accent)' }} />
                  </div>
                </div>
              </div>
            </div>

            {/* High Readability Transaction Table */}
            <div
              className="mt-6 overflow-x-auto rounded-2xl border"
              style={{
                borderColor: 'var(--border)',
                background: 'var(--surface)',
                boxShadow: 'var(--shadow-card)'
              }}
            >
              <table className="w-full text-left text-sm">
                <thead
                  className="border-b uppercase tracking-wider"
                  style={{
                    borderColor: 'var(--border)',
                    background: 'color-mix(in srgb, var(--surface-elevated) 90%, transparent)',
                    color: 'var(--text-secondary)'
                  }}
                >
                  <tr>
                    <th className="py-4 pl-6 pr-2">
                      <input
                        type="checkbox"
                        checked={selectedRowIds.length === transactions.length}
                        onChange={toggleSelectAll}
                        className="rounded border"
                        style={{
                          borderColor: 'var(--border-strong)',
                          background: 'var(--surface-input)',
                          accentColor: 'var(--accent)'
                        }}
                      />
                    </th>
                    <th className="py-4 px-4 font-semibold">Invoice no.</th>
                    <th className="py-4 px-4 font-semibold">Date</th>
                    <th className="py-4 px-4 font-semibold">Party</th>
                    <th className="py-4 px-4 font-semibold">Amount</th>
                    <th className="py-4 px-4 font-semibold">Predicted voucher</th>
                    <th className="py-4 px-4 font-semibold">Confidence</th>
                    <th className="py-4 px-4 font-semibold">Status</th>
                    <th className="py-4 pr-6 text-right font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody
                  className="divide-y"
                  style={{ borderColor: 'var(--border)' }}
                >
                  {filteredTransactions.map((tx) => {
                    const isSelected = selectedRowIds.includes(tx.id);
                    return (
                      <tr
                        key={tx.id}
                        onClick={() => setSelectedTransaction(tx)}
                        className="cursor-pointer transition-colors duration-150"
                        style={{
                          background: isSelected ? 'color-mix(in srgb, var(--accent) 12%, transparent)' : 'transparent'
                        }}
                        onMouseEnter={(e) => {
                          if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'var(--surface-elevated)';
                        }}
                        onMouseLeave={(e) => {
                          if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'transparent';
                        }}
                      >
                        <td
                          className="py-4.5 pl-6 pr-2"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleSelectRow(tx.id);
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelectRow(tx.id)}
                            className="rounded border"
                            style={{
                              borderColor: 'var(--border-strong)',
                              background: 'var(--surface-input)',
                              accentColor: 'var(--accent)'
                            }}
                          />
                        </td>
                        <td className="py-4.5 px-4 font-mono font-semibold" style={{ color: 'var(--text)' }}>
                          {tx.invoiceNo}
                        </td>
                        <td className="py-4.5 px-4 font-medium" style={{ color: 'var(--text-muted)' }}>{tx.date}</td>
                        <td className="py-4.5 px-4 font-medium" style={{ color: 'var(--text)' }}>{tx.party}</td>
                        <td className="py-4.5 px-4 font-mono font-semibold" style={{ color: 'var(--text)' }}>{tx.amount}</td>
                        <td className="py-4.5 px-4 font-semibold" style={{ color: 'var(--text-secondary)' }}>
                          {tx.predictedVoucher}
                        </td>
                        <td className="py-4.5 px-4 font-mono font-semibold" style={{ color: 'var(--accent)' }}>
                          {tx.confidence}%
                        </td>
                        <td className="py-4.5 px-4">
                          {tx.isVerified ? (
                            <span
                              className="inline-flex items-center gap-1.5 text-xs font-semibold"
                              style={{ color: 'var(--status-success-text)' }}
                            >
                              <Check className="size-4" /> Verified
                            </span>
                          ) : tx.status === 'High' ? (
                            <span
                              className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold"
                              style={{
                                borderColor: 'color-mix(in srgb, var(--status-success) 40%, transparent)',
                                background: 'color-mix(in srgb, var(--status-success) 20%, transparent)',
                                color: 'var(--status-success-text)'
                              }}
                            >
                              <span className="size-1.5 rounded-full" style={{ background: 'var(--status-success-text)' }} />
                              High
                            </span>
                          ) : tx.status === 'Review' ? (
                            <span
                              className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold"
                              style={{
                                borderColor: 'color-mix(in srgb, var(--status-warn) 40%, transparent)',
                                background: 'color-mix(in srgb, var(--status-warn) 20%, transparent)',
                                color: 'var(--status-warn-text)'
                              }}
                            >
                              <span className="size-1.5 rounded-full" style={{ background: 'var(--status-warn-text)' }} />
                              Review
                            </span>
                          ) : (
                            <span
                              className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold"
                              style={{
                                borderColor: 'color-mix(in srgb, var(--status-error) 40%, transparent)',
                                background: 'color-mix(in srgb, var(--status-error) 20%, transparent)',
                                color: 'var(--status-error-text)'
                              }}
                            >
                              <span className="size-1.5 rounded-full" style={{ background: 'var(--status-error-text)' }} />
                              Exception
                            </span>
                          )}
                        </td>
                        <td className="py-4.5 pr-6 text-right">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedTransaction(tx);
                            }}
                            className="transition-colors"
                            style={{ color: 'var(--text-faint)' }}
                            onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.color = 'var(--accent)'}
                            onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.color = 'var(--text-faint)'}
                          >
                            <MoreHorizontal className="size-5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Transaction Detail Drawer */}
      <TransactionDrawer
        transaction={selectedTransaction}
        onClose={() => setSelectedTransaction(null)}
      />
    </AppLayout>
  );
}
