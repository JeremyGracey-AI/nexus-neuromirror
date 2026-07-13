# data/ (git-ignored)

Place your own CSV/TSV recordings here. Everything except this README is
git-ignored — **do not commit real neural data**.

Expected tidy format (one row per sample):

| time | Fz | FCz | Pz | Oz | marker | session |
|------|----|-----|----|----|--------|---------|

- `time` (optional): seconds; the sample rate is inferred from it.
- `Fz, FCz, Pz, Oz`: channel amplitudes in microvolts. Header aliases such as
  `EEG Fz-A1A2` or `Ch1` are accepted (see `configs/default.yaml`).
- `marker`: event label at each event's onset row; empty / `0` elsewhere.
- `session`: recording-session id, used for session-aware cross-validation.

No medical or mental-state claims are made; labels are whatever experimental
conditions you define.
