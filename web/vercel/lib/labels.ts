/**
 * Label normalization and alias matching (TypeScript port of labels.py).
 *
 * BioTrace+ / EDF exports use inconsistent channel and marker labels
 * ("EEG Fz-A1A2", "Fz", "Ch1", ...). `normalize` strips case and separators;
 * `coreLabel` additionally removes a leading "EEG" prefix and trailing
 * reference tokens (A1A2, LE, ...) so a small alias list matches many surface
 * forms without brittle enumeration.
 */

const SEP = /[^a-z0-9]+/g;

const PREFIXES = ['eeg'];
const REF_SUFFIXES = [
  'a1a2', 'a2a1', 'm1m2', 'm2m1',
  'linkedears', 'linkedear', 'le',
  'ref', 'avg', 'cor',
  'a1', 'a2', 'm1', 'm2',
];

export function normalize(label: string): string {
  return label.trim().toLowerCase().replace(SEP, '');
}

export function coreLabel(label: string): string {
  let norm = normalize(label);
  for (const pre of PREFIXES) {
    if (norm.startsWith(pre) && norm.length > pre.length) {
      norm = norm.slice(pre.length);
      break;
    }
  }
  for (const suf of REF_SUFFIXES) {
    if (norm.endsWith(suf) && norm.length > suf.length) {
      norm = norm.slice(0, norm.length - suf.length);
      break;
    }
  }
  return norm;
}

export function matchAlias(label: string, aliases: string[]): boolean {
  const norm = normalize(label);
  const core = coreLabel(label);
  for (const a of aliases) {
    if (norm === normalize(a) || core === coreLabel(a)) return true;
  }
  return false;
}

export function findChannel(channelNames: string[], aliases: string[]): string | null {
  for (const name of channelNames) {
    if (matchAlias(name, aliases)) return name;
  }
  return null;
}

export function containsToken(label: string, tokens: string[]): boolean {
  const norm = normalize(label);
  return tokens.some((t) => t && norm.includes(normalize(t)));
}
