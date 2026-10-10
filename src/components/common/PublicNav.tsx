import { Link } from 'react-router-dom';

export function PublicNav() {
  return (
    <header className="fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-8 py-6 sm:px-12 lg:px-16">
      {/* Brand */}
      <Link
        to="/"
        className="font-serif text-2xl font-normal tracking-tight text-[#E8D29A] transition-opacity hover:opacity-90 sm:text-3xl lg:text-4xl"
      >
        Accountable
      </Link>

      {/* Center Nav Links - Significantly Larger */}
      <nav className="hidden items-center gap-8 md:flex lg:gap-12">
        <a
          href="#product"
          onClick={(e) => e.preventDefault()}
          className="text-base font-medium tracking-wide text-[#B9AD92] transition-colors hover:text-[#F0E5CA] sm:text-lg lg:text-xl"
        >
          Product
        </a>
        <a
          href="#how-it-works"
          onClick={(e) => e.preventDefault()}
          className="text-base font-medium tracking-wide text-[#B9AD92] transition-colors hover:text-[#F0E5CA] sm:text-lg lg:text-xl"
        >
          How it works
        </a>
        <a
          href="#security"
          onClick={(e) => e.preventDefault()}
          className="text-base font-medium tracking-wide text-[#B9AD92] transition-colors hover:text-[#F0E5CA] sm:text-lg lg:text-xl"
        >
          Security
        </a>
      </nav>

      {/* Right Actions - Significantly Larger */}
      <div className="flex items-center gap-6 lg:gap-8">
        <Link
          to="/login"
          className="hidden text-base font-semibold text-[#B9AD92] transition-colors hover:text-[#F0E5CA] sm:inline-block sm:text-lg lg:text-xl"
        >
          Sign in
        </Link>

        <Link
          to="/signup"
          className="inline-flex items-center justify-center gap-2 rounded-full border border-[rgba(200,168,90,0.45)] bg-[rgba(200,168,90,0.06)] px-6 py-2.5 text-base font-medium tracking-wide text-[#E8D29A] backdrop-blur-md transition-all duration-200 hover:border-[#C8A85A] hover:bg-[rgba(200,168,90,0.18)] hover:text-[#F0E5CA] sm:px-7 sm:py-3 sm:text-lg"
        >
          <span>Try accountable →</span>
        </Link>
      </div>
    </header>
  );
}
