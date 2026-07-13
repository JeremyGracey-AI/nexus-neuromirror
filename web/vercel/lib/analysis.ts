/**
 * EDF analysis (TypeScript port of the Python verify/metrics/markers pipeline).
 *
 * Produces:
 *  - a full diagnostic payload (same shape as reports/diagnostic_demo/diagnostic.json),
 *  - a compact `AnalysisSummary` for the dashboard,
 *  - soft warnings and hard failures from the validation gate.
 *
 * This is a first-prototype analysis of the four expected channels
 * (Fz / FCz / Pz / Oz) plus marker/event detection. It is deliberately
 * lightweight (no filtering, no PSD) so it runs within Vercel serverless limits.
 * It is not a medical or diagnostic tool.
 */

import { CONFIG, type AnalysisConfig } from './config.js';
import { parseEdf, type EdfFile } from './edf.js';
import { containsToken, findChannel, matchAlias } from './labels.js';

export interface ChannelMetrics {
  rms_uv: number;
  ptp_uv: number;
  max_abs_uv: number;
  mean_uv: number;
}

export interface ExpectedChannelResult {
  canonical: string;
  matched_name: string | null;
  found: boolean;
  metrics: ChannelMetrics | null;
}

export interface MarkerEvent {
  onset_s: number;
  label: string;
  source: string;
}

function round(n: number, dp: number): number {
  const f = 10 ** dp;
  return Math.round(n * f) / f;
}

function computeMetrics(uv: Float64Array): ChannelMetrics {
  if (uv.length === 0) {
    return { rms_uv: 0, ptp_uv: 0, max_abs_uv: 0, mean_uv: 0 };
  }
  let sumSq = 0;
  let sum = 0;
  let min = Infinity;
  let max = -Infinity;
  let maxAbs = 0;
  for (let i = 0; i < uv.length; i++) {
    const v = uv[i];
    sumSq += v * v;
    sum += v;
    if (v < min) min = v;
    if (v > max) max = v;
    const a = Math.abs(v);
    if (a > maxAbs) maxAbs = a;
  }
  const n = uv.length;
  return {
    rms_uv: round(Math.sqrt(sumSq / n), 4),
    ptp_uv: round(max - min, 4),
    max_abs_uv: round(maxAbs, 4),
    mean_uv: round(sum / n, 4),
  };
}

// --- Marker detection --------------------------------------------------------

function annotationEvents(edf: EdfFile, cfg: AnalysisConfig): MarkerEvent[] {
  const events: MarkerEvent[] = [];
  for (const ann of edf.annotations) {
    for (const label of ann.labels) {
      events.push({ onset_s: round(ann.onsetS, 4), label, source: 'annotation' });
    }
  }
  // Prefer marker-looking annotations if aliases are configured, but never drop
  // everything.
  if (cfg.markers.annotationAliases.length) {
    const filtered = events.filter((e) =>
      containsToken(e.label, cfg.markers.annotationAliases),
    );
    if (filtered.length) return filtered;
  }
  return events;
}

function candidateMarkerChannels(edf: EdfFile, cfg: AnalysisConfig): string[] {
  const out: string[] = [];
  for (const name of edf.channelNames) {
    if (
      matchAlias(name, cfg.markers.channelAliases) ||
      containsToken(name, cfg.markers.channelAliases)
    ) {
      out.push(name);
    }
  }
  return out;
}

function channelEvents(edf: EdfFile, channel: string): MarkerEvent[] {
  // Marker/status channels carry integer codes; a raw-code read is cleaner than
  // the microvolt-scaled read. Reconstruct nominal codes from physical values:
  // for a status channel physical == digital typically, so rounding the uV read
  // back through its own scaling would distort. We read the physical value and
  // round to the nearest integer, matching the Python `np.rint` behavior on the
  // already-physical MNE data (Status channels are dimensionless counts).
  const uv = edf.readChannelUv(channel);
  const sfreq = edf.sfreqHz;
  const events: MarkerEvent[] = [];
  let prev = 0;
  for (let i = 0; i < uv.length; i++) {
    const code = Math.round(uv[i]);
    if (code !== prev && code !== 0) {
      events.push({ onset_s: round(i / sfreq, 4), label: `code:${code}`, source: channel });
    }
    prev = code;
  }
  return events;
}

// --- Full analysis -----------------------------------------------------------

export interface DiagnosticPayload {
  status: string;
  config_name: string;
  unit_assumption: string;
  recording: {
    path: string;
    n_channels: number;
    channel_names: string[];
    sfreq_hz: number;
    n_samples: number;
    duration_s: number;
    n_annotations: number;
    highpass_hz: number | null;
    lowpass_hz: number | null;
    meas_date: string | null;
  };
  expected_channels: ExpectedChannelResult[];
  other_channels: { name: string; metrics: ChannelMetrics }[];
  markers: {
    n_events: number;
    n_annotation_events: number;
    n_channel_events: number;
    candidate_marker_channels: string[];
    distinct_labels: string[];
    events: MarkerEvent[];
  };
  hard_failures: string[];
  warnings: string[];
}

export interface AnalysisSummary {
  status: string;
  config_name: string;
  unit_assumption: string;
  recording: {
    n_channels: number | null;
    channel_names: string[];
    sfreq_hz: number | null;
    duration_s: number | null;
    n_samples: number | null;
    n_annotations: number | null;
    highpass_hz: number | null;
    lowpass_hz: number | null;
    meas_date: string | null;
  };
  expected_channels: ExpectedChannelResult[];
  markers: {
    n_events: number | null;
    distinct_labels: string[];
    candidate_marker_channels: string[];
    events: MarkerEvent[];
  };
}

export interface AnalysisResult {
  ok: boolean;
  status: 'ok' | 'failed';
  diagnostic: DiagnosticPayload;
  summary: AnalysisSummary;
  warnings: string[];
  hard_failures: string[];
}

function classifyOtherChannels(
  allNames: string[],
  matched: Set<string>,
  cfg: AnalysisConfig,
): string[] {
  const others: string[] = [];
  for (const name of allNames) {
    if (matched.has(name)) continue;
    if (containsToken(name, cfg.channels.ignorePatterns)) continue;
    if (containsToken(name, cfg.markers.channelAliases)) continue;
    others.push(name);
  }
  return others;
}

/**
 * Analyze an EDF buffer. `pathLabel` is only a display string in the payload;
 * it is never a real filesystem path on Vercel.
 */
export function analyzeEdfBuffer(
  buffer: Uint8Array,
  pathLabel: string,
  cfg: AnalysisConfig = CONFIG,
): AnalysisResult {
  const edf = parseEdf(buffer);

  // Resolve each expected channel through its aliases.
  const expected: ExpectedChannelResult[] = [];
  const matchedNames = new Set<string>();
  for (const ec of cfg.channels.expected) {
    const found = findChannel(edf.channelNames, ec.aliases);
    expected.push({ canonical: ec.canonical, matched_name: found, found: found !== null, metrics: null });
    if (found) matchedNames.add(found);
  }

  // Metrics for matched expected channels.
  for (const res of expected) {
    if (res.matched_name && matchedNames.has(res.matched_name)) {
      res.metrics = computeMetrics(edf.readChannelUv(res.matched_name));
    }
  }

  // Metrics for other (non-ignored, non-marker) channels, for context.
  const otherNames = classifyOtherChannels(edf.channelNames, matchedNames, cfg);
  const otherChannels = otherNames.map((name) => ({
    name,
    metrics: computeMetrics(edf.readChannelUv(name)),
  }));

  // Markers.
  const annEvents = annotationEvents(edf, cfg);
  const candidateChannels = candidateMarkerChannels(edf, cfg);
  const chEvents: MarkerEvent[] = [];
  for (const ch of candidateChannels) chEvents.push(...channelEvents(edf, ch));
  const allEvents = [...annEvents, ...chEvents].sort((a, b) => a.onset_s - b.onset_s);
  const distinctLabels = [...new Set(allEvents.map((e) => e.label))].sort();

  // Validation gate.
  const hardFailures: string[] = [];
  const warnings: string[] = [];
  const v = cfg.validation;

  if (edf.durationS < v.minDurationS) {
    hardFailures.push(
      `Recording too short: ${edf.durationS.toFixed(1)}s < required ${v.minDurationS.toFixed(1)}s.`,
    );
  }
  const allowed = cfg.allowedSampleRatesHz;
  const expectedRates = cfg.expectedSampleRatesHz;
  if (allowed.length && !allowed.includes(edf.sfreqHz)) {
    hardFailures.push(
      `Sample rate ${edf.sfreqHz} Hz not in allowed set [${allowed.join(', ')}].`,
    );
  } else if (expectedRates.length && !expectedRates.includes(edf.sfreqHz)) {
    warnings.push(
      `Sample rate ${edf.sfreqHz} Hz not in expected set [${expectedRates.join(', ')}] ` +
        '(allowed, but confirm acquisition settings).',
    );
  }

  const missing = expected.filter((r) => !r.found).map((r) => r.canonical);
  if (missing.length) {
    const msg = `Missing expected EEG channels: ${missing.join(', ')}.`;
    if (v.requireAllExpectedChannels) hardFailures.push(msg);
    else warnings.push(msg);
  }

  for (const res of expected) {
    if (!res.metrics) continue;
    const m = res.metrics;
    if (m.rms_uv < v.rmsUvMin) {
      warnings.push(
        `${res.canonical} (${res.matched_name}): RMS ${m.rms_uv.toFixed(2)} uV below ` +
          `${v.rmsUvMin} uV — possible disconnected lead.`,
      );
    } else if (m.rms_uv > v.rmsUvMax) {
      warnings.push(
        `${res.canonical} (${res.matched_name}): RMS ${m.rms_uv.toFixed(2)} uV above ` +
          `${v.rmsUvMax} uV — possible poor contact / noise.`,
      );
    }
    if (m.ptp_uv > v.ptpUvMax) {
      warnings.push(
        `${res.canonical} (${res.matched_name}): peak-to-peak ${m.ptp_uv.toFixed(0)} uV ` +
          `exceeds ${v.ptpUvMax.toFixed(0)} uV — possible motion / artifact.`,
      );
    }
  }

  if (cfg.markers.minExpectedEvents > 0 && allEvents.length < cfg.markers.minExpectedEvents) {
    hardFailures.push(
      `Found ${allEvents.length} events, expected at least ${cfg.markers.minExpectedEvents}.`,
    );
  }

  const ok = hardFailures.length === 0;
  const status = ok ? 'ok' : 'failed';

  const diagnostic: DiagnosticPayload = {
    status,
    config_name: cfg.name,
    unit_assumption: cfg.eegUnitAssumption,
    recording: {
      path: pathLabel,
      n_channels: edf.channelNames.length,
      channel_names: edf.channelNames,
      sfreq_hz: edf.sfreqHz,
      n_samples: edf.nSamplesPerChannel,
      duration_s: round(edf.durationS, 4),
      n_annotations: edf.annotations.reduce((a, x) => a + x.labels.length, 0),
      highpass_hz: edf.highpassHz,
      lowpass_hz: edf.lowpassHz,
      meas_date: edf.measDate,
    },
    expected_channels: expected,
    other_channels: otherChannels,
    markers: {
      n_events: allEvents.length,
      n_annotation_events: annEvents.length,
      n_channel_events: chEvents.length,
      candidate_marker_channels: candidateChannels,
      distinct_labels: distinctLabels,
      events: allEvents.slice(0, 500),
    },
    hard_failures: hardFailures,
    warnings,
  };

  const summary: AnalysisSummary = {
    status: diagnostic.status,
    config_name: diagnostic.config_name,
    unit_assumption: diagnostic.unit_assumption,
    recording: {
      n_channels: diagnostic.recording.n_channels,
      channel_names: diagnostic.recording.channel_names,
      sfreq_hz: diagnostic.recording.sfreq_hz,
      duration_s: diagnostic.recording.duration_s,
      n_samples: diagnostic.recording.n_samples,
      n_annotations: diagnostic.recording.n_annotations,
      highpass_hz: diagnostic.recording.highpass_hz,
      lowpass_hz: diagnostic.recording.lowpass_hz,
      meas_date: diagnostic.recording.meas_date,
    },
    expected_channels: diagnostic.expected_channels,
    markers: {
      n_events: diagnostic.markers.n_events,
      distinct_labels: diagnostic.markers.distinct_labels,
      candidate_marker_channels: diagnostic.markers.candidate_marker_channels,
      events: diagnostic.markers.events,
    },
  };

  return { ok, status, diagnostic, summary, warnings, hard_failures: hardFailures };
}
