"""Minimal, accessible diagnostic visualizations.

Design constraints (see project styling requirements):
- neutral background, no decorative graphics
- teal primary (#20808D), rust secondary (#A84B2F)
- direct labels rather than legends where practical
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless / deterministic rendering

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

TEAL = "#20808D"
RUST = "#A84B2F"
INK = "#222222"
GRID = "#DDDDDD"
BG = "#FFFFFF"

_BASE_RC = {
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 10,
    "figure.dpi": 110,
}


def _welch(x: np.ndarray, sfreq: float, nperseg: int) -> tuple[np.ndarray, np.ndarray]:
    """Simple Welch PSD estimate (Hann window, 50% overlap) in uV^2/Hz.

    Kept dependency-light (NumPy only) and adequate for a diagnostic view.
    """
    n = x.size
    nperseg = int(min(nperseg, n))
    if nperseg < 8:
        freqs = np.fft.rfftfreq(max(n, 1), d=1.0 / sfreq)
        return freqs, np.zeros_like(freqs)
    step = max(nperseg // 2, 1)
    window = np.hanning(nperseg)
    win_power = np.sum(window**2)
    segments = range(0, n - nperseg + 1, step)
    acc = np.zeros(nperseg // 2 + 1)
    count = 0
    for start in segments:
        seg = x[start : start + nperseg] * window
        spec = np.abs(np.fft.rfft(seg)) ** 2
        acc += spec
        count += 1
    if count == 0:
        count = 1
    psd = acc / (count * win_power * sfreq)
    psd[1:-1] *= 2.0  # one-sided correction
    freqs = np.fft.rfftfreq(nperseg, d=1.0 / sfreq)
    return freqs, psd


def plot_multichannel_trace(
    names: list[str],
    data_uv: np.ndarray,
    sfreq: float,
    *,
    window_s: float = 5.0,
    title: str = "Multichannel trace",
) -> plt.Figure:
    """Stacked short trace of each channel with a shared scale bar."""
    with plt.rc_context(_BASE_RC):
        n_ch = len(names)
        n_show = int(min(window_s * sfreq, data_uv.shape[1])) if data_uv.size else 0
        t = np.arange(n_show) / sfreq
        fig, ax = plt.subplots(figsize=(9, 1.2 * max(n_ch, 1) + 1))

        seg = data_uv[:, :n_show] if n_show else data_uv
        spread = float(np.nanmax(np.abs(seg))) if seg.size else 1.0
        offset = spread * 2.2 if spread > 0 else 1.0

        for i, name in enumerate(names):
            y = seg[i] if seg.size else np.zeros_like(t)
            base = (n_ch - 1 - i) * offset
            color = TEAL if i % 2 == 0 else RUST
            ax.plot(t, y + base, color=color, linewidth=0.8)
            ax.text(-0.01 * (t[-1] if t.size else 1), base, name,
                    ha="right", va="center", fontweight="bold")

        ax.set_yticks([])
        ax.set_xlabel("Time (s)")
        ax.set_title(f"{title} (first {window_s:g}s)")
        ax.margins(x=0)
        fig.tight_layout()
        return fig


def plot_psd(
    names: list[str],
    data_uv: np.ndarray,
    sfreq: float,
    *,
    fmax: float = 40.0,
    title: str = "Power spectral density",
) -> plt.Figure:
    """Per-channel Welch PSD on a log-y axis up to ``fmax``."""
    with plt.rc_context(_BASE_RC):
        fig, ax = plt.subplots(figsize=(9, 5))
        nperseg = int(min(sfreq * 2, data_uv.shape[1])) if data_uv.size else 256
        colors = _color_cycle(len(names))
        for i, name in enumerate(names):
            freqs, psd = _welch(data_uv[i], sfreq, nperseg)
            mask = freqs <= fmax
            ax.semilogy(freqs[mask], psd[mask] + 1e-12, color=colors[i], linewidth=1.2, label=name)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel(r"PSD ($\mu V^2/Hz$)")
        ax.set_title(title)
        ax.set_xlim(0, fmax)
        ax.legend(frameon=False, ncol=min(len(names), 4), loc="upper right")
        fig.tight_layout()
        return fig


def plot_marker_timeline(
    events: list[tuple[float, str]],
    duration_s: float,
    *,
    title: str = "Marker timeline",
) -> plt.Figure:
    """Timeline of event onsets; distinct labels get distinct colors."""
    with plt.rc_context(_BASE_RC):
        fig, ax = plt.subplots(figsize=(9, 2.6))
        labels = sorted({lbl for _, lbl in events})
        colors = _color_cycle(len(labels))
        color_for = {lbl: colors[i] for i, lbl in enumerate(labels)}
        for onset, lbl in events:
            ax.axvline(onset, color=color_for[lbl], linewidth=1.2, alpha=0.9)
        # Direct labels: one handle per distinct label for a compact legend.
        for lbl in labels:
            ax.plot([], [], color=color_for[lbl], label=lbl)
        ax.set_xlim(0, max(duration_s, 1e-6))
        ax.set_yticks([])
        ax.set_xlabel("Time (s)")
        ax.set_title(f"{title} ({len(events)} events)")
        if labels:
            ax.legend(frameon=False, ncol=min(len(labels), 5), loc="upper right", fontsize=8)
        fig.tight_layout()
        return fig


def _color_cycle(n: int) -> list[str]:
    base = [TEAL, RUST, "#3B6E75", "#C97A5E", "#14565E", "#7A2E18"]
    if n <= len(base):
        return base[:n]
    return [base[i % len(base)] for i in range(n)]
