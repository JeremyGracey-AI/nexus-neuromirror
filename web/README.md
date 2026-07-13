# NeXus NeuroMirror — Web Dashboard

A local, single-user web dashboard for uploading BioTrace+ EEG exports, running
the `nexus_neuromirror` diagnostic verifier, and (optionally) committing raw
recordings plus generated reports to this private repository.

> **Private research prototype. Not a medical or diagnostic tool.** It makes no
> clinical claims and surfaces the same research diagnostics as the CLI.

## Layout

```
web/
  backend/            FastAPI service (reuses the nexus_neuromirror package)
    nnm_web/
      app.py          endpoints: health, repo-sync, demo, sessions, upload, artifact
      settings.py     env-driven configuration
      security.py     filename sanitization, extension/size validation, SHA-256
      storage.py      session catalog + traversal-safe artifact resolution
      analysis.py     EDF analysis wrapper around report.generate_report
      gitsync.py      server-side git add(-force)/commit/push with graceful failure
    tests/            pytest suite (security, gitsync, api, gitsync integration)
    requirements.txt
    pytest.ini
  frontend/           React + Vite + TypeScript + Tailwind (hash-routed SPA)
    src/
      pages/          Overview, Upload, Sessions, SessionDetail
      components/     ui primitives, Logo, AnalysisViews
      api.ts hooks.ts lib.ts types.ts App.tsx main.tsx
```

## Backend

Requires the project virtualenv with the `nexus_neuromirror` package installed
(`pip install -e ".[dev]"` from the repo root), plus the web dependencies:

```bash
pip install -r web/backend/requirements.txt
cd web/backend && PYTHONPATH=. uvicorn nnm_web.app:app --port 8000
```

Server listens on **port 8000**. When `web/frontend/dist/` exists, it is served
statically at `/`, so a production build runs as a single process.

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Status, version, accepted formats, size limit |
| GET | `/api/repo-sync` | Git sync enablement + credential reachability |
| GET | `/api/demo` | Bundled synthetic demo diagnostic (Overview) |
| GET | `/api/sessions` | Session catalog (newest first) |
| GET | `/api/sessions/{id}` | Session metadata + analysis |
| POST | `/api/upload` | Secure multipart upload → validate → store → analyze → sync |
| GET | `/api/artifact?path=` | Serve a report/upload artifact (traversal-safe) |

### Upload flow

`validate → sanitize filename → reject traversal → enforce extension + 8 MB
size limit → write under data/uploads/YYYY-MM-DD/<session-id>/ → SHA-256 →
metadata.json → (EDF only) run verifier → write report under
reports/uploads/<session-id>/ → (if enabled) git add-force + commit + push →
return metadata incl. git status/commit URL.`

Push failures never lose the local upload; the error is returned for display.

### Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `NNM_REPO_ROOT` | repo root | Repository root for storage + git |
| `NNM_UPLOADS_SUBDIR` | `data/uploads` | Where raw uploads are written |
| `NNM_REPORTS_SUBDIR` | `reports/uploads` | Where generated reports are written |
| `NNM_CONFIG_PATH` | `configs/project.example.yaml` | Verifier config |
| `NNM_MAX_UPLOAD_BYTES` | `8388608` (8 MB) | Upload size cap |
| `NNM_GIT_SYNC_ENABLED` | `1` | Commit + push accepted uploads |
| `NNM_GIT_REMOTE` | `origin` | Git remote name |
| `NNM_GIT_BRANCH` | `master` | Branch to push to |

## Frontend

```bash
cd web/frontend
npm install
npm run dev        # Vite dev server, proxies /api -> http://127.0.0.1:8000
npm run typecheck  # tsc --noEmit
npm run lint       # eslint, zero warnings
npm run build      # tsc -b && vite build -> dist/
```

Design: technical neurophysiology control-panel aesthetic — warm-neutral light
and dark themes, teal primary + rust secondary, General Sans / IBM Plex Mono,
tabular numerals, fixed dashboard shell with a single scroll region, hash
routing, 44px min touch targets, and status indicators that never rely on color
alone (each pill carries a glyph and text label).

## Testing

```bash
cd web/backend && python -m pytest       # backend unit + integration
cd web/frontend && npm run typecheck && npm run lint && npm run build
```

Backend tests cover filename sanitization, extension/size rejection, checksum,
local save, EDF analysis, catalog listing, artifact serving/traversal, and safe
git sync (mocked runner **and** a real isolated temp-repo integration test that
proves the per-file force-add does not sweep in other ignored files).

## Privacy & git hygiene

- Real recordings (`data/**`) and generated reports (`reports/**`) stay
  git-ignored. Accepted uploads are added only via an explicit per-file safe
  `git add --force` in the upload path — the data directories are never broadly
  un-ignored.
- The only committed report is the **synthetic** `reports/diagnostic_demo/`,
  which powers the Overview demo from a clean checkout.
- `node_modules/`, `dist/`, and the QA screenshot directory are git-ignored.
- GitHub credentials are server-side only and never exposed to the frontend.
  Behind a hosted preview they must be injected into the server environment at
  runtime and may not survive the session; sync then degrades to local-only.
