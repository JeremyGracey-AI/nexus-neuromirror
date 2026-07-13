import { api } from '../api';
import { useAsync, navigate } from '../hooks';
import type { SessionMeta } from '../types';
import { Button, Card, EmptyState, ErrorState, Metric, SectionTitle, Skeleton, StatusPill } from '../components/ui';
import { ChannelStatus, FigurePanel, Findings, MarkerTimeline } from '../components/AnalysisViews';
import { formatBytes, formatDuration, formatTimestamp } from '../lib';

function artifactByStem(m: SessionMeta, stem: string, fmt = 'png'): string | null {
  const rel = m.report_relpaths.find((p) => p.endsWith(`${stem}.${fmt}`));
  return rel ? api.artifactUrl(rel) : null;
}

export function SessionDetail({ id }: { id: string }) {
  const { data: m, error, loading, reload } = useAsync<SessionMeta>(() => api.session(id), [id]);

  if (loading) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[68px]" />
          ))}
        </div>
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (error || !m) {
    return (
      <ErrorState
        title="Session not found"
        body="This session could not be loaded. It may have been removed."
        onRetry={reload}
      />
    );
  }

  const a = m.analysis;
  const git = m.git;

  return (
    <div className="space-y-7">
      {/* Header */}
      <div>
        <a href="#/sessions" className="text-xs text-text-muted hover:text-text">
          ← Back to sessions
        </a>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <h2 className="truncate text-xl font-semibold tracking-tight font-mono">{m.original_filename}</h2>
          <StatusPill kind="ok" label="Saved" />
        </div>
      </div>

      {/* Metadata */}
      <section>
        <SectionTitle>Metadata</SectionTitle>
        <Card className="p-4">
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Field label="Format" value={m.format_label} />
            <Field label="Mode" value={m.analysis_mode} />
            <Field label="Size" value={formatBytes(m.size_bytes)} />
            <Field label="Uploaded" value={formatTimestamp(m.uploaded_at)} />
            <Field label="Session ID" value={m.session_id} mono />
            <Field label="SHA-256" value={m.sha256} mono title={m.sha256} truncate />
          </dl>
        </Card>
      </section>

      {/* GitHub sync */}
      <section>
        <SectionTitle>Repository sync</SectionTitle>
        <GitBlock git={git} />
      </section>

      {/* Analysis (EDF only) */}
      {m.analysis_mode === 'analyze' && a ? (
        <>
          <section>
            <SectionTitle hint={a.unit_assumption}>Recording</SectionTitle>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Metric label="Duration" value={formatDuration(a.recording.duration_s)} />
              <Metric label="Sample rate" value={a.recording.sfreq_hz ?? '—'} unit="Hz" />
              <Metric label="Channels" value={a.recording.n_channels ?? '—'} />
              <Metric label="Markers" value={a.markers.n_events ?? 0} unit="events" />
            </div>
          </section>

          <section>
            <SectionTitle>Channel metrics</SectionTitle>
            <ChannelStatus channels={a.expected_channels} />
          </section>

          <section>
            <SectionTitle hint="waveform · spectrum">Signal figures</SectionTitle>
            <div className="grid gap-4 md:grid-cols-2">
              <FigurePanel title="EEG trace" src={artifactByStem(m, 'trace')} caption="multichannel waveform" />
              <FigurePanel title="Power spectral density" src={artifactByStem(m, 'psd')} caption="0–40 Hz" />
            </div>
          </section>

          {a.markers.events.length > 0 && (
            <section>
              <SectionTitle hint={`${a.markers.events.length} events`}>Marker timeline</SectionTitle>
              <Card className="p-4">
                <MarkerTimeline events={a.markers.events} duration={a.recording.duration_s} />
              </Card>
            </section>
          )}

          <section>
            <SectionTitle>Validation findings</SectionTitle>
            <Findings warnings={m.warnings} failures={m.hard_failures} />
          </section>
        </>
      ) : m.analysis_mode === 'analyze' && m.analysis_status === 'error' ? (
        <ErrorState
          title="Analysis failed"
          body={m.hard_failures[0] ?? 'The EDF could not be analyzed.'}
        />
      ) : (
        <section>
          <SectionTitle>Analysis</SectionTitle>
          <EmptyState
            glyph={m.analysis_mode === 'archival-only' ? '▣' : '◧'}
            title={m.analysis_mode === 'archival-only' ? 'Archival format — not parsed' : 'Cataloged — not parsed in MVP'}
            body={
              m.analysis_mode === 'archival-only'
                ? 'BCD is stored for archival provenance only. It is never parsed by this tool.'
                : 'ASCII/CSV and MATLAB .mat files are cataloged with checksum and metadata. Signal analysis is not part of the MVP for these formats.'
            }
          />
        </section>
      )}

      {/* Raw / download links */}
      <section>
        <SectionTitle>Files</SectionTitle>
        <Card className="divide-y divide-border">
          <FileRow label="Raw recording" relpath={m.raw_relpath} />
          {m.report_relpaths.map((rel) => (
            <FileRow key={rel} label={rel.split('/').pop() ?? rel} relpath={rel} />
          ))}
        </Card>
      </section>

      <div>
        <Button variant="ghost" onClick={() => navigate('/sessions')}>
          Back to catalog
        </Button>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  mono,
  truncate,
  title,
}: {
  label: string;
  value: string;
  mono?: boolean;
  truncate?: boolean;
  title?: string;
}) {
  return (
    <div className="min-w-0">
      <dt className="text-xs uppercase tracking-wide text-text-muted">{label}</dt>
      <dd
        className={`mt-0.5 text-sm ${mono ? 'font-mono' : ''} ${truncate ? 'truncate' : ''}`}
        title={title}
      >
        {value}
      </dd>
    </div>
  );
}

function GitBlock({ git }: { git: SessionMeta['git'] }) {
  if (!git || !git.enabled) {
    return (
      <Card className="flex items-center gap-3 p-4">
        <StatusPill kind="neutral" label="Sync disabled" />
        <span className="text-sm text-text-muted">Uploads were saved locally without git sync.</span>
      </Card>
    );
  }
  if (git.pushed) {
    return (
      <Card className="flex flex-wrap items-center gap-3 p-4">
        <StatusPill kind="ok" label="Committed & pushed" />
        {git.commit_url && (
          <a href={git.commit_url} target="_blank" rel="noreferrer" className="text-sm text-primary underline" data-testid="link-commit">
            {git.commit_sha?.slice(0, 10)} · view commit
          </a>
        )}
      </Card>
    );
  }
  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <StatusPill kind={git.committed ? 'warning' : 'failed'} label={git.committed ? 'Committed · push failed' : 'Not committed'} />
      </div>
      {git.error && (
        <p className="mt-2 flex items-start gap-2 text-sm text-text-muted" role="alert">
          <span aria-hidden className="text-warning">▲</span>
          {git.error}
        </p>
      )}
    </Card>
  );
}

function FileRow({ label, relpath }: { label: string; relpath: string }) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-2.5">
      <span className="min-w-0 truncate font-mono text-xs text-text-muted" title={relpath}>
        {label}
      </span>
      <a
        href={api.artifactUrl(relpath)}
        target="_blank"
        rel="noreferrer"
        className="shrink-0 text-xs text-primary underline"
      >
        Download
      </a>
    </div>
  );
}
