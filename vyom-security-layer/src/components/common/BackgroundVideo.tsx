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
      // Force autoplay attempt if browser requires explicit play call
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
          {/* Subtle warm key light glow on 3D mechanical object */}
          <div className="absolute inset-0 bg-radial-[ellipse_65%_65%_at_70%_40%] from-[#C8A85A]/25 to-transparent mix-blend-soft-light" />
          {/* Soft atmospheric vignette layer */}
          <div className="absolute inset-0 bg-radial-[ellipse_85%_85%_at_45%_45%] from-transparent via-black/15 to-[#090704]/75" />
          {/* Top subtle navbar fade */}
          <div className="absolute inset-x-0 top-0 h-28 bg-linear-to-b from-[#090704]/80 to-transparent" />
          {/* Bottom subtle scroll fade */}
          <div className="absolute inset-x-0 bottom-0 h-32 bg-linear-to-t from-[#090704]/85 to-transparent" />
        </div>
      )}
    </div>
  );
}
