import type { AnalysisSummary, ExpectedChannel, MarkerEvent } from '../types';
import { Card, Metric, SectionTitle, StatusPill } from './ui';
import { formatDuration } from '../lib';

// --- Top-line recording metrics ---------------------------------------------
export function RecordingMetrics({ a }: { a: AnalysisSummary }) {
  const r = a.recording;
  const foundCount = a.expected_channels.filter((c) => c.found).length;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Metric label="Duration" value={formatDuration(r.duration_s)} />
      <Metric label="Sample rate" value={r.sfreq_hz ?? '—'} unit="Hz" />
      <Metric
        label="Channels"
        value={`${foundCount}/${a.expected_channels.length}`}
        unit="EEG"
      />
      <Metric label="Markers" value={a.markers.n_events ?? 0} unit="events" />
    </div>
  );
}

// --- Per-channel metrics table ----------------------------------------------
export function ChannelStatus({ channels }: { channels: ExpectedChannel[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead className="bg-surface-alt text-left text-xs uppercase tracking-wide text-text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Channel</th>
            <th className="px-3 py-2 font-medium">Matched</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 text-right font-medium">RMS µV</th>
            <th className="px-3 py-2 text-right font-medium">p2p µV</th>
            <th className="px-3 py-2 text-right font-medium">max|µV|</th>
          </tr>
        </thead>
        <tbody>
          {channels.map((c) => (
            <tr key={c.canonical} className="border-t border-border" data-testid={`row-channel-${c.canonical}`}>
              <td className="px-3 py-2 font-medium">{c.canonical}</td>
              <td className="px-3 py-2 font-mono text-xs text-text-muted">
                {c.matched_name ?? '—'}
              </td>
              <td className="px-3 py-2">
                {c.found ? (
                  <StatusPill kind="ok" label="Present" />
                ) : (
                  <StatusPill kind="failed" label="Missing" />
                )}
              </td>
              <td className="px-3 py-2 text-right tnum">{c.metrics ? c.metrics.rms_uv.toFixed(2) : '—'}</td>
              <td className="px-3 py-2 text-right tnum">{c.metrics ? c.metrics.ptp_uv.toFixed(1) : '—'}</td>
              <td className="px-3 py-2 text-right tnum">{c.metrics ? c.metrics.max_abs_uv.toFixed(1) : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Figure panel (trace / psd / markers images) ----------------------------
export function FigurePanel({
  title,
  src,
  caption,
}: {
  title: string;
  src: string | null;
  caption: string;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <span className="text-sm font-medium">{title}</span>
        <span className="text-xs text-text-muted">{caption}</span>
      </div>
      <div className="bg-surface-alt p-3">
        {src ? (
          <img
            src={src}
            alt={`${title} figure`}
            className="mx-auto max-h-[280px] w-full object-contain"
            loading="lazy"
          />
        ) : (
          <div className="flex h-40 items-center justify-center text-sm text-text-muted">
            No figure available
          </div>
        )}
      </div>
    </Card>
  );
}

// --- Marker timeline (rendered inline, no external image needed) -------------
export function MarkerTimeline({
  events,
  duration,
}: {
  events: MarkerEvent[];
  duration: number | null;
}) {
  const dur = duration && duration > 0 ? duration : 60;
  const labels = Array.from(new Set(events.map((e) => e.label)));
  const colorFor = (label: string) => {
    const idx = labels.indexOf(label);
    const palette = ['hsl(var(--primary))', 'hsl(var(--secondary))', 'hsl(var(--warning))', 'hsl(var(--success))'];
    return palette[idx % palette.length];
  };
  return (
    <div>
      <div className="relative h-14 rounded-lg border border-border bg-surface-alt">
        {events.map((e, i) => (
          <div
            key={i}
            title={`${e.label} @ ${e.onset_s.toFixed(1)}s (${e.source})`}
            className="absolute top-2 h-10 w-[2px]"
            style={{ left: `${Math.min(99, (e.onset_s / dur) * 100)}%`, background: colorFor(e.label) }}
          />
        ))}
        <span className="absolute bottom-1 left-2 text-[10px] text-text-faint tnum">0s</span>
        <span className="absolute bottom-1 right-2 text-[10px] text-text-faint tnum">{dur.toFixed(0)}s</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-3">
        {labels.map((l) => (
          <span key={l} className="inline-flex items-center gap-1.5 text-xs text-text-muted">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: colorFor(l) }} aria-hidden />
            {l}
          </span>
        ))}
      </div>
    </div>
  );
}

// --- Warnings / failures block ----------------------------------------------
export function Findings({ warnings, failures }: { warnings: string[]; failures: string[] }) {
  if (warnings.length === 0 && failures.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-success/40 bg-success/5 px-4 py-3 text-sm">
        <StatusPill kind="ok" label="Passed" />
        <span className="text-text-muted">No warnings or hard failures.</span>
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {failures.map((f, i) => (
        <div key={`f${i}`} className="flex items-start gap-2 rounded-lg border border-error/40 bg-error/5 px-4 py-2.5 text-sm">
          <StatusPill kind="failed" label="Failure" />
          <span>{f}</span>
        </div>
      ))}
      {warnings.map((w, i) => (
        <div key={`w${i}`} className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning/5 px-4 py-2.5 text-sm">
          <StatusPill kind="warning" label="Warning" />
          <span>{w}</span>
        </div>
      ))}
    </div>
  );
}

export function SectionHeader({ title, hint }: { title: string; hint?: string }) {
  return <SectionTitle hint={hint}>{title}</SectionTitle>;
}
