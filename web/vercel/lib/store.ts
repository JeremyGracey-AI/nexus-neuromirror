/**
 * Session store backed by GitHub (no local filesystem).
 *
 * An upload becomes a *session* committed to the repository:
 *
 *   data/uploads/YYYY-MM-DD/<session-id>/
 *       <sanitized-original-name>   # the raw recording
 *       metadata.json               # provenance + checksum + analysis state
 *
 * Derived report artifacts (EDF diagnostic JSON) live under:
 *
 *   reports/uploads/<session-id>/
 *       diagnostic.json
 *
 * The catalog is the set of metadata.json files in the repo tree — no separate
 * database, matching the original prototype's design.
 */

import { randomBytes } from 'node:crypto';
import { analyzeEdfBuffer } from './analysis.js';
import type { GitHubClient } from './github.js';
import { classifyExtension, extensionOf, formatLabel, type AnalysisMode } from './security.js';

export const UPLOADS_SUBDIR = 'data/uploads';
export const REPORTS_SUBDIR = 'reports/uploads';

export const GIT_AUTHOR = {
  name: 'NeXus NeuroMirror Dashboard',
  email: 'dashboard@nexus-neuromirror.local',
};

export interface GitStatus {
  enabled: boolean;
  committed: boolean;
  pushed: boolean;
  commit_sha: string | null;
  commit_url: string | null;
  branch: string | null;
  message: string;
  error: string | null;
  steps: string[];
}

export interface SessionMeta {
  session_id: string;
  date: string;
  original_filename: string;
  extension: string;
  format_label: string;
  analysis_mode: AnalysisMode;
  size_bytes: number;
  sha256: string;
  uploaded_at: string;
  raw_relpath: string;
  analysis_status: string;
  analysis: ReturnType<typeof analyzeEdfBuffer>['summary'] | null;
  report_relpaths: string[];
  warnings: string[];
  hard_failures: string[];
  git: GitStatus | null;
}

export function newSessionId(): string {
  return randomBytes(6).toString('hex');
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function nowIso(): string {
  return new Date().toISOString();
}

export function sessionDir(date: string, sessionId: string): string {
  return `${UPLOADS_SUBDIR}/${date}/${sessionId}`;
}

export function reportDir(sessionId: string): string {
  return `${REPORTS_SUBDIR}/${sessionId}`;
}

export interface UploadOutcome {
  metadata: SessionMeta;
  /** Files to commit atomically (repo-relative path + bytes). */
  files: { path: string; bytes: Uint8Array }[];
}

/**
 * Build a new session's metadata + the set of files to commit. Runs EDF
 * analysis in-process for `analyze` mode. Does NOT talk to GitHub — the caller
 * commits `files` atomically and then records the git status.
 */
export function buildSession(filename: string, data: Uint8Array, checksum: string): UploadOutcome {
  const date = today();
  const sessionId = newSessionId();
  const ext = extensionOf(filename);
  const mode = classifyExtension(ext);
  const rawRelpath = `${sessionDir(date, sessionId)}/${filename}`;

  const metadata: SessionMeta = {
    session_id: sessionId,
    date,
    original_filename: filename,
    extension: ext,
    format_label: formatLabel(ext),
    analysis_mode: mode,
    size_bytes: data.length,
    sha256: checksum,
    uploaded_at: nowIso(),
    raw_relpath: rawRelpath,
    analysis_status: mode === 'analyze' ? 'pending' : 'not-applicable',
    analysis: null,
    report_relpaths: [],
    warnings: [],
    hard_failures: [],
    git: null,
  };

  const files: { path: string; bytes: Uint8Array }[] = [{ path: rawRelpath, bytes: data }];

  if (mode === 'analyze') {
    try {
      const result = analyzeEdfBuffer(data, rawRelpath);
      metadata.analysis_status = result.ok ? 'ok' : 'failed';
      metadata.analysis = result.summary;
      metadata.warnings = result.warnings;
      metadata.hard_failures = result.hard_failures;
      const diagPath = `${reportDir(sessionId)}/diagnostic.json`;
      metadata.report_relpaths = [diagPath];
      files.push({
        path: diagPath,
        bytes: new TextEncoder().encode(JSON.stringify(result.diagnostic, null, 2)),
      });
    } catch (err) {
      // Surface a clean failure; never echo raw contents.
      metadata.analysis_status = 'error';
      const msg = err instanceof Error ? err.message : 'Unknown analysis error.';
      metadata.hard_failures = [`Analysis failed: ${msg}`];
    }
  }

  // metadata.json is committed last so it reflects analysis results.
  files.push({
    path: `${sessionDir(date, sessionId)}/metadata.json`,
    bytes: new TextEncoder().encode(JSON.stringify(metadata, null, 2)),
  });

  return { metadata, files };
}

/** List all sessions from the repo, newest first. */
export async function listSessions(client: GitHubClient): Promise<SessionMeta[]> {
  const paths = await client.findMetadataPaths(UPLOADS_SUBDIR);
  const sessions: SessionMeta[] = [];
  for (const p of paths) {
    const text = await client.getFileText(p);
    if (!text) continue;
    try {
      sessions.push(JSON.parse(text) as SessionMeta);
    } catch {
      // Skip malformed metadata rather than failing the whole catalog.
    }
  }
  sessions.sort((a, b) => (b.uploaded_at || '').localeCompare(a.uploaded_at || ''));
  return sessions;
}

/** Fetch one session by id (scans metadata paths). */
export async function getSession(
  client: GitHubClient,
  sessionId: string,
): Promise<SessionMeta | null> {
  if (!/^[a-f0-9]{6,32}$/i.test(sessionId)) return null;
  const paths = await client.findMetadataPaths(UPLOADS_SUBDIR);
  for (const p of paths) {
    if (!p.includes(`/${sessionId}/`)) continue;
    const text = await client.getFileText(p);
    if (!text) continue;
    try {
      const meta = JSON.parse(text) as SessionMeta;
      if (meta.session_id === sessionId) return meta;
    } catch {
      // ignore
    }
  }
  return null;
}
