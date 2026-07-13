import type {
  DemoResponse,
  HealthStatus,
  RepoSyncStatus,
  SessionMeta,
} from './types';

// Deployment note: the app is served by the FastAPI backend, so a relative
// base works both locally and behind the deploy proxy.
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
