# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-13

### Added
- Initial starter repository for the four-channel NeXus-10 + BioTrace+ AI
  neurofeedback prototype.
- `README.md` with project overview, safety/research disclaimer, four-channel
  montage (Fz, FCz, Pz, Oz), phased workflow, and pipeline diagrams.
- `docs/setup-checklist.md` covering hardware/software inventory, NeXus-10
  bring-up, BioTrace+ configuration, a 60-second diagnostic recording, EDF/EDF+
  export, marker verification, and a data-governance checklist.
- `docs/architecture.md` describing the offline-first / blockwise closed-loop
  design with component, sequence, and data-flow diagrams and a real-time
  SDK extension path.
- `configs/montage.yaml` and `configs/project.example.yaml`.
- `nexus_neuromirror` Python package: config loading, EDF verification through
  MNE, metrics, marker detection, and a matplotlib report/visualization layer.
- `nexus-neuromirror verify` CLI producing machine-readable JSON and
  PNG/SVG diagnostics, with nonzero exit on hard validation failure.
- Test suite based on synthetic MNE `RawArray` / temporary EDF exports.
- Packaging: `pyproject.toml`, `Makefile`, `.gitignore`, MIT `LICENSE`,
  `CONTRIBUTING.md`, and data-governance READMEs under `data/` and `reports/`.
