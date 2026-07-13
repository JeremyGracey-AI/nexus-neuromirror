# NeuralSet Integration Specification for NeXus NeuroMirror

**Status:** Draft technical specification (standalone, implementation-ready)
**Scope:** Adding NeuralSet compatibility to the existing NeXus NeuroMirror pipeline (NeXus-10 + BioTrace+, four-channel EEG, Fz/FCz/Pz/Oz)
**Author context:** Prepared as an integration spec against the current NeXus NeuroMirror codebase and the NeuralSet framework paper

---

## 1. Purpose and scientific scope

This document specifies how to make NeXus NeuroMirror's BioTrace+ EDF/EDF+ sessions consumable by **NeuralSet**, a Python framework from Meta FAIR that unifies neural-recording processing and AI-embedding extraction behind a single PyTorch `DataLoader` interface, using `Study`, `Events`, `Extractors`, `Segmenter`, and `Batch`/`SegmentDataset` abstractions ([NeuralSet paper](https://github.com/facebookresearch/neuroai/)). NeuralSet is explicitly an **orchestration layer**, not a replacement for validated signal-processing libraries — it "does not reinvent validated signal processing algorithms; rather, it harmonizes them with the high-dimensional embeddings of contemporary AI models," delegating EEG-specific work to MNE-Python under the hood (NeuralSet paper, Discussion §"Orchestration, not reinvention"). This integration follows that same principle: it does not touch NeXus NeuroMirror's existing verification/metrics/report logic, and it does not introduce any new signal-processing algorithm.

**Scientific scope constraint.** NeXus NeuroMirror is documented as "a research / educational prototype, not a medical device... It is not intended to diagnose, treat, cure, or prevent any disease, and it makes no clinical claims" (`README.md`). Nothing in this spec changes that posture. NeuralSet compatibility is a **data-engineering and provenance integration**: it produces PyTorch-ready tensors and cached feature representations from the same four-channel EEG recordings the project already verifies. It does not claim, imply, or provide any means of inferring consciousness, awareness, cognitive state, or clinical status from these signals. Any future modeling work built on top of a NeuralSet `SegmentDataset` (e.g., bandpower classifiers, embedding-based decoders) is subject to the same disclaimer and must not be described in consciousness or clinical terms without independent, validated, peer-reviewed evidence — which is out of scope here.

---

## 2. Current system baseline (what is being integrated)

NeXus NeuroMirror's existing pipeline, as implemented today, is:

- **Acquisition boundary:** NeXus-10 amplifier → BioTrace+ acquisition software → EDF/EDF+ export file. The architecture doc treats this export as "the system boundary" (`docs/architecture.md`).
- **Channels:** four expected EEG sites — Fz, FCz, Pz, Oz — resolved from vendor-specific aliases (`configs/project.example.yaml`, `src/nexus_neuromirror/labels.py`).
- **Adapter:** `edf.py` reads EDF/EDF+ (and other MNE-readable formats) into an MNE `Raw` object and extracts a compact `RecordingInfo` (channel names, sample rate, duration, annotation count, filter settings, measurement date).
- **Events/markers:** `markers.py` detects two independent sources of events — EDF+ annotations (`_annotation_events`) and step changes on candidate marker/status channels (`_channel_events`) — and merges them into a single time-sorted `MarkerReport`.
- **Metrics:** `metrics.py` computes per-channel RMS, peak-to-peak, max-abs, and mean in microvolts, with the volts→µV conversion factor (`VOLTS_TO_UV = 1e6`) centralized in one place.
- **Validation gate:** `verify.py` separates **hard failures** (short duration, disallowed sample rate, missing required channels, insufficient event count) from **warnings** (out-of-range sample rate, RMS/peak-to-peak out of band), producing a `VerificationResult`.
- **Reporting:** `report.py` writes `diagnostic.json` plus PNG/SVG figures (multichannel trace, PSD, marker timeline) using only matched expected channels.
- **Web layer:** a FastAPI backend (`web/backend/nnm_web/analysis.py`) wraps `generate_report` for uploaded EDFs, and a React/Vite SPA (Upload, Sessions, SessionDetail, Overview pages) exposes this to users; `security.py`/`storage.py` sanitize filenames and paths.
- **Configuration:** everything above is driven by one YAML file (`configs/project.example.yaml`) parsed into typed dataclasses by `config.py`, including a `model` section already anticipating windowing (`window_s`, `window_overlap`), band-pass/notch filtering, and per-band bandpower features — but with no model or feature-extraction code implemented yet.

This baseline is the exact substrate NeuralSet compatibility must attach to without modification (per task constraint, the `nexus-neuromirror` directory itself is not edited by this spec).

---

## 3. NeuralSet framework primitives (as specified in the paper)

NeuralSet organizes every pipeline around five abstractions ([NeuralSet paper](https://github.com/facebookresearch/neuroai/), §2):

1. **Events** — the atomic description of "what happens and when." Every event is a lightweight object (a Python dict / DataFrame row) defined by a `type`, `start`, `duration`, and `timeline` (a unique identifier for a continuous recording session). A `Study` object assembles all events of a dataset into a single pandas DataFrame; this is "consistent with, but not restricted to, BIDS-compliant datasets." `EventsTransform` operations chain to enrich, filter, or reorganize events before extraction.
2. **Extractors** — turn events that fall within a temporal window into dense tensors. For neural recordings, NeuralSet wraps existing domain libraries rather than reimplementing them — "an EEG or MEG extractor delegates to MNE-Python for filtering, re-referencing, and resampling." Extractors follow a three-phase execution model: **configure** (Pydantic validation at construction), **prepare** (pre-compute and cache heavy outputs for all events), **extract** (lazy, cached retrieval during training). Extractors can be **static** (one D-dimensional vector per event) or **dynamic** (a D×T matrix varying over time), independent of the data's intrinsic nature.
3. **Segmenter / Segments** — a `Segment` is a contiguous temporal window over events, representing one training example. The `Segmenter` slices the events DataFrame either on a regular grid (sliding window) or anchored to trigger events (e.g., marker onsets), producing a `SegmentDataset`.
4. **Batch Data** — the actual tensors: a dictionary of tensors keyed by extractor name, produced only when `SegmentDataset.prepare()` / DataLoader iteration triggers real I/O. Configuration and slicing are metadata-only operations; "millions of segments can be prepared without touching the raw signal files."
5. **Backend (exca)** — Pydantic-based proactive validation (catches bad parameters "before job submission"), deterministic hash-based caching keyed to "its specific non-default parameters and its relevant preceding dependencies" (so changing one parameter invalidates only downstream cache), and hardware-agnostic execution that dispatches identical code to a local machine or a SLURM cluster via one configuration flag.

The paper is explicit that NeuralSet's Extractor abstraction is designed for **bidirectional integration**: "maintainers of any existing package can expose their pipeline as a NeuralSet backend through a thin adapter, thereby gaining access to lazy loading, deterministic caching, and cluster-level execution without modifying their own codebase" (Discussion, "Complementing the ecosystem"). This is the intended integration seam for NeXus NeuroMirror.

---

## 4. Mapping: BioTrace+ sessions → NeuralSet abstractions

| NeXus NeuroMirror concept | NeuralSet abstraction | Mapping rule |
|---|---|---|
| One BioTrace+ recording block / EDF export | **Timeline** | `timeline = "{subject_id}_{session_id}_{block_index}"`. One EDF file = one timeline, matching the architecture doc's block-wise closed loop (`docs/architecture.md`). |
| All sessions across subjects for a project config | **Study** | `Study(name=cfg.name, path=<data root>)`. `Study.build()` returns the pandas DataFrame of events; this mirrors `configs/project.example.yaml`'s `project.name` and `paths.data_dir`. |
| Fz/FCz/Pz/Oz EEG channels + continuous recording span | **Continuous "Eeg" event** | One event per timeline: `type="Eeg", start=0.0, duration=info.duration_s, timeline=<id>, filepath=<edf path>`, carrying `RecordingInfo.as_dict()` fields (sfreq, channel names, filter settings) as event metadata columns. |
| EDF+ annotations (`markers._annotation_events`) | **"Annotation" events** | One event per `MarkerEvent`: `type="Annotation", start=onset_s, duration=0.0, timeline=<id>, label=..., source="annotation"`. |
| Marker/status-channel step changes (`markers._channel_events`) | **"Marker" events** | One event per code transition: `type="Marker", start=onset_s, duration=0.0, timeline=<id>, label="code:<int>", source=<channel name>`. |
| `verify.VerificationResult` (hard failures / warnings / metrics) | **Study-level metadata columns, not events** | Verification output is provenance/QC metadata attached to the timeline row(s), not a stimulus or neural signal — see §6. It gates which timelines enter a `Study` at all (§7). |
| `model.window_s` / `model.window_overlap` (configured, not yet implemented) | **Segmenter** | `Segmenter(start=0.0, duration=cfg.model["window_s"], stride=cfg.model["window_s"] * (1 - cfg.model["window_overlap"]))` for grid segmentation; `trigger_query='type == "Marker" or type == "Annotation"'` for event-anchored segmentation. |
| EEG bandpass/notch/bandpower config (`model.bandpass_hz`, `model.bands`) | **EEG Extractor configuration** | Passed as `filter=cfg.model["bandpass_hz"]` and a custom bandpower post-step (§5.2) inside a NeuralSet `EegExtractor`-equivalent, which itself wraps MNE — consistent with the paper's "an EEG or MEG extractor delegates to MNE-Python for filtering, re-referencing, and resampling." |
| `diagnostic.json` + PNG/SVG report artifacts | **Out-of-band provenance sidecar**, not a Segment/Batch input | Stored as a linked file path in Study metadata for traceability; not fed into the tensor pipeline (see §8). |
| PyTorch `DataLoader` consumption in a training loop | **Batch** | `dataset = segmenter.apply(events)`; `DataLoader(dataset, batch_size=B, collate_fn=dataset.collate_fn)` — identical to the paper's Figure 3 usage pattern. |

This mapping treats the EDF file itself as a single long "Eeg" event and represents everything else (annotations, marker-channel transitions) as zero-duration point events on the same timeline, which matches NeuralSet's own worked example of representing "an fMRI acquisition, the video stimulus, and potentially hundreds of word-onset annotations" as "a handful of concurrent events on the same timeline" (NeuralSet paper §2.1).

---

## 5. Adapter interfaces

### 5.1 `NnmStudyBuilder` (Events layer adapter)

Responsibility: turn one or more `data/uploads/**/metadata.json` + EDF pairs (or a directory of BioTrace+ exports) into a NeuralSet-compatible events DataFrame, **without duplicating EDF parsing** — it must call the existing `nexus_neuromirror.edf.read_edf` / `extract_info` and `nexus_neuromirror.markers.detect_markers` functions and only reshape their outputs.

```python
# Proposed adapter module: neuralset_adapter/study_builder.py
# (new module; does not modify nexus_neuromirror/*)

from pathlib import Path
import pandas as pd
from nexus_neuromirror.config import Config, load_config
from nexus_neuromirror.edf import extract_info, read_edf
from nexus_neuromirror.markers import detect_markers
from nexus_neuromirror.verify import verify_raw


def build_events(session_paths: list[Path], cfg: Config) -> pd.DataFrame:
    """Build a NeuralSet-compatible events DataFrame from BioTrace+ EDF exports.

    One row per event; three event types are emitted per session:
    'Eeg' (one continuous span), 'Annotation', 'Marker'.
    Verification outcome and channel-resolution metadata are attached as
    extra columns on the 'Eeg' row only (see Sec. 6), never inferred or
    imputed.
    """
    rows: list[dict] = []
    for path in session_paths:
        raw = read_edf(path)
        info = extract_info(raw, path)
        result = verify_raw(raw, path, cfg)          # reuses existing gate
        markers = detect_markers(raw, cfg.markers)     # reuses existing detector
        timeline = _timeline_id(path)

        rows.append({
            "type": "Eeg", "start": 0.0, "duration": info.duration_s,
            "timeline": timeline, "filepath": str(path),
            "sfreq_hz": info.sfreq_hz, "channel_names": info.channel_names,
            "highpass_hz": info.highpass_hz, "lowpass_hz": info.lowpass_hz,
            "verification_status": "ok" if result.ok else "failed",
            "hard_failures": list(result.hard_failures),
            "warnings": list(result.warnings),
            "matched_channels": dict(zip(
                [r.canonical for r in result.resolutions],
                [r.matched_name for r in result.resolutions],
            )),
            "config_name": cfg.name,
            "unit_assumption": cfg.acquisition.eeg_unit_assumption,
        })
        for e in markers.annotation_events:
            rows.append({"type": "Annotation", "start": e.onset_s, "duration": 0.0,
                         "timeline": timeline, "label": e.label, "source": e.source})
        for e in markers.channel_events:
            rows.append({"type": "Marker", "start": e.onset_s, "duration": 0.0,
                         "timeline": timeline, "label": e.label, "source": e.source})
    return pd.DataFrame(rows)
```

`build_events` is the *only* new code that touches MNE/EDF objects; every downstream NeuralSet component (Extractor, Segmenter) consumes the resulting DataFrame, matching NeuralSet's structure–data decoupling principle.

### 5.2 `NxsBioTraceEegExtractor` (Extractor layer adapter)

Responsibility: implement the paper's three-phase Extractor contract (`configure` → `prepare` → `extract`) for `type == "Eeg"` events, delegating all signal processing to MNE exactly as NeXus NeuroMirror already does in `edf.py`/`metrics.py`, and exposing the project's existing filter/resample/bandpower configuration (`configs/project.example.yaml: model.*`) as Pydantic-validated Extractor parameters.

```python
# neuralset_adapter/extractors.py
import pydantic
import numpy as np
from nexus_neuromirror.edf import read_edf
from nexus_neuromirror.metrics import VOLTS_TO_UV

class NxsBioTraceEegExtractor(pydantic.BaseModel):
    """NeuralSet Extractor wrapping the existing NeXus NeuroMirror EDF adapter.

    Configure-time validation only; no I/O until `prepare()`.
    """
    channels: list[str] = ["Fz", "FCz", "Pz", "Oz"]   # canonical names from config.py
    resample_hz: float = 200.0                         # matches resample.target_hz
    bandpass_hz: tuple[float, float] = (1.0, 40.0)      # matches model.bandpass_hz
    notch_hz: list[float] = [50.0]                      # matches model.notch_hz
    dynamic: bool = True   # True: D x T tensor; False: static per-segment feature vector

    def prepare(self, events_eeg_rows) -> None:
        """Pre-compute + cache filtered/resampled Raw per unique EDF filepath.
        One-time cost per file; downstream `extract()` calls hit cache only."""
        ...  # reads via nexus_neuromirror.edf.read_edf, applies MNE filter/resample,
             # keyed by (filepath, resample_hz, bandpass_hz, notch_hz) per exca's
             # parameter-aware cache-key convention (Sec. 2.5 of the paper)

    def extract(self, segment) -> np.ndarray:
        """Return channels x time (dynamic) or channels x 1 (static, e.g. bandpower)
        tensor in microvolts, reusing metrics.VOLTS_TO_UV for the volts->uV step."""
        ...
```

Key design constraints carried over from the paper and from NeXus NeuroMirror's own conventions:
- **No re-implementation of signal processing.** Filtering/resampling/re-referencing must go through MNE, as both NeuralSet's own EEG extractor and NeXus NeuroMirror's `edf.py` already do.
- **Unit discipline.** The adapter must apply `metrics.VOLTS_TO_UV` exactly once, in the same place NeXus NeuroMirror does, to avoid the classic MNE volts-vs-microvolts double-conversion bug.
- **Static vs. dynamic duality.** Per the paper's §2.2 distinction, the same extractor must be configurable to yield either a raw multichannel time series (`dynamic=True`, for e.g. a CNN/transformer input) or a static per-band bandpower feature vector (`dynamic=False`, matching `model.features: [bandpower, relative_bandpower]` in the existing YAML) — "NeuralSet allows any extractor to produce its output either statically or dynamically, regardless of the data's intrinsic nature."

### 5.3 `NxsMarkerExtractor` (optional static/text-like extractor)

A thin extractor over `type in {"Annotation", "Marker"}` rows that returns a one-hot or embedding vector of the event label, enabling label-conditioned segments (e.g., "segments starting 0.5 s before each `code:2` marker"). This is directly analogous to the paper's `HuggingFaceText` extractor pattern but intentionally kept to simple categorical encoding, since BioTrace+ marker labels are short discrete codes (`code:<int>`) or free-text annotation strings, not natural language requiring an embedding model. Using a pretrained text embedding on marker codes would be scientifically unjustified overkill and is explicitly out of scope.

### 5.4 `NxsSegmenterConfig` (Segmenter layer adapter)

Wraps NeuralSet's `Segmenter` with two named presets, both expressed purely as YAML-loadable configuration (consistent with the project's "config over code" principle in `docs/architecture.md`):

- `sliding_window`: `start`, `duration=model.window_s`, `stride=model.window_s * (1 - model.window_overlap)` — for continuous feature extraction (bandpower time series, resting-state analysis).
- `marker_locked`: `start=-0.5, duration=model.window_s, trigger_query='type == "Marker" or type == "Annotation"'` — for event-related analyses (e.g., markers bracketing task blocks).

### 5.5 `NxsBatchAdapter` (Batch/DataLoader layer)

No custom code is required here beyond what NeuralSet's own `Segmenter.apply(events)` → `torch.utils.data.DataLoader(dataset, collate_fn=dataset.collate_fn)` already provides (paper, Fig. 3). The adapter layer's job is limited to ensuring `dataset.prepare()` is invoked in a context (local laptop vs. batch job) chosen via the existing exca `TaskInfra` configuration flag — no NeXus NeuroMirror-specific batching logic is needed since Segment/Batch are file-format-agnostic once Extractors are wired up.

---

## 6. Schemas

### 6.1 Events DataFrame schema (Study output)

| Column | Type | Applies to | Notes |
|---|---|---|---|
| `type` | str enum: `Eeg`, `Annotation`, `Marker` | all | Matches NeuralSet's `type` field convention. |
| `start` | float (seconds) | all | 0.0 for the continuous `Eeg` row; onset time for point events. |
| `duration` | float (seconds) | all | `info.duration_s` for `Eeg`; `0.0` for `Annotation`/`Marker`. |
| `timeline` | str | all | `"{subject}_{session}_{block}"`; must be unique per EDF file. |
| `filepath` | str | `Eeg` only | Absolute or repo-relative path to the source EDF/EDF+ file. |
| `sfreq_hz` | float | `Eeg` only | From `RecordingInfo.sfreq_hz`; carried through unmodified. |
| `channel_names` | list[str] | `Eeg` only | Raw channel names as read by MNE, pre-alias-resolution. |
| `highpass_hz` / `lowpass_hz` | float \| null | `Eeg` only | Hardware/acquisition-reported filter settings, if present in the EDF header. |
| `verification_status` | str: `ok` \| `failed` | `Eeg` only | Mirrors `VerificationResult.ok`. |
| `hard_failures` / `warnings` | list[str] | `Eeg` only | Verbatim from `verify.py`; never summarized or reworded. |
| `matched_channels` | dict[str, str \| null] | `Eeg` only | canonical → matched raw name, from `ChannelResolution`. |
| `config_name` / `unit_assumption` | str | `Eeg` only | From the loaded `Config`, for provenance (see §6.3). |
| `label` | str | `Annotation`, `Marker` | Annotation description text, or `"code:<int>"` for channel-derived markers. |
| `source` | str | `Annotation`, `Marker` | `"annotation"` or the originating marker-channel name. |

### 6.2 Extractor output tensor schema

- **Dynamic mode:** `float32[C, T]`, `C = len(channels)` (≤4 for the current montage), `T = round(duration_s * resample_hz)`. Units: microvolts.
- **Static mode (bandpower):** `float32[C, B]`, `B = len(cfg.model["bands"])` (5 for the default delta/theta/alpha/beta/gamma set in `configs/project.example.yaml`). Units: µV²/Hz (absolute) or unitless ratio (relative), matching whichever of `model.features` is requested.
- Both modes carry an attached `segment` reference (per the paper's Segment abstraction) so the originating trigger event, timeline, and absolute recording offset remain traceable from any tensor — this is the mechanism by which "any processed tensor can be traced back to the exact version of the raw data" (paper §2.5, "Full Provenance").

### 6.3 Provenance/config schema (attached, not inferred)

Every `Eeg` event row must carry a `provenance` block reproducing the exact preprocessing chain applied, to satisfy NeuralSet's own provenance guarantee and NeXus NeuroMirror's existing "config over code" discipline:

```json
{
  "source_config": "configs/project.example.yaml",
  "config_name": "nexus-neuromirror",
  "unit_assumption": "volts (MNE-internal); EDF physical dimension expected uV",
  "resample_hz": 200.0,
  "resample_method": "fir",
  "bandpass_hz": [1.0, 40.0],
  "notch_hz": [50.0],
  "extractor_version": "<pinned adapter package version>",
  "neuralset_cache_key": "<exca-generated hash>",
  "verification_status": "ok",
  "diagnostic_json_path": "reports/uploads/<session>/diagnostic.json"
}
```

This block is metadata only — it is never used as a model input feature, and no field in it may be silently defaulted when missing; a missing `source_config` or `unit_assumption` should raise a build-time error in `NnmStudyBuilder`, mirroring `config.py`'s `ConfigError` philosophy of failing loud on structural problems rather than guessing.

---

## 7. Conversion boundaries

1. **EDF parsing boundary stays exactly where it is today.** All binary EDF/EDF+ reading remains inside `nexus_neuromirror.edf.read_edf`. The NeuralSet adapter layer never opens an EDF file directly — it only calls existing NeXus NeuroMirror functions and reshapes their return values into events/tensors. This preserves the architecture doc's principle that "the rest of the system depends only on an MNE `Raw` object" and isolates vendor specifics to one thin adapter.
2. **Verification boundary stays a hard gate, not a soft filter.** A session whose `VerificationResult.ok` is `False` must still be representable as an `Eeg` event (so its `hard_failures` are visible in the Study for auditing), but `NxsBioTraceEegExtractor.prepare()` must refuse to extract tensors for any timeline with `verification_status == "failed"` unless the caller explicitly passes `allow_failed=True` with a logged justification. This prevents silently training on disconnected-lead or wrong-sample-rate recordings.
3. **Unit boundary stays inside the Extractor, applied once.** Any µV conversion happens only via the existing `metrics.VOLTS_TO_UV` constant, reused (not reimplemented) inside the extractor's `prepare`/`extract` methods.
4. **Marker semantics boundary: no inferred labels.** `Annotation` and `Marker` events carry only what `markers.py` already detected (EDF+ annotation text, or `code:<int>` transitions on a candidate channel). The adapter must not invent semantic labels (e.g., mapping `code:2` to "eyes closed") unless that mapping is explicitly present in the project YAML's `markers` section or supplied by the experimenter — matching the existing code's own conservative behavior of keeping unlabeled annotations rather than dropping them (`markers._annotation_events`).
5. **Model/consciousness boundary.** Nothing produced by this integration (tensors, embeddings, cached features) may be described, logged, or surfaced as a measure of "consciousness," "awareness level," or any clinical construct. Output artifacts are limited to signal representations (raw/filtered EEG, bandpower) and their provenance. This boundary is a documentation/labeling constraint, enforced by convention and code review, not a runtime check — call sites and downstream READMEs must retain NeXus NeuroMirror's existing non-clinical disclaimer.
6. **Web upload boundary is unaffected.** The FastAPI upload/analysis path (`web/backend/nnm_web/analysis.py`, `security.py`, `storage.py`) continues to run `generate_report` exactly as today; NeuralSet integration is an **additional, optional consumer** of the same `data/uploads/**` EDF files and `reports/uploads/**/diagnostic.json` sidecars, invoked out-of-band (e.g., a batch job or notebook), not from the request path of the existing upload endpoint. This avoids adding NeuralSet/PyTorch as a runtime dependency of the web request handler and keeps the browser-facing latency budget (documented 8 MB upload cap, synchronous analysis) unchanged.

---

## 8. Event semantics

- **`Eeg` events are containers, not signals.** The tensor is never materialized until an Extractor's `extract()` runs inside a `Segment` — consistent with the paper's laziness guarantee that "only the final iteration triggers data loading and feature extraction" (Fig. 3 caption).
- **`Annotation` vs. `Marker` are kept as distinct types**, not merged into one generic "Event" type, because they have different reliability characteristics: EDF+ annotations are vendor/software-generated free text (can be empty or malformed), while marker-channel transitions are derived from a numeric step-detection heuristic (`markers._channel_events`) that assumes zero is "no code" and may misfire on noisy status channels. Keeping them separate preserves this distinction for any downstream filtering (e.g., "trust `Marker` over `Annotation` when both are present for the same nominal event").
- **Trigger semantics for `Segmenter`.** When using `marker_locked` segmentation, the Segment's trigger reference must resolve to the *specific* `Marker`/`Annotation` row that anchored it, not merely "some event within the window" — this mirrors the paper's explicit design goal that "each segment retains a reference to its trigger, so that extractors can distinguish... the particular word [event] that anchored a... window from the other [events] that happen to fall within it" (§2.3).
- **No cross-timeline joins in v1.** Per the paper's own stated limitation ("cross-session and cross-modality dependencies are not yet first-class citizens in the framework," Discussion §"Beyond time series"), this integration does not attempt to join sessions across subjects/days via relational semantics. Each BioTrace+ export is one self-contained timeline; cross-session analyses (e.g., comparing block 1 vs. block 2 bandpower) are handled by grouping on a `subject`/`session_group` metadata column in pandas after `Study.build()`, not inside NeuralSet's event-join machinery.

---

## 9. Preprocessing provenance

Provenance in this integration has two independent layers, both required, mirroring NeuralSet's own "Deterministic and Incremental Caching" and "Full Provenance" guarantees (paper §2.5):

1. **NeXus NeuroMirror-native provenance (unchanged).** `diagnostic.json` continues to be produced exactly as today by `report.generate_report`, and its repo-relative path is recorded in the Study events DataFrame's `provenance.diagnostic_json_path` field. This file remains the authoritative human-readable QC record.
2. **NeuralSet/exca cache provenance (new).** Every `Extractor.prepare()` call is decorated with an `exca.TaskInfra`-style cache key that is "a deterministic function of both its local configuration and the upstream data state" (paper §2.5). Concretely, the cache key for `NxsBioTraceEegExtractor` must incorporate: the EDF file path + modification time or content hash, `resample_hz`, `bandpass_hz`, `notch_hz`, and the extractor code version. Changing any one of these — e.g., widening the bandpass from `[1.0, 40.0]` to `[0.5, 45.0]` — must invalidate only the cached tensors for that parameter branch, leaving other cached extractions untouched, exactly as described for "a smoothing kernel width" in the paper's Parameter-Aware Storage bullet.

Both layers must agree: if `diagnostic.json` reports `verification_status: failed` for a timeline, the NeuralSet-side cache entry for that timeline's `Eeg` extractor must be tagged with the same status (§7.2) so a downstream researcher inspecting only the NeuralSet cache cannot lose the fact that the underlying recording failed validation.

---

## 10. Milestones

| Milestone | Deliverable | Depends on |
|---|---|---|
| M0 — Spec sign-off | This document reviewed and accepted; NeuralSet pinned to a specific released version/commit | — |
| M1 — `NnmStudyBuilder` | `build_events()` producing a validated events DataFrame from existing `data/uploads/**` sessions, unit-tested against the repo's synthetic EDF generator (`synth.py`) | M0 |
| M2 — `NxsBioTraceEegExtractor` (static: bandpower) | Extractor producing `[C, B]` bandpower tensors matching `model.bands` from `configs/project.example.yaml`, cached via exca | M1 |
| M3 — `NxsBioTraceEegExtractor` (dynamic: raw trace) | Same extractor configurable to emit `[C, T]` filtered/resampled time series | M2 |
| M4 — `NxsMarkerExtractor` + Segmenter presets | `sliding_window` and `marker_locked` presets producing `SegmentDataset`s from real sessions | M1, M3 |
| M5 — End-to-end PyTorch DataLoader demo | A notebook/script reproducing the paper's Fig. 3 flow (`Study → Events → Extractors → Segmenter → DataLoader`) on a NeXus NeuroMirror synthetic session, with no modification to `nexus_neuromirror/*` | M2–M4 |
| M6 — Provenance cross-check tooling | A script asserting `diagnostic.json` status matches NeuralSet cache metadata for every timeline in a Study (§9) | M5 |
| M7 — Optional cluster dispatch | exca `TaskInfra` configured for a documented HPC/cluster backend, verified on ≥1 non-local environment | M6 |
| M8 — Documentation & non-clinical disclaimer propagation | Adapter README explicitly restates the non-clinical/non-consciousness scope (§1); linked from any consuming notebook | M5 |

---

## 11. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **Marker-channel step detection is a heuristic**, not a vendor-confirmed protocol (`markers._channel_events` treats any nonzero-to-different-value transition as an event) | Spurious `Marker` events from channel noise could silently anchor `marker_locked` segments | Carry `source` channel name through to NeuralSet events; require a minimum-count or debounce check before trusting channel-derived markers in Segmenter triggers; keep `Annotation` and `Marker` types separate (§8) so this risk doesn't contaminate annotation-based analyses |
| **No public confirmed real-time SDK for NeXus-10** (`docs/architecture.md`, "Why not real-time?") | NeuralSet's DataLoader model, while lazy, is still fundamentally a batch/offline abstraction; there is no straightforward way to make this integration "live" without inventing an unverified streaming interface | Explicitly scope this integration to offline/blockwise EDF exports only, matching the existing architecture's block-wise closed loop; do not claim real-time capability |
| **Unit double-conversion (volts vs. µV)** is a known class of MNE integration bug | Silent 10^6-scale errors in bandpower/RMS features would invalidate any downstream model without an obvious symptom | Reuse `metrics.VOLTS_TO_UV` verbatim rather than reimplementing; add a unit test asserting extractor output RMS falls within the same physiological range (`validation.rms_uv_min/max`) already enforced by `verify.py` |
| **Cache key omits a relevant parameter**, causing stale tensors to be silently reused (a known general risk of hash-based caching systems, acknowledged implicitly by the paper's emphasis on "Parameter-Aware Storage") | Wrong dataset (stale content) is delivered to a model without a version-mismatch warning | Include a content hash (not just mtime) of the source EDF file in the cache key; add an M6 cross-check step (see Milestones) that fails the build if `diagnostic.json` and cache-recorded provenance disagree |
| **Small n (four channels, short recordings)** limits any embedding/model built on top from being statistically robust | Any bandpower or embedding-based classifier trained on this pipeline risks overfitting or false-positive "signal" | Out of scope for this spec (data-engineering only), but must be flagged in any downstream modeling proposal; do not present classifier outputs as validated findings |
| **Overclaiming NeuralSet's applicability to consciousness research** — NeuralSet's own paper positions it as Neuro-AI infrastructure for tasks like naturalistic stimulus decoding, not consciousness assessment | Reputational/scientific risk if the integration's purpose is described inaccurately | This spec and all derived documentation must describe the integration strictly as "PyTorch-ready data engineering for four-channel EEG neurofeedback research," per §1 |
| **Adding NeuralSet/PyTorch/exca as dependencies** to a project currently dependency-light (`pyproject.toml`) | Increases install footprint, especially in the web backend's request path if wired in incorrectly | Keep the NeuralSet adapter as a separate optional package/extra (e.g., `pip install -e ".[neuralset]"`), never imported by `web/backend/nnm_web/*` request handlers (§7.6) |
| **Concurrent modification of `nexus-neuromirror`** by another agent (explicit task constraint) | Any code sketch in this spec that assumes current file contents could drift before implementation | This spec cites exact current file contents/line-level behavior as of the time of writing; implementers must re-verify `config.py`, `edf.py`, `markers.py`, `metrics.py`, `verify.py`, `report.py` against the repository state at implementation time before wiring the adapter |

---

## 12. Integration tests

All tests target the **adapter layer only** (new code); they must not modify or duplicate `nexus_neuromirror`'s own test suite (`tests/test_*.py`), which already covers config/labels/markers/metrics/verify/report in isolation.

1. **`test_build_events_schema`** — Given the repo's synthetic EDF (via `nexus_neuromirror.synth`), assert `build_events()` returns a DataFrame with exactly the columns in §6.1, one `Eeg` row per input file, and `len(Annotation) + len(Marker) == markers.n_events` from the corresponding `MarkerReport`.
2. **`test_build_events_preserves_hard_failures`** — Feed a synthetic recording engineered to fail validation (e.g., truncated duration below `validation.min_duration_s`) and assert the resulting `Eeg` row's `hard_failures` list is non-empty and verbatim-matches `VerificationResult.hard_failures`.
3. **`test_extractor_refuses_failed_verification`** — Assert `NxsBioTraceEegExtractor.prepare()` raises (or returns an explicit skip marker) for any timeline with `verification_status == "failed"` unless `allow_failed=True` is passed (§7.2).
4. **`test_extractor_unit_consistency`** — Assert the RMS of a `dynamic=True` extractor's output, computed independently in the test, falls within `[validation.rms_uv_min, validation.rms_uv_max]` for a known-good synthetic signal, catching any volts/µV scale regression.
5. **`test_static_vs_dynamic_duality`** — For the same segment, assert `ToStatic`-style aggregation of the dynamic bandpower time series is numerically consistent with the static-mode extractor output (within floating-point tolerance), mirroring the paper's Fig. 4 static/dynamic conversion guarantee.
6. **`test_segmenter_trigger_reference`** — For `marker_locked` segmentation, assert each produced Segment's trigger event `onset_s` falls within `[segment.start, segment.start + segment.duration)` and correctly identifies the *specific* marker among several markers that may fall in the same window (§8).
7. **`test_cache_invalidation_on_param_change`** — Run `prepare()` twice with identical parameters (assert second run is a cache hit, e.g. via timing or an exca-exposed cache-hit flag) and once with a changed `bandpass_hz` (assert cache miss / recompute), verifying Parameter-Aware Storage behavior end-to-end.
8. **`test_provenance_cross_check`** — Given a session's `diagnostic.json` and the NeuralSet-side cached provenance block (§6.3, §9), assert `verification_status` and `unit_assumption` agree between the two; fail loudly (not silently) on mismatch.
9. **`test_no_pytorch_import_in_web_backend`** — Static check (e.g., `grep`/AST scan) asserting no module under `web/backend/nnm_web/` imports `neuralset`, `torch`, or the adapter package, enforcing the boundary in §7.6.
10. **`test_end_to_end_dataloader_smoke`** — Full pipeline smoke test: synthetic EDF → `build_events` → `NxsBioTraceEegExtractor` + `NxsMarkerExtractor` → `Segmenter` → `SegmentDataset` → one `DataLoader` batch iterated successfully, with tensor shapes matching §6.2 exactly, reproducing the paper's Fig. 3 pattern on NeXus NeuroMirror data.

---

## Sources

- NeuralSet paper (King, Bel, Evanson, et al., Meta FAIR), local copy: `/home/user/workspace/uploaded_attachments/cc1393d1e4a448119a4854b1135b1bb1/NeuralSet.pdf`; project code repository referenced in the paper: [https://github.com/facebookresearch/neuroai/](https://github.com/facebookresearch/neuroai/)
- NeXus NeuroMirror repository (read-only reference for this spec): `nexus-neuromirror/README.md`, `nexus-neuromirror/docs/architecture.md`, `nexus-neuromirror/configs/project.example.yaml`, `nexus-neuromirror/src/nexus_neuromirror/{config,edf,labels,markers,metrics,verify,report}.py`, `nexus-neuromirror/web/backend/nnm_web/analysis.py`

*This document does not modify any file under `nexus-neuromirror/`. All code excerpts are illustrative adapter sketches for a proposed new, separate module and are not applied to the existing codebase.*
