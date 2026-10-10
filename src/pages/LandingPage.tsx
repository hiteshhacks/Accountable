import { Link } from 'react-router-dom';
import { ChevronDown, CheckCircle2, ShieldCheck, FileCheck, Layers } from 'lucide-react';
import { BackgroundVideo } from '../components/common/BackgroundVideo';
import { PublicNav } from '../components/common/PublicNav';

export function LandingPage() {
  const scrollToProduct = () => {
    const el = document.getElementById('product');
    el?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="relative min-h-screen w-full text-[#F0E5CA]">
      {/* Hero Section Container with Video Background */}
      <div className="relative min-h-screen w-full overflow-hidden">
        {/* Immutable background video playing in background */}
        <BackgroundVideo showOverlay={true} />

        {/* Top Navigation */}
        <PublicNav />

        {/* Hero Content */}
        <main className="relative z-10 flex min-h-screen w-full flex-col items-center justify-between px-6 pt-[16vh] pb-[6vh] text-center">
          <div className="flex flex-col items-center">
            {/* 3D Metallic Gold Title */}
            <h1 className="gold-3d-title text-[clamp(4.5rem,10.5vw,8.5rem)] font-normal leading-[0.92] tracking-[-0.035em] select-none">
              Accountable
            </h1>

            {/* Subtitle */}
            <p className="mt-6 font-serif text-[clamp(1.25rem,2.5vw,1.85rem)] font-normal leading-[1.3] text-[#F0E5CA]/90 drop-shadow-[0_2px_15px_rgba(0,0,0,0.7)]">
              Intelligent voucher classification <br />
              for modern accounting
            </p>

            {/* Single Dominant Hero CTA */}
            <div className="mt-9 flex flex-col items-center">
              <Link
                to="/signup"
                className="inline-flex h-[64px] w-[270px] items-center justify-center gap-2.5 rounded-xl bg-[#D8BC78] text-lg font-semibold tracking-wide text-[#090704] shadow-[0_8px_36px_rgba(200,168,90,0.3)] transition-all duration-200 hover:-translate-y-1 hover:bg-[#E8D29A] hover:shadow-[0_12px_44px_rgba(200,168,90,0.42)] sm:h-[72px] sm:w-[320px] sm:text-xl"
              >
                <span>Try accountable →</span>
              </Link>
            </div>
          </div>

          {/* Bottom Scroll Indicator */}
          <div
            onClick={scrollToProduct}
            className="flex flex-col items-center gap-2 text-[#B9AD92]/70 opacity-75 transition-opacity hover:opacity-100 cursor-pointer"
          >
            <div className="flex size-8 items-center justify-center rounded-full border border-[rgba(200,168,90,0.3)] bg-[#100D08]/70 sm:size-9">
              <ChevronDown className="size-4 text-[#C8A85A]" />
            </div>
            <span className="font-serif text-[11px] tracking-[0.25em] uppercase">
              Scroll to explore
            </span>
            <div className="h-6 w-px bg-gradient-to-b from-[rgba(200,168,90,0.35)] to-transparent" />
          </div>
        </main>
      </div>

      {/* #product Section */}
      <section id="product" className="relative z-10 border-t border-[rgba(200,168,90,0.15)] bg-[#090704] mx-auto max-w-full px-8 py-24 lg:py-36">
        <div className="mx-auto max-w-[1200px]">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[#C8A85A]">
              Product Capabilities
            </p>
            <h2 className="mt-3 font-serif text-3xl font-normal text-[#F0E5CA] sm:text-4xl lg:text-5xl">
              Built for the accounting workflow.
            </h2>
          </div>

          <div className="mt-16 grid grid-cols-1 gap-8 md:grid-cols-2 lg:gap-10">
            {/* Capability 1 */}
            <div className="rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#100D08]/90 p-8 backdrop-blur-md transition-all duration-300 hover:border-[rgba(200,168,90,0.4)] hover:bg-[#17130D]">
              <div className="flex size-12 items-center justify-center rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#1D1810] text-[#C8A85A]">
                <Layers className="size-6" />
              </div>
              <h3 className="mt-6 font-serif text-2xl font-normal text-[#F0E5CA]">
                Intelligent Voucher Classification
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-[#B9AD92]">
                Automatically identify the most appropriate voucher type from structured transaction data.
              </p>
            </div>

            {/* Capability 2 */}
            <div className="rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#100D08]/90 p-8 backdrop-blur-md transition-all duration-300 hover:border-[rgba(200,168,90,0.4)] hover:bg-[#17130D]">
              <div className="flex size-12 items-center justify-center rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#1D1810] text-[#C8A85A]">
                <CheckCircle2 className="size-6" />
              </div>
              <h3 className="mt-6 font-serif text-2xl font-normal text-[#F0E5CA]">
                Confidence-Aware Decisions
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-[#B9AD92]">
                High-confidence transactions can move forward while ambiguous cases are flagged for review.
              </p>
            </div>

            {/* Capability 3 */}
            <div className="rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#100D08]/90 p-8 backdrop-blur-md transition-all duration-300 hover:border-[rgba(200,168,90,0.4)] hover:bg-[#17130D]">
              <div className="flex size-12 items-center justify-center rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#1D1810] text-[#C8A85A]">
                <ShieldCheck className="size-6" />
              </div>
              <h3 className="mt-6 font-serif text-2xl font-normal text-[#F0E5CA]">
                GST Intelligence
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-[#B9AD92]">
                Validate GST-related information and surface potential issues using deterministic checks.
              </p>
            </div>

            {/* Capability 4 */}
            <div className="rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#100D08]/90 p-8 backdrop-blur-md transition-all duration-300 hover:border-[rgba(200,168,90,0.4)] hover:bg-[#17130D]">
              <div className="flex size-12 items-center justify-center rounded-xl border border-[rgba(200,168,90,0.3)] bg-[#1D1810] text-[#C8A85A]">
                <FileCheck className="size-6" />
              </div>
              <h3 className="mt-6 font-serif text-2xl font-normal text-[#F0E5CA]">
                Reconciliation & Auditability
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-[#B9AD92]">
                Compare records, identify mismatches and maintain an auditable trail of decisions.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* #how-it-works Section */}
      <section id="how-it-works" className="relative z-10 border-t border-[rgba(200,168,90,0.12)] bg-[#090704] py-24 lg:py-36">
        <div className="mx-auto max-w-[1200px] px-8">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[#C8A85A]">
              Sequential Workflow
            </p>
            <h2 className="mt-3 font-serif text-3xl font-normal text-[#F0E5CA] sm:text-4xl lg:text-5xl">
              From transaction data to accounting intelligence.
            </h2>
          </div>

          <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {/* Step 01 */}
            <div className="relative rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#17130D] p-7 transition-all duration-300 hover:border-[#C8A85A]">
              <span className="font-serif text-3xl font-normal text-[#C8A85A]">01</span>
              <h3 className="mt-4 font-serif text-xl font-normal text-[#F0E5CA]">Upload</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#B9AD92]">
                Upload your XLSX or CSV transaction data.
              </p>
            </div>

            {/* Step 02 */}
            <div className="relative rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#17130D] p-7 transition-all duration-300 hover:border-[#C8A85A]">
              <span className="font-serif text-3xl font-normal text-[#C8A85A]">02</span>
              <h3 className="mt-4 font-serif text-xl font-normal text-[#F0E5CA]">Validate</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#B9AD92]">
                Accountable checks structure, fields and data quality.
              </p>
            </div>

            {/* Step 03 */}
            <div className="relative rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#17130D] p-7 transition-all duration-300 hover:border-[#C8A85A]">
              <span className="font-serif text-3xl font-normal text-[#C8A85A]">03</span>
              <h3 className="mt-4 font-serif text-xl font-normal text-[#F0E5CA]">Classify</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#B9AD92]">
                The AI pipeline analyzes transaction context and predicts the appropriate voucher category.
              </p>
            </div>

            {/* Step 04 */}
            <div className="relative rounded-2xl border border-[rgba(200,168,90,0.18)] bg-[#17130D] p-7 transition-all duration-300 hover:border-[#C8A85A]">
              <span className="font-serif text-3xl font-normal text-[#C8A85A]">04</span>
              <h3 className="mt-4 font-serif text-xl font-normal text-[#F0E5CA]">Review & Export</h3>
              <p className="mt-2 text-xs leading-relaxed text-[#B9AD92]">
                Review uncertain classifications and export the finalized results.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
