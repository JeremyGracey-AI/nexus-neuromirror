import type { ReactNode } from 'react';
import { cx } from '../lib';

// --- Card --------------------------------------------------------------------
export function Card({
  children,
  className,
  ...rest
}: { children: ReactNode; className?: string } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cx(
        'rounded-lg border border-border bg-surface',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <h2 className="text-lg font-semibold tracking-tight">{children}</h2>
      {hint && <span className="text-xs text-text-muted">{hint}</span>}
    </div>
  );
}

// --- Status pill: never color-only (icon glyph + text) -----------------------
type StatusKind = 'ok' | 'failed' | 'error' | 'pending' | 'warning' | 'neutral' | 'archival' | 'catalog';

const STATUS_STYLES: Record<StatusKind, { cls: string; glyph: string }> = {
  ok: { cls: 'text-success border-success/40 bg-success/10', glyph: '●' },
  failed: { cls: 'text-error border-error/40 bg-error/10', glyph: '▲' },
  error: { cls: 'text-error border-error/40 bg-error/10', glyph: '✕' },
  pending: { cls: 'text-text-muted border-border bg-surface-alt', glyph: '◌' },
  warning: { cls: 'text-warning border-warning/40 bg-warning/10', glyph: '▲' },
  neutral: { cls: 'text-text-muted border-border bg-surface-alt', glyph: '—' },
  archival: { cls: 'text-text-muted border-border bg-surface-alt', glyph: '▣' },
  catalog: { cls: 'text-primary border-primary/40 bg-primary/10', glyph: '◧' },
};

export function StatusPill({
  kind,
  label,
  'data-testid': testId,
}: {
  kind: StatusKind;
  label: string;
  'data-testid'?: string;
}) {
  const s = STATUS_STYLES[kind];
  return (
    <span
      data-testid={testId}
      className={cx(
        'inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-medium tnum',
        s.cls,
      )}
    >
      <span aria-hidden className="text-[10px] leading-none">{s.glyph}</span>
      {label}
    </span>
  );
}

// --- Format badge ------------------------------------------------------------
export function FormatBadge({ label, mode, ext }: { label: string; mode: string; ext?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded border border-border bg-surface-alt px-2 py-0.5 text-xs text-text-muted">
      {ext && <span className="font-mono text-text-faint">{ext}</span>}
      <span className="font-medium text-text">{label}</span>
      <span aria-hidden className="text-text-faint">·</span>
      <span>{mode}</span>
    </span>
  );
}

// --- Skeleton ----------------------------------------------------------------
export function Skeleton({ className }: { className?: string }) {
  return <div className={cx('skeleton', className)} aria-hidden />;
}

// --- Empty / Error states ----------------------------------------------------
export function EmptyState({
  title,
  body,
  action,
  glyph = '◌',
}: {
  title: string;
  body: string;
  action?: ReactNode;
  glyph?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-surface px-6 py-14 text-center">
      <div aria-hidden className="mb-3 text-2xl text-text-faint">{glyph}</div>
      <p className="text-base font-medium">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-text-muted">{body}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ title, body, onRetry }: { title: string; body: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-error/40 bg-error/5 px-6 py-12 text-center">
      <div aria-hidden className="mb-2 text-xl text-error">✕</div>
      <p className="text-base font-medium text-error">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-text-muted">{body}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 min-h-[44px] rounded border border-border bg-surface px-4 text-sm font-medium hover:bg-surface-alt"
        >
          Retry
        </button>
      )}
    </div>
  );
}

// --- Button ------------------------------------------------------------------
export function Button({
  children,
  variant = 'primary',
  className,
  ...rest
}: {
  children: ReactNode;
  variant?: 'primary' | 'ghost' | 'secondary';
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const variants = {
    primary: 'bg-primary text-white hover:bg-primary-hover border-transparent',
    secondary: 'bg-secondary text-white hover:bg-secondary-hover border-transparent',
    ghost: 'bg-surface text-text hover:bg-surface-alt border-border',
  };
  return (
    <button
      className={cx(
        'inline-flex min-h-[44px] items-center justify-center gap-2 rounded border px-4 text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none',
        variants[variant],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

// --- Metric tile -------------------------------------------------------------
export function Metric({ label, value, unit }: { label: string; value: ReactNode; unit?: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface-alt px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-text-muted">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="text-xl font-semibold tnum">{value}</span>
        {unit && <span className="text-sm text-text-muted">{unit}</span>}
      </div>
    </div>
  );
}
