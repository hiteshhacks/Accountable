import { useState } from 'react';
import {
  Download,
  Search,
  ChevronDown,
  MoreHorizontal,
  Check,
} from 'lucide-react';
import { AppLayout } from '../components/common/AppLayout';
import { TransactionDrawer } from '../components/common/TransactionDrawer';
import { MOCK_TRANSACTIONS } from '../mockData';
import { Transaction } from '../types';

export function ResultsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>(MOCK_TRANSACTIONS);
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [filterTab, setFilterTab] = useState<'all' | 'high' | 'review' | 'exception'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [voucherFilter, setVoucherFilter] = useState('all');
  const [selectedRowIds, setSelectedRowIds] = useState<string[]>([]);

  const handleVerify = (id: string) => {
    setTransactions((prev) =>
      prev.map((t) => (t.id === id ? { ...t, isVerified: true, status: 'High' } : t))
    );
  };

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
    // Tab filter
    if (filterTab === 'high' && t.status !== 'High') return false;
    if (filterTab === 'review' && t.status !== 'Review') return false;
    if (filterTab === 'exception' && t.status !== 'Exception') return false;

    // Voucher dropdown filter
    if (voucherFilter !== 'all' && t.predictedVoucher !== voucherFilter) return false;

    // Search query filter
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
            <h1 className="font-serif text-3xl font-normal text-[#F1E7CF] sm:text-4xl">
              Processing complete
            </h1>
            <p className="mt-1 text-sm text-[#B9AD92]">
              12,450 transactions analyzed successfully.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => alert('Exporting Excel formatted workbook...')}
              className="inline-flex items-center gap-2 rounded-lg border border-[rgba(200,168,90,0.25)] bg-[#17130D] px-4 py-2 text-xs font-medium text-[#F1E7CF] transition-colors hover:border-[#C8A85A] hover:bg-[#1D1810]"
            >
              <Download className="size-3.5 text-[#C8A85A]" />
              <span>Download Excel</span>
            </button>

            <button
              type="button"
              onClick={() => alert('Exporting JSON dataset...')}
              className="inline-flex items-center gap-2 rounded-lg border border-[rgba(200,168,90,0.25)] bg-[#17130D] px-4 py-2 text-xs font-medium text-[#F1E7CF] transition-colors hover:border-[#C8A85A] hover:bg-[#1D1810]"
            >
              <Download className="size-3.5 text-[#C8A85A]" />
              <span>Download JSON</span>
              <ChevronDown className="size-3 text-[#8F7742]" />
            </button>
          </div>
        </div>

        {/* 3 Summary Cards */}
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {/* High Confidence */}
          <div
            onClick={() => setFilterTab('high')}
            className={`cursor-pointer rounded-xl border p-5 transition-all ${
              filterTab === 'high'
                ? 'border-[#4E7A58] bg-[#1D1810]'
                : 'border-[rgba(200,168,90,0.18)] bg-[#17130D] hover:border-[rgba(200,168,90,0.35)]'
            }`}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="font-serif text-3xl font-normal text-[#F1E7CF]">11,982</p>
                <p className="mt-1 text-xs text-[#B9AD92]">High confidence (≥ 70%)</p>
              </div>
              <span className="rounded-full border border-[#4E7A58]/40 bg-[#4E7A58]/15 px-2.5 py-0.5 text-[11px] font-semibold text-[#78A882]">
                96.2%
              </span>
            </div>
          </div>

          {/* Needs Review */}
          <div
            onClick={() => setFilterTab('review')}
            className={`cursor-pointer rounded-xl border p-5 transition-all ${
              filterTab === 'review'
                ? 'border-[#C8A85A] bg-[#1D1810]'
                : 'border-[rgba(200,168,90,0.18)] bg-[#17130D] hover:border-[rgba(200,168,90,0.35)]'
            }`}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="font-serif text-3xl font-normal text-[#F1E7CF]">421</p>
                <p className="mt-1 text-xs text-[#B9AD92]">Needs review (&lt; 70%)</p>
              </div>
              <span className="rounded-full border border-[#C8A85A]/40 bg-[#C8A85A]/15 px-2.5 py-0.5 text-[11px] font-semibold text-[#D8BC78]">
                3.4%
              </span>
            </div>
          </div>

          {/* Exceptions */}
          <div
            onClick={() => setFilterTab('exception')}
            className={`cursor-pointer rounded-xl border p-5 transition-all ${
              filterTab === 'exception'
                ? 'border-[#8B3A3A] bg-[#1D1810]'
                : 'border-[rgba(200,168,90,0.18)] bg-[#17130D] hover:border-[rgba(200,168,90,0.35)]'
            }`}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="font-serif text-3xl font-normal text-[#F1E7CF]">47</p>
                <p className="mt-1 text-xs text-[#B9AD92]">Exceptions (validation issues)</p>
              </div>
              <span className="rounded-full border border-[#8B3A3A]/40 bg-[#8B3A3A]/15 px-2.5 py-0.5 text-[11px] font-semibold text-[#D48080]">
                0.4%
              </span>
            </div>
          </div>
        </div>

        {/* Filter Tabs & Search Bar */}
        <div className="mt-8 space-y-4">
          {/* Tabs */}
          <div className="flex border-b border-[rgba(200,168,90,0.15)] pb-px">
            <button
              type="button"
              onClick={() => setFilterTab('all')}
              className={`pb-3 text-xs font-semibold tracking-wider transition-colors ${
                filterTab === 'all'
                  ? 'border-b-2 border-[#C8A85A] text-[#F1E7CF]'
                  : 'text-[#756B58] hover:text-[#B9AD92]'
              }`}
            >
              All transactions <span className="ml-1 text-[11px] font-mono text-[#8F7742]">12,450</span>
            </button>
            <button
              type="button"
              onClick={() => setFilterTab('high')}
              className={`ml-8 pb-3 text-xs font-semibold tracking-wider transition-colors ${
                filterTab === 'high'
                  ? 'border-b-2 border-[#C8A85A] text-[#F1E7CF]'
                  : 'text-[#756B58] hover:text-[#B9AD92]'
              }`}
            >
              High confidence <span className="ml-1 text-[11px] font-mono text-[#8F7742]">11,982</span>
            </button>
            <button
              type="button"
              onClick={() => setFilterTab('review')}
              className={`ml-8 pb-3 text-xs font-semibold tracking-wider transition-colors ${
                filterTab === 'review'
                  ? 'border-b-2 border-[#C8A85A] text-[#F1E7CF]'
                  : 'text-[#756B58] hover:text-[#B9AD92]'
              }`}
            >
              Needs review <span className="ml-1 text-[11px] font-mono text-[#8F7742]">421</span>
            </button>
            <button
              type="button"
              onClick={() => setFilterTab('exception')}
              className={`ml-8 pb-3 text-xs font-semibold tracking-wider transition-colors ${
                filterTab === 'exception'
                  ? 'border-b-2 border-[#C8A85A] text-[#F1E7CF]'
                  : 'text-[#756B58] hover:text-[#B9AD92]'
              }`}
            >
              Exceptions <span className="ml-1 text-[11px] font-mono text-[#8F7742]">47</span>
            </button>
          </div>

          {/* Search Bar + Dropdowns */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-[#756B58]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by invoice, party, amount..."
                className="w-full rounded-lg border border-[rgba(200,168,90,0.18)] bg-[#17130D] py-2 pl-10 pr-4 text-xs text-[#F1E7CF] placeholder-[#756B58] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
              />
            </div>

            <div className="flex items-center gap-3">
              <div className="relative">
                <select
                  value={voucherFilter}
                  onChange={(e) => setVoucherFilter(e.target.value)}
                  className="appearance-none rounded-lg border border-[rgba(200,168,90,0.18)] bg-[#17130D] py-2 pl-3 pr-8 text-xs text-[#B9AD92] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
                >
                  <option value="all">Voucher type (All)</option>
                  <option value="Purchase">Purchase</option>
                  <option value="Sales">Sales</option>
                  <option value="Payment">Payment</option>
                  <option value="Expense">Expense</option>
                  <option value="Journal">Journal</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 size-3 text-[#8F7742]" />
              </div>

              <div className="relative">
                <select
                  className="appearance-none rounded-lg border border-[rgba(200,168,90,0.18)] bg-[#17130D] py-2 pl-3 pr-8 text-xs text-[#B9AD92] transition-colors focus:border-[#C8A85A] focus:outline-hidden"
                >
                  <option value="all">Confidence (All)</option>
                  <option value="90">≥ 90%</option>
                  <option value="70">≥ 70%</option>
                  <option value="50">&lt; 70%</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 size-3 text-[#8F7742]" />
              </div>
            </div>
          </div>
        </div>

        {/* Transaction Table */}
        <div className="mt-4 overflow-x-auto rounded-xl border border-[rgba(200,168,90,0.18)] bg-[#17130D] shadow-[0_12px_40px_rgba(0,0,0,0.5)]">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-[rgba(200,168,90,0.15)] bg-[#1D1810]/70 text-[#756B58] uppercase tracking-wider">
              <tr>
                <th className="py-3.5 pl-4 pr-2">
                  <input
                    type="checkbox"
                    checked={selectedRowIds.length === transactions.length}
                    onChange={toggleSelectAll}
                    className="rounded border-[rgba(200,168,90,0.3)] bg-[#100D08] accent-[#C8A85A]"
                  />
                </th>
                <th className="py-3.5 px-3">Invoice no.</th>
                <th className="py-3.5 px-3">Date</th>
                <th className="py-3.5 px-3">Party</th>
                <th className="py-3.5 px-3">Amount</th>
                <th className="py-3.5 px-3">Predicted voucher</th>
                <th className="py-3.5 px-3">Confidence</th>
                <th className="py-3.5 px-3">Status</th>
                <th className="py-3.5 pr-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(200,168,90,0.08)]">
              {filteredTransactions.map((tx) => {
                const isSelected = selectedRowIds.includes(tx.id);
                return (
                  <tr
                    key={tx.id}
                    onClick={() => setSelectedTransaction(tx)}
                    className={`cursor-pointer transition-colors duration-150 ${
                      isSelected
                        ? 'bg-[rgba(200,168,90,0.08)]'
                        : 'hover:bg-[#1D1810]'
                    }`}
                  >
                    <td
                      className="py-3.5 pl-4 pr-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSelectRow(tx.id);
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectRow(tx.id)}
                        className="rounded border-[rgba(200,168,90,0.3)] bg-[#100D08] accent-[#C8A85A]"
                      />
                    </td>
                    <td className="py-3.5 px-3 font-mono text-[#F1E7CF]">
                      {tx.invoiceNo}
                    </td>
                    <td className="py-3.5 px-3 text-[#B9AD92]">{tx.date}</td>
                    <td className="py-3.5 px-3 font-medium text-[#F1E7CF]">{tx.party}</td>
                    <td className="py-3.5 px-3 font-mono text-[#F1E7CF]">{tx.amount}</td>
                    <td className="py-3.5 px-3 font-medium text-[#E8D29A]">
                      {tx.predictedVoucher}
                    </td>
                    <td className="py-3.5 px-3 font-mono text-[#B9AD92]">
                      {tx.confidence}%
                    </td>
                    <td className="py-3.5 px-3">
                      {tx.isVerified ? (
                        <span className="inline-flex items-center gap-1 text-[11px] text-[#78A882]">
                          <Check className="size-3" /> Verified
                        </span>
                      ) : tx.status === 'High' ? (
                        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#4E7A58]/40 bg-[#4E7A58]/15 px-2 py-0.5 text-[11px] text-[#78A882]">
                          <span className="size-1.5 rounded-full bg-[#78A882]" />
                          High
                        </span>
                      ) : tx.status === 'Review' ? (
                        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#C8A85A]/40 bg-[#C8A85A]/15 px-2 py-0.5 text-[11px] text-[#D8BC78]">
                          <span className="size-1.5 rounded-full bg-[#D8BC78]" />
                          Review
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#8B3A3A]/40 bg-[#8B3A3A]/15 px-2 py-0.5 text-[11px] text-[#D48080]">
                          <span className="size-1.5 rounded-full bg-[#D48080]" />
                          Exception
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 pr-4 text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedTransaction(tx);
                        }}
                        className="text-[#756B58] hover:text-[#C8A85A]"
                      >
                        <MoreHorizontal className="size-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transaction Detail Drawer (Screen 09) */}
      <TransactionDrawer
        transaction={selectedTransaction}
        onClose={() => setSelectedTransaction(null)}
        onVerify={handleVerify}
      />
    </AppLayout>
  );
}
