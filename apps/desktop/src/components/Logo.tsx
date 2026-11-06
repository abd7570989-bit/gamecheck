export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} role="img" aria-label="GameCheck">
      <defs>
        <linearGradient id="gc-logo" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#6cc0ff" />
          <stop offset="1" stopColor="#1f7fff" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="60" height="60" rx="16" fill="#0d1117" stroke="url(#gc-logo)" strokeWidth="3" />
      <path d="M18 33.5 28 43l18-21" fill="none" stroke="url(#gc-logo)" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
