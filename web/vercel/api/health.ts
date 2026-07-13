import { ALLOWED_EXTENSIONS, FORMAT_LABELS, maxUploadBytes } from '../lib/config.js';
import { classifyExtension } from '../lib/security.js';
import { hasToken } from '../lib/github.js';
import { methodNotAllowed, sendJson, type VercelReq, type VercelRes } from '../lib/http.js';

export const VERSION = '0.2.0';

export default function handler(req: VercelReq, res: VercelRes): void {
  if (req.method !== 'GET') return methodNotAllowed(res, ['GET']);
  const max = maxUploadBytes();
  sendJson(res, 200, {
    status: 'ok',
    version: VERSION,
    // "config_available" now reflects whether the durable GitHub backend can
    // be reached at all (token present). The analysis config is bundled.
    config_available: hasToken(),
    max_upload_bytes: max,
    max_upload_mb: Math.round((max / (1024 * 1024)) * 10) / 10,
    accepted_formats: [...ALLOWED_EXTENSIONS]
      .sort()
      .map((ext) => ({ ext, label: FORMAT_LABELS[ext], mode: classifyExtension(ext) })),
  });
}
