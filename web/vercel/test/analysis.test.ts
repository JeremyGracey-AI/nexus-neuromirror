import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { analyzeEdfBuffer } from '../lib/analysis.js';
import { parseEdf } from '../lib/edf.js';

const fixture = new Uint8Array(
  readFileSync(fileURLToPath(new URL('./fixtures/nnm_demo.edf', import.meta.url))),
);
const ref = JSON.parse(
  readFileSync(
    fileURLToPath(new URL('../../../reports/diagnostic_demo/diagnostic.json', import.meta.url)),
    'utf-8',
  ),
);

describe('EDF parser', () => {
  const edf = parseEdf(fixture);

  it('reads header metadata', () => {
    expect(edf.channelNames).toEqual([
      'EEG Fz-A1A2',
      'EEG FCz-A1A2',
      'EEG Pz-A1A2',
      'EEG Oz-A1A2',
      'Status',
    ]);
    expect(edf.sfreqHz).toBe(256);
    expect(edf.durationS).toBe(60);
    expect(edf.nSamplesPerChannel).toBe(15360);
    expect(edf.isEdfPlus).toBe(true);
  });

  it('parses EDF+ annotations (TAL)', () => {
    const labels = edf.annotations.flatMap((a) => a.labels);
    expect(labels).toContain('cue/block-A');
    expect(labels).toContain('cue/block-B');
  });

  it('rejects a too-small buffer', () => {
    expect(() => parseEdf(new Uint8Array(10))).toThrow();
  });
});

describe('analysis matches the Python reference', () => {
  const { diagnostic, ok, status } = analyzeEdfBuffer(fixture, '/tmp/nnm_demo.edf');

  it('resolves all four expected channels', () => {
    expect(ok).toBe(true);
    expect(status).toBe('ok');
    const found = diagnostic.expected_channels.filter((c) => c.found).length;
    expect(found).toBe(4);
  });

  it('reproduces channel metrics within 0.001 uV', () => {
    for (let i = 0; i < 4; i++) {
      const a = diagnostic.expected_channels[i].metrics!;
      const b = ref.expected_channels[i].metrics;
      for (const k of Object.keys(b) as (keyof typeof b)[]) {
        expect(Math.abs((a as any)[k] - b[k])).toBeLessThanOrEqual(0.001);
      }
    }
  });

  it('reproduces markers exactly', () => {
    expect(diagnostic.markers.n_events).toBe(ref.markers.n_events);
    expect(diagnostic.markers.n_annotation_events).toBe(ref.markers.n_annotation_events);
    expect(diagnostic.markers.n_channel_events).toBe(ref.markers.n_channel_events);
    expect(diagnostic.markers.distinct_labels).toEqual(ref.markers.distinct_labels);
    expect(diagnostic.markers.candidate_marker_channels).toEqual(
      ref.markers.candidate_marker_channels,
    );
    expect(diagnostic.markers.events).toEqual(ref.markers.events);
  });

  it('matches recording summary fields', () => {
    expect(diagnostic.recording.n_channels).toBe(ref.recording.n_channels);
    expect(diagnostic.recording.channel_names).toEqual(ref.recording.channel_names);
    expect(diagnostic.recording.sfreq_hz).toBe(ref.recording.sfreq_hz);
    expect(diagnostic.recording.n_samples).toBe(ref.recording.n_samples);
    expect(diagnostic.recording.duration_s).toBe(ref.recording.duration_s);
    expect(diagnostic.recording.n_annotations).toBe(ref.recording.n_annotations);
    expect(diagnostic.recording.meas_date).toBe(ref.recording.meas_date);
  });
});
