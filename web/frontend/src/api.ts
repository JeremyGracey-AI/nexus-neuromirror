import type {
  DemoResponse,
  HealthStatus,
  RepoSyncStatus,
  SessionMeta,
} from './types';

// Deployment note.
//
// `deploy_website` replaces the `__PORT_8000__` placeholder with the proxy path
// (`port/8000`) at deploy time. Two runtime modes:
//
//   - Local / backend-served: the placeholder is left unreplaced (it still
//     starts with `__`), so `PORT_PREFIX` is empty and requests hit `/api/...`
//     on the same origin. This works with the Vite dev proxy AND when the
//     FastAPI backend serves the built files directly at `/`.
//   - Deployed behind the preview proxy: `PORT_PREFIX` becomes the *relative*
//     path `port/8000`, so requests hit `port/8000/api/...`, resolved against
//     the nested preview URL (paired with `base: './'` in vite.config.ts).
//
// Using a leading slash for the local case keeps root-relative behavior for the
// backend-served build; the deployed case is intentionally relative so it
// resolves under the nested URL.
const PORT_PREFIX = '__PORT_8000__'.startsWith('__') ? '' : '__PORT_8000__';
const BASE = PORT_PREFIX ? `${PORT_PREFIX}/api` : '/api';

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
