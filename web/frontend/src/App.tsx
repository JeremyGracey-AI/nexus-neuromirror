import { useState } from 'react';
import { Logo } from './components/Logo';
import { api } from './api';
import { useAsync, useHashRoute, useTheme } from './hooks';
import { cx } from './lib';
import type { RepoSyncStatus } from './types';
import { Overview } from './pages/Overview';
import { UploadPage } from './pages/Upload';
import { Sessions } from './pages/Sessions';
import { SessionDetail } from './pages/SessionDetail';

const NAV = [
  { path: '/', label: 'Overview', glyph: '◧' },
  { path: '/upload', label: 'Upload', glyph: '↑' },
  { path: '/sessions', label: 'Sessions', glyph: '▤' },
];

function NavItem({
  path,
  label,
  glyph,
  active,
  onClick,
}: {
  path: string;
  label: string;
  glyph: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <a
      href={`#${path}`}
      onClick={onClick}
      data-testid={`nav-${label.toLowerCase()}`}
      className={cx(
        'flex min-h-[44px] items-center gap-3 rounded px-3 text-sm font-medium transition-colors',
        active
          ? 'bg-primary/10 text-primary'
          : 'text-text-muted hover:bg-surface-alt hover:text-text',
      )}
      aria-current={active ? 'page' : undefined}
    >
      <span aria-hidden className="w-4 text-center text-base">{glyph}</span>
      {label}
    </a>
  );
}

function PrivacyBanner() {
  // Only promise a GitHub push when the server can actually reach the remote
  // with credentials. Otherwise state the honest local-only behavior.
  const { data: sync } = useAsync<RepoSyncStatus>(() => api.repoSync());
  const canPush = !!sync && sync.enabled && sync.credentials_available;

  let syncSentence: string;
  if (!sync) {
    // Status not yet loaded — describe only what is always true.
    syncSentence = 'Uploads are stored in this repository and committed locally.';
  } else if (canPush) {
    syncSentence =
      'Uploads are stored in this repository, committed, and pushed to the private GitHub repo.';
  } else {
    syncSentence =
      'Uploads are stored in this repository and committed locally; they are pushed to ' +
      'GitHub only when server-side GitHub credentials are configured.';
  }

  return (
    <div
      role="note"
      className="flex items-start gap-2 border-b border-warning/40 bg-warning/10 px-4 py-2 text-xs text-text sm:text-sm"
      data-testid="privacy-banner"
    >
      <span aria-hidden className="mt-0.5 text-warning">▲</span>
      <p>
        <span className="font-semibold">Private prototype.</span> EEG/neurofeedback data is
        sensitive. {syncSentence} Sharing this site grants upload access. Not a medical or
        diagnostic tool.
      </p>
    </div>
  );
}

function Router() {
  const route = useHashRoute();
  if (route === '/' || route === '') return <Overview />;
  if (route === '/upload') return <UploadPage />;
  if (route === '/sessions') return <Sessions />;
  if (route.startsWith('/sessions/')) {
    return <SessionDetail id={route.slice('/sessions/'.length)} />;
  }
  return (
    <div className="p-8 text-center text-text-muted">
      <p className="text-lg font-medium">Page not found</p>
      <a href="#/" className="mt-2 inline-block text-primary underline">
        Return to Overview
      </a>
    </div>
  );
}

export function App() {
  const route = useHashRoute();
  const [dark, toggleTheme] = useTheme();
  const [mobileNav, setMobileNav] = useState(false);

  const activePath =
    route.startsWith('/sessions') ? '/sessions' : route === '' ? '/' : route;

  return (
    <div className="grid h-full grid-rows-[auto_auto_1fr] md:grid-cols-[220px_1fr] md:grid-rows-[auto_1fr]">
      {/* Sidebar */}
      <aside
        className={cx(
          'border-border bg-surface md:row-span-2 md:border-r',
          'md:flex md:flex-col',
        )}
      >
        <div className="flex items-center justify-between px-4 py-3.5 md:border-b md:border-border">
          <a href="#/" className="flex items-center gap-2.5 text-text" aria-label="NeXus NeuroMirror home">
            <Logo size={26} />
            <div className="leading-tight">
              <div className="text-sm font-semibold tracking-tight">NeXus NeuroMirror</div>
              <div className="text-[10px] uppercase tracking-widest text-text-muted">EEG Console</div>
            </div>
          </a>
          <button
            className="min-h-[44px] min-w-[44px] rounded text-text-muted hover:bg-surface-alt md:hidden"
            onClick={() => setMobileNav((v) => !v)}
            aria-label="Toggle navigation"
            aria-expanded={mobileNav}
            data-testid="button-mobile-nav"
          >
            <span aria-hidden>☰</span>
          </button>
        </div>
        <nav
          className={cx(
            'flex-col gap-1 px-3 pb-3 md:flex md:pt-3',
            mobileNav ? 'flex border-b border-border' : 'hidden',
          )}
        >
          {NAV.map((n) => (
            <NavItem
              key={n.path}
              {...n}
              active={activePath === n.path}
              onClick={() => setMobileNav(false)}
            />
          ))}
        </nav>
        <div className="mt-auto hidden px-4 py-3 text-[10px] text-text-faint md:block">
          v0.1 · offline-first prototype
        </div>
      </aside>

      {/* Header */}
      <header className="flex items-center justify-between border-b border-border bg-surface px-4 py-2.5 md:px-6">
        <h1 className="text-sm font-medium text-text-muted">
          {activePath === '/' && 'Overview'}
          {activePath === '/upload' && 'Upload recording'}
          {activePath === '/sessions' && 'Session catalog'}
        </h1>
        <div className="flex items-center gap-2">
          <a
            href="#/upload"
            className="hidden min-h-[36px] items-center rounded bg-primary px-3 text-sm font-medium text-white hover:bg-primary-hover sm:inline-flex"
          >
            Upload
          </a>
          <button
            onClick={toggleTheme}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded border border-border text-text-muted hover:bg-surface-alt"
            aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            data-testid="button-theme-toggle"
          >
            <span aria-hidden>{dark ? '☀' : '☾'}</span>
          </button>
        </div>
      </header>

      {/* Main: the single primary scroll region */}
      <main className="scroll-region bg-bg">
        <PrivacyBanner />
        <div className="mx-auto max-w-5xl px-4 py-5 md:px-6 md:py-6">
          <Router />
        </div>
      </main>
    </div>
  );
}
