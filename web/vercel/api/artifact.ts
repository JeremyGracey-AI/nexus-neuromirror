import { GitHubClient, GitHubConfigError } from '../lib/github.js';
import { isPathSafe } from '../lib/security.js';
import {
  guessContentType,
  methodNotAllowed,
  sendBytes,
  sendJson,
  type VercelReq,
  type VercelRes,
} from '../lib/http.js';

// Only these repo subtrees are downloadable through the artifact endpoint.
const ALLOWED_PREFIXES = ['reports/uploads/', 'data/uploads/', 'reports/diagnostic_demo/'];

/**
 * Stream a stored artifact (report JSON/PNG/SVG or a raw recording) from the
 * GitHub-backed store. Path is strictly validated: no traversal, and only the
 * uploads/reports subtrees are reachable.
 */
export default async function handler(req: VercelReq, res: VercelRes): Promise<void> {
  if (req.method !== 'GET') return methodNotAllowed(res, ['GET']);

  const raw = req.query?.path;
  const path = Array.isArray(raw) ? raw[0] : raw;
  if (!path) {
    sendJson(res, 400, { error: 'Missing artifact path.' });
    return;
  }
  if (!isPathSafe(path) || !ALLOWED_PREFIXES.some((p) => path.startsWith(p))) {
    sendJson(res, 400, { error: 'Invalid or disallowed artifact path.' });
    return;
  }

  try {
    const client = GitHubClient.fromEnv();
    const file = await client.getFileContent(path);
    if (!file) {
      sendJson(res, 404, { error: 'Artifact not found.' });
      return;
    }
    sendBytes(res, 200, file.bytes, guessContentType(path));
  } catch (err) {
    if (err instanceof GitHubConfigError) {
      sendJson(res, 503, { error: err.message });
      return;
    }
    const msg = err instanceof Error ? err.message : 'Failed to load artifact.';
    sendJson(res, 502, { error: msg });
  }
}
