import { api } from '../api';
import { useAsync } from '../hooks';
import type { DemoResponse } from '../types';
import { Card, ErrorState, Metric, SectionTitle, Skeleton, StatusPill } from '../components/ui';
import {
  ChannelStatus,
  FigurePanel,
  Findings,
  MarkerTimeline,
} from '../components/AnalysisViews';
import { formatDuration } from '../lib';

function OverviewSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[68px]" />
        ))}
      </div>
      <Skeleton className="h-40" />
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}

export function Overview() {
  const { data, error, loading, reload } = useAsync<DemoResponse>(() => api.demo());

  if (loading) return <OverviewSkeleton />;
  if (error || !data)
    return (
      <ErrorState
        title="Could not load the demo report"
        body="The synthetic diagnostic report is unavailable. Check the backend is running."
        onRetry={reload}
      />
    );

  const d = data.diagnostic;
  const rec = d.recording ?? {};
  const expected = (d.expected_channels ?? []).map((c: any) => ({
    canonical: c.canonical,
    matched_name: c.matched_name,
    found: c.found,
    metrics: c.metrics,
  }));
  const events = d.markers?.events ?? [];
  const foundCount = expected.filter((c: any) => c.found).length;
  const art = data.artifacts;

  return (
    <div className="space-y-7">
      <div>
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <h2 className="text-xl font-semibold tracking-tight">Synthetic demo session</h2>
          <StatusPill kind={d.status === 'ok' ? 'ok' : 'failed'} label={d.status === 'ok' ? 'Passed gate' : 'Failed gate'} />
        </div>
        <p className="max-w-2xl text-sm text-text-muted">
          A worked example generated from bundled synthetic data — four midline EEG channels,
          256 Hz, EDF+ annotations, and a status marker channel. No real neural data is involved.
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric label="Duration" value={formatDuration(rec.duration_s)} />
        <Metric label="Sample rate" value={rec.sfreq_hz ?? '—'} unit="Hz" />
        <Metric label="Channels" value={`${foundCount}/${expected.length}`} unit="EEG" />
        <Metric label="Markers" value={d.markers?.n_events ?? 0} unit="events" />
      </div>

      {/* Channel status */}
      <section>
        <SectionTitle hint={`config: ${d.config_name}`}>Channel status</SectionTitle>
        <ChannelStatus channels={expected} />
      </section>

      {/* Visualizations */}
      <section>
        <SectionTitle hint="waveform · spectrum">Signal figures</SectionTitle>
        <div className="grid gap-4 md:grid-cols-2">
          {/* Demo artifacts are bundled static files (root-relative URLs),
              so they load without any GitHub round-trip or token. */}
          <FigurePanel
            title="EEG trace"
            src={art.trace_png ?? null}
            caption="multichannel waveform"
          />
          <FigurePanel
            title="Power spectral density"
            src={art.psd_png ?? null}
            caption="0–40 Hz"
          />
        </div>
      </section>

      {/* Marker timeline */}
      <section>
        <SectionTitle hint={`${events.length} events`}>Marker timeline</SectionTitle>
        <Card className="p-4">
          <MarkerTimeline events={events} duration={rec.duration_s} />
        </Card>
      </section>

      {/* Findings */}
      <section>
        <SectionTitle>Validation findings</SectionTitle>
        <Findings warnings={d.warnings ?? []} failures={d.hard_failures ?? []} />
      </section>
    </div>
  );
}
