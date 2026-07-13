// Minimal geometric mark: an electrode ring bisected by a midline EEG probe.
// Uses currentColor so it adapts to light/dark. Works at 24px and 200px.
export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      role="img"
      aria-label="NeXus NeuroMirror logo"
    >
      <circle cx="16" cy="16" r="10" stroke="currentColor" strokeWidth="1.75" />
      <circle cx="16" cy="16" r="2.1" fill="currentColor" />
      <path
        d="M2 16 h6 l2.4 -6 l3.4 12 l2.4 -6 h1.4"
        stroke="hsl(var(--primary))"
        strokeWidth="1.75"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <path
        d="M23.5 16 h6.5"
        stroke="hsl(var(--secondary))"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}
