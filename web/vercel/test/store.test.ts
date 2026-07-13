import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { buildSession } from '../lib/store.js';
import { sha256OfBytes } from '../lib/security.js';

const fixture = new Uint8Array(
  readFileSync(fileURLToPath(new URL('./fixtures/nnm_demo.edf', import.meta.url))),
);

describe('buildSession', () => {
  it('produces metadata + files for an analyzable EDF', () => {
    const checksum = sha256OfBytes(fixture);
    const { metadata, files } = buildSession('nnm_demo.edf', fixture, checksum);

    expect(metadata.extension).toBe('.edf');
    expect(metadata.analysis_mode).toBe('analyze');
    expect(metadata.format_label).toBe('EDF/EDF+');
    expect(metadata.sha256).toBe(checksum);
    expect(metadata.analysis_status).toBe('ok');
    expect(metadata.analysis?.expected_channels.filter((c) => c.found)).toHaveLength(4);

    // Files to commit: raw recording, diagnostic report, metadata.json.
    const paths = files.map((f) => f.path);
    expect(paths.some((p) => p.endsWith('/nnm_demo.edf'))).toBe(true);
    expect(paths.some((p) => p.endsWith('/diagnostic.json'))).toBe(true);
    expect(paths.some((p) => p.endsWith('/metadata.json'))).toBe(true);
    expect(paths.every((p) => p.startsWith('data/uploads/') || p.startsWith('reports/uploads/'))).toBe(true);
  });

  it('marks non-EDF formats as catalog/archival only (no analysis)', () => {
    const data = new TextEncoder().encode('a,b,c\n1,2,3\n');
    const csv = buildSession('table.csv', data, sha256OfBytes(data));
    expect(csv.metadata.analysis_mode).toBe('catalog-only');
    expect(csv.metadata.analysis_status).toBe('not-applicable');
    expect(csv.files.map((f) => f.path).some((p) => p.endsWith('/diagnostic.json'))).toBe(false);

    const bcdData = new Uint8Array([0, 1, 2]);
    const bcd = buildSession('archive.bcd', bcdData, sha256OfBytes(bcdData));
    expect(bcd.metadata.analysis_mode).toBe('archival-only');
  });
});
