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
            <h1 className="font-serif text-3xl font-normal text-[#F0E5CA] sm:text-4xl lg:text-5xl">
              Processing complete
            </h1>
            <p className="mt-2 text-base font-medium text-[#E8D29A]">
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
                className="inline-flex items-center gap-2.5 rounded-xl border border-[rgba(200,168,90,0.35)] bg-[#17130D] px-6 py-3 text-sm font-semibold text-[#F0E5CA] shadow-xs transition-colors hover:border-[#C8A85A] hover:bg-[#1D1810] cursor-pointer"
              >
                <Download className="size-4.5 text-[#C8A85A]" />
                <span>Download Excel</span>
              </button>

              <button
                type="button"
                onClick={exportToJSON}
                className="inline-flex items-center gap-2.5 rounded-xl border border-[rgba(200,168,90,0.35)] bg-[#17130D] px-6 py-3 text-sm font-semibold text-[#F0E5CA] shadow-xs transition-colors hover:border-[#C8A85A] hover:bg-[#1D1810] cursor-pointer"
              >
                <Download className="size-4.5 text-[#C8A85A]" />
                <span>Download JSON</span>
              </button>
            </div>
          )}
        </div>

        {totalCount === 0 ? (
          /* Empty State */
          <div className="mt-12 flex flex-col items-center justify-center rounded-2xl border border-[rgba(200,168,90,0.22)] bg-[#17130D]/90 px-6 py-20 text-center">
            <div className="flex size-16 items-center justify-center rounded-2xl border border-[rgba(200,168,90,0.3)] bg-[#100D08] text-[#C8A85A]">
              <FolderOpen className="size-8" />
            </div>
            <h3 className="mt-6 font-serif text-2xl font-normal text-[#F0E5CA] sm:text-3xl">
              No classification results yet.
            </h3>
            <p className="mt-2.5 max-w-lg text-base text-[#E8D29A]">
              Upload a transaction file to view AI classification results, confidence scores, and GST intelligence.
            </p>
            <button
              type="button"
              onClick={() => navigate('/upload')}
              className="mt-7 inline-flex items-center gap-2.5 rounded-xl bg-[#D8BC78] px-8 py-4 text-base font-semibold text-[#090704] transition-all hover:bg-[#E8D29A]"
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
                className={`cursor-pointer rounded-2xl border p-7 transition-all ${
                  filterTab === 'high'
                    ? 'border-[#4E7A58] bg-[#1D1810]'
                    : 'border-[rgba(200,168,90,0.25)] bg-[#17130D] hover:border-[rgba(200,168,90,0.45)]'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-serif text-4xl font-normal text-[#F0E5CA]">
                      {highCount.toLocaleString()}
                    </p>
                    <p className="mt-1.5 text-sm font-medium text-[#E8D29A]">
                      High confidence (≥ 70%)
                    </p>
                  </div>
                  <span className="rounded-full border border-[#4E7A58]/40 bg-[#4E7A58]/20 px-3.5 py-1 text-xs font-semibold text-[#78A882]">
                    {highPct}%
                  </span>
                </div>
              </div>

              {/* Needs Review */}
              <div
                onClick={() => setFilterTab('review')}
                className={`cursor-pointer rounded-2xl border p-7 transition-all ${
                  filterTab === 'review'
                    ? 'border-[#C8A85A] bg-[#1D1810]'
                    : 'border-[rgba(200,168,90,0.25)] bg-[#17130D] hover:border-[rgba(200,168,90,0.45)]'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-serif text-4xl font-normal text-[#F0E5CA]">
                      {reviewCount.toLocaleString()}
                    </p>
                    <p className="mt-1.5 text-sm font-medium text-[#E8D29A]">
                      Needs review (&lt; 70%)
                    </p>
                  </div>
                  <span className="rounded-full border border-[#C8A85A]/40 bg-[#C8A85A]/20 px-3.5 py-1 text-xs font-semibold text-[#D8BC78]">
                    {reviewPct}%
                  </span>
                </div>
              </div>

              {/* Exceptions */}
              <div
                onClick={() => setFilterTab('exception')}
                className={`cursor-pointer rounded-2xl border p-7 transition-all ${
                  filterTab === 'exception'
                    ? 'border-[#8B3A3A] bg-[#1D1810]'
                    : 'border-[rgba(200,168,90,0.25)] bg-[#17130D] hover:border-[rgba(200,168,90,0.45)]'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-serif text-4xl font-normal text-[#F0E5CA]">
                      {exceptionCount.toLocaleString()}
                    </p>
                    <p className="mt-1.5 text-sm font-medium text-[#E8D29A]">
                      Exceptions (validation issues)
                    </p>
                  </div>
                  <span className="rounded-full border border-[#8B3A3A]/40 bg-[#8B3A3A]/20 px-3.5 py-1 text-xs font-semibold text-[#D48080]">
                    {exceptionPct}%
                  </span>
                </div>
              </div>
            </div>

            {/* Filter Tabs & Search Bar */}
            <div className="mt-10 space-y-5">
              <div className="flex border-b border-[rgba(200,168,90,0.2)] pb-px">
                <button
                  type="button"
                  onClick={() => setFilterTab('all')}
                  className={`pb-4 text-sm font-semibold tracking-wider transition-colors cursor-pointer ${
                    filterTab === 'all'
                      ? 'border-b-2 border-[#C8A85A] text-[#F0E5CA]'
                      : 'text-[#B9AD92] hover:text-[#F0E5CA]'
                  }`}
                >
                  All transactions{' '}
                  <span className="ml-1.5 font-mono text-[#C8A85A] font-bold">{totalCount}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setFilterTab('high')}
                  className={`ml-10 pb-4 text-sm font-semibold tracking-wider transition-colors cursor-pointer ${
                    filterTab === 'high'
                      ? 'border-b-2 border-[#C8A85A] text-[#F0E5CA]'
                      : 'text-[#B9AD92] hover:text-[#F0E5CA]'
                  }`}
                >
                  High confidence{' '}
                  <span className="ml-1.5 font-mono text-[#C8A85A] font-bold">{highCount}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setFilterTab('review')}
                  className={`ml-10 pb-4 text-sm font-semibold tracking-wider transition-colors cursor-pointer ${
                    filterTab === 'review'
                      ? 'border-b-2 border-[#C8A85A] text-[#F0E5CA]'
                      : 'text-[#B9AD92] hover:text-[#F0E5CA]'
                  }`}
                >
                  Needs review{' '}
                  <span className="ml-1.5 font-mono text-[#C8A85A] font-bold">{reviewCount}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setFilterTab('exception')}
                  className={`ml-10 pb-4 text-sm font-semibold tracking-wider transition-colors cursor-pointer ${
                    filterTab === 'exception'
                      ? 'border-b-2 border-[#C8A85A] text-[#F0E5CA]'
                      : 'text-[#B9AD92] hover:text-[#F0E5CA]'
                  }`}
                >
                  Exceptions{' '}
                  <span className="ml-1.5 font-mono text-[#C8A85A] font-bold">{exceptionCount}</span>
                </button>
              </div>

              {/* Search Bar + Dropdowns */}
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="relative flex-1 max-w-md">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 size-4.5 text-[#B9AD92]" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search by invoice, party, amount..."
                    className="w-full rounded-xl border border-[rgba(200,168,90,0.25)] bg-[#17130D] py-3 pl-11 pr-4 text-sm text-[#F0E5CA] placeholder-[#756B58] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
                  />
                </div>

                <div className="flex items-center gap-3">
                  <div className="relative">
                    <select
                      value={voucherFilter}
                      onChange={(e) => setVoucherFilter(e.target.value)}
                      className="appearance-none rounded-xl border border-[rgba(200,168,90,0.25)] bg-[#17130D] py-3 pl-4 pr-10 text-sm font-medium text-[#F0E5CA] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
                    >
                      <option value="all">Voucher type (All)</option>
                      <option value="Purchase">Purchase</option>
                      <option value="Sales">Sales</option>
                      <option value="Payment">Payment</option>
                      <option value="Expense">Expense</option>
                      <option value="Journal">Journal</option>
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 size-4 text-[#C8A85A]" />
                  </div>
                </div>
              </div>
            </div>

            {/* High Readability Transaction Table */}
            <div className="mt-6 overflow-x-auto rounded-2xl border border-[rgba(200,168,90,0.25)] bg-[#17130D] shadow-[0_12px_40px_rgba(0,0,0,0.6)]">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-[rgba(200,168,90,0.2)] bg-[#1D1810]/90 text-[#E8D29A] uppercase tracking-wider">
                  <tr>
                    <th className="py-4 pl-6 pr-2">
                      <input
                        type="checkbox"
                        checked={selectedRowIds.length === transactions.length}
                        onChange={toggleSelectAll}
                        className="rounded border-[rgba(200,168,90,0.35)] bg-[#100D08] accent-[#C8A85A]"
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
                <tbody className="divide-y divide-[rgba(200,168,90,0.1)]">
                  {filteredTransactions.map((tx) => {
                    const isSelected = selectedRowIds.includes(tx.id);
                    return (
                      <tr
                        key={tx.id}
                        onClick={() => setSelectedTransaction(tx)}
                        className={`cursor-pointer transition-colors duration-150 ${
                          isSelected
                            ? 'bg-[rgba(200,168,90,0.12)]'
                            : 'hover:bg-[#1D1810]'
                        }`}
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
                            className="rounded border-[rgba(200,168,90,0.35)] bg-[#100D08] accent-[#C8A85A]"
                          />
                        </td>
                        <td className="py-4.5 px-4 font-mono font-semibold text-[#F0E5CA]">
                          {tx.invoiceNo}
                        </td>
                        <td className="py-4.5 px-4 font-medium text-[#B9AD92]">{tx.date}</td>
                        <td className="py-4.5 px-4 font-medium text-[#F0E5CA]">{tx.party}</td>
                        <td className="py-4.5 px-4 font-mono font-semibold text-[#F0E5CA]">{tx.amount}</td>
                        <td className="py-4.5 px-4 font-semibold text-[#E8D29A]">
                          {tx.predictedVoucher}
                        </td>
                        <td className="py-4.5 px-4 font-mono font-semibold text-[#C8A85A]">
                          {tx.confidence}%
                        </td>
                        <td className="py-4.5 px-4">
                          {tx.isVerified ? (
                            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#78A882]">
                              <Check className="size-4" /> Verified
                            </span>
                          ) : tx.status === 'High' ? (
                            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#4E7A58]/40 bg-[#4E7A58]/20 px-3 py-1 text-xs font-semibold text-[#78A882]">
                              <span className="size-1.5 rounded-full bg-[#78A882]" />
                              High
                            </span>
                          ) : tx.status === 'Review' ? (
                            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#C8A85A]/40 bg-[#C8A85A]/20 px-3 py-1 text-xs font-semibold text-[#D8BC78]">
                              <span className="size-1.5 rounded-full bg-[#D8BC78]" />
                              Review
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#8B3A3A]/40 bg-[#8B3A3A]/20 px-3 py-1 text-xs font-semibold text-[#D48080]">
                              <span className="size-1.5 rounded-full bg-[#D48080]" />
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
                            className="text-[#756B58] transition-colors hover:text-[#C8A85A]"
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
