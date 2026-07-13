import { api } from '../api';
import { useAsync, navigate } from '../hooks';
import type { SessionMeta } from '../types';
import { Button, EmptyState, ErrorState, FormatBadge, Skeleton, StatusPill } from '../components/ui';
import { formatBytes, formatTimestamp } from '../lib';

function analysisPill(m: SessionMeta) {
  if (m.analysis_mode === 'analyze') {
    if (m.analysis_status === 'ok') return <StatusPill kind="ok" label="Analyzed" />;
    if (m.analysis_status === 'failed') return <StatusPill kind="failed" label="Gate failed" />;
    if (m.analysis_status === 'error') return <StatusPill kind="error" label="Error" />;
    return <StatusPill kind="pending" label="Pending" />;
  }
  if (m.analysis_mode === 'archival-only') return <StatusPill kind="archival" label="Archival" />;
  return <StatusPill kind="catalog" label="Cataloged" />;
}

function gitPill(m: SessionMeta) {
  const g = m.git;
  if (!g || !g.enabled) return <StatusPill kind="neutral" label="No sync" />;
  if (g.pushed)
    return g.commit_url ? (
      <a href={g.commit_url} target="_blank" rel="noreferrer" className="text-xs text-primary underline">
        {g.commit_sha?.slice(0, 7) ?? 'commit'}
      </a>
    ) : (
      <StatusPill kind="ok" label="Pushed" />
    );
  if (g.committed) return <StatusPill kind="warning" label="Local only" />;
  return <StatusPill kind="failed" label="Uncommitted" />;
}

function SessionsSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-14" />
      ))}
    </div>
  );
}

export function Sessions() {
  const { data, error, loading, reload } = useAsync<{ sessions: SessionMeta[] }>(() =>
    api.sessions(),
  );

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Session catalog</h2>
          <p className="mt-1 text-sm text-text-muted">Uploaded recordings, newest first.</p>
        </div>
        <Button variant="ghost" onClick={reload} data-testid="button-refresh">
          Refresh
        </Button>
      </div>

      {loading && <SessionsSkeleton />}

      {!loading && error && (
        <ErrorState
          title="Could not load sessions"
          body="The catalog is unavailable. Check the backend is running."
          onRetry={reload}
        />
      )}

      {!loading && !error && data && data.sessions.length === 0 && (
        <EmptyState
          title="No sessions yet"
          body="Upload a BioTrace export to populate the catalog. Use the synthetic demo EDF for testing."
          action={<Button onClick={() => navigate('/upload')}>Upload a recording</Button>}
        />
      )}

      {!loading && !error && data && data.sessions.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-surface-alt text-left text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="px-3 py-2 font-medium">File</th>
                <th className="px-3 py-2 font-medium">Format</th>
                <th className="px-3 py-2 text-right font-medium">Size</th>
                <th className="px-3 py-2 font-medium">Checksum</th>
                <th className="px-3 py-2 font-medium">Analysis</th>
                <th className="px-3 py-2 font-medium">GitHub</th>
                <th className="px-3 py-2 font-medium">Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {data.sessions.map((m) => (
                <tr
                  key={m.session_id}
                  className="cursor-pointer border-t border-border hover:bg-surface-alt"
                  onClick={() => navigate(`/sessions/${m.session_id}`)}
                  data-testid={`row-session-${m.session_id}`}
                >
                  <td className="max-w-[180px] truncate px-3 py-2.5 font-mono text-xs">{m.original_filename}</td>
                  <td className="px-3 py-2.5">
                    <FormatBadge label={m.format_label} mode={m.analysis_mode} />
                  </td>
                  <td className="px-3 py-2.5 text-right tnum">{formatBytes(m.size_bytes)}</td>
                  <td className="px-3 py-2.5 font-mono text-xs text-text-muted" title={m.sha256}>
                    {m.sha256.slice(0, 10)}…
                  </td>
                  <td className="px-3 py-2.5">{analysisPill(m)}</td>
                  <td className="px-3 py-2.5">{gitPill(m)}</td>
                  <td className="px-3 py-2.5 text-xs text-text-muted tnum">{formatTimestamp(m.uploaded_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
