/** Fresh Citrus mark: an orange slice. One mark everywhere (sidebar, sign-in). */
export function LogoMark({ className = "size-9" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
      <circle cx="20" cy="20" r="18" fill="var(--color-brand)" />
      <circle cx="20" cy="20" r="14" fill="var(--color-orange-soft)" />
      <g stroke="var(--color-peach)" strokeWidth="2" strokeLinecap="round">
        <path d="M20 8v24M8 20h24M11.5 11.5l17 17M28.5 11.5l-17 17" />
      </g>
      <circle cx="20" cy="20" r="2.5" fill="var(--color-brand)" />
    </svg>
  );
}

export function Logo({ subtitle = true }: { subtitle?: boolean }) {
  return (
    <span className="flex items-center gap-3">
      <LogoMark />
      <span className="text-left">
        <strong className="block text-lg leading-tight text-strong">Fresh Citrus</strong>
        {subtitle && <span className="block text-xs text-muted">AI Wellness</span>}
      </span>
    </span>
  );
}
