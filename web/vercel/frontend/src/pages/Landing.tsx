import { useEffect, useRef, useState } from 'react';
import { navigate } from '../hooks';

const REPO_URL = 'https://github.com/jeremygracey-ai/nexus-neuromirror';

// Bright-blue "X" wordmark, matching the logo animation.
function Wordmark({ className = '' }: { className?: string }) {
  return (
    <span className={className}>
      Ne<span className="text-primary">X</span>us
      <span className="text-text-muted"> </span>NeuroMirror
    </span>
  );
}

// One-time split-animation intro. Plays once per session, but never blocks the
// site: it always dismisses — on video end, on error, or after a hard timeout —
// so a stalled or autoplay-blocked video can't trap the user on the intro.
// Plays ONE cycle, then lands on the static hero — it never loops.
const INTRO_MAX_MS = 9000; // clip is ~8s; guarantee dismissal even if stalled

function Intro({ onDone }: { onDone: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    // Hard safety timeout — fires regardless of video state.
    const timer = window.setTimeout(onDone, INTRO_MAX_MS);
    // Try to start playback; if the browser rejects autoplay, skip the intro.
    const v = videoRef.current;
    if (v) {
      const p = v.play();
      if (p && typeof p.catch === 'function') p.catch(() => onDone());
    }
    return () => window.clearTimeout(timer);
  }, [onDone]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#050a17]"
      role="presentation"
      onClick={onDone}
    >
      <video
        ref={videoRef}
        className="h-full w-full object-cover"
        src="/brand/nexus_intro.mp4"
        poster="/brand/hero_still.jpg"
        autoPlay
        muted
        playsInline
        preload="auto"
        onEnded={onDone}
        onError={onDone}
      />
      <button
        onClick={onDone}
        className="absolute bottom-6 right-6 rounded-full border border-white/30 bg-black/40 px-4 py-2 text-sm font-medium text-white backdrop-blur hover:bg-black/60"
      >
        Skip intro →
      </button>
    </div>
  );
}

export function Landing() {
  const [introDone, setIntroDone] = useState(false);

  return (
    <div className="relative h-full w-full overflow-hidden bg-[#050a17] text-white">
      {!introDone && <Intro onDone={() => setIntroDone(true)} />}

      {/* Static brand hero background (no looping video) */}
      <img
        className="absolute inset-0 h-full w-full object-cover"
        src="/brand/hero_still.jpg"
        alt=""
        aria-hidden
      />
      {/* Legibility gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#050a17]/70 via-[#050a17]/40 to-[#050a17]/95" />

      {/* Top bar */}
      <header className="absolute inset-x-0 top-0 z-10 flex items-center justify-between px-5 py-4 md:px-10">
        <Wordmark className="text-lg font-semibold tracking-tight" />
        <nav className="flex items-center gap-2">
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden rounded-md px-3 py-2 text-sm font-medium text-white/75 hover:text-white sm:inline-flex"
          >
            View the code
          </a>
          <button
            onClick={() => navigate('/overview')}
            className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-primary/25 hover:bg-primary-hover"
          >
            Open workbench
          </button>
        </nav>
      </header>

      {/* Hero content */}
      <div className="scroll-region relative z-10 flex h-full flex-col items-center justify-center px-6 text-center">
        <p className="mb-4 text-xs font-medium uppercase tracking-[0.35em] text-primary/90">
          Four-channel EEG · Neuro-AI research
        </p>
        <h1 className="max-w-4xl text-4xl font-semibold leading-tight tracking-tight md:text-6xl">
          A four-channel EEG
          <br />
          neurofeedback workbench
        </h1>
        <p className="mt-6 max-w-2xl text-base text-white/70 md:text-lg">
          Teaching AI to recognize measurable patterns in human cognitive state.
          NeXus NeuroMirror lines up brain signals, behavior, and stimulus on one
          shared clock — a reproducible, offline-first diagnostic workflow you can
          trust.
        </p>

        <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={() => navigate('/overview')}
            className="rounded-lg bg-primary px-6 py-3 text-sm font-semibold text-white shadow-xl shadow-primary/30 hover:bg-primary-hover"
          >
            Open the workbench →
          </button>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-white/20 bg-white/5 px-6 py-3 text-sm font-semibold text-white/90 backdrop-blur hover:bg-white/10"
          >
            View the code
          </a>
        </div>

        <p className="mt-10 max-w-xl text-xs text-white/45">
          Research and educational prototype. Not a medical or diagnostic device;
          it makes no clinical claims.
        </p>
      </div>
    </div>
  );
}
