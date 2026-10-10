import { useEffect, useRef, type RefObject } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion, type Variants } from 'framer-motion';
import { X } from 'lucide-react';
import { Brand } from './Logo';
import { NAV_LINKS, SIGN_IN_HREF, SIGN_UP_HREF, primaryButton, secondaryButton } from './nav';

const EASE = [0.22, 1, 0.36, 1] as const;

const listVariants: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06, delayChildren: 0.18 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, x: 24 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.4, ease: EASE } },
};

const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

type MobileMenuProps = {
  open: boolean;
  onClose: () => void;
  /** Receives focus again once the sheet closes. */
  returnFocusRef: RefObject<HTMLElement | null>;
};

export function MobileMenu({ open, onClose, returnFocusRef }: MobileMenuProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;

    const { body, documentElement } = document;
    const returnTarget = returnFocusRef.current;
    const previousOverflow = body.style.overflow;
    const previousPaddingRight = body.style.paddingRight;
    const scrollbarWidth = window.innerWidth - documentElement.clientWidth;

    body.style.overflow = 'hidden';
    if (scrollbarWidth > 0) body.style.paddingRight = `${scrollbarWidth}px`;

    closeButtonRef.current?.focus({ preventScroll: true });

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }

      const panel = panelRef.current;
      if (event.key !== 'Tab' || !panel) return;

      const focusable = panel.querySelectorAll<HTMLElement>(FOCUSABLE);
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      const outside = !panel.contains(active);

      if (event.shiftKey && (active === first || outside)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (active === last || outside)) {
        event.preventDefault();
        first.focus();
      }
    };

    // The trigger disappears at the desktop breakpoint, so close rather than strand the sheet.
    const desktop = window.matchMedia('(min-width: 64rem)');
    const onBreakpoint = (event: MediaQueryListEvent) => {
      if (event.matches) onClose();
    };

    document.addEventListener('keydown', onKeyDown);
    desktop.addEventListener('change', onBreakpoint);

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      desktop.removeEventListener('change', onBreakpoint);
      body.style.overflow = previousOverflow;
      body.style.paddingRight = previousPaddingRight;
      returnTarget?.focus({ preventScroll: true });
    };
  }, [open, onClose, returnFocusRef]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="backdrop"
            aria-hidden="true"
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/70 backdrop-blur-[4px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
          />

          <motion.div
            key="sheet"
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-label="Menu"
            className="fixed top-0 right-0 z-50 flex h-[100dvh] w-[min(88vw,360px)] flex-col border-l border-(--color-border) bg-(--color-surface) shadow-[-24px_0_48px_-16px_rgba(0,0,0,0.7)]"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.45, ease: EASE }}
          >
            <div className="flex items-center justify-between px-6 pt-5 pb-5">
              <Brand />
              <button
                ref={closeButtonRef}
                type="button"
                onClick={onClose}
                aria-label="Close menu"
                className="-mr-2 grid size-11 place-items-center rounded-full text-(--color-text)/80 transition-colors duration-200 hover:bg-(--color-accent)/10 hover:text-(--color-accent)"
              >
                <X className="size-5" strokeWidth={1.75} aria-hidden="true" />
              </button>
            </div>

            <div
              aria-hidden="true"
              className="mx-6 h-px bg-linear-to-r from-(--color-accent)/70 via-(--color-accent)/25 to-transparent"
            />

            <nav aria-label="Mobile" className="flex-1 overflow-y-auto px-6 pt-3">
              <motion.ul variants={listVariants} initial="hidden" animate="visible">
                {NAV_LINKS.map(({ label, href }) => (
                  <motion.li key={label} variants={itemVariants}>
                    <a
                      href={href}
                      onClick={onClose}
                      className="block rounded-sm border-b border-white/[0.06] py-4 text-lg font-medium text-(--color-text) transition-colors duration-200 hover:text-(--color-accent)"
                    >
                      {label}
                    </a>
                  </motion.li>
                ))}
              </motion.ul>
            </nav>

            <div className="flex flex-col gap-3 px-6 pt-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
              <a href={SIGN_UP_HREF} onClick={onClose} className={`${primaryButton} h-12 w-full`}>
                Start For Free
              </a>
              <a href={SIGN_IN_HREF} onClick={onClose} className={`${secondaryButton} h-12 w-full`}>
                Sign In
              </a>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>,
    document.body,
  );
}
