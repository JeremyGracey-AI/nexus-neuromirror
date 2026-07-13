import { DEMO_ARTIFACTS, DEMO_DIAGNOSTIC } from '../lib/demo.js';
import { methodNotAllowed, sendJson, type VercelReq, type VercelRes } from '../lib/http.js';

/**
 * Serve the bundled synthetic demo diagnostic + artifact paths. This requires
 * no GitHub access and works even before a token is configured, so the Overview
 * page always renders. The artifacts themselves are static files served from
 * the deployed frontend under /reports/diagnostic_demo/.
 */
export default function handler(req: VercelReq, res: VercelRes): void {
  if (req.method !== 'GET') return methodNotAllowed(res, ['GET']);
  sendJson(res, 200, {
    diagnostic: DEMO_DIAGNOSTIC,
    artifacts: DEMO_ARTIFACTS,
  });
}
