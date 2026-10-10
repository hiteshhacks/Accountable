import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
  wide?: boolean;
}

/** Centered dialog rendered inside .ws-root so it inherits the console theme. */
export function Modal({ title, subtitle, onClose, children, footer, wide }: ModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-black/45 backdrop-blur-[2px]" onClick={onClose} />
      <div
        className={`ws-card relative flex max-h-[92vh] w-full flex-col overflow-hidden ${wide ? 'max-w-[1120px]' : 'max-w-[760px]'}`}
        style={{ background: 'var(--ws-bg)' }}
      >
        <div className="flex items-start justify-between gap-4 border-b px-6 py-5" style={{ borderColor: 'var(--ws-border)' }}>
          <div>
            <h2 className="text-[28px] leading-tight">{title}</h2>
            {subtitle && <p className="mt-1 text-sm" style={{ color: 'var(--ws-text-2)' }}>{subtitle}</p>}
          </div>
          <button type="button" className="ws-btn-ghost rounded-full p-2" onClick={onClose} aria-label="Close">
            <X className="size-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer && (
          <div className="flex flex-wrap items-center justify-end gap-3 border-t px-6 py-4" style={{ borderColor: 'var(--ws-border)' }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="ws-chip-bad rounded-xl border px-4 py-3 text-sm" role="alert">
      {message}
    </div>
  );
}
