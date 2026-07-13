import type {
  DemoResponse,
  HealthStatus,
  RepoSyncStatus,
  SessionMeta,
} from './types';

// Deployment note (Vercel).
//
// On Vercel the serverless functions live at same-origin `/api/*`, so the
// frontend always talks to a leading-slash `/api` base. This also works with
// the local Vite dev server (via `vercel dev`, which serves the functions on
// the same origin) and with `vite` + a dev proxy. No port-placeholder rewriting
// is needed for the Vercel target.
const BASE = '/api';

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => getJSON<HealthStatus>('/health'),
  repoSync: () => getJSON<RepoSyncStatus>('/repo-sync'),
  demo: () => getJSON<DemoResponse>('/demo'),
  sessions: () => getJSON<{ sessions: SessionMeta[] }>('/sessions'),
  session: (id: string) => getJSON<SessionMeta>(`/sessions/${id}`),
  artifactUrl: (relpath: string) =>
    `${BASE}/artifact?path=${encodeURIComponent(relpath)}`,

  async upload(
    file: File,
    onProgress?: (pct: number) => void,
  ): Promise<{ ok: boolean; status: number; data: any }> {
    return new Promise((resolve) => {
      const form = new FormData();
      form.append('file', file);
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${BASE}/upload`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      };
      xhr.onload = () => {
        let data: any = {};
        try {
          data = JSON.parse(xhr.responseText);
        } catch {
          data = { error: 'Malformed server response.' };
        }
        resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, data });
      };
      xhr.onerror = () =>
        resolve({ ok: false, status: 0, data: { error: 'Network error during upload.' } });
      xhr.send(form);
    });
  },
};
