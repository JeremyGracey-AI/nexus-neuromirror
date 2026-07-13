/**
 * Minimal, audited EDF / EDF+ parser (no external dependencies).
 *
 * Scope: enough to power the first-prototype diagnostic — header metadata,
 * per-signal physical values in microvolts, and EDF+ "EDF Annotations" (TAL)
 * events. This intentionally does NOT reimplement MNE/SciPy; it reads the
 * documented EDF/EDF+ on-disk layout directly.
 *
 * Reference: Kemp & Olivan, "European Data Format 'plus' (EDF+)".
 * - 256-byte static header, then (ns * 256)-byte signal header block.
 * - Data records: for each record, each signal contributes
 *   `samplesPerRecord[i]` little-endian int16 samples.
 * - Physical value = (digital - digMin) * (physMax - physMin) /
 *   (digMax - digMin) + physMin.
 * - EDF+ annotations live in a signal whose label is "EDF Annotations",
 *   stored as UTF-8 TAL bytes (2-byte samples reinterpreted as raw bytes).
 *
 * All parsing is bounds-checked; malformed files throw `EdfParseError` with a
 * message that never contains raw signal contents.
 */

export class EdfParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'EdfParseError';
  }
}

export interface EdfAnnotation {
  onsetS: number;
  durationS: number | null;
  labels: string[];
}

export interface EdfSignalHeader {
  label: string;
  transducer: string;
  physicalDimension: string;
  physicalMin: number;
  physicalMax: number;
  digitalMin: number;
  digitalMax: number;
  prefiltering: string;
  samplesPerRecord: number;
  isAnnotation: boolean;
}

export interface EdfFile {
  version: string;
  patient: string;
  recording: string;
  startDate: string;
  startTime: string;
  headerBytes: number;
  reserved: string;
  isEdfPlus: boolean;
  nDataRecords: number;
  recordDurationS: number;
  nSignals: number;
  signals: EdfSignalHeader[];
  /** Ordinary (non-annotation) signal channel names in file order. */
  channelNames: string[];
  sfreqHz: number;
  nSamplesPerChannel: number;
  durationS: number;
  annotations: EdfAnnotation[];
  /** Highest sample-rate among ordinary signals (used as the nominal sfreq). */
  highpassHz: number | null;
  lowpassHz: number | null;
  measDate: string | null;
  /**
   * Read physical (microvolt-scaled) samples for one ordinary channel by index
   * into `channelNames`. Lazily decodes to keep memory bounded.
   */
  readChannelUv(channelName: string): Float64Array;
}

function ascii(buf: Uint8Array, start: number, len: number): string {
  let s = '';
  for (let i = start; i < start + len && i < buf.length; i++) {
    s += String.fromCharCode(buf[i]);
  }
  return s;
}

function parseIntStrict(s: string, field: string): number {
  const t = s.trim();
  const n = Number.parseInt(t, 10);
  if (!Number.isFinite(n)) {
    throw new EdfParseError(`Malformed EDF header: bad integer for ${field}.`);
  }
  return n;
}

function parseFloatStrict(s: string, field: string): number {
  const t = s.trim();
  const n = Number.parseFloat(t);
  if (!Number.isFinite(n)) {
    throw new EdfParseError(`Malformed EDF header: bad number for ${field}.`);
  }
  return n;
}

/** Parse "dd.mm.yy" + "hh.mm.ss" into an ISO date string, or null. */
function parseMeasDate(date: string, time: string): string | null {
  const dm = date.trim().match(/^(\d{2})\.(\d{2})\.(\d{2})$/);
  const tm = time.trim().match(/^(\d{2})\.(\d{2})\.(\d{2})$/);
  if (!dm || !tm) return null;
  const dd = Number(dm[1]);
  const mm = Number(dm[2]);
  let yy = Number(dm[3]);
  // EDF clipping rule: 85-99 -> 1900s, 00-84 -> 2000s.
  yy = yy >= 85 ? 1900 + yy : 2000 + yy;
  const [, hh, min, ss] = tm;
  const iso = `${yy.toString().padStart(4, '0')}-${mm
    .toString()
    .padStart(2, '0')}-${dd.toString().padStart(2, '0')}T${hh}:${min}:${ss}+00:00`;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : iso;
}

/** Parse an EDF+ TAL (Time-stamped Annotations List) block into events. */
function parseTAL(bytes: Uint8Array): EdfAnnotation[] {
  const events: EdfAnnotation[] = [];
  // TAL bytes are UTF-8. Separators: 0x14 (field), 0x15 (duration), 0x00 (end).
  const decoder = new TextDecoder('utf-8', { fatal: false });
  let i = 0;
  const n = bytes.length;
  while (i < n) {
    // Skip padding null bytes between TALs.
    if (bytes[i] === 0x00) {
      i++;
      continue;
    }
    // Read until 0x00 to isolate one TAL.
    let end = i;
    while (end < n && bytes[end] !== 0x00) end++;
    const tal = bytes.subarray(i, end);
    i = end + 1;
    if (tal.length === 0) continue;

    // Split TAL on 0x14. First chunk is onset[+0x15 duration].
    const parts: Uint8Array[] = [];
    let s = 0;
    for (let k = 0; k <= tal.length; k++) {
      if (k === tal.length || tal[k] === 0x14) {
        parts.push(tal.subarray(s, k));
        s = k + 1;
      }
    }
    if (parts.length === 0) continue;

    // parts[0]: onset (with optional 0x15 duration).
    const timing = parts[0];
    let onsetBytes = timing;
    let durationBytes: Uint8Array | null = null;
    for (let k = 0; k < timing.length; k++) {
      if (timing[k] === 0x15) {
        onsetBytes = timing.subarray(0, k);
        durationBytes = timing.subarray(k + 1);
        break;
      }
    }
    const onsetStr = decoder.decode(onsetBytes).trim();
    const onsetS = Number.parseFloat(onsetStr);
    if (!Number.isFinite(onsetS)) continue; // timekeeping TAL with no annotation
    let durationS: number | null = null;
    if (durationBytes && durationBytes.length) {
      const d = Number.parseFloat(decoder.decode(durationBytes).trim());
      durationS = Number.isFinite(d) ? d : null;
    }

    // parts[1..]: annotation text labels (may be empty -> timekeeping only).
    const labels: string[] = [];
    for (let p = 1; p < parts.length; p++) {
      const text = decoder.decode(parts[p]).replace(/\x00+$/g, '').trim();
      if (text) labels.push(text);
    }
    if (labels.length > 0) {
      events.push({ onsetS, durationS, labels });
    }
  }
  return events;
}

export function parseEdf(buffer: Uint8Array): EdfFile {
  if (buffer.length < 256) {
    throw new EdfParseError('File is too small to be a valid EDF header.');
  }
  const version = ascii(buffer, 0, 8).trim();
  const patient = ascii(buffer, 8, 80).trim();
  const recording = ascii(buffer, 88, 80).trim();
  const startDate = ascii(buffer, 168, 8).trim();
  const startTime = ascii(buffer, 176, 8).trim();
  const headerBytes = parseIntStrict(ascii(buffer, 184, 8), 'header bytes');
  const reserved = ascii(buffer, 192, 44).trim();
  const nDataRecords = parseIntStrict(ascii(buffer, 236, 8), 'n data records');
  const recordDurationS = parseFloatStrict(ascii(buffer, 244, 8), 'record duration');
  const nSignals = parseIntStrict(ascii(buffer, 252, 4), 'n signals');

  if (nSignals <= 0 || nSignals > 2048) {
    throw new EdfParseError(`Implausible signal count in EDF header: ${nSignals}.`);
  }
  const expectedHeader = 256 + nSignals * 256;
  if (buffer.length < expectedHeader) {
    throw new EdfParseError('EDF signal header block is truncated.');
  }

  const isEdfPlus = reserved.startsWith('EDF+');

  // Signal header block: fixed-width fields, each ns entries concatenated.
  const labelBase = 256;
  const readField = (fieldOffset: number, width: number, i: number): string =>
    ascii(buffer, labelBase + fieldOffset * nSignals + i * width, width);

  const signals: EdfSignalHeader[] = [];
  for (let i = 0; i < nSignals; i++) {
    const label = readField(0, 16, i).trim();
    const transducer = readField(16, 80, i).trim();
    const physicalDimension = readField(96, 8, i).trim();
    const physicalMin = parseFloatStrict(readField(104, 8, i), `physMin[${i}]`);
    const physicalMax = parseFloatStrict(readField(112, 8, i), `physMax[${i}]`);
    const digitalMin = parseIntStrict(readField(120, 8, i), `digMin[${i}]`);
    const digitalMax = parseIntStrict(readField(128, 8, i), `digMax[${i}]`);
    const prefiltering = readField(136, 80, i).trim();
    const samplesPerRecord = parseIntStrict(readField(216, 8, i), `nsamp[${i}]`);
    const isAnnotation = label === 'EDF Annotations';
    signals.push({
      label,
      transducer,
      physicalDimension,
      physicalMin,
      physicalMax,
      digitalMin,
      digitalMax,
      prefiltering,
      samplesPerRecord,
      isAnnotation,
    });
  }

  const samplesPerRecordTotal = signals.reduce((a, s) => a + s.samplesPerRecord, 0);
  const bytesPerRecord = samplesPerRecordTotal * 2;
  const dataStart = 256 + nSignals * 256;
  const availableRecordBytes = buffer.length - dataStart;

  // EDF may declare nDataRecords = -1 (unknown); derive from file size.
  let nRecords = nDataRecords;
  if (nRecords < 0) {
    nRecords = bytesPerRecord > 0 ? Math.floor(availableRecordBytes / bytesPerRecord) : 0;
  }
  if (bytesPerRecord > 0 && availableRecordBytes < nRecords * bytesPerRecord) {
    // Clamp to what's actually present rather than reading out of bounds.
    nRecords = Math.floor(availableRecordBytes / bytesPerRecord);
  }

  if (recordDurationS <= 0) {
    throw new EdfParseError('EDF record duration must be positive.');
  }

  // Ordinary (non-annotation) signals.
  const ordinary = signals.filter((s) => !s.isAnnotation);
  if (ordinary.length === 0) {
    throw new EdfParseError('EDF contains no ordinary signal channels.');
  }
  const channelNames = ordinary.map((s) => s.label);

  // Nominal sampling frequency: use the max samples-per-record among ordinary
  // signals (channels can technically differ; the prototype expects uniform).
  const maxSamplesPerRecord = Math.max(...ordinary.map((s) => s.samplesPerRecord));
  const sfreqHz = maxSamplesPerRecord / recordDurationS;
  const nSamplesPerChannel = maxSamplesPerRecord * nRecords;
  const durationS = nRecords * recordDurationS;

  // Precompute per-signal byte offset within a record.
  const recordOffsets: number[] = [];
  {
    let off = 0;
    for (const s of signals) {
      recordOffsets.push(off);
      off += s.samplesPerRecord * 2;
    }
  }

  const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);

  const signalIndexByName = new Map<string, number>();
  signals.forEach((s, idx) => {
    if (!s.isAnnotation && !signalIndexByName.has(s.label)) {
      signalIndexByName.set(s.label, idx);
    }
  });

  function readChannelUv(channelName: string): Float64Array {
    const sigIdx = signalIndexByName.get(channelName);
    if (sigIdx === undefined) {
      throw new EdfParseError(`Unknown channel requested: ${channelName}.`);
    }
    const sig = signals[sigIdx];
    const spr = sig.samplesPerRecord;
    const out = new Float64Array(spr * nRecords);
    const digRange = sig.digitalMax - sig.digitalMin;
    const physRange = sig.physicalMax - sig.physicalMin;
    const scale = digRange !== 0 ? physRange / digRange : 0;
    // Determine unit scaling to microvolts based on physical dimension.
    const dim = sig.physicalDimension.trim().toLowerCase();
    let toUv = 1;
    if (dim === 'v') toUv = 1e6;
    else if (dim === 'mv') toUv = 1e3;
    else if (dim === 'uv' || dim === 'µv' || dim === 'μv') toUv = 1;
    else toUv = 1; // unknown dimension: assume already uV (documented assumption)

    let w = 0;
    for (let r = 0; r < nRecords; r++) {
      const recBase = dataStart + r * bytesPerRecord + recordOffsets[sigIdx];
      for (let k = 0; k < spr; k++) {
        const digital = view.getInt16(recBase + k * 2, true);
        const phys = (digital - sig.digitalMin) * scale + sig.physicalMin;
        out[w++] = phys * toUv;
      }
    }
    return out;
  }

  // EDF+ annotations: concatenate all annotation-signal bytes across records.
  const annotations: EdfAnnotation[] = [];
  if (isEdfPlus) {
    const annSignals = signals
      .map((s, idx) => ({ s, idx }))
      .filter((x) => x.s.isAnnotation);
    for (const { s, idx } of annSignals) {
      const spr = s.samplesPerRecord;
      const bytesPerSigRecord = spr * 2;
      const chunks: Uint8Array[] = [];
      for (let r = 0; r < nRecords; r++) {
        const recBase = dataStart + r * bytesPerRecord + recordOffsets[idx];
        chunks.push(buffer.subarray(recBase, recBase + bytesPerSigRecord));
      }
      const total = chunks.reduce((a, c) => a + c.length, 0);
      const merged = new Uint8Array(total);
      let o = 0;
      for (const c of chunks) {
        merged.set(c, o);
        o += c.length;
      }
      annotations.push(...parseTAL(merged));
    }
  }

  const meas = parseMeasDate(startDate, startTime);

  return {
    version,
    patient,
    recording,
    startDate,
    startTime,
    headerBytes,
    reserved,
    isEdfPlus,
    nDataRecords: nRecords,
    recordDurationS,
    nSignals,
    signals,
    channelNames,
    sfreqHz,
    nSamplesPerChannel,
    durationS,
    annotations,
    highpassHz: null,
    lowpassHz: null,
    measDate: meas,
    readChannelUv,
  };
}
