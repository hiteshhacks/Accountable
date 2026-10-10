import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Upload,
  Settings,
  LogOut,
} from 'lucide-react';

export function Sidebar() {
  const location = useLocation();

  const isDashboard = location.pathname === '/dashboard';
  const isUpload = location.pathname.startsWith('/upload') ||
    location.pathname.startsWith('/validation') ||
    location.pathname.startsWith('/processing') ||
    location.pathname.startsWith('/results');

  return (
    <aside className="fixed top-0 bottom-0 left-0 z-30 flex w-56 flex-col border-r border-[rgba(200,168,90,0.15)] bg-[#100D08]/90 backdrop-blur-md">
      {/* Brand */}
      <div className="flex h-16 items-center px-6 border-b border-[rgba(200,168,90,0.1)]">
        <Link
          to="/"
          className="font-serif text-xl tracking-tight text-[#E8D29A] transition-colors hover:text-[#F1E7CF]"
        >
          Accountable
        </Link>
      </div>

      {/* Main Nav */}
      <nav className="flex-1 space-y-1.5 px-3 py-6">
        <Link
          to="/dashboard"
          className={`flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition-all duration-200 ${
            isDashboard
              ? 'border border-[rgba(200,168,90,0.3)] bg-[rgba(200,168,90,0.12)] text-[#E8D29A] shadow-[0_2px_12px_rgba(200,168,90,0.08)]'
              : 'text-[#B9AD92] hover:bg-[#17130D] hover:text-[#F1E7CF]'
          }`}
        >
          <LayoutDashboard
            className={`size-4 ${isDashboard ? 'text-[#C8A85A]' : 'text-[#8F7742]'}`}
          />
          <span>Dashboard</span>
        </Link>

        <Link
          to="/upload"
          className={`flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition-all duration-200 ${
            isUpload
              ? 'border border-[rgba(200,168,90,0.3)] bg-[rgba(200,168,90,0.12)] text-[#E8D29A] shadow-[0_2px_12px_rgba(200,168,90,0.08)]'
              : 'text-[#B9AD92] hover:bg-[#17130D] hover:text-[#F1E7CF]'
          }`}
        >
          <Upload
            className={`size-4 ${isUpload ? 'text-[#C8A85A]' : 'text-[#8F7742]'}`}
          />
          <span>Upload</span>
        </Link>
      </nav>

      {/* Footer Nav */}
      <div className="space-y-1.5 border-t border-[rgba(200,168,90,0.1)] px-3 py-4">
        <button
          type="button"
          onClick={() => alert('Settings is a Phase 2 feature.')}
          className="flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium text-[#756B58] transition-colors hover:bg-[#17130D] hover:text-[#B9AD92]"
        >
          <Settings className="size-4 text-[#756B58]" />
          <span>Settings</span>
        </button>

        <Link
          to="/login"
          className="flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium text-[#756B58] transition-colors hover:bg-[#17130D] hover:text-[#B9AD92]"
        >
          <LogOut className="size-4 text-[#756B58]" />
          <span>Logout</span>
        </Link>
      </div>
    </aside>
  );
}
