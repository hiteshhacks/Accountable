import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Moon, Search, Sun, UserCog } from 'lucide-react';
import { useWorkspace } from '../../context/WorkspaceContext';

export function TopBar() {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useWorkspace();
  const [query, setQuery] = useState('');

  return (
    <header
      className="sticky top-0 z-20 flex h-[70px] items-center justify-between gap-4 border-b px-6 backdrop-blur-md lg:px-9"
      style={{ borderColor: 'var(--ws-border)', background: 'color-mix(in srgb, var(--ws-bg) 88%, transparent)' }}
    >
      <form
        className="relative w-full max-w-[350px]"
        onSubmit={(e) => {
          e.preventDefault();
          navigate(`/transactions${query.trim() ? `?q=${encodeURIComponent(query.trim())}` : ''}`);
        }}
      >
        <Search className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2" style={{ color: 'var(--ws-muted)' }} />
        <input
          className="ws-input rounded-xl py-2.5 pl-10"
          placeholder="Search transactions, parties, GSTINs..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search transactions"
        />
      </form>

      <div className="flex items-center gap-3">
        <div className="ws-card flex items-center gap-3 px-3.5 py-2" style={{ boxShadow: 'none' }}>
          <div className="flex size-8 items-center justify-center rounded-lg border"
            style={{ borderColor: 'var(--ws-border-strong)', background: 'var(--ws-sidebar)', color: 'var(--ws-gold)' }}>
            <UserCog className="size-4" />
          </div>
          <div className="leading-tight">
            <p className="text-[13px] font-semibold">Vyom Administrator</p>
            <p className="text-[11px] font-semibold" style={{ color: 'var(--ws-gold)' }}>Admin</p>
          </div>
        </div>
        <button
          type="button"
          onClick={toggleTheme}
          className="ws-btn-ghost rounded-full p-2"
          aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          title={theme === 'light' ? 'Dark mode' : 'Light mode'}
        >
          {theme === 'light' ? <Moon className="size-5" /> : <Sun className="size-5" />}
        </button>
      </div>
    </header>
  );
}
