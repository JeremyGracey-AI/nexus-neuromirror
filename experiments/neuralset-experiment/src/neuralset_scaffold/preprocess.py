"""Conservative preprocessing: notch, bandpass, resample, artifact flagging.

Design choice: artifacts are **flagged, never silently deleted**. Downstream
windowing decides whether to drop a window based on its flagged fraction, and
that decision is counted and reported.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal

from .config import Preprocess
from .io import Recording


@dataclass
class Preprocessed:
    channels: list[str]
    data_uv: np.ndarray            # (4, n) filtered, resampled
    sfreq_hz: float                # post-resample rate
    artifact_flags: np.ndarray     # (4, n) bool, True == flagged sample
    marker_raw: np.ndarray         # resampled-aligned per-sample markers
    session: np.ndarray            # resampled-aligned per-sample session
    steps: list[str]

    @property
    def n_samples(self) -> int:
        return self.data_uv.shape[1]

    @property
    def artifact_fraction(self) -> float:
        return float(self.artifact_flags.mean()) if self.artifact_flags.size else 0.0


def _apply_notch(data: np.ndarray, sfreq: float, freqs: list[float], q: float = 30.0) -> np.ndarray:
    out = data
    nyq = sfreq / 2.0
    for f0 in freqs:
        if 0 < f0 < nyq:
            b, a = signal.iirnotch(f0, q, sfreq)
            out = signal.filtfilt(b, a, out, axis=1)
    return out


def _apply_bandpass(data: np.ndarray, sfreq: float, lo: float, hi: float) -> np.ndarray:
    nyq = sfreq / 2.0
    hi = min(hi, nyq * 0.99)
    sos = signal.butter(4, [lo / nyq, hi / nyq], btype="band", output="sos")
    return signal.sosfiltfilt(sos, data, axis=1)


def _resample_markers(marker_raw: np.ndarray, n_in: int, n_out: int) -> np.ndarray:
    """Map per-sample markers to the resampled grid, preserving onset labels."""
    out = np.array([""] * n_out, dtype=object)
    if n_in == 0 or n_out == 0:
        return out
    for i, raw in enumerate(marker_raw):
        s = "" if raw is None else str(raw).strip()
        if s:
            j = min(int(round(i * (n_out - 1) / max(n_in - 1, 1))), n_out - 1)
            if out[j] == "":
                out[j] = s
    return out


def _resample_labels(labels: np.ndarray, n_out: int) -> np.ndarray:
    n_in = len(labels)
    if n_in == 0:
        return np.array(["session-1"] * n_out, dtype=object)
    idx = np.clip((np.arange(n_out) * (n_in - 1) / max(n_out - 1, 1)).round().astype(int), 0, n_in - 1)
    return labels[idx]


def preprocess(rec: Recording, cfg: Preprocess) -> Preprocessed:
    """Filter, resample, and flag artifacts. Never removes samples."""
    steps: list[str] = []
    data = rec.data_uv.astype(np.float64)
    sfreq = rec.sfreq_hz

    # Detrend (remove DC / slow drift per channel) before filtering.
    data = signal.detrend(data, axis=1, type="constant")
    steps.append("detrend(constant)")

    if cfg.notch_hz:
        data = _apply_notch(data, sfreq, cfg.notch_hz)
        steps.append(f"notch{cfg.notch_hz}")

    data = _apply_bandpass(data, sfreq, cfg.bandpass_hz[0], cfg.bandpass_hz[1])
    steps.append(f"bandpass{list(cfg.bandpass_hz)}")

    # Resample to the target rate.
    n_in = data.shape[1]
    target = cfg.resample_hz
    if abs(target - sfreq) > 1e-6:
        n_out = max(int(round(n_in * target / sfreq)), 1)
        data = signal.resample(data, n_out, axis=1)
        marker_rs = _resample_markers(rec.marker_raw, n_in, n_out)
        session_rs = _resample_labels(rec.session, n_out)
        sfreq = target
        steps.append(f"resample->{target}Hz")
    else:
        n_out = n_in
        marker_rs = rec.marker_raw.copy()
        session_rs = rec.session.copy()

    # Artifact flags (non-destructive): absolute amplitude and per-sample gradient.
    flags = np.zeros_like(data, dtype=bool)
    flags |= np.abs(data) > cfg.artifact_amp_uv
    grad = np.abs(np.diff(data, axis=1, prepend=data[:, :1]))
    flags |= grad > cfg.artifact_grad_uv
    steps.append(
        f"artifact_flag(amp>{cfg.artifact_amp_uv}uV, grad>{cfg.artifact_grad_uv}uV)"
    )

    return Preprocessed(
        channels=list(rec.channels),
        data_uv=data,
        sfreq_hz=sfreq,
        artifact_flags=flags,
        marker_raw=marker_rs,
        session=session_rs,
        steps=steps,
    )
