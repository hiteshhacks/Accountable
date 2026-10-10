export const NAV_LINKS = [
  { label: 'Vault', href: '#vault' },
  { label: 'Plans', href: '#plans' },
  { label: 'Install', href: '#install' },
  { label: 'News', href: '#news' },
  { label: 'Help', href: '#help' },
] as const;

export const SIGN_IN_HREF = '#sign-in';
export const SIGN_UP_HREF = '#start';

// Shared by the desktop navbar and the mobile sheet so both stay identical.
const pill =
  'inline-flex items-center justify-center rounded-full border px-5 py-2.5 text-sm whitespace-nowrap transition-colors duration-200';

export const primaryButton = `${pill} border-transparent bg-(--color-accent) font-semibold text-[#100E08] hover:bg-(--color-accent-hover)`;

export const secondaryButton = `${pill} border-(--color-accent)/50 bg-(--color-login-bg) font-medium text-(--color-text) hover:border-(--color-accent) hover:text-(--color-accent-hover)`;
