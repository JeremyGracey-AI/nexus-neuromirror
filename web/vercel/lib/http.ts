/**
 * Tiny HTTP helpers for Vercel Node serverless functions.
 *
 * These avoid a framework dependency and keep responses consistent. Vercel
 * passes Node-style (req, res) objects; we type them loosely to avoid coupling
 * to a specific @vercel/node version at build time.
 */

export interface VercelReq {
  method?: string;
  url?: string;
  query?: Record<string, string | string[] | undefined>;
  headers: Record<string, string | string[] | undefined>;
  on(event: string, cb: (chunk?: unknown) => void): void;
}

export interface VercelRes {
  statusCode: number;
  setHeader(name: string, value: string | number): void;
  end(body?: string | Buffer): void;
}

export function sendJson(res: VercelRes, status: number, body: unknown): void {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(body));
}

export function sendBytes(
  res: VercelRes,
  status: number,
  bytes: Uint8Array,
  contentType: string,
): void {
  res.statusCode = status;
  res.setHeader('Content-Type', contentType);
  res.setHeader('Cache-Control', 'no-store');
  res.end(Buffer.from(bytes));
}

export function methodNotAllowed(res: VercelRes, allowed: string[]): void {
  res.setHeader('Allow', allowed.join(', '));
  sendJson(res, 405, { error: `Method not allowed. Allowed: ${allowed.join(', ')}.` });
}

/** Read the raw request body up to `maxBytes`; rejects if exceeded. */
export function readRawBody(req: VercelReq, maxBytes: number): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let total = 0;
    req.on('data', (chunk) => {
      const buf = chunk as Buffer;
      total += buf.length;
      if (total > maxBytes) {
        reject(new Error('PAYLOAD_TOO_LARGE'));
        return;
      }
      chunks.push(buf);
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', () => reject(new Error('REQUEST_STREAM_ERROR')));
  });
}

export function guessContentType(path: string): string {
  const lower = path.toLowerCase();
  if (lower.endsWith('.json')) return 'application/json; charset=utf-8';
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.svg')) return 'image/svg+xml';
  if (lower.endsWith('.csv') || lower.endsWith('.txt') || lower.endsWith('.asc'))
    return 'text/plain; charset=utf-8';
  if (lower.endsWith('.edf') || lower.endsWith('.bcd') || lower.endsWith('.mat'))
    return 'application/octet-stream';
  return 'application/octet-stream';
}
