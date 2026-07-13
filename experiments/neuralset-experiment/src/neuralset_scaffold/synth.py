"""Synthetic demo-data generator.

Produces a continuous four-channel recording (Fz, FCz, Pz, Oz) with two event
classes that differ in a physiologically plausible but entirely synthetic way:

- class "A": enhanced ~10 Hz (alpha), strongest posteriorly (Pz, Oz)
- class "B": enhanced ~20 Hz (beta), strongest anteriorly (Fz, FCz)

The classes are separable *above chance* but not perfectly, because broadband
noise and inter-trial variability are added. No real neural data is involved
and nothing here represents a mental state, diagnosis, or "decoded" content.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CHANNELS = ("Fz", "FCz", "Pz", "Oz")


def _pink_like(rng: np.random.Generator, n: int) -> np.ndarray:
    white = rng.standard_normal(n)
    kernel = np.ones(16) / 16.0
    return np.convolve(white, kernel, mode="same")


def generate_synthetic(
    *,
    sfreq_hz: float = 256.0,
    n_sessions: int = 3,
    trials_per_class: int = 20,
    trial_len_s: float = 3.0,
    iti_s: float = 1.0,
    noise_uv: float = 28.0,
    effect_uv: float = 2.0,
    seed: int = 17,
) -> pd.DataFrame:
    """Return a tidy DataFrame: time, Fz, FCz, Pz, Oz, marker, session."""
    rng = np.random.default_rng(seed)
    trial_n = int(trial_len_s * sfreq_hz)
    iti_n = int(iti_s * sfreq_hz)

    frames: list[pd.DataFrame] = []
    t_global = 0.0
    for s in range(n_sessions):
        session_id = f"session-{s + 1}"
        # Balanced, shuffled trial order.
        order = np.array(["A"] * trials_per_class + ["B"] * trials_per_class)
        rng.shuffle(order)

        # Slight per-session amplitude drift to make sessions non-identical.
        sess_gain = 1.0 + 0.1 * rng.standard_normal()

        seg_channels = {ch: [] for ch in CHANNELS}
        seg_marker: list[str] = []
        seg_time: list[float] = []

        for label in order:
            total_n = trial_n + iti_n
            tt = np.arange(total_n) / sfreq_hz
            # Background noise per channel.
            for ch in CHANNELS:
                seg_channels[ch].append(noise_uv * _pink_like(rng, total_n))

            # Class-specific oscillation only during the trial portion.
            trial_mask = np.zeros(total_n)
            trial_mask[:trial_n] = np.hanning(trial_n) if trial_n > 1 else 1.0
            if label == "A":
                freq = 10.0
                weights = {"Fz": 0.3, "FCz": 0.4, "Pz": 0.9, "Oz": 1.0}
            else:
                freq = 20.0
                weights = {"Fz": 1.0, "FCz": 0.9, "Pz": 0.4, "Oz": 0.3}
            phase = rng.uniform(0, 2 * np.pi)
            osc = np.sin(2 * np.pi * freq * tt + phase) * trial_mask
            for ch in CHANNELS:
                amp = effect_uv * sess_gain * weights[ch] * (0.85 + 0.3 * rng.random())
                seg_channels[ch][-1] = seg_channels[ch][-1] + amp * osc

            # Marker at the trial onset only.
            marker_col = [""] * total_n
            marker_col[0] = label
            seg_marker.extend(marker_col)
            seg_time.extend((t_global + tt).tolist())
            t_global += total_n / sfreq_hz

        df = pd.DataFrame(
            {
                "time": seg_time,
                **{ch: np.concatenate(seg_channels[ch]) for ch in CHANNELS},
                "marker": seg_marker,
                "session": session_id,
            }
        )
        frames.append(df)

    out = pd.concat(frames, ignore_index=True)
    out["time"] = np.arange(len(out)) / sfreq_hz  # monotonic global clock
    return out


def write_synthetic(path: str, *, sep: str | None = None, **kwargs) -> str:
    """Generate synthetic data and write it to CSV (``,``) or TSV (``\\t``)."""
    df = generate_synthetic(**kwargs)
    if sep is None:
        sep = "\t" if str(path).lower().endswith((".tsv", ".tab")) else ","
    df.to_csv(path, sep=sep, index=False)
    return path
