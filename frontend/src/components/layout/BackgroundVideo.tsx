'use client';

import { useEffect, useRef } from 'react';
import Hls from 'hls.js';

// Swap this playback ID to change the global background:
// Globe (current): BuGGTsiXq1T00WUb8qfURrHkTCbhrkfFLSv4uAOZzdhw
// DS00Spx1CV902MCtPj5WknGlR102V5HFkDe  (Mux demo)
const HLS_SRC = 'https://stream.mux.com/BuGGTsiXq1T00WUb8qfURrHkTCbhrkfFLSv4uAOZzdhw.m3u8';

export function BackgroundVideo() {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (Hls.isSupported()) {
      const hls = new Hls({ startLevel: -1 });
      hls.loadSource(HLS_SRC);
      hls.attachMedia(video);
      return () => hls.destroy();
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // Safari native HLS
      video.src = HLS_SRC;
    }
  }, []);

  return (
    /* z-[-30] keeps this behind all page content */
    <div className="fixed inset-0 w-screen h-screen overflow-hidden pointer-events-none z-[-30]">
      <video
        ref={videoRef}
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 w-full h-full object-cover scale-[1.04]"
        style={{ minWidth: '177.77vh', minHeight: '56.25vw' }}
      />

      {/* Horizontal gradient — protects left-side text */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'linear-gradient(90deg, rgba(3,7,18,0.72) 0%, rgba(3,7,18,0.45) 50%, rgba(3,7,18,0.15) 100%)',
        }}
      />

      {/* Vertical gradient — bleeds video into dark sections at the bottom */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'linear-gradient(to bottom, rgba(3,7,18,0.1) 0%, rgba(3,7,18,0.25) 60%, rgba(3,7,18,0.85) 90%, #030712 100%)',
        }}
      />
    </div>
  );
}
