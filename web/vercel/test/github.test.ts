import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  GitHubClient,
  GitHubConfigError,
  resolveGitHubConfig,
  hasToken,
} from '../lib/github.js';

const cfg = {
  token: 'test-token',
  owner: 'JeremyGracey-AI',
  repo: 'nexus-neuromirror',
  branch: 'master',
  apiBase: 'https://api.github.com',
};

/** Build a mock fetch that records requests and returns scripted responses. */
function mockGitHub() {
  const calls: { method: string; url: string; body: any }[] = [];
  const authHeaders: (string | undefined)[] = [];
  const fetchImpl = vi.fn(async (url: string, init: any) => {
    const method = init?.method ?? 'GET';
    const body = init?.body ? JSON.parse(init.body) : undefined;
    calls.push({ method, url, body });
    authHeaders.push(init?.headers?.Authorization);

    const json = (obj: unknown, status = 200) =>
      ({ ok: status < 400, status, json: async () => obj } as unknown as Response);

    if (url.endsWith('/git/ref/heads/master')) return json({ object: { sha: 'BASECOMMIT' } });
    if (url.includes('/git/commits/BASECOMMIT')) return json({ tree: { sha: 'BASETREE' } });
    if (url.endsWith('/git/blobs')) return json({ sha: `blob-${calls.length}` }, 201);
    if (url.endsWith('/git/trees')) return json({ sha: 'NEWTREE' }, 201);
    if (url.endsWith('/git/commits')) return json({ sha: 'NEWCOMMIT' }, 201);
    if (url.endsWith('/git/refs/heads/master')) return json({}, 200);
    return json({ message: 'unexpected' }, 404);
  });
  return { fetchImpl, calls, authHeaders };
}

describe('resolveGitHubConfig', () => {
  const OLD = process.env.GITHUB_TOKEN;
  afterEach(() => {
    if (OLD === undefined) delete process.env.GITHUB_TOKEN;
    else process.env.GITHUB_TOKEN = OLD;
  });

  it('throws a clear error when GITHUB_TOKEN is absent', () => {
    delete process.env.GITHUB_TOKEN;
    expect(hasToken()).toBe(false);
    expect(() => resolveGitHubConfig()).toThrow(GitHubConfigError);
  });

  it('defaults owner/repo/branch', () => {
    process.env.GITHUB_TOKEN = 'abc';
    delete process.env.GITHUB_OWNER;
    delete process.env.GITHUB_REPO;
    delete process.env.GITHUB_BRANCH;
    const c = resolveGitHubConfig();
    expect(c.owner).toBe('JeremyGracey-AI');
    expect(c.repo).toBe('nexus-neuromirror');
    expect(c.branch).toBe('master');
  });
});

describe('atomic commitFiles', () => {
  it('performs the ref->commit->blobs->tree->commit->ref sequence', async () => {
    const { fetchImpl, calls, authHeaders } = mockGitHub();
    const client = new GitHubClient(cfg, fetchImpl as unknown as typeof fetch);
    const files = [
      { path: 'data/uploads/2026-07-13/abc/rec.edf', bytes: new Uint8Array([1, 2, 3]) },
      { path: 'data/uploads/2026-07-13/abc/metadata.json', bytes: new TextEncoder().encode('{}') },
    ];
    const result = await client.commitFiles(files, 'Add session abc', {
      name: 'Bot',
      email: 'bot@example.com',
    });

    expect(result.sha).toBe('NEWCOMMIT');
    expect(result.url).toBe(
      'https://github.com/JeremyGracey-AI/nexus-neuromirror/commit/NEWCOMMIT',
    );

    const methodsUrls = calls.map((c) => `${c.method} ${c.url.split('/repos/')[1]}`);
    expect(methodsUrls).toEqual([
      'GET JeremyGracey-AI/nexus-neuromirror/git/ref/heads/master',
      'GET JeremyGracey-AI/nexus-neuromirror/git/commits/BASECOMMIT',
      'POST JeremyGracey-AI/nexus-neuromirror/git/blobs',
      'POST JeremyGracey-AI/nexus-neuromirror/git/blobs',
      'POST JeremyGracey-AI/nexus-neuromirror/git/trees',
      'POST JeremyGracey-AI/nexus-neuromirror/git/commits',
      'PATCH JeremyGracey-AI/nexus-neuromirror/git/refs/heads/master',
    ]);

    // Tree layered on the base tree with two blob entries.
    const treeCall = calls.find((c) => c.url.endsWith('/git/trees'))!;
    expect(treeCall.body.base_tree).toBe('BASETREE');
    expect(treeCall.body.tree).toHaveLength(2);
    expect(treeCall.body.tree[0]).toMatchObject({ mode: '100644', type: 'blob' });

    // Every request authenticated with the bearer token.
    expect(authHeaders.every((h) => h === 'Bearer test-token')).toBe(true);
  });

  it('never embeds raw file bytes in the tree request (only blob shas)', async () => {
    const { fetchImpl, calls } = mockGitHub();
    const client = new GitHubClient(cfg, fetchImpl as unknown as typeof fetch);
    await client.commitFiles(
      [{ path: 'data/uploads/x/secret.edf', bytes: new Uint8Array([9, 9, 9]) }],
      'msg',
      { name: 'B', email: 'b@e.com' },
    );
    const treeCall = calls.find((c) => c.url.endsWith('/git/trees'))!;
    for (const entry of treeCall.body.tree) {
      expect(entry).not.toHaveProperty('content');
      expect(entry.sha).toMatch(/^blob-/);
    }
  });
});
