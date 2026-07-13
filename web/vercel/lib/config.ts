/**
 * Static analysis configuration for the NeXus NeuroMirror prototype.
 *
 * This mirrors `configs/project.example.yaml` from the Python package. It is
 * embedded here (rather than read from disk) because Vercel serverless
 * functions have no durable local filesystem — GitHub is the backend.
 *
 * These values drive the first-prototype EDF analysis: the four expected
 * channels (Fz / FCz / Pz / Oz), marker detection, and the validation gate.
 */

export interface ExpectedChannelCfg {
  canonical: string;
  aliases: string[];
}

export interface AnalysisConfig {
  name: string;
  eegUnitAssumption: string;
  expectedSampleRatesHz: number[];
  allowedSampleRatesHz: number[];
  channels: {
    expected: ExpectedChannelCfg[];
    ignorePatterns: string[];
  };
  markers: {
    annotationAliases: string[];
    channelAliases: string[];
    minExpectedEvents: number;
  };
  validation: {
    minDurationS: number;
    rmsUvMin: number;
    rmsUvMax: number;
    ptpUvMax: number;
    requireAllExpectedChannels: boolean;
  };
}

export const CONFIG: AnalysisConfig = {
  name: 'nexus-neuromirror',
  eegUnitAssumption:
    'volts (MNE-internal); EDF physical dimension expected uV',
  expectedSampleRatesHz: [256, 512, 1024],
  allowedSampleRatesHz: [128, 256, 512, 1024, 2048],
  channels: {
    expected: [
      { canonical: 'Fz', aliases: ['Fz', 'EEG Fz', 'Fz-A1A2', 'Fz-LE', 'Ch1', 'A-Fz'] },
      { canonical: 'FCz', aliases: ['FCz', 'EEG FCz', 'FCz-A1A2', "Cz'", 'Ch2', 'B-FCz'] },
      { canonical: 'Pz', aliases: ['Pz', 'EEG Pz', 'Pz-A1A2', 'Pz-LE', 'Ch3', 'C-Pz'] },
      { canonical: 'Oz', aliases: ['Oz', 'EEG Oz', 'Oz-A1A2', 'Oz-LE', 'Ch4', 'D-Oz'] },
    ],
    ignorePatterns: [
      'ECG', 'EMG', 'EOG', 'HR', 'BVP', 'GSR', 'Resp', 'Temp', 'Accel', 'Status',
    ],
  },
  markers: {
    annotationAliases: ['marker', 'trigger', 'stim', 'event', 'cue', 'block'],
    channelAliases: ['Status', 'Marker', 'Trigger', 'STI 014', 'Events'],
    minExpectedEvents: 0,
  },
  validation: {
    minDurationS: 30.0,
    rmsUvMin: 0.5,
    rmsUvMax: 150.0,
    ptpUvMax: 3000.0,
    requireAllExpectedChannels: true,
  },
};

// --- Accepted upload formats ------------------------------------------------
// Extension -> human label. BCD is archival-only and must never be parsed.
// ASCII/CSV/TXT/ASC and MAT are catalog-only in the MVP. EDF/EDF+ is analyzed.
export const FORMAT_LABELS: Record<string, string> = {
  '.edf': 'EDF/EDF+',
  '.csv': 'ASCII/CSV',
  '.txt': 'ASCII/CSV',
  '.asc': 'ASCII/CSV',
  '.mat': 'MATLAB .mat',
  '.bcd': 'BCD (archival)',
};

export const ANALYZABLE_EXTENSIONS = new Set<string>(['.edf']);
export const CATALOG_ONLY_EXTENSIONS = new Set<string>(['.csv', '.txt', '.asc', '.mat']);
export const ARCHIVAL_ONLY_EXTENSIONS = new Set<string>(['.bcd']);
export const ALLOWED_EXTENSIONS = new Set<string>([
  ...ANALYZABLE_EXTENSIONS,
  ...CATALOG_ONLY_EXTENSIONS,
  ...ARCHIVAL_ONLY_EXTENSIONS,
]);

// Vercel's Serverless/Edge request body limit is 4.5 MB. Keep the upload cap
// safely below that. Overridable via NNM_MAX_UPLOAD_BYTES.
export const DEFAULT_MAX_UPLOAD_BYTES = 4 * 1024 * 1024;

export function maxUploadBytes(): number {
  const raw = process.env.NNM_MAX_UPLOAD_BYTES;
  const n = raw ? parseInt(raw, 10) : NaN;
  return Number.isFinite(n) && n > 0 ? n : DEFAULT_MAX_UPLOAD_BYTES;
}
