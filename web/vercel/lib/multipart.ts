/**
 * Minimal multipart/form-data parser for a single file field.
 *
 * The dashboard uploads exactly one file under the field name "file". A full
 * multipart library is unnecessary and would add serverless bundle weight, so
 * this extracts the first file part directly from the raw body buffer.
 *
 * It is defensive: it validates the boundary, bounds all indexing, and never
 * logs or echoes file contents.
 */

export interface ParsedFile {
  fieldName: string;
  filename: string;
  contentType: string;
  data: Uint8Array;
}

export class MultipartError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'MultipartError';
  }
}

function getBoundary(contentType: string | undefined): string {
  if (!contentType) throw new MultipartError('Missing Content-Type header.');
  const m = contentType.match(/boundary=(?:"([^"]+)"|([^;]+))/i);
  const boundary = (m && (m[1] || m[2]))?.trim();
  if (!boundary) throw new MultipartError('Missing multipart boundary.');
  return boundary;
}

function indexOf(haystack: Buffer, needle: Buffer, from: number): number {
  return haystack.indexOf(needle, from);
}

/** Parse the first file part from a multipart/form-data body. */
export function parseSingleFile(
  body: Buffer,
  contentType: string | undefined,
): ParsedFile {
  const boundary = getBoundary(contentType);
  const delimiter = Buffer.from(`--${boundary}`);
  const CRLFCRLF = Buffer.from('\r\n\r\n');
  const CRLF = Buffer.from('\r\n');

  let pos = indexOf(body, delimiter, 0);
  if (pos === -1) throw new MultipartError('Multipart boundary not found in body.');

  while (pos !== -1) {
    // Move past the delimiter.
    let partStart = pos + delimiter.length;
    // End marker "--" indicates the last boundary.
    if (body.slice(partStart, partStart + 2).toString() === '--') break;
    // Skip the CRLF after the boundary.
    if (body.slice(partStart, partStart + 2).equals(CRLF)) partStart += 2;

    const headerEnd = indexOf(body, CRLFCRLF, partStart);
    if (headerEnd === -1) break;
    const headerBlock = body.slice(partStart, headerEnd).toString('utf-8');
    const contentStart = headerEnd + CRLFCRLF.length;

    const nextBoundary = indexOf(body, delimiter, contentStart);
    if (nextBoundary === -1) break;
    // Content is up to the CRLF preceding the next boundary.
    let contentEnd = nextBoundary;
    if (body.slice(contentEnd - 2, contentEnd).equals(CRLF)) contentEnd -= 2;

    const dispMatch = headerBlock.match(/content-disposition:\s*form-data;([^\r\n]*)/i);
    if (dispMatch) {
      const disp = dispMatch[1];
      const nameMatch = disp.match(/name="([^"]*)"/i);
      const filenameMatch = disp.match(/filename="([^"]*)"/i);
      const ctMatch = headerBlock.match(/content-type:\s*([^\r\n]+)/i);
      if (filenameMatch) {
        return {
          fieldName: nameMatch ? nameMatch[1] : '',
          filename: filenameMatch[1],
          contentType: ctMatch ? ctMatch[1].trim() : 'application/octet-stream',
          data: new Uint8Array(body.slice(contentStart, contentEnd)),
        };
      }
    }
    pos = nextBoundary;
  }

  throw new MultipartError('No file part found in multipart body.');
}
