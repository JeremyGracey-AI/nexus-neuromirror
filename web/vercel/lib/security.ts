/**
 * Upload safety primitives (TypeScript port of security.py):
 * filename sanitization, path-traversal rejection, extension allow-listing,
 * size limits, and SHA-256 checksums.
 *
 * Pure and side-effect free so they can be unit tested in isolation. Raw file
 * *contents* are never logged, echoed, or embedded in errors.
 */

import { createHash } from 'node:crypto';
import {
  ALLOWED_EXTENSIONS,
  ANALYZABLE_EXTENSIONS,
  ARCHIVAL_ONLY_EXTENSIONS,
  CATALOG_ONLY_EXTENSIONS,
  FORMAT_LABELS,
} from './config.js';

export class UploadValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'UploadValidationError';
  }
}

const SAFE_CHARS = /[^A-Za-z0-9._-]+/g;
const MULTI_DOT = /\.{2,}/g;

/** Return the final path component regardless of separator style. */
function baseName(name: string): string {
  const normalized = name.replace(/\\/g, '/');
  const parts = normalized.split('/');
  return parts[parts.length - 1] ?? '';
}

/**
 * Return a safe base filename with no directory components.
 * - Strips any path (POSIX and Windows), defeating traversal.
 * - Normalizes Unicode (NFKD) and drops non-ASCII.
 * - Collapses repeated dots so "a..b" cannot re-introduce traversal.
 * - Rejects empty results.
 */
export function sanitizeFilename(rawName: string | null | undefined): string {
  if (rawName == null) {
    throw new UploadValidationError('Missing filename.');
  }
  // Normalize Unicode to a canonical form, then drop non-ASCII.
  let name = rawName.normalize('NFKD').replace(/[^\x00-\x7F]/g, '');
  // Take only the final path component.
  name = baseName(name);
  // Remove control chars and disallowed characters.
  name = name.replace(/\x00/g, '');
  name = name.replace(SAFE_CHARS, '_').replace(/^[._]+|[._]+$/g, '');
  name = name.replace(MULTI_DOT, '.');

  if (!name || name === '.' || name === '..') {
    throw new UploadValidationError('Filename is empty after sanitization.');
  }
  if (name.length > 128) {
    const dot = name.lastIndexOf('.');
    if (dot > 0) {
      const stem = name.slice(0, dot);
      const ext = name.slice(dot + 1);
      name = `${stem.slice(0, 120)}.${ext}`;
    } else {
      name = name.slice(0, 128);
    }
  }
  return name;
}

/** True if `candidate` has no traversal or absolute components. */
export function isPathSafe(candidate: string): boolean {
  if (!candidate) return false;
  const normalized = candidate.replace(/\\/g, '/');
  if (normalized.startsWith('/')) return false;
  const parts = normalized.split('/');
  return !parts.includes('..') && !parts.some((p) => p.startsWith('/'));
}

/** Return the lowercased extension including the leading dot (or ''). */
export function extensionOf(filename: string): string {
  const base = baseName(filename);
  const dot = base.lastIndexOf('.');
  return dot > 0 ? base.slice(dot).toLowerCase() : '';
}

export type AnalysisMode = 'analyze' | 'catalog-only' | 'archival-only' | 'unsupported';

export function classifyExtension(ext: string): AnalysisMode {
  const e = ext.toLowerCase();
  if (ANALYZABLE_EXTENSIONS.has(e)) return 'analyze';
  if (CATALOG_ONLY_EXTENSIONS.has(e)) return 'catalog-only';
  if (ARCHIVAL_ONLY_EXTENSIONS.has(e)) return 'archival-only';
  return 'unsupported';
}

export function formatLabel(ext: string): string {
  return FORMAT_LABELS[ext.toLowerCase()] ?? 'Unknown';
}

/** Validate the extension against the allow-list; return the normalized ext. */
export function validateExtension(filename: string): string {
  const ext = extensionOf(filename);
  if (!ALLOWED_EXTENSIONS.has(ext)) {
    const allowed = [...ALLOWED_EXTENSIONS].sort().join(', ');
    throw new UploadValidationError(
      `Unsupported file type '${ext || '(none)'}'. Allowed: ${allowed}.`,
    );
  }
  return ext;
}

/** Reject empty or oversized uploads. */
export function validateSize(sizeBytes: number, maxBytes: number): void {
  if (sizeBytes <= 0) {
    throw new UploadValidationError('Uploaded file is empty.');
  }
  if (sizeBytes > maxBytes) {
    const mb = maxBytes / (1024 * 1024);
    throw new UploadValidationError(
      `File exceeds the ${mb.toFixed(0)} MB upload limit ` +
        '(Vercel caps serverless request bodies at ~4.5 MB).',
    );
  }
}

/** Compute a hex SHA-256 digest of raw bytes without logging contents. */
export function sha256OfBytes(data: Uint8Array): string {
  return createHash('sha256').update(data).digest('hex');
}
