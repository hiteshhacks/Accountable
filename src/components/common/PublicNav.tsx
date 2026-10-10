import { Link } from 'react-router-dom';

export function PublicNav() {
  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-8 py-6 sm:px-12 lg:px-16 bg-[#090704]/75 backdrop-blur-md border-b border-[rgba(200,168,90,0.12)]">
      {/* Brand */}
      <Link
        to="/"
        className="font-serif text-2xl font-normal tracking-tight text-[#E8D29A] transition-opacity hover:opacity-90 sm:text-3xl lg:text-4xl"
      >
        Accountable
      </Link>

      {/* Center Nav Links */}
      <nav className="hidden items-center gap-8 md:flex lg:gap-12">
        <button
          type="button"
          onClick={() => scrollToSection('product')}
          className="text-base font-medium tracking-wide text-[#B9AD92] transition-colors hover:text-[#F0E5CA] sm:text-lg lg:text-xl cursor-pointer"
        >
          Product
        </button>
        <button
          type="button"
          onClick={() => scrollToSection('how-it-works')}
          className="text-base font-medium tracking-wide text-[#B9AD92] transition-colors hover:text-[#F0E5CA] sm:text-lg lg:text-xl cursor-pointer"
        >
          How it works
        </button>
        <a
          href="https://github.com/hiteshhacks/Accountable#table-of-contents"
          target="_blank"
          rel="noopener noreferrer"
          className="text-base font-medium tracking-wide text-[#B9AD92] transition-colors hover:text-[#F0E5CA] sm:text-lg lg:text-xl"
        >
          Security
        </a>
      </nav>

      {/* Right Action - Sign in Link Only (Try Accountable button removed) */}
      <div className="flex items-center">
        <Link
          to="/login"
          className="rounded-full border border-[rgba(200,168,90,0.4)] bg-[rgba(200,168,90,0.08)] px-7 py-2.5 text-base font-medium tracking-wide text-[#E8D29A] backdrop-blur-md transition-all duration-200 hover:border-[#C8A85A] hover:bg-[rgba(200,168,90,0.18)] hover:text-[#F0E5CA] sm:text-lg"
        >
          Sign in
        </Link>
      </div>
    </header>
  );
}
