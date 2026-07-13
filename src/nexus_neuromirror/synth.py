"""Synthetic recording generator for demos and tests.

Produces an MNE ``RawArray`` that resembles a four-channel NeXus-10 export:
midline EEG channels with an occipital alpha rhythm, a marker/status channel,
and EDF+ annotations. No real neural data is involved.
"""

from __future__ import annotations

import mne
import numpy as np


def make_synthetic_raw(
    *,
    sfreq: float = 256.0,
    duration_s: float = 60.0,
    seed: int = 7,
    channel_names: tuple[str, ...] = ("EEG Fz-A1A2", "EEG FCz-A1A2", "EEG Pz-A1A2", "EEG Oz-A1A2"),
    add_marker_channel: bool = True,
    add_annotations: bool = True,
) -> mne.io.RawArray:
    """Build a synthetic Raw. EEG data is generated in volts (MNE convention)."""
    rng = np.random.default_rng(seed)
    n = int(sfreq * duration_s)
    t = np.arange(n) / sfreq

    signals: list[np.ndarray] = []
    # Pink-ish background + channel-specific rhythms, scaled to ~tens of uV.
    for i, _name in enumerate(channel_names):
        noise = rng.standard_normal(n)
        # 1/f-ish smoothing
        kernel = np.ones(8) / 8.0
        noise = np.convolve(noise, kernel, mode="same")
        alpha_amp = 15.0 if i == len(channel_names) - 1 else 6.0  # strongest at Oz
        alpha = alpha_amp * np.sin(2 * np.pi * 10.0 * t + rng.uniform(0, 2 * np.pi))
        theta = 4.0 * np.sin(2 * np.pi * 6.0 * t + rng.uniform(0, 2 * np.pi))
        micro_v = 20.0 * noise + alpha + theta
        signals.append(micro_v * 1e-6)  # uV -> V

    ch_names = list(channel_names)
    ch_types = ["eeg"] * len(channel_names)

    if add_marker_channel:
        marker = np.zeros(n)
        # Two block codes alternating every 10 s.
        for k, onset in enumerate(np.arange(5.0, duration_s, 10.0)):
            start = int(onset * sfreq)
            end = min(int((onset + 0.05) * sfreq), n)  # brief pulse
            marker[start:end] = 1 if k % 2 == 0 else 2
        signals.append(marker)
        ch_names.append("Status")
        ch_types.append("stim")

    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)
    raw = mne.io.RawArray(np.vstack(signals), info, verbose="ERROR")

    if add_annotations:
        onsets = list(np.arange(5.0, duration_s, 10.0))
        descriptions = [f"cue/block-{'A' if k % 2 == 0 else 'B'}" for k in range(len(onsets))]
        raw.set_annotations(
            mne.Annotations(onset=onsets, duration=[0.0] * len(onsets), description=descriptions)
        )
    return raw


def export_synthetic_edf(path: str, **kwargs) -> str:
    """Write a synthetic recording to an EDF file at ``path``. Returns the path."""
    raw = make_synthetic_raw(**kwargs)
    mne.export.export_raw(path, raw, fmt="edf", overwrite=True, verbose="ERROR")
    return path
