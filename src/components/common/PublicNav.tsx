import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ThemeToggle } from './ThemeToggle';

export function PublicNav() {
  const [mobileOpen, setMobileOpen] = useState(false);

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
      setMobileOpen(false);
    }
  };

  return (
    <>
      {/* Gradient scrim behind nav — pointer-events none so it never blocks clicks */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-x-0 top-0 z-39 h-[140px]"
        style={{ background: 'var(--scrim)' }}
      />

      <header
        className="fixed inset-x-0 top-0 z-40 flex items-center justify-between px-6 py-5 sm:px-10 lg:px-14"
        style={{ background: 'none', border: 'none', boxShadow: 'none' }}
      >
        {/* ── Brand ── */}
        <Link
          to="/"
          className="font-serif text-2xl font-normal tracking-tight transition-opacity hover:opacity-90 sm:text-3xl lg:text-4xl"
          style={{
            color: 'var(--text)',
            textShadow: '0 1px 8px rgba(0,0,0,0.45)',
          }}
        >
          Accountable
        </Link>

        {/* ── Center nav — single frosted-glass pill ── */}
        <nav aria-label="Primary" className="hidden md:flex items-center">
          <div className="public-nav-pill flex items-center" style={{ gap: '32px' }}>
            <button
              type="button"
              onClick={() => scrollToSection('product')}
              className="public-nav-link font-serif text-base font-medium tracking-wide transition-all duration-200 cursor-pointer rounded-full px-3 py-1"
            >
              Product
            </button>
            <button
              type="button"
              onClick={() => scrollToSection('how-it-works')}
              className="public-nav-link font-serif text-base font-medium tracking-wide transition-all duration-200 cursor-pointer rounded-full px-3 py-1"
            >
              How it works
            </button>
            <a
              href="https://github.com/hiteshhacks/Accountable#table-of-contents"
              target="_blank"
              rel="noopener noreferrer"
              className="public-nav-link font-serif text-base font-medium tracking-wide transition-all duration-200 rounded-full px-3 py-1"
            >
              Security
            </a>
          </div>
        </nav>

        {/* ── Right: ThemeToggle + Sign in ── */}
        <div className="hidden md:flex items-center gap-3">
          <ThemeToggle />
          <Link
            to="/login"
            className="rounded-full border px-7 py-2.5 text-base font-serif font-medium tracking-wide transition-all duration-200"
            style={{
              borderColor: 'var(--glass-border)',
              background: 'var(--glass-bg)',
              color: 'var(--text-secondary)',
              backdropFilter: 'blur(16px) saturate(140%)',
              WebkitBackdropFilter: 'blur(16px) saturate(140%)',
              boxShadow: 'var(--glass-shadow)',
              textShadow: '0 1px 8px rgba(0,0,0,0.30)',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = 'var(--accent)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = 'var(--glass-border)';
            }}
          >
            Sign in
          </Link>
        </div>

        {/* ── Mobile: ThemeToggle + Hamburger ── */}
        <div className="md:hidden flex items-center gap-2">
          <ThemeToggle />
          <button
            type="button"
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((v) => !v)}
            className="flex flex-col justify-center items-center w-10 h-10 gap-[5px] rounded-full border transition-all duration-200"
            style={{
              borderColor: 'var(--glass-border)',
              background: 'var(--glass-bg)',
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
            }}
          >
            <span
              className={`block h-[1.5px] w-5 rounded-full transition-all duration-200 origin-center ${mobileOpen ? 'rotate-45 translate-y-[6.5px]' : ''}`}
              style={{ background: 'var(--text-secondary)' }}
            />
            <span
              className={`block h-[1.5px] w-5 rounded-full transition-all duration-200 ${mobileOpen ? 'opacity-0 scale-x-0' : ''}`}
              style={{ background: 'var(--text-secondary)' }}
            />
            <span
              className={`block h-[1.5px] w-5 rounded-full transition-all duration-200 origin-center ${mobileOpen ? '-rotate-45 -translate-y-[6.5px]' : ''}`}
              style={{ background: 'var(--text-secondary)' }}
            />
          </button>
        </div>
      </header>

      {/* ── Mobile menu panel ── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-50 md:hidden"
          onClick={() => setMobileOpen(false)}
        >
          <div
            className="absolute inset-0 bg-black/60"
            style={{ backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)' }}
          />
          <div
            className="absolute inset-x-4 top-[80px] rounded-2xl p-6 flex flex-col gap-5"
            style={{
              background: 'color-mix(in srgb, var(--surface) 90%, transparent)',
              backdropFilter: 'blur(24px) saturate(140%)',
              WebkitBackdropFilter: 'blur(24px) saturate(140%)',
              border: '1px solid var(--glass-border)',
              boxShadow: '0 16px 48px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.08)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => scrollToSection('product')}
              className="font-serif text-lg font-medium text-left py-2 border-b transition-colors duration-200"
              style={{ color: 'var(--text)', borderColor: 'var(--border)' }}
            >
              Product
            </button>
            <button
              type="button"
              onClick={() => scrollToSection('how-it-works')}
              className="font-serif text-lg font-medium text-left py-2 border-b transition-colors duration-200"
              style={{ color: 'var(--text)', borderColor: 'var(--border)' }}
            >
              How it works
            </button>
            <a
              href="https://github.com/hiteshhacks/Accountable#table-of-contents"
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setMobileOpen(false)}
              className="font-serif text-lg font-medium py-2 border-b transition-colors duration-200"
              style={{ color: 'var(--text)', borderColor: 'var(--border)' }}
            >
              Security
            </a>
            <Link
              to="/login"
              onClick={() => setMobileOpen(false)}
              className="mt-1 rounded-full border px-6 py-3 text-center font-serif text-base font-medium transition-all duration-200"
              style={{
                borderColor: 'var(--glass-border)',
                background: 'var(--glass-bg)',
                color: 'var(--text-secondary)',
              }}
            >
              Sign in
            </Link>
          </div>
        </div>
      )}
    </>
  );
}
