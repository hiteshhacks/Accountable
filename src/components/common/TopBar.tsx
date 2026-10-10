import { ThemeToggle } from './ThemeToggle';

export function TopBar() {
  return (
    <header
      className="sticky top-0 z-20 flex h-16 items-center justify-end px-8 border-b backdrop-blur-md"
      style={{
        borderColor: 'var(--border)',
        background: 'color-mix(in srgb, var(--bg) 80%, transparent)',
      }}
    >
      {/* Theme toggle */}
      <ThemeToggle />
    </header>
  );
}
