# Contributing

Thanks for your interest in improving NeXus NeuroMirror. This is a research
prototype; contributions should keep the codebase small, readable, and correct.

## Ground rules

- **No neural data in the repo.** Never commit `.edf`/`.bdf`/`.fif` recordings
  or generated reports. See [`data/README.md`](data/README.md) and
  [`reports/README.md`](reports/README.md).
- **No unverifiable vendor claims.** In particular, do not state that a public
  real-time NeXus-10 SDK exists. The design is offline-first / blockwise.
- Keep dependencies conservative. Prefer the standard library and the existing
  stack (MNE, NumPy, matplotlib, PyYAML) before adding anything new.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
make install-dev
```

## Before opening a PR

```bash
make check   # ruff + mypy + pytest
```

- Add or update tests for any behavior change. Tests must run without private
  BioTrace files — use synthetic MNE `RawArray` fixtures or temporary EDF
  exports.
- Update `CHANGELOG.md` under `[Unreleased]`.
- Keep documentation (README, `docs/`) consistent with code and configs.

## Commit / PR style

- Small, focused commits with imperative subject lines.
- PR descriptions should state what changed and how it was tested.
