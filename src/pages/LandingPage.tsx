import { Link } from 'react-router-dom';
import { Play, ChevronDown } from 'lucide-react';
import { BackgroundVideo } from '../components/common/BackgroundVideo';
import { PublicNav } from '../components/common/PublicNav';

export function LandingPage() {
  return (
    <div className="relative isolate h-screen w-screen overflow-hidden bg-[#090704] text-[#F0E5CA]">
      {/* Immutable background video preserved 100% */}
      <BackgroundVideo showOverlay={true} />

      {/* Top Navigation */}
      <PublicNav />

      {/* Hero Container */}
      <main className="relative flex h-full w-full flex-col items-center justify-between px-6 pt-[14vh] pb-[4vh] text-center">
        <div className="flex flex-col items-center">
          {/* Premium Awwwards-Level 3D Metallic Gold Garamond Title */}
          <h1 className="gold-3d-title text-[clamp(4.5rem,10.5vw,8.5rem)] font-normal leading-[0.92] tracking-[-0.035em] select-none">
            Accountable
          </h1>

          {/* Subtitle */}
          <p className="mt-6 font-serif text-[clamp(1.25rem,2.5vw,1.85rem)] font-normal leading-[1.3] text-[#F0E5CA]/90 drop-shadow-[0_2px_15px_rgba(0,0,0,0.7)]">
            Intelligent voucher classification <br />
            for modern accounting
          </p>

          {/* CTAs */}
          <div className="mt-8 flex flex-col items-center gap-4.5">
            {/* Primary CTA */}
            <Link
              to="/signup"
              className="inline-flex h-[64px] w-[270px] items-center justify-center gap-2.5 rounded-xl bg-[#D8BC78] text-lg font-semibold tracking-wide text-[#090704] shadow-[0_8px_36px_rgba(200,168,90,0.3)] transition-all duration-200 hover:-translate-y-1 hover:bg-[#E8D29A] hover:shadow-[0_12px_44px_rgba(200,168,90,0.42)] sm:h-[72px] sm:w-[320px] sm:text-xl"
            >
              <span>Try accountable →</span>
            </Link>

            {/* Watch Demo CTA */}
            <button
              type="button"
              onClick={() => alert('Demo video preview: 12,450 transactions classified in 42 seconds.')}
              className="inline-flex h-[54px] w-[220px] items-center justify-center gap-3 rounded-full border border-[rgba(200,168,90,0.4)] bg-[#100D08]/80 text-sm font-medium tracking-wide text-[#E8D29A] backdrop-blur-md transition-all duration-200 hover:border-[#C8A85A] hover:bg-[#17130D] sm:h-[60px] sm:w-[250px] sm:text-base"
            >
              <div className="flex size-7 items-center justify-center rounded-full border border-[rgba(200,168,90,0.45)] bg-black/50 sm:size-8">
                <Play className="size-3 translate-x-0.5 fill-[#C8A85A] text-[#C8A85A] sm:size-3.5" />
              </div>
              <span>Watch demo</span>
            </button>
          </div>
        </div>

        {/* Bottom Scroll Indicator */}
        <div className="flex flex-col items-center gap-2 text-[#B9AD92]/70 opacity-70 transition-opacity hover:opacity-100 cursor-pointer">
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
  );
}
