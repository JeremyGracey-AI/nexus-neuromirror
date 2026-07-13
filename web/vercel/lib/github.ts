/**
 * GitHub as the durable backend (REST Git Data + Contents APIs).
 *
 * Vercel serverless functions are stateless with no persistent filesystem, so
 * every uploaded session — the raw recording, its metadata.json, and any
 * derived report artifacts — is committed to the GitHub repository in a single
 * atomic commit via the Git Data API:
 *
 *   1. GET  ref            -> current branch head SHA
 *   2. GET  commit         -> base tree SHA
 *   3. POST blobs          -> one blob per file (base64)
 *   4. POST trees          -> new tree layered on the base tree
 *   5. POST commits        -> new commit pointing at the new tree
 *   6. PATCH ref           -> fast-forward the branch to the new commit
 *
 * Reads (catalog, session detail, artifact download) use the Contents API.
 *
 * Security:
 *   - The token is read from `GITHUB_TOKEN` (server-only). It is never returned
 *     to the client, embedded in responses, or logged.
 *   - Raw file *contents* are never logged.
 *   - The API fails clearly with a typed error if `GITHUB_TOKEN` is absent.
 */

export class GitHubConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'GitHubConfigError';
  }
}

export class GitHubApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'GitHubApiError';
    this.status = status;
  }
}

export interface GitHubConfig {
  token: string;
  owner: string;
  repo: string;
  branch: string;
  apiBase: string;
}

/**
 * Resolve GitHub configuration from environment. Throws `GitHubConfigError`
 * when the token is missing so callers can surface a clear 503.
 */
export function resolveGitHubConfig(): GitHubConfig {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    throw new GitHubConfigError(
      'GITHUB_TOKEN is not configured. Add a fine-grained GitHub token with ' +
        'Contents: Read and write to the Vercel project environment variables.',
    );
  }
  return {
    token,
    owner: process.env.GITHUB_OWNER || 'JeremyGracey-AI',
    repo: process.env.GITHUB_REPO || 'nexus-neuromirror',
    branch: process.env.GITHUB_BRANCH || 'master',
    apiBase: process.env.GITHUB_API_BASE || 'https://api.github.com',
  };
}

/** Whether a token is present (used for status endpoints without leaking it). */
export function hasToken(): boolean {
  return !!process.env.GITHUB_TOKEN;
}

export function repoEnv(): { owner: string; repo: string; branch: string } {
  return {
    owner: process.env.GITHUB_OWNER || 'JeremyGracey-AI',
    repo: process.env.GITHUB_REPO || 'nexus-neuromirror',
    branch: process.env.GITHUB_BRANCH || 'master',
  };
}

export function commitUrl(cfg: { owner: string; repo: string }, sha: string): string {
  return `https://github.com/${cfg.owner}/${cfg.repo}/commit/${sha}`;
}

type FetchLike = typeof fetch;

export class GitHubClient {
  private cfg: GitHubConfig;
  private fetchImpl: FetchLike;

  constructor(cfg: GitHubConfig, fetchImpl: FetchLike = fetch) {
    this.cfg = cfg;
    this.fetchImpl = fetchImpl;
  }

  static fromEnv(fetchImpl: FetchLike = fetch): GitHubClient {
    return new GitHubClient(resolveGitHubConfig(), fetchImpl);
  }

  get config(): GitHubConfig {
    return this.cfg;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const url = path.startsWith('http') ? path : `${this.cfg.apiBase}${path}`;
    const res = await this.fetchImpl(url, {
      method,
      headers: {
        Authorization: `Bearer ${this.cfg.token}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
        'User-Agent': 'nexus-neuromirror-dashboard',
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!res.ok) {
      // Never include the request body (which may contain file content) in the
      // error. Only echo the GitHub status message.
      let detail = '';
      try {
        const j = (await res.json()) as { message?: string };
        detail = j?.message ? `: ${j.message}` : '';
      } catch {
        detail = '';
      }
      throw new GitHubApiError(`GitHub ${method} ${path} failed (${res.status})${detail}`, res.status);
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }

  private repoPath(suffix: string): string {
    return `/repos/${this.cfg.owner}/${this.cfg.repo}${suffix}`;
  }

  // --- Reads ---------------------------------------------------------------

  /** Read a file's decoded bytes and metadata via the Contents API. */
  async getFileContent(
    repoPath: string,
  ): Promise<{ bytes: Uint8Array; sha: string } | null> {
    try {
      const data = await this.request<{
        content?: string;
        encoding?: string;
        sha: string;
        type: string;
      }>('GET', this.repoPath(`/contents/${encodeContentsPath(repoPath)}?ref=${this.cfg.branch}`));
      if (data.type !== 'file' || data.content === undefined) return null;
      const bytes = Buffer.from(data.content, (data.encoding as BufferEncoding) || 'base64');
      return { bytes: new Uint8Array(bytes), sha: data.sha };
    } catch (err) {
      if (err instanceof GitHubApiError && err.status === 404) return null;
      throw err;
    }
  }

  async getFileText(repoPath: string): Promise<string | null> {
    const f = await this.getFileContent(repoPath);
    return f ? Buffer.from(f.bytes).toString('utf-8') : null;
  }

  /** List directory entries via the Contents API (non-recursive). */
  async listDir(
    repoPath: string,
  ): Promise<{ name: string; path: string; type: string }[]> {
    try {
      const data = await this.request<
        { name: string; path: string; type: string }[]
      >('GET', this.repoPath(`/contents/${encodeContentsPath(repoPath)}?ref=${this.cfg.branch}`));
      return Array.isArray(data) ? data : [];
    } catch (err) {
      if (err instanceof GitHubApiError && err.status === 404) return [];
      throw err;
    }
  }

  /**
   * Recursively find all metadata.json paths under a base dir using the Git
   * Trees API (one request for the whole tree, filtered client-side).
   */
  async findMetadataPaths(baseDir: string): Promise<string[]> {
    const ref = await this.getRef();
    if (!ref) return [];
    const commit = await this.getCommit(ref.sha);
    const tree = await this.request<{
      tree: { path: string; type: string }[];
      truncated: boolean;
    }>('GET', this.repoPath(`/git/trees/${commit.treeSha}?recursive=1`));
    const prefix = baseDir.endsWith('/') ? baseDir : `${baseDir}/`;
    return tree.tree
      .filter((t) => t.type === 'blob' && t.path.startsWith(prefix) && t.path.endsWith('/metadata.json'))
      .map((t) => t.path);
  }

  // --- Git Data (atomic multi-file commit) ---------------------------------

  async getRef(): Promise<{ sha: string } | null> {
    try {
      const data = await this.request<{ object: { sha: string } }>(
        'GET',
        this.repoPath(`/git/ref/heads/${this.cfg.branch}`),
      );
      return { sha: data.object.sha };
    } catch (err) {
      if (err instanceof GitHubApiError && err.status === 404) return null;
      throw err;
    }
  }

  async getCommit(sha: string): Promise<{ treeSha: string }> {
    const data = await this.request<{ tree: { sha: string } }>(
      'GET',
      this.repoPath(`/git/commits/${sha}`),
    );
    return { treeSha: data.tree.sha };
  }

  async createBlob(bytes: Uint8Array): Promise<string> {
    const content = Buffer.from(bytes).toString('base64');
    const data = await this.request<{ sha: string }>('POST', this.repoPath('/git/blobs'), {
      content,
      encoding: 'base64',
    });
    return data.sha;
  }

  async createTree(
    baseTreeSha: string,
    entries: { path: string; sha: string }[],
  ): Promise<string> {
    const data = await this.request<{ sha: string }>('POST', this.repoPath('/git/trees'), {
      base_tree: baseTreeSha,
      tree: entries.map((e) => ({ path: e.path, mode: '100644', type: 'blob', sha: e.sha })),
    });
    return data.sha;
  }

  async createCommit(
    message: string,
    treeSha: string,
    parents: string[],
    author: { name: string; email: string },
  ): Promise<string> {
    const data = await this.request<{ sha: string }>('POST', this.repoPath('/git/commits'), {
      message,
      tree: treeSha,
      parents,
      author: { name: author.name, email: author.email, date: new Date().toISOString() },
    });
    return data.sha;
  }

  async updateRef(sha: string): Promise<void> {
    await this.request('PATCH', this.repoPath(`/git/refs/heads/${this.cfg.branch}`), {
      sha,
      force: false,
    });
  }

  /**
   * Commit multiple files atomically. Returns the new commit SHA and URL.
   * Files are `{ path, bytes }` repo-relative paths. Never logs contents.
   */
  async commitFiles(
    files: { path: string; bytes: Uint8Array }[],
    message: string,
    author: { name: string; email: string },
  ): Promise<{ sha: string; url: string }> {
    const ref = await this.getRef();
    if (!ref) {
      throw new GitHubApiError(
        `Branch '${this.cfg.branch}' not found in ${this.cfg.owner}/${this.cfg.repo}.`,
        404,
      );
    }
    const base = await this.getCommit(ref.sha);
    const entries: { path: string; sha: string }[] = [];
    for (const f of files) {
      const blobSha = await this.createBlob(f.bytes);
      entries.push({ path: f.path, sha: blobSha });
    }
    const treeSha = await this.createTree(base.treeSha, entries);
    const commitSha = await this.createCommit(message, treeSha, [ref.sha], author);
    await this.updateRef(commitSha);
    return { sha: commitSha, url: commitUrl(this.cfg, commitSha) };
  }

  /** Lightweight read-only reachability check (does not mutate anything). */
  async canReach(): Promise<boolean> {
    try {
      await this.request('GET', this.repoPath(''));
      return true;
    } catch {
      return false;
    }
  }
}

/** Encode a repo path for the Contents API, preserving slashes. */
function encodeContentsPath(p: string): string {
  return p
    .split('/')
    .map((seg) => encodeURIComponent(seg))
    .join('/');
}
