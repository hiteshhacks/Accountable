import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

interface ThemeToggleProps {
  /** Extra CSS classes for positioning */
  className?: string;
}

export function ThemeToggle({ className = '' }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-pressed={!isDark}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={`theme-toggle-btn ${className}`}
    >
      {isDark ? (
        <Sun className="size-[18px] transition-transform duration-300 rotate-0" aria-hidden="true" />
      ) : (
        <Moon className="size-[18px] transition-transform duration-300 rotate-0" aria-hidden="true" />
      )}
    </button>
  );
}
