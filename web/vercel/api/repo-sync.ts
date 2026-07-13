import { hasToken, repoEnv } from '../lib/github.js';
import { methodNotAllowed, sendJson, type VercelReq, type VercelRes } from '../lib/http.js';

/**
 * Report whether the GitHub durable backend is configured. On Vercel there is
 * no local git working copy — GitHub *is* the store — so "ahead" is always 0
 * and every committed upload is immediately durable. This endpoint never leaks
 * the token; it only reports its presence.
 */
export default function handler(req: VercelReq, res: VercelRes): void {
  if (req.method !== 'GET') return methodNotAllowed(res, ['GET']);
  const { owner, repo, branch } = repoEnv();
  const credentials = hasToken();
  sendJson(res, 200, {
    enabled: credentials,
    branch,
    remote: `${owner}/${repo}`,
    remote_url: `https://github.com/${owner}/${repo}`,
    credentials_available: credentials,
    ahead: 0,
    note: credentials
      ? 'Uploads are committed directly to GitHub via the REST API; each is durable on commit.'
      : 'GITHUB_TOKEN is not configured. Uploads are disabled until a token is added in Vercel settings.',
  });
}
