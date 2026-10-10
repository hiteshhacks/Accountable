import { useState } from 'react';
import { Link } from 'react-router-dom';

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
        style={{ background: 'linear-gradient(to bottom, rgba(0,0,0,0.35), transparent)' }}
      />

      <header
        className="fixed inset-x-0 top-0 z-40 flex items-center justify-between px-6 py-5 sm:px-10 lg:px-14"
        style={{ background: 'none', border: 'none', boxShadow: 'none' }}
      >
        {/* ── Brand ── */}
        <Link
          to="/"
          className="font-serif text-2xl font-normal tracking-tight text-[#E8D29A] transition-opacity hover:opacity-90 sm:text-3xl lg:text-4xl"
          style={{ textShadow: '0 1px 8px rgba(0,0,0,0.45)' }}
        >
          Accountable
        </Link>

        {/* ── Center nav — single frosted-glass pill ── */}
        <nav
          aria-label="Primary"
          className="hidden md:flex items-center gap-8"
          style={{ gap: '32px' }}
        >
          {/* The single pill wraps all three links */}
          <div className="public-nav-pill flex items-center" style={{ gap: '32px' }}>
            <button
              type="button"
              onClick={() => scrollToSection('product')}
              className="public-nav-link font-serif text-base font-medium tracking-wide text-[#F0E5CA]/85 transition-all duration-200 cursor-pointer rounded-full px-3 py-1 hover:text-[#F0E5CA]"
            >
              Product
            </button>
            <button
              type="button"
              onClick={() => scrollToSection('how-it-works')}
              className="public-nav-link font-serif text-base font-medium tracking-wide text-[#F0E5CA]/85 transition-all duration-200 cursor-pointer rounded-full px-3 py-1 hover:text-[#F0E5CA]"
            >
              How it works
            </button>
            <a
              href="https://github.com/hiteshhacks/Accountable#table-of-contents"
              target="_blank"
              rel="noopener noreferrer"
              className="public-nav-link font-serif text-base font-medium tracking-wide text-[#F0E5CA]/85 transition-all duration-200 rounded-full px-3 py-1 hover:text-[#F0E5CA]"
            >
              Security
            </a>
          </div>
        </nav>

        {/* ── Right: Sign in ── */}
        <div className="hidden md:flex items-center">
          <Link
            to="/login"
            className="rounded-full border border-[rgba(217,188,122,0.40)] bg-[rgba(255,255,255,0.08)] px-7 py-2.5 text-base font-serif font-medium tracking-wide text-[#E8D29A] transition-all duration-200 hover:border-[#C8A85A] hover:bg-[rgba(217,188,122,0.15)] hover:text-[#F0E5CA]"
            style={{
              backdropFilter: 'blur(16px) saturate(140%)',
              WebkitBackdropFilter: 'blur(16px) saturate(140%)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.18)',
              textShadow: '0 1px 8px rgba(0,0,0,0.45)',
            }}
          >
            Sign in
          </Link>
        </div>

        {/* ── Mobile hamburger ── */}
        <button
          type="button"
          aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((v) => !v)}
          className="md:hidden flex flex-col justify-center items-center w-10 h-10 gap-[5px] rounded-full border border-[rgba(217,188,122,0.3)] bg-[rgba(255,255,255,0.06)] transition-all duration-200 hover:border-[#C8A85A] hover:bg-[rgba(217,188,122,0.1)]"
          style={{ backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' }}
        >
          <span
            className={`block h-[1.5px] w-5 bg-[#E8D29A] rounded-full transition-all duration-200 origin-center ${mobileOpen ? 'rotate-45 translate-y-[6.5px]' : ''}`}
          />
          <span
            className={`block h-[1.5px] w-5 bg-[#E8D29A] rounded-full transition-all duration-200 ${mobileOpen ? 'opacity-0 scale-x-0' : ''}`}
          />
          <span
            className={`block h-[1.5px] w-5 bg-[#E8D29A] rounded-full transition-all duration-200 origin-center ${mobileOpen ? '-rotate-45 -translate-y-[6.5px]' : ''}`}
          />
        </button>
      </header>

      {/* ── Mobile menu panel ── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-50 md:hidden"
          onClick={() => setMobileOpen(false)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/60" style={{ backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)' }} />

          {/* Glass panel */}
          <div
            className="absolute inset-x-4 top-[80px] rounded-2xl p-6 flex flex-col gap-5"
            style={{
              background: 'rgba(14, 10, 6, 0.82)',
              backdropFilter: 'blur(24px) saturate(140%)',
              WebkitBackdropFilter: 'blur(24px) saturate(140%)',
              border: '1px solid rgba(217,188,122,0.25)',
              boxShadow: '0 16px 48px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.08)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => scrollToSection('product')}
              className="font-serif text-lg font-medium text-[#F0E5CA]/85 hover:text-[#F0E5CA] text-left py-2 border-b border-[rgba(217,188,122,0.12)] transition-colors duration-200"
            >
              Product
            </button>
            <button
              type="button"
              onClick={() => scrollToSection('how-it-works')}
              className="font-serif text-lg font-medium text-[#F0E5CA]/85 hover:text-[#F0E5CA] text-left py-2 border-b border-[rgba(217,188,122,0.12)] transition-colors duration-200"
            >
              How it works
            </button>
            <a
              href="https://github.com/hiteshhacks/Accountable#table-of-contents"
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setMobileOpen(false)}
              className="font-serif text-lg font-medium text-[#F0E5CA]/85 hover:text-[#F0E5CA] py-2 border-b border-[rgba(217,188,122,0.12)] transition-colors duration-200"
            >
              Security
            </a>
            <Link
              to="/login"
              onClick={() => setMobileOpen(false)}
              className="mt-1 rounded-full border border-[rgba(217,188,122,0.40)] bg-[rgba(217,188,122,0.08)] px-6 py-3 text-center font-serif text-base font-medium text-[#E8D29A] transition-all duration-200 hover:bg-[rgba(217,188,122,0.18)] hover:text-[#F0E5CA]"
            >
              Sign in
            </Link>
          </div>
        </div>
      )}
    </>
  );
}
