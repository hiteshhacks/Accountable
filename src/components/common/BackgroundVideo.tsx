import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';

export const VIDEO_SRC =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260518_003132_8b7edcb6-c64d-4a52-a9ca-879942e122ad.mp4';

export const VIDEO_GRADE = 'saturate(0.55) sepia(0.6) brightness(0.55) contrast(2.1)';

interface BackgroundVideoProps {
  showOverlay?: boolean;
  dimmed?: boolean;
}

export function BackgroundVideo({ showOverlay = true, dimmed = false }: BackgroundVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoReady, setVideoReady] = useState(true);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (reduceMotion) {
      video.pause();
    } else {
      video.play().catch(() => {
        // Autoplay policy fallback
      });
    }
  }, [reduceMotion]);

  return (
    <div className="pointer-events-none absolute inset-0 z-0 h-full w-full overflow-hidden">
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
        onCanPlay={() => setVideoReady(true)}
        onPlay={() => setVideoReady(true)}
        style={{ filter: VIDEO_GRADE }}
        className={`absolute inset-0 h-full w-full object-cover object-[72%_50%] transition-opacity duration-700 ease-out lg:object-center ${
          videoReady ? 'opacity-100' : 'opacity-90'
        } ${dimmed ? 'opacity-25' : ''}`}
      />

      {showOverlay && (
        <div aria-hidden="true" className="absolute inset-0 z-0">
          {/* Theme-aware warm/dark key light */}
          <div
            className="absolute inset-0 mix-blend-soft-light"
            style={{
              background: 'radial-gradient(ellipse 65% 65% at 70% 40%, color-mix(in srgb, var(--accent) 25%, transparent), transparent)',
            }}
          />
          {/* Atmospheric vignette using CSS tokens */}
          <div
            className="absolute inset-0"
            style={{
              background: 'radial-gradient(ellipse 85% 85% at 45% 45%, transparent, color-mix(in srgb, var(--bg) 60%, transparent))',
            }}
          />
          {/* Top scrim — theme-aware */}
          <div
            className="absolute inset-x-0 top-0 h-28"
            style={{ background: 'var(--scrim)' }}
          />
          {/* Bottom fade */}
          <div
            className="absolute inset-x-0 bottom-0 h-32"
            style={{ background: 'linear-gradient(to top, var(--bg), transparent)' }}
          />
        </div>
      )}
    </div>
  );
}
