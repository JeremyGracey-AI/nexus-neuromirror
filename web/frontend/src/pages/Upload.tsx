import { useCallback, useMemo, useRef, useState } from 'react';
import { api } from '../api';
import { useAsync, navigate } from '../hooks';
import type { HealthStatus, RepoSyncStatus, SessionMeta } from '../types';
import { Button, Card, FormatBadge, SectionTitle, Skeleton, StatusPill } from '../components/ui';
import { cx, formatBytes } from '../lib';

type Phase = 'idle' | 'validating' | 'uploading' | 'done' | 'rejected';

function extOf(name: string): string {
  const i = name.lastIndexOf('.');
  return i >= 0 ? name.slice(i).toLowerCase() : '';
}

export function UploadPage() {
  const { data: health, loading } = useAsync<HealthStatus>(() => api.health());
  const { data: sync } = useAsync<RepoSyncStatus>(() => api.repoSync());
  const canPush = !!sync && sync.enabled && sync.credentials_available;
  const [phase, setPhase] = useState<Phase>('idle');
  const [progress, setProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [selected, setSelected] = useState<File | null>(null);
  const [rejectReason, setRejectReason] = useState<string>('');
  const [result, setResult] = useState<SessionMeta | null>(null);
  const [serverError, setServerError] = useState<string>('');
  const inputRef = useRef<HTMLInputElement>(null);

  const accepted = useMemo(() => health?.accepted_formats ?? [], [health]);
  const maxMb = health?.max_upload_mb ?? 8;
  const maxBytes = health?.max_upload_bytes ?? 8 * 1024 * 1024;
  const acceptAttr = useMemo(() => accepted.map((f) => f.ext).join(','), [accepted]);

  const validate = useCallback(
    (file: File): string | null => {
      const ext = extOf(file.name);
      const ok = accepted.some((f) => f.ext === ext);
      if (!ok) {
        return `Unsupported format "${ext || '(none)'}". Accepted: ${accepted
          .map((f) => f.ext)
          .join(', ')}.`;
      }
      if (file.size <= 0) return 'File is empty.';
      if (file.size > maxBytes) {
        return `File is ${formatBytes(file.size)}, above the ${maxMb} MB limit.`;
      }
      return null;
    },
    [accepted, maxBytes, maxMb],
  );

  const pick = useCallback(
    (file: File) => {
      setResult(null);
      setServerError('');
      const reason = validate(file);
      if (reason) {
        setSelected(file);
        setRejectReason(reason);
        setPhase('rejected');
        return;
      }
      setSelected(file);
      setRejectReason('');
      setPhase('validating');
    },
    [validate],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files?.[0];
      if (file) pick(file);
    },
    [pick],
  );

  const doUpload = useCallback(async () => {
    if (!selected) return;
    setPhase('uploading');
    setProgress(0);
    const res = await api.upload(selected, setProgress);
    if (res.ok) {
      setResult(res.data as SessionMeta);
      setPhase('done');
    } else {
      setServerError(res.data?.error ?? `Upload failed (${res.status}).`);
      setPhase('rejected');
      setRejectReason(res.data?.error ?? `Upload failed (${res.status}).`);
    }
  }, [selected]);

  const reset = () => {
    setSelected(null);
    setResult(null);
    setPhase('idle');
    setProgress(0);
    setRejectReason('');
    setServerError('');
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">Upload a BioTrace export</h2>
        <p className="mt-1 max-w-2xl text-sm text-text-muted">
          Drag a recording here or browse. EDF/EDF+ is analyzed with the MNE pipeline; other
          accepted formats are cataloged. Files are checksummed, stored, and committed locally
          {canPush
            ? ', then pushed to the private GitHub repo.'
            : '. They are pushed to GitHub only when server-side GitHub credentials are configured.'}
        </p>
      </div>

      {/* Privacy notice specific to upload */}
      <div className="flex items-start gap-2 rounded-lg border border-border bg-surface-alt px-4 py-3 text-sm">
        <span aria-hidden className="mt-0.5 text-primary">◆</span>
        <div>
          <p className="font-medium">Handling notice</p>
          <p className="mt-0.5 text-text-muted">
            Do not upload personal data during testing — use the synthetic demo EDF. Filenames are
            sanitized, contents are never logged, and uploads are capped at {maxMb} MB (the
            deployment proxy rejects requests over 10 MB).
          </p>
        </div>
      </div>

      {/* Format badges */}
      <div>
        <SectionTitle>Accepted formats</SectionTitle>
        {loading ? (
          <div className="flex gap-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-6 w-28" />
            ))}
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {accepted.map((f) => (
              <FormatBadge key={f.ext} ext={f.ext} label={f.label} mode={f.mode} />
            ))}
          </div>
        )}
      </div>

      {/* Dropzone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        className={cx(
          'rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors',
          dragActive ? 'border-primary bg-primary/5' : 'border-border bg-surface',
        )}
        data-testid="dropzone"
      >
        <div aria-hidden className="mb-2 text-2xl text-text-faint">↑</div>
        <p className="text-sm font-medium">Drop a recording, or</p>
        <div className="mt-3">
          <input
            ref={inputRef}
            type="file"
            accept={acceptAttr}
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) pick(file);
            }}
            data-testid="input-file"
          />
          <Button variant="ghost" onClick={() => inputRef.current?.click()} data-testid="button-browse">
            Browse files
          </Button>
        </div>
        <p className="mt-3 text-xs text-text-muted">Max {maxMb} MB · single file</p>
      </div>

      {/* Selected file + rejection */}
      {selected && phase !== 'done' && (
        <Card className="p-4" data-testid="selected-file">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate font-mono text-sm">{selected.name}</div>
              <div className="mt-0.5 text-xs text-text-muted tnum">
                {formatBytes(selected.size)} · {extOf(selected.name) || 'no ext'}
              </div>
            </div>
            {phase === 'rejected' ? (
              <StatusPill kind="error" label="Rejected" data-testid="status-rejected" />
            ) : (
              <FormatBadge
                label={extOf(selected.name).toUpperCase()}
                mode={accepted.find((f) => f.ext === extOf(selected.name))?.mode ?? '—'}
              />
            )}
          </div>

          {phase === 'rejected' && (
            <div
              className="mt-3 flex items-start gap-2 rounded border border-error/40 bg-error/5 px-3 py-2 text-sm text-error"
              data-testid="reject-reason"
              role="alert"
            >
              <span aria-hidden>✕</span>
              <span>{rejectReason || serverError}</span>
            </div>
          )}

          {phase === 'uploading' && (
            <div className="mt-3">
              <div className="mb-1 flex justify-between text-xs text-text-muted tnum">
                <span>Uploading…</span>
                <span>{progress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded bg-surface-alt">
                <div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          <div className="mt-4 flex gap-2">
            {(phase === 'validating' || phase === 'uploading') && (
              <Button onClick={doUpload} disabled={phase === 'uploading'} data-testid="button-upload">
                {phase === 'uploading' ? 'Uploading…' : 'Upload & analyze'}
              </Button>
            )}
            <Button variant="ghost" onClick={reset} data-testid="button-reset">
              {phase === 'rejected' ? 'Choose another' : 'Cancel'}
            </Button>
          </div>
        </Card>
      )}

      {/* Result: local save / analysis / git sync */}
      {phase === 'done' && result && <UploadResult meta={result} onReset={reset} />}
    </div>
  );
}

function UploadResult({ meta, onReset }: { meta: SessionMeta; onReset: () => void }) {
  const git = meta.git;
  const analysisKind =
    meta.analysis_status === 'ok'
      ? 'ok'
      : meta.analysis_status === 'failed' || meta.analysis_status === 'error'
        ? 'failed'
        : 'neutral';
  const analysisLabel =
    meta.analysis_mode === 'analyze'
      ? meta.analysis_status === 'ok'
        ? 'Analyzed'
        : meta.analysis_status === 'failed'
          ? 'Analyzed · gate failed'
          : meta.analysis_status === 'error'
            ? 'Analysis error'
            : 'Pending'
      : meta.analysis_mode === 'archival-only'
        ? 'Archival only'
        : 'Cataloged (not parsed)';

  let gitKind: 'ok' | 'warning' | 'failed' | 'neutral' = 'neutral';
  let gitLabel = 'Sync disabled';
  if (git?.enabled) {
    if (git.pushed) {
      gitKind = 'ok';
      gitLabel = 'Committed & pushed';
    } else if (git.committed) {
      gitKind = 'warning';
      gitLabel = 'Committed · push failed';
    } else {
      gitKind = 'failed';
      gitLabel = 'Not committed';
    }
  }

  return (
    <Card className="p-5" data-testid="upload-result">
      <div className="mb-4 flex items-center gap-2">
        <StatusPill kind="ok" label="Saved" />
        <h3 className="text-base font-semibold">Upload complete</h3>
      </div>

      <dl className="grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-xs uppercase tracking-wide text-text-muted">File</dt>
          <dd className="mt-0.5 truncate font-mono text-sm">{meta.original_filename}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-text-muted">SHA-256</dt>
          <dd className="mt-0.5 truncate font-mono text-xs" title={meta.sha256}>
            {meta.sha256.slice(0, 24)}…
          </dd>
        </div>
      </dl>

      {/* Three-state result row */}
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-border bg-surface-alt p-3">
          <div className="text-xs uppercase tracking-wide text-text-muted">Local save</div>
          <div className="mt-1.5"><StatusPill kind="ok" label="Written" data-testid="result-local" /></div>
          <p className="mt-1.5 truncate font-mono text-[11px] text-text-faint" title={meta.raw_relpath}>
            {meta.raw_relpath}
          </p>
        </div>
        <div className="rounded-lg border border-border bg-surface-alt p-3">
          <div className="text-xs uppercase tracking-wide text-text-muted">Analysis</div>
          <div className="mt-1.5"><StatusPill kind={analysisKind} label={analysisLabel} data-testid="result-analysis" /></div>
          <p className="mt-1.5 text-[11px] text-text-faint">{meta.format_label}</p>
        </div>
        <div className="rounded-lg border border-border bg-surface-alt p-3">
          <div className="text-xs uppercase tracking-wide text-text-muted">GitHub sync</div>
          <div className="mt-1.5"><StatusPill kind={gitKind} label={gitLabel} data-testid="result-git" /></div>
          {git?.commit_url ? (
            <a href={git.commit_url} target="_blank" rel="noreferrer" className="mt-1.5 block truncate text-[11px] text-primary underline">
              View commit
            </a>
          ) : (
            <p className="mt-1.5 text-[11px] text-text-faint">{git?.error ?? git?.message ?? '—'}</p>
          )}
        </div>
      </div>

      {git?.enabled && !git.pushed && git.error && (
        <div className="mt-3 flex items-start gap-2 rounded border border-warning/40 bg-warning/5 px-3 py-2 text-sm" role="alert" data-testid="push-failure">
          <span aria-hidden className="text-warning">▲</span>
          <span>{git.error}</span>
        </div>
      )}

      <div className="mt-5 flex gap-2">
        <Button onClick={() => navigate(`/sessions/${meta.session_id}`)} data-testid="button-view-session">
          View session
        </Button>
        <Button variant="ghost" onClick={onReset}>
          Upload another
        </Button>
      </div>
    </Card>
  );
}
