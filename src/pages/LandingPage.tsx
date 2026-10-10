import { Link } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { BackgroundVideo } from '../components/common/BackgroundVideo';
import { PublicNav } from '../components/common/PublicNav';

export function LandingPage() {
  const scrollToProduct = () => {
    const el = document.getElementById('product');
    el?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="relative min-h-screen w-full" style={{ color: 'var(--text)' }}>
      {/* Hero Section Container with Video Background */}
      <div className="relative min-h-screen w-full overflow-hidden">
        <BackgroundVideo showOverlay={true} />
        <PublicNav />

        {/* Hero Content */}
        <main className="relative z-10 flex min-h-screen w-full flex-col items-center justify-between px-6 pt-[16vh] pb-[6vh] text-center">
          <div className="flex flex-col items-center">
            <h1 className="gold-3d-title text-[clamp(4.5rem,10.5vw,8.5rem)] font-normal leading-[0.92] tracking-[-0.035em] select-none">
              Accountable
            </h1>

            <p
              className="mt-6 font-serif text-[clamp(1.25rem,2.5vw,1.85rem)] font-normal leading-[1.3] drop-shadow-[0_2px_15px_rgba(0,0,0,0.5)]"
              style={{ color: 'var(--text)' }}
            >
              Intelligent voucher classification <br />
              for modern accounting
            </p>

            <div className="mt-9 flex flex-col items-center">
              <Link
                to="/signup"
                className="inline-flex h-[64px] w-[270px] items-center justify-center gap-2.5 rounded-xl text-lg font-semibold tracking-wide shadow-[0_8px_36px_rgba(200,168,90,0.3)] transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_12px_44px_rgba(200,168,90,0.42)] sm:h-[72px] sm:w-[320px] sm:text-xl"
                style={{ background: 'var(--accent-warm)', color: 'var(--accent-contrast)' }}
              >
                <span>Try accountable →</span>
              </Link>
            </div>
          </div>

          {/* Scroll Indicator */}
          <div
            onClick={scrollToProduct}
            className="flex flex-col items-center gap-2 opacity-75 transition-opacity hover:opacity-100 cursor-pointer"
            style={{ color: 'var(--text-muted)' }}
          >
            <div
              className="flex size-8 items-center justify-center rounded-full border sm:size-9"
              style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--bg) 70%, transparent)' }}
            >
              <ChevronDown className="size-4" style={{ color: 'var(--accent)' }} />
            </div>
            <span className="font-serif text-[11px] tracking-[0.25em] uppercase">Scroll to explore</span>
            <div
              className="h-6 w-px"
              style={{ background: 'linear-gradient(to bottom, var(--border-strong), transparent)' }}
            />
          </div>
        </main>
      </div>

      {/* #product Section */}
      <section
        id="product"
        className="relative z-10 mx-auto max-w-full px-8 py-24 lg:py-36 scroll-mt-[120px]"
        style={{ background: 'var(--bg)' }}
      >
        <div className="mx-auto max-w-[1200px]">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.25em]" style={{ color: 'var(--accent)' }}>
              Product Capabilities
            </p>
            <h2 className="mt-3 font-serif text-3xl font-normal sm:text-4xl lg:text-5xl" style={{ color: 'var(--text)' }}>
              Built for the accounting workflow.
            </h2>
          </div>

          <div className="mt-16 grid grid-cols-1 gap-8 md:grid-cols-2 lg:gap-10">
            {[
              {
                title: 'Context-aware classification',
                desc: 'Accountable reads the whole transaction, not just a keyword, to decide which voucher it belongs to.',
                hood: 'Separates look-alikes such as Purchase vs Purchase Order, Payment vs Receipt vs Contra, and Purchase Return (Debit Note) vs Sales Return (Credit Note).'
              },
              {
                title: 'Confidence-aware review',
                desc: 'Every prediction comes with a confidence score. Clear cases move ahead, and uncertain ones are flagged for you to check instead of being guessed.',
                hood: 'Ambiguous records are surfaced for human review rather than forced into a category.'
              },
              {
                title: 'Validation before classification',
                desc: 'Your file is checked before anything is classified, so problems are caught early.',
                hood: 'Verifies required columns, field formats and missing values from the actual uploaded data.'
              },
              {
                title: 'Results you can use',
                desc: 'Review every predicted voucher in one table, then download the final results.',
                hood: 'Export as Excel (.xlsx) or JSON.'
              },
            ].map(({ title, desc, hood }) => (
              <div
                key={title}
                className="flex flex-col justify-between rounded-2xl border p-9 backdrop-blur-md transition-all duration-300"
                style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--surface) 90%, transparent)' }}
              >
                <div>
                  <h3 className="font-serif text-2xl font-normal" style={{ color: 'var(--text)' }}>{title}</h3>
                  <p className="mt-3 text-base leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{desc}</p>
                </div>
                <div className="mt-8 pt-6 border-t" style={{ borderColor: 'var(--border)' }}>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.2em]" style={{ color: 'var(--accent)' }}>
                    Under the hood
                  </p>
                  <p className="mt-2 text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                    {hood}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* #how-it-works Section */}
      <section
        id="how-it-works"
        className="relative z-10 py-24 lg:py-36 scroll-mt-[120px]"
        style={{ background: 'var(--bg)' }}
      >
        <div className="mx-auto max-w-[1200px] px-8">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.25em]" style={{ color: 'var(--accent)' }}>
              Sequential Workflow
            </p>
            <h2 className="mt-3 font-serif text-3xl font-normal sm:text-4xl lg:text-5xl" style={{ color: 'var(--text)' }}>
              From transaction data to accounting intelligence.
            </h2>
          </div>

          <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { n: '01', title: 'Upload',          desc: 'Upload your transactions as an Excel (.xlsx) or CSV file.' },
              { n: '02', title: 'Validate',         desc: 'Accountable checks columns, formats and missing values, and shows what needs fixing before processing.' },
              { n: '03', title: 'Classify',          desc: 'An open-source AI model reads each transaction\'s full context and predicts its voucher type with a confidence score.' },
              { n: '04', title: 'Review & export',  desc: 'Check the flagged records, then download the results as Excel or JSON.' },
            ].map(({ n, title, desc }) => (
              <div
                key={n}
                className="relative rounded-2xl border p-8 transition-all duration-300 flex flex-col h-full"
                style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}
              >
                <span className="font-serif text-3xl font-normal" style={{ color: 'var(--accent)' }}>{n}</span>
                <h3 className="mt-5 font-serif text-xl font-normal" style={{ color: 'var(--text)' }}>{title}</h3>
                <p className="mt-3 text-sm leading-relaxed flex-1" style={{ color: 'var(--text-muted)' }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
