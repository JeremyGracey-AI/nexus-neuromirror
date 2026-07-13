import { describe, it, expect } from 'vitest';
import {
  sanitizeFilename,
  validateExtension,
  validateSize,
  sha256OfBytes,
  isPathSafe,
  classifyExtension,
  extensionOf,
  UploadValidationError,
} from '../lib/security.js';

describe('sanitizeFilename', () => {
  it('strips POSIX and Windows directory components (traversal defense)', () => {
    expect(sanitizeFilename('../../etc/passwd')).toBe('passwd');
    expect(sanitizeFilename('..\\..\\windows\\system32\\x.edf')).toBe('x.edf');
    expect(sanitizeFilename('/abs/path/rec.edf')).toBe('rec.edf');
  });

  it('collapses repeated dots so traversal cannot be reintroduced', () => {
    // After stripping dirs, "a..edf" would collapse to "a.edf".
    expect(sanitizeFilename('a..edf')).toBe('a.edf');
  });

  it('replaces disallowed characters', () => {
    expect(sanitizeFilename('my file (1)!.edf')).toBe('my_file_1_.edf');
  });

  it('drops non-ASCII after NFKD normalization', () => {
    // NFKD decomposes accented letters to base + combining mark, then the
    // combining marks (non-ASCII) are dropped: 'é' -> 'e', 'ç' -> 'c'.
    expect(sanitizeFilename('résumé.edf')).toBe('resume.edf');
    // Characters with no ASCII decomposition (e.g. 'ø') are removed entirely,
    // which is the safe outcome.
    expect(sanitizeFilename('naïve.edf')).toBe('naive.edf');
  });

  it('rejects empty results', () => {
    expect(() => sanitizeFilename('...')).toThrow(UploadValidationError);
    expect(() => sanitizeFilename('/')).toThrow(UploadValidationError);
    expect(() => sanitizeFilename(null)).toThrow(UploadValidationError);
  });

  it('caps length while preserving extension', () => {
    const long = 'x'.repeat(300) + '.edf';
    const out = sanitizeFilename(long);
    expect(out.length).toBeLessThanOrEqual(128);
    expect(out.endsWith('.edf')).toBe(true);
  });
});

describe('isPathSafe', () => {
  it('rejects traversal and absolute paths', () => {
    expect(isPathSafe('reports/uploads/x/diagnostic.json')).toBe(true);
    expect(isPathSafe('../secret')).toBe(false);
    expect(isPathSafe('/etc/passwd')).toBe(false);
    expect(isPathSafe('a/../../b')).toBe(false);
    expect(isPathSafe('')).toBe(false);
  });
});

describe('extension handling', () => {
  it('extracts lowercased extensions', () => {
    expect(extensionOf('REC.EDF')).toBe('.edf');
    expect(extensionOf('noext')).toBe('');
  });

  it('validates against the allow-list', () => {
    for (const ok of ['a.edf', 'a.csv', 'a.txt', 'a.asc', 'a.mat', 'a.bcd']) {
      expect(validateExtension(ok)).toBe(extensionOf(ok));
    }
    expect(() => validateExtension('a.exe')).toThrow(UploadValidationError);
    expect(() => validateExtension('a')).toThrow(UploadValidationError);
  });

  it('classifies analysis modes', () => {
    expect(classifyExtension('.edf')).toBe('analyze');
    expect(classifyExtension('.csv')).toBe('catalog-only');
    expect(classifyExtension('.mat')).toBe('catalog-only');
    expect(classifyExtension('.bcd')).toBe('archival-only');
    expect(classifyExtension('.zzz')).toBe('unsupported');
  });
});

describe('validateSize', () => {
  it('rejects empty and oversized uploads', () => {
    expect(() => validateSize(0, 1000)).toThrow(UploadValidationError);
    expect(() => validateSize(-5, 1000)).toThrow(UploadValidationError);
    expect(() => validateSize(2000, 1000)).toThrow(UploadValidationError);
    expect(() => validateSize(500, 1000)).not.toThrow();
  });
});

describe('sha256OfBytes', () => {
  it('computes a stable hex digest', () => {
    const digest = sha256OfBytes(new TextEncoder().encode('hello'));
    expect(digest).toBe('2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824');
  });
});
