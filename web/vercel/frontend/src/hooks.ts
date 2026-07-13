import { useEffect, useState } from 'react';

// --- Hash router (deploy-safe; no path-based routing) -------------------------
export function useHashRoute(): string {
  const [route, setRoute] = useState(() => window.location.hash.slice(1) || '/');
  useEffect(() => {
    const onHash = () => setRoute(window.location.hash.slice(1) || '/');
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  return route;
}

export function navigate(to: string) {
  window.location.hash = to;
}

// --- Dark mode (no localStorage — blocked in sandbox iframe) ------------------
export function useTheme(): [boolean, () => void] {
  const [dark, setDark] = useState(() =>
    window.matchMedia('(prefers-color-scheme: dark)').matches,
  );
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
  }, [dark]);
  return [dark, () => setDark((d) => !d)];
}

// --- Generic async data hook -------------------------------------------------
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    fn()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e?.message ?? 'Request failed'))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { data, error, loading, reload: () => setNonce((n) => n + 1) };
}
