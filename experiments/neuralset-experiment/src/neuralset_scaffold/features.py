"""Baseline spectral features: per-channel absolute and relative band power."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal
from scipy.integrate import trapezoid

from .windows import WindowSet


@dataclass
class FeatureMatrix:
    X: np.ndarray                  # (n_windows, n_features)
    y: np.ndarray                  # (n_windows,) str
    groups: np.ndarray             # (n_windows,) session id
    feature_names: list[str]

    @property
    def shape(self) -> tuple[int, int]:
        return self.X.shape


def _bandpower(psd: np.ndarray, freqs: np.ndarray, lo: float, hi: float) -> float:
    mask = (freqs >= lo) & (freqs < hi)
    if not mask.any():
        return 0.0
    return float(trapezoid(psd[mask], freqs[mask]))


def compute_features(windows: WindowSet, bands: dict[str, list[float]]) -> FeatureMatrix:
    """Welch PSD per channel, then absolute + relative band power features."""
    n_win = windows.n_windows
    channels = windows.channels
    band_items = list(bands.items())
    feature_names: list[str] = []
    for ch in channels:
        for name, _ in band_items:
            feature_names.append(f"{ch}:{name}:abs")
        for name, _ in band_items:
            feature_names.append(f"{ch}:{name}:rel")

    if n_win == 0:
        return FeatureMatrix(
            X=np.empty((0, len(feature_names))),
            y=windows.labels,
            groups=windows.sessions,
            feature_names=feature_names,
        )

    sfreq = windows.sfreq_hz
    nperseg = min(windows.data_uv.shape[2], int(sfreq))
    nperseg = max(nperseg, 16)

    rows = []
    for w in range(n_win):
        feats: list[float] = []
        for c in range(len(channels)):
            freqs, psd = signal.welch(windows.data_uv[w, c], fs=sfreq, nperseg=nperseg)
            abs_powers = [_bandpower(psd, freqs, lo, hi) for _, (lo, hi) in band_items]
            total = float(sum(abs_powers)) or 1.0
            rel_powers = [p / total for p in abs_powers]
            # log-abs stabilizes scale across channels/sessions.
            feats.extend([float(np.log(p + 1e-12)) for p in abs_powers])
            feats.extend(rel_powers)
        rows.append(feats)

    X = np.asarray(rows, dtype=np.float64)
    return FeatureMatrix(
        X=X, y=windows.labels, groups=windows.sessions, feature_names=feature_names
    )
