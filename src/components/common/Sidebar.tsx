import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Upload, Settings, LogOut } from 'lucide-react';

export function Sidebar() {
  const location = useLocation();

  const isDashboard = location.pathname === '/dashboard';
  const isUpload =
    location.pathname.startsWith('/upload') ||
    location.pathname.startsWith('/validation') ||
    location.pathname.startsWith('/processing') ||
    location.pathname.startsWith('/results');

  const navLink = (active: boolean) => ({
    borderColor: active ? 'var(--border)' : 'transparent',
    background: active ? 'color-mix(in srgb, var(--accent) 12%, transparent)' : 'transparent',
    color: active ? 'var(--text-secondary)' : 'var(--text-muted)',
  });

  return (
    <aside
      className="fixed top-0 bottom-0 left-0 z-30 flex w-56 flex-col border-r backdrop-blur-md"
      style={{
        borderColor: 'var(--border)',
        background: 'color-mix(in srgb, var(--bg-elevated) 90%, transparent)',
      }}
    >
      {/* Brand */}
      <div
        className="flex h-16 items-center px-6 border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        <Link
          to="/"
          className="font-serif text-xl tracking-tight transition-colors hover:opacity-90"
          style={{ color: 'var(--text-secondary)' }}
        >
          Accountable
        </Link>
      </div>

      {/* Main Nav */}
      <nav className="flex-1 space-y-1.5 px-3 py-6">
        <Link
          to="/dashboard"
          className="flex items-center gap-3 rounded-lg border px-3.5 py-2.5 text-sm font-medium transition-all duration-200"
          style={navLink(isDashboard)}
        >
          <LayoutDashboard className="size-4" style={{ color: isDashboard ? 'var(--accent)' : 'var(--accent-muted)' }} />
          <span>Dashboard</span>
        </Link>

        <Link
          to="/upload"
          className="flex items-center gap-3 rounded-lg border px-3.5 py-2.5 text-sm font-medium transition-all duration-200"
          style={navLink(isUpload)}
        >
          <Upload className="size-4" style={{ color: isUpload ? 'var(--accent)' : 'var(--accent-muted)' }} />
          <span>Upload</span>
        </Link>
      </nav>

      {/* Footer Nav */}
      <div
        className="space-y-1.5 border-t px-3 py-4"
        style={{ borderColor: 'var(--border)' }}
      >
        <button
          type="button"
          onClick={() => alert('Settings is a Phase 2 feature.')}
          className="flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition-colors"
          style={{ color: 'var(--text-faint)' }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--text-muted)')}
          onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--text-faint)')}
        >
          <Settings className="size-4" style={{ color: 'var(--text-faint)' }} />
          <span>Settings</span>
        </button>

        <Link
          to="/login"
          className="flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition-colors"
          style={{ color: 'var(--text-faint)' }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--text-muted)')}
          onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--text-faint)')}
        >
          <LogOut className="size-4" style={{ color: 'var(--text-faint)' }} />
          <span>Logout</span>
        </Link>
      </div>
    </aside>
  );
}
