import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';

export const VIDEO_SRC =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260518_003132_8b7edcb6-c64d-4a52-a9ca-879942e122ad.mp4';

export const VIDEO_GRADE = 'saturate(0.52) sepia(0.6) brightness(0.5) contrast(2.2)';

interface BackgroundVideoProps {
  showOverlay?: boolean;
  dimmed?: boolean;
}

export function BackgroundVideo({ showOverlay = true, dimmed = false }: BackgroundVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoReady, setVideoReady] = useState(false);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (reduceMotion) {
      videoRef.current?.pause();
    }
  }, [reduceMotion]);

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 h-full w-full overflow-hidden bg-[#090704]">
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
        style={{ filter: VIDEO_GRADE }}
        className={`absolute inset-0 h-full w-full object-cover object-center transition-opacity duration-1000 ease-out ${
          videoReady ? 'opacity-100' : 'opacity-0'
        } ${dimmed ? 'opacity-20' : ''}`}
      />

      {showOverlay && (
        <div aria-hidden="true" className="absolute inset-0">
          {/* Subtle warm key light glow */}
          <div className="absolute inset-0 bg-radial-[ellipse_65%_65%_at_68%_38%] from-[#C8A85A]/20 to-transparent mix-blend-soft-light" />
          {/* Soft vignette layer matching Reference 1 - preserving golden structure on right and track on left */}
          <div className="absolute inset-0 bg-radial-[ellipse_85%_85%_at_45%_45%] from-transparent via-black/20 to-[#090704]/80" />
          {/* Top fade for quiet navbar */}
          <div className="absolute inset-x-0 top-0 h-24 bg-linear-to-b from-[#090704]/70 to-transparent" />
          {/* Bottom fade for scroll indicator */}
          <div className="absolute inset-x-0 bottom-0 h-28 bg-linear-to-t from-[#090704]/90 to-transparent" />
        </div>
      )}
    </div>
  );
}
