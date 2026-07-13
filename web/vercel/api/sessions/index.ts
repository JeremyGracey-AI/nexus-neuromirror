import { GitHubClient, GitHubConfigError } from '../../lib/github.js';
import { listSessions } from '../../lib/store.js';
import { methodNotAllowed, sendJson, type VercelReq, type VercelRes } from '../../lib/http.js';

/** List all sessions from the GitHub-backed catalog (newest first). */
export default async function handler(req: VercelReq, res: VercelRes): Promise<void> {
  if (req.method !== 'GET') return methodNotAllowed(res, ['GET']);
  try {
    const client = GitHubClient.fromEnv();
    const sessions = await listSessions(client);
    sendJson(res, 200, { sessions });
  } catch (err) {
    if (err instanceof GitHubConfigError) {
      sendJson(res, 503, { error: err.message, sessions: [] });
      return;
    }
    const msg = err instanceof Error ? err.message : 'Failed to list sessions.';
    sendJson(res, 502, { error: msg, sessions: [] });
  }
}
