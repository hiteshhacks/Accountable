import { useCallback, useRef, useState } from 'react';
import { Menu } from 'lucide-react';
import { Brand } from './Logo';
import { MobileMenu } from './MobileMenu';
import { NAV_LINKS, SIGN_IN_HREF, SIGN_UP_HREF, primaryButton, secondaryButton } from './nav';

export function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeMenu = useCallback(() => setMenuOpen(false), []);

  return (
    <header className="relative pt-5 sm:pt-6 lg:pt-8">
      <nav
        aria-label="Primary"
        className="flex items-center justify-between gap-6 lg:grid lg:grid-cols-[1fr_auto_1fr]"
      >
        <a href="/" aria-label="VaultShield home" className="justify-self-start rounded-md">
          <Brand />
        </a>

        <ul className="hidden items-center gap-9 lg:flex">
          {NAV_LINKS.map(({ label, href }) => (
            <li key={label}>
              <a
                href={href}
                className="rounded-sm text-sm font-medium text-(--color-text)/70 transition-colors duration-200 hover:text-(--color-accent)"
              >
                {label}
              </a>
            </li>
          ))}
        </ul>

        <div className="hidden items-center gap-3 justify-self-end lg:flex">
          <a href={SIGN_IN_HREF} className={secondaryButton}>
            Sign In
          </a>
          <a href={SIGN_UP_HREF} className={primaryButton}>
            Start For Free
          </a>
        </div>

        <button
          ref={menuButtonRef}
          type="button"
          aria-label="Open menu"
          aria-haspopup="dialog"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(true)}
          className="-mr-2 grid size-11 place-items-center rounded-full text-(--color-accent) transition-colors duration-200 hover:bg-(--color-accent)/10 hover:text-(--color-accent-hover) lg:hidden"
        >
          <Menu className="size-6" strokeWidth={1.75} aria-hidden="true" />
        </button>
      </nav>

      <MobileMenu open={menuOpen} onClose={closeMenu} returnFocusRef={menuButtonRef} />
    </header>
  );
}
