import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';

const VIDEO_SRC =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260518_003132_8b7edcb6-c64d-4a52-a9ca-879942e122ad.mp4';

/*
 * Source footage color grading filter.
 */
const VIDEO_GRADE = 'saturate(0.45) sepia(0.55) brightness(0.44) contrast(2.3)';

export function Hero() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoReady, setVideoReady] = useState(false);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (reduceMotion) videoRef.current?.pause();
  }, [reduceMotion]);

  return (
    <div className="relative isolate w-full min-h-[100svh] overflow-hidden bg-(--color-background)">
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
        }`}
      />

      {/* Subtle vignette layer */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-radial-[ellipse_80%_80%_at_50%_50%] from-transparent via-black/10 to-black/60" />
      </div>
    </div>
  );
}

