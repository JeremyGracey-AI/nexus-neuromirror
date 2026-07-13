# NeuralSet Experiment Scaffold

A standalone, executable **first-experiment scaffold** for four-channel EEG
recordings exported from a NeXus-10 / BioTrace+ setup (midline chain
**Fz, FCz, Pz, Oz** plus an event-marker column).

It takes a tidy CSV/TSV recording and runs a complete, conservative baseline
pipeline:

1. **Validate** the file and all four raw channels (with header-alias matching).
2. **Validate and normalize** event markers into discrete onset events.
3. **Preprocess** conservatively: detrend → notch → band-pass → resample, then
   **flag** artifacts (amplitude + gradient) — samples are *never silently
   deleted*.
4. **Window** the signal into event-aligned 1–4 s epochs (out-of-bounds and
   heavily-artifacted windows are dropped, and the drops are *counted*).
5. **Featurize** with Welch band power (absolute log + relative) per channel/band.
6. **Evaluate** a small baseline classifier (logistic regression or LDA) with
   **session-aware cross-validation** (leave-one-session-out / GroupKFold) so
   windows from one session never leak across train/test.
7. **Emit** `metrics.json` plus diagnostic plots.

A `synth` command generates **synthetic demo data** so the whole pipeline is
runnable with no private files. An optional **NeuralSet adapter** boundary is
exposed but never required — the scaffold runs fully without it.

> **Scope / disclaimer.** This is an experimental signal-processing and
> machine-learning scaffold on synthetic or user-supplied data. It makes **no
> medical, diagnostic, or mental-state claims**, and it does **not** decode
> consciousness or any private mental content. "Class A / B" are arbitrary
> experimental condition labels that you define.

## Install

Requires Python 3.10+.

```bash
cd /home/user/workspace/neuralset-experiment-scaffold
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Runtime dependencies: `numpy`, `scipy`, `pandas`, `scikit-learn`, `matplotlib`,
`PyYAML`. The `[dev]` extra adds `pytest` and `ruff`.

## Quick start (demo — no data needed)

Generate synthetic data and run the full experiment end-to-end:

```bash
neuralset-scaffold demo --out outputs/demo
```

This writes `outputs/demo/demo_data.csv`, `outputs/demo/metrics.json`, and five
diagnostic plots, and prints a summary (validation, events, windows, features,
CV accuracy vs. chance).

## Commands

All commands are also available as `python -m neuralset_scaffold.cli ...`.

### Generate synthetic data

```bash
neuralset-scaffold synth --out data/demo.csv --sessions 3 --trials 20 --sfreq 256 --seed 17
```

Write a `.tsv` extension to get tab-separated output.

### Validate a recording

```bash
neuralset-scaffold validate data/demo.csv
```

Prints a JSON validation report (resolved columns, inferred sample rate,
warnings/errors). Exit code `0` if usable, `1` if not.

### Run the full experiment

```bash
neuralset-scaffold run data/demo.csv --out outputs/run
```

Add `--config configs/default.yaml` to use an explicit config, or `--no-plots`
to skip figure generation.

## Input format

Tidy CSV/TSV, one row per sample (see `data/README.md`):

| time | Fz | FCz | Pz | Oz | marker | session |
|------|----|-----|----|----|--------|---------|

- `time` (optional): seconds; sample rate is inferred from it (falls back to
  `columns.sample_rate_hz`).
- Channels: amplitudes in microvolts. Header aliases such as `EEG Fz-A1A2` or
  `Ch1` are accepted (configured in `configs/default.yaml`).
- `marker`: event label at each event's onset row; empty / `0` elsewhere.
- `session`: recording-session id, enabling session-aware cross-validation.

## Configuration

Copy and edit `configs/default.yaml`. Key knobs: channel aliases, notch
(`50`/`60` Hz), band-pass, resample rate, artifact thresholds, window length
(1–4 s), feature bands, and model (`logreg`/`lda`, CV splits).

## Outputs

Into the `--out` directory (see `outputs/README.md`):

- `metrics.json` — validation report, event/window summary, preprocessing
  steps, CV metrics per fold, confusion matrix, top features, NeuralSet status.
- `trace.png`, `psd.png`, `confusion.png`, `fold_accuracy.png`,
  `feature_importance.png`.

`data/` and `outputs/` are git-ignored (except their READMEs) — **do not commit
real neural data**.

## NeuralSet adapter (optional)

`src/neuralset_scaffold/neuralset_adapter.py` is a stable seam for a NeuralSet
backend. If the `neuralset` package is importable, `is_available()` returns
`True`; otherwise the scaffold uses its built-in spectral features. No NeuralSet
API is fabricated — `NeuralSetAdapter.transform()` is an explicit wiring point.

```bash
pip install -e ".[neuralset]"   # optional extra
```

## Development

```bash
pytest            # run the test suite (uses synthetic data only)
ruff check src tests
```

## License

MIT — see `LICENSE`.
