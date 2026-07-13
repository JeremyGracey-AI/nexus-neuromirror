import { maxUploadBytes } from '../lib/config.js';
import {
  GitHubClient,
  GitHubConfigError,
  resolveGitHubConfig,
} from '../lib/github.js';
import { parseSingleFile, MultipartError } from '../lib/multipart.js';
import {
  sanitizeFilename,
  validateExtension,
  validateSize,
  sha256OfBytes,
  UploadValidationError,
} from '../lib/security.js';
import { buildSession, GIT_AUTHOR, type GitStatus } from '../lib/store.js';
import {
  methodNotAllowed,
  readRawBody,
  sendJson,
  type VercelReq,
  type VercelRes,
} from '../lib/http.js';

// Disable Vercel's automatic body parser so we can read the raw multipart body.
export const config = { api: { bodyParser: false } };

/**
 * Accept one uploaded recording, validate it, run EDF analysis (for .edf), and
 * commit the raw file + metadata + any report atomically to GitHub.
 *
 * Fails clearly (503) if GITHUB_TOKEN is absent — the API never silently drops
 * an upload. Never logs raw file contents.
 */
export default async function handler(req: VercelReq, res: VercelRes): Promise<void> {
  if (req.method !== 'POST') return methodNotAllowed(res, ['POST']);

  // Fail fast if the durable backend is not configured.
  let ghConfig;
  try {
    ghConfig = resolveGitHubConfig();
  } catch (err) {
    if (err instanceof GitHubConfigError) {
      sendJson(res, 503, { error: err.message });
      return;
    }
    throw err;
  }

  const max = maxUploadBytes();

  // Read the raw body with a hard cap (defends against oversized requests even
  // before we parse the multipart envelope).
  let body: Buffer;
  try {
    body = await readRawBody(req, max + 64 * 1024); // small envelope allowance
  } catch (err) {
    const msg = err instanceof Error ? err.message : '';
    if (msg === 'PAYLOAD_TOO_LARGE') {
      sendJson(res, 413, {
        error: `Upload exceeds the ${(max / (1024 * 1024)).toFixed(0)} MB limit ` +
          '(Vercel caps serverless request bodies at ~4.5 MB).',
      });
      return;
    }
    sendJson(res, 400, { error: 'Failed to read request body.' });
    return;
  }

  // Parse the single file part.
  let part;
  try {
    const ct = req.headers['content-type'];
    part = parseSingleFile(body, Array.isArray(ct) ? ct[0] : ct);
  } catch (err) {
    const msg = err instanceof MultipartError ? err.message : 'Invalid multipart body.';
    sendJson(res, 400, { error: msg });
    return;
  }

  // Validate filename, extension, and size.
  let safeName: string;
  try {
    safeName = sanitizeFilename(part.filename);
    validateExtension(safeName);
    validateSize(part.data.length, max);
  } catch (err) {
    if (err instanceof UploadValidationError) {
      const status = /limit|exceed/i.test(err.message) ? 413 : 400;
      sendJson(res, status, { error: err.message });
      return;
    }
    throw err;
  }

  // Checksum without logging contents.
  const checksum = sha256OfBytes(part.data);

  // Build the session (runs EDF analysis for .edf).
  const { metadata, files } = buildSession(safeName, part.data, checksum);

  // Commit atomically to GitHub.
  const gitStatus: GitStatus = {
    enabled: true,
    committed: false,
    pushed: false,
    commit_sha: null,
    commit_url: null,
    branch: ghConfig.branch,
    message: '',
    error: null,
    steps: [],
  };

  try {
    const client = new GitHubClient(ghConfig);
    const message =
      `Add session ${metadata.session_id} (${metadata.original_filename}) ` +
      `[${metadata.analysis_mode}]`;
    gitStatus.steps.push('create-blobs', 'create-tree', 'create-commit', 'update-ref');
    const result = await client.commitFiles(files, message, GIT_AUTHOR);
    gitStatus.committed = true;
    gitStatus.pushed = true; // committing via the REST API IS the push.
    gitStatus.commit_sha = result.sha;
    gitStatus.commit_url = result.url;
    gitStatus.message = message;
  } catch (err) {
    gitStatus.error = err instanceof Error ? err.message : 'Commit failed.';
    metadata.git = gitStatus;
    sendJson(res, 502, {
      error: `Upload validated but could not be committed to GitHub: ${gitStatus.error}`,
      metadata,
    });
    return;
  }

  metadata.git = gitStatus;
  sendJson(res, 201, metadata);
}
