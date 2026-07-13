import { GitHubClient, GitHubConfigError } from '../../lib/github.js';
import { getSession } from '../../lib/store.js';
import { methodNotAllowed, sendJson, type VercelReq, type VercelRes } from '../../lib/http.js';

/** Fetch a single session's metadata from GitHub by id. */
export default async function handler(req: VercelReq, res: VercelRes): Promise<void> {
  if (req.method !== 'GET') return methodNotAllowed(res, ['GET']);
  const raw = req.query?.id;
  const id = Array.isArray(raw) ? raw[0] : raw;
  if (!id) {
    sendJson(res, 400, { error: 'Missing session id.' });
    return;
  }
  try {
    const client = GitHubClient.fromEnv();
    const session = await getSession(client, id);
    if (!session) {
      sendJson(res, 404, { error: 'Session not found.' });
      return;
    }
    sendJson(res, 200, session);
  } catch (err) {
    if (err instanceof GitHubConfigError) {
      sendJson(res, 503, { error: err.message });
      return;
    }
    const msg = err instanceof Error ? err.message : 'Failed to load session.';
    sendJson(res, 502, { error: msg });
  }
}
