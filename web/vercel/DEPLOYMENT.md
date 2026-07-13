# NeXus NeuroMirror — Vercel Deployment

Production, GitHub-backed deployment of the EEG quality-control **prototype**
dashboard. This is a research/engineering prototype for signal quality checks —
**not a medical or diagnostic tool**, and it makes no clinical claims.

The app runs entirely on Vercel:

- **Frontend** — the existing Vite + React dashboard (unchanged UI, including the
  private-EEG warning banner), served as static files.
- **API** — lightweight Node/TypeScript serverless functions under `api/`.
- **Durable storage** — **GitHub is the backend.** Every upload and its derived
  metadata/report are committed to the repository via the GitHub REST API. There
  is no persistent local filesystem and no long-running FastAPI process.

---

## Vercel project settings (unambiguous)

| Setting               | Value                                    |
| --------------------- | ---------------------------------------- |
| **Root Directory**    | `web/vercel`                             |
| **Framework Preset**  | Other (`framework: null` in vercel.json) |
| **Build Command**     | `npm run build` (from vercel.json)       |
| **Output Directory**  | `frontend/dist` (from vercel.json)       |
| **Install Command**   | `npm install` (from vercel.json)         |
| **Node.js version**   | 20.x                                     |

`vercel.json` already pins the build command, output directory, function runtime
(`@vercel/node@3.2.0`, `maxDuration` 30s), and SPA rewrites, so the dashboard
settings only need the **Root Directory** set to `web/vercel`.

The build runs `npm --prefix frontend install && npm --prefix frontend run build`,
emitting static files to `frontend/dist`. Vercel auto-discovers each `api/**/*.ts`
file as a serverless function at the matching `/api/...` route.

---

## Required environment variables (server-side only)

Set these in **Vercel → Project → Settings → Environment Variables**. They are
server-only and must never be exposed to the client or prefixed with `VITE_`.

| Variable         | Required | Default             | Purpose                                              |
| ---------------- | -------- | ------------------- | ---------------------------------------------------- |
| `GITHUB_TOKEN`   | **Yes**  | —                   | Fine-grained token with Contents: Read and write.    |
| `GITHUB_OWNER`   | No       | `JeremyGracey-AI`   | Repository owner.                                    |
| `GITHUB_REPO`    | No       | `nexus-neuromirror` | Repository name.                                     |
| `GITHUB_BRANCH`  | No       | `master`            | Branch that receives session commits.                |
| `GITHUB_API_BASE`| No       | `https://api.github.com` | Override for GitHub Enterprise / proxy.        |
| `NNM_MAX_UPLOAD_BYTES` | No | `4194304` (4 MB)    | Upload cap. Keep below Vercel's ~4.5 MB body limit.  |

### Creating the `GITHUB_TOKEN`

Create a **fine-grained personal access token** (GitHub → Settings → Developer
settings → Fine-grained tokens):

1. **Resource owner:** `JeremyGracey-AI`
2. **Repository access:** Only select repositories → `nexus-neuromirror`
3. **Permissions → Repository permissions → Contents:** **Read and write**
4. Copy the token and paste it as `GITHUB_TOKEN` in Vercel.

> The secure credential handle used during development (`custom-cred:api.github.com`)
> **cannot** be exported to Vercel. You must add the same fine-grained token
> manually as `GITHUB_TOKEN` in the Vercel project settings.

**If `GITHUB_TOKEN` is absent the API fails clearly** (HTTP 503 with a descriptive
message) instead of silently dropping uploads. `GET /api/health` reports
`config_available: false` and `GET /api/repo-sync` reports
`credentials_available: false` in that state.

---

## Upload size limit

Vercel caps serverless request bodies at **~4.5 MB**. The server enforces a
**4 MB** upload limit by default (`NNM_MAX_UPLOAD_BYTES`), and the UI reads the
active limit from `/api/health` so the dashboard copy always matches the server.
Files larger than the limit are rejected with HTTP 413.

---

## API routes (all same-origin `/api/...`)

| Route                 | Method | Purpose                                                     |
| --------------------- | ------ | ----------------------------------------------------------- |
| `/api/health`         | GET    | Version, accepted formats, active upload limit, token presence. |
| `/api/repo-sync`      | GET    | GitHub backend status (never leaks the token).              |
| `/api/demo`           | GET    | Bundled synthetic diagnostic (works with no token).         |
| `/api/sessions`       | GET    | Session catalog, read from GitHub.                          |
| `/api/sessions/[id]`  | GET    | One session's metadata, read from GitHub.                   |
| `/api/upload`         | POST   | Validate + analyze + atomically commit an upload to GitHub. |
| `/api/artifact?path=` | GET    | Stream a stored report/recording from GitHub.               |

### Accepted formats

`.edf`, `.asc`, `.bcd`, `.csv`, `.mat`, `.txt`. Only **EDF/EDF+** is analyzed
(first-prototype analysis of the four expected midline channels Fz / FCz / Pz / Oz
plus event markers). `.csv` / `.txt` / `.asc` / `.mat` are catalog-only; `.bcd` is
archival-only. The EDF analysis uses a minimal, audited in-repo parser — no MNE or
SciPy — so it stays within serverless limits.

---

## How storage works (GitHub as the backend)

Each upload becomes a **session** committed atomically via the Git Data API
(create blobs → tree → commit → update ref), so the raw recording, its
`metadata.json`, and any derived report land in a single commit:

```
data/uploads/YYYY-MM-DD/<session-id>/
    <sanitized-original-name>     # raw recording
    metadata.json                # provenance, checksum, analysis state, git status
reports/uploads/<session-id>/
    diagnostic.json              # EDF diagnostic (analyze mode only)
```

The session catalog is simply the set of `metadata.json` files in the repo tree —
no separate database. The synthetic Overview demo is **bundled into the app** and
needs neither GitHub nor a token.

### Security properties

- Filenames are sanitized (Unicode-normalized, path components stripped,
  disallowed characters replaced, traversal defeated, length-capped).
- Extension and size are validated against an allow-list before any commit.
- A SHA-256 checksum is recorded for every upload.
- **Raw file contents are never logged**, echoed in errors, or embedded in tree
  requests (only blob SHAs are).
- The GitHub token is read from a server-only env var and never returned to the
  client.

---

## Local development

```bash
cd web/vercel
npm install
cp .env.example .env.local      # then paste your GITHUB_TOKEN
npx vercel dev                  # serves frontend + functions on one origin
```

Or run the frontend alone against a separately running API:

```bash
cd web/vercel/frontend
npm install
npm run dev                     # Vite on :5173 (see vite.config.ts proxy)
```

### Tests, lint, typecheck, build

```bash
cd web/vercel
npm test                        # vitest: security, labels, EDF/analysis, GitHub (mocked)
npm run typecheck               # tsc for api/lib + frontend
npm run lint                    # eslint (frontend)
npm run build                   # builds frontend/dist
```

The analysis tests verify the TypeScript pipeline reproduces the Python
reference diagnostic for the bundled synthetic EDF: all marker events match
exactly and all channel metrics match within 0.001 µV.

> **`npx vercel build` requires Vercel authentication** (it resolves the project
> scope before building) and was intentionally **not** run in this environment to
> avoid any deploy/link side effects. The equivalent steps it runs — the frontend
> build and the function typecheck — pass locally (`npm run build`, `npm run
> typecheck`).

---

## Access control — the deployment URL grants upload access

There is **no application-level authentication** in this prototype. Anyone who
can reach the deployment can upload files that are committed to the GitHub repo.

- Keep the Vercel project **private / protected**. Enable **Vercel Authentication**
  (Deployment Protection) under Project → Settings → Deployment Protection, or put
  the project behind Vercel SSO / a password, so only authorized users can reach it.
- **Do not share the deployment URL** — sharing it grants upload (and therefore
  repo-commit) access.
- This document does **not** claim any in-app auth exists; protection must be
  configured at the Vercel platform level.

---

## Deploying (manual, when you choose to)

Deployment is **not** performed automatically. When ready:

1. In the Vercel dashboard, import the repo and set **Root Directory** to
   `web/vercel`.
2. Add the environment variables above (at minimum `GITHUB_TOKEN`).
3. Enable Deployment Protection.
4. Deploy. `vercel.json` handles the rest (build, output dir, functions, SPA
   rewrites).
