import { Link, useLocation } from 'react-router-dom';
import {
  LayoutGrid,
  ReceiptText,
  ListChecks,
  Sparkles,
  GitCompareArrows,
  FileText,
  ShieldCheck,
  Users,
  ScrollText,
  Settings,
  LogOut,
  ChevronRight,
  type LucideIcon,
} from 'lucide-react';

interface NavItem {
  label: string;
  icon: LucideIcon;
  to?: string;              // undefined = not built yet
  match?: (path: string, search: string) => boolean;
}

const NAV: NavItem[] = [
  { label: 'Overview', icon: LayoutGrid, to: '/dashboard', match: (p) => p === '/dashboard' },
  { label: 'Transactions', icon: ReceiptText, to: '/transactions',
    match: (p, s) => p === '/transactions' && !s.includes('view=review') },
  { label: 'Review Queue', icon: ListChecks, to: '/transactions?view=review',
    match: (p, s) => p === '/transactions' && s.includes('view=review') },
  { label: 'GST Intelligence', icon: Sparkles, to: '/gst', match: (p, s) => p === '/gst' && !s.includes('tab=report') },
  { label: 'Reconciliation', icon: GitCompareArrows },
  { label: 'Reports', icon: FileText, to: '/gst?tab=report', match: (p, s) => p === '/gst' && s.includes('tab=report') },
  { label: 'Blockchain Certificates', icon: ShieldCheck },
  { label: 'Users & Roles', icon: Users },
  { label: 'Audit Logs', icon: ScrollText },
  { label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const { pathname, search } = useLocation();

  return (
    <aside
      className="fixed top-0 bottom-0 left-0 z-30 flex w-[230px] flex-col border-r"
      style={{ background: 'var(--ws-sidebar)', borderColor: 'var(--ws-border)' }}
    >
      <div className="flex h-[70px] items-center border-b px-6" style={{ borderColor: 'var(--ws-border)' }}>
        <Link to="/" className="ws-serif text-[26px] leading-none" style={{ color: 'var(--ws-text-2)' }}>
          Accountable
        </Link>
      </div>

      <div className="px-3 pt-4">
        <div className="ws-card flex items-center gap-3 px-3 py-3.5" style={{ boxShadow: 'none' }}>
          <div
            className="ws-serif flex size-10 shrink-0 items-center justify-center rounded-full border text-lg"
            style={{ borderColor: 'var(--ws-border-strong)', color: 'var(--ws-gold)', background: 'var(--ws-gold-soft)' }}
          >
            V
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">Vyom Administrator</p>
            <span className="ws-chip ws-chip-gold mt-1 px-2 py-0 text-[10px] tracking-wider">ADMIN</span>
          </div>
        </div>
      </div>

      <p className="mt-6 mb-2 px-6 text-[10px] font-bold tracking-[0.16em]" style={{ color: 'var(--ws-muted)' }}>
        WORKSPACE
      </p>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3">
        {NAV.map((item) => {
          const active = item.match ? item.match(pathname, search) : false;
          const Icon = item.icon;
          const body = (
            <>
              <Icon className="size-[17px] shrink-0" style={{ color: active ? 'var(--ws-gold)' : 'var(--ws-text-2)' }} />
              <span className="flex-1 truncate">{item.label}</span>
              {active && <ChevronRight className="size-4" style={{ color: 'var(--ws-gold)' }} />}
              {!item.to && (
                <span className="text-[9px] font-bold tracking-wider" style={{ color: 'var(--ws-muted)' }}>
                  SOON
                </span>
              )}
            </>
          );
          const cls = 'flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-[14px] font-medium transition-colors';
          if (!item.to) {
            return (
              <div key={item.label} className={`${cls} cursor-not-allowed`} style={{ color: 'var(--ws-muted)' }}
                title="Not available yet">
                {body}
              </div>
            );
          }
          return (
            <Link
              key={item.label}
              to={item.to}
              className={cls}
              style={active
                ? { background: 'var(--ws-gold-soft)', border: '1px solid var(--ws-border-strong)', color: 'var(--ws-text)' }
                : { border: '1px solid transparent', color: 'var(--ws-text-2)' }}
            >
              {body}
            </Link>
          );
        })}
      </nav>

      <div className="border-t px-3 py-4" style={{ borderColor: 'var(--ws-border)' }}>
        <Link
          to="/login"
          className="flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium"
          style={{ background: 'var(--ws-bad-bg)', color: 'var(--ws-bad-text)' }}
        >
          <LogOut className="size-4" />
          <span>Sign Out</span>
        </Link>
      </div>
    </aside>
  );
}
