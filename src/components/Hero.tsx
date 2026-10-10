import { useEffect, useRef, useState } from 'react';
import { motion, useReducedMotion, type Variants } from 'framer-motion';
import {
  ArrowRightCircle,
  Fingerprint,
  LockKeyhole,
  Pause,
  Play,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { Navbar } from './Navbar';
import { SIGN_UP_HREF } from './nav';

const VIDEO_SRC =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260518_003132_8b7edcb6-c64d-4a52-a9ca-879942e122ad.mp4';

/*
 * The source footage is a bright, near-white studio scene. Desaturating, warming
 * and steepening contrast pushes its pale backdrop toward black while the lit
 * machine keeps its form; the overlays below handle the rest.
 */
const VIDEO_GRADE = 'saturate(0.45) sepia(0.55) brightness(0.44) contrast(2.3)';

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 28 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.15,
      duration: 0.6,
      ease: [0.22, 1, 0.36, 1],
    },
  }),
};

function HeadingIcon({ icon: Icon }: { icon: LucideIcon }) {
  return (
    <Icon
      aria-hidden="true"
      strokeWidth={2}
      className="inline-block size-5 align-middle text-(--color-accent) sm:size-6"
    />
  );
}

export function Hero() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoReady, setVideoReady] = useState(false);
  const [videoFailed, setVideoFailed] = useState(false);
  const [videoPlaying, setVideoPlaying] = useState(false);
  const reduceMotion = useReducedMotion();

  // The footage is decorative, so hold its first frame for reduced-motion users.
  useEffect(() => {
    if (reduceMotion) videoRef.current?.pause();
  }, [reduceMotion]);

  const toggleVideo = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) void video.play().catch(() => {});
    else video.pause();
  };

  return (
    <div className="relative isolate w-full min-h-[100svh] overflow-hidden bg-(--color-background)">
      {!videoFailed && (
        <video
          ref={videoRef}
          src={VIDEO_SRC}
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          aria-hidden="true"
          tabIndex={-1}
          disablePictureInPicture
          onLoadedData={() => setVideoReady(true)}
          onPlay={() => setVideoPlaying(true)}
          onPause={() => setVideoPlaying(false)}
          onError={() => setVideoFailed(true)}
          style={{ filter: VIDEO_GRADE }}
          className={`absolute inset-0 h-full w-full object-cover object-[72%_50%] transition-opacity duration-1000 ease-out motion-reduce:transition-none lg:object-center ${
            videoReady ? 'opacity-100' : 'opacity-0'
          }`}
        />
      )}

      {/* Grading layers, back to front: warm key light, vignette, text scrim, edge fades. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-radial-[ellipse_45%_55%_at_72%_42%] from-(--color-accent)/30 to-transparent mix-blend-soft-light" />
        <div className="absolute inset-0 bg-radial-[ellipse_75%_60%_at_70%_35%] from-black/20 to-black/90 to-80% lg:bg-radial-[ellipse_50%_70%_at_72%_45%] lg:from-black/10 lg:to-black/95 lg:to-75%" />
        <div className="absolute inset-0 bg-linear-to-b from-black/20 via-black/55 to-black/85 lg:bg-linear-to-r lg:from-black/90 lg:via-black/55 lg:via-35% lg:to-transparent lg:to-65%" />
        <div className="absolute inset-x-0 top-0 h-32 bg-linear-to-b from-black/80 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-linear-to-t from-black to-transparent" />
      </div>

      <div className="relative mx-auto flex min-h-[100svh] w-full max-w-[1280px] flex-col px-5 sm:px-8 lg:px-16">
        <Navbar />

        <main className="flex flex-1 items-center pt-14 pb-24 sm:pt-16 lg:pb-28">
          <section aria-labelledby="hero-heading" className="w-full max-w-[560px]">
            <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={0}>
              <p className="mb-5 text-[11px] font-medium tracking-[0.25em] text-(--color-accent) uppercase sm:mb-6 sm:text-xs">
                Your digital life. Protected.
              </p>
              <h1
                id="hero-heading"
                className="font-heading text-[clamp(2.25rem,5vw,4.5rem)] leading-[1.05] tracking-[-0.025em] text-balance text-(--color-text)"
              >
                <span className="whitespace-nowrap">
                  <HeadingIcon icon={Zap} /> Lock
                </span>{' '}
                Down Your Passwords{' '}
                <span className="whitespace-nowrap">
                  <HeadingIcon icon={LockKeyhole} /> with
                </span>{' '}
                <span className="text-(--color-accent)">
                  Ironclad{' '}
                  <span className="whitespace-nowrap">
                    Security <HeadingIcon icon={Fingerprint} />
                  </span>
                </span>
              </h1>
            </motion.div>

            <motion.p
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={1}
              className="mt-6 max-w-[520px] text-[clamp(0.95rem,2vw,1.1rem)] leading-[1.65] text-pretty text-(--color-text-muted)"
            >
              Zero stress, total control. VaultShield keeps you covered with unbreakable storage,
              one-tap access, and pro-grade tools for your non-stop world.
            </motion.p>

            <motion.div
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={2}
              className="mt-10"
            >
              <motion.a
                href={SIGN_UP_HREF}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                className="inline-flex min-w-[210px] items-center justify-between gap-8 rounded-[50px] bg-(--color-accent) px-6 py-[17px] text-base font-semibold text-[#100E08] shadow-[0_4px_24px_rgba(212,175,97,0.16)] transition-colors duration-300 hover:bg-(--color-accent-hover)"
              >
                Get It Free
                <ArrowRightCircle className="size-5" strokeWidth={2} aria-hidden="true" />
              </motion.a>
            </motion.div>
          </section>
        </main>

        {!videoFailed && (
          <button
            type="button"
            onClick={toggleVideo}
            aria-label={videoPlaying ? 'Pause background video' : 'Play background video'}
            className="absolute right-5 bottom-5 grid size-9 place-items-center rounded-full border border-(--color-border) bg-black/40 text-(--color-text)/70 backdrop-blur-sm transition-colors duration-200 hover:border-(--color-accent)/60 hover:text-(--color-accent) sm:right-8 sm:bottom-6 lg:right-16 lg:bottom-8"
          >
            {videoPlaying ? (
              <Pause className="size-3.5" fill="currentColor" strokeWidth={0} aria-hidden="true" />
            ) : (
              <Play className="size-3.5 translate-x-px" fill="currentColor" strokeWidth={0} aria-hidden="true" />
            )}
          </button>
        )}
      </div>
    </div>
  );
}
