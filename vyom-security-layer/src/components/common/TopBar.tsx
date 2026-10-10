import { ChevronDown } from 'lucide-react';

interface TopBarProps {
  companyName?: string;
}

export function TopBar({ companyName = 'ABC Private Limited' }: TopBarProps) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-end px-8 border-b border-[rgba(200,168,90,0.12)] bg-[#0A0805]/80 backdrop-blur-md">
      <div className="flex items-center gap-4">
        {/* Company Selector Pill */}
        <button
          type="button"
          className="flex items-center gap-2 rounded-full border border-[rgba(200,168,90,0.25)] bg-[#17130D] px-3.5 py-1.5 text-xs font-medium text-[#F1E7CF] transition-colors hover:border-[#C8A85A] hover:bg-[#1D1810]"
        >
          <span>{companyName}</span>
          <ChevronDown className="size-3 text-[#C8A85A]" />
        </button>

        {/* User Avatar */}
        <div className="flex size-8 items-center justify-center rounded-full border border-[rgba(200,168,90,0.4)] bg-[#1D1810] text-xs font-semibold text-[#E8D29A] shadow-xs">
          P
        </div>
      </div>
    </header>
  );
}
