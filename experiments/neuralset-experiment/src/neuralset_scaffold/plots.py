"""Diagnostic plots (headless matplotlib). Restrained, direct-labeled styling."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import signal  # noqa: E402

from .features import FeatureMatrix  # noqa: E402
from .model import EvalResult  # noqa: E402
from .preprocess import Preprocessed  # noqa: E402

TEAL = "#20808D"
RUST = "#A84B2F"
INK = "#222222"
GRID = "#DDDDDD"

_RC = {
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": INK,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 10,
    "figure.dpi": 110,
}


def _palette(n: int) -> list[str]:
    base = [TEAL, RUST, "#3B6E75", "#C97A5E", "#14565E", "#7A2E18"]
    return [base[i % len(base)] for i in range(n)]


def save_all(pre: Preprocessed, feats: FeatureMatrix, result: EvalResult, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    with plt.rc_context(_RC):
        written.append(_save(_plot_trace(pre), out_dir / "trace.png"))
        written.append(_save(_plot_psd(pre), out_dir / "psd.png"))
        written.append(_save(_plot_confusion(result), out_dir / "confusion.png"))
        written.append(_save(_plot_folds(result), out_dir / "fold_accuracy.png"))
        fi = _plot_feature_importance(result)
        if fi is not None:
            written.append(_save(fi, out_dir / "feature_importance.png"))
    return written


def _save(fig: plt.Figure, path: Path) -> str:
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def _plot_trace(pre: Preprocessed, window_s: float = 5.0) -> plt.Figure:
    n_ch = len(pre.channels)
    n_show = int(min(window_s * pre.sfreq_hz, pre.n_samples))
    t = np.arange(n_show) / pre.sfreq_hz
    seg = pre.data_uv[:, :n_show]
    spread = float(np.nanmax(np.abs(seg))) if seg.size else 1.0
    offset = spread * 2.2 if spread > 0 else 1.0
    fig, ax = plt.subplots(figsize=(9, 1.1 * n_ch + 1))
    colors = _palette(n_ch)
    for i, ch in enumerate(pre.channels):
        base = (n_ch - 1 - i) * offset
        ax.plot(t, seg[i] + base, color=colors[i], linewidth=0.8)
        # Overlay flagged samples.
        flg = pre.artifact_flags[i, :n_show]
        if flg.any():
            ax.plot(t[flg], (seg[i] + base)[flg], ".", color="black", markersize=1.5)
        ax.text(-0.01 * (t[-1] if t.size else 1), base, ch, ha="right", va="center", fontweight="bold")
    ax.set_yticks([])
    ax.set_xlabel("Time (s)")
    ax.set_title(f"Preprocessed trace (first {window_s:g}s; black dots = artifact-flagged)")
    ax.margins(x=0)
    fig.tight_layout()
    return fig


def _plot_psd(pre: Preprocessed, fmax: float = 45.0) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = _palette(len(pre.channels))
    nperseg = min(pre.n_samples, int(pre.sfreq_hz * 2)) or 16
    for i, ch in enumerate(pre.channels):
        freqs, psd = signal.welch(pre.data_uv[i], fs=pre.sfreq_hz, nperseg=max(nperseg, 16))
        mask = freqs <= fmax
        ax.semilogy(freqs[mask], psd[mask] + 1e-12, color=colors[i], linewidth=1.2, label=ch)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel(r"PSD ($\mu V^2/Hz$)")
    ax.set_title("Power spectral density (whole recording)")
    ax.set_xlim(0, fmax)
    ax.legend(frameon=False, ncol=len(pre.channels))
    fig.tight_layout()
    return fig


def _plot_confusion(result: EvalResult) -> plt.Figure:
    cm = np.asarray(result.confusion)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(cm, cmap="BuGn")
    ax.set_xticks(range(len(result.classes)), result.classes)
    ax.set_yticks(range(len(result.classes)), result.classes)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Confusion matrix (pooled CV)")
    thresh = cm.max() / 2 if cm.size else 0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > thresh else INK)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig


def _plot_folds(result: EvalResult) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7, 4))
    folds = [f.fold for f in result.folds]
    accs = [f.accuracy for f in result.folds]
    ax.bar(folds, accs, color=TEAL, width=0.6)
    ax.axhline(result.chance_level, color=RUST, linestyle="--", label=f"chance {result.chance_level:.2f}")
    ax.axhline(result.mean_accuracy, color=INK, linestyle=":", label=f"mean {result.mean_accuracy:.2f}")
    ax.set_ylim(0, 1)
    ax.set_xlabel("CV fold")
    ax.set_ylabel("Accuracy")
    ax.set_title(f"Per-fold accuracy ({result.cv_scheme})")
    ax.set_xticks(folds)
    ax.legend(frameon=False)
    fig.tight_layout()
    return fig


def _plot_feature_importance(result: EvalResult) -> plt.Figure | None:
    if not result.feature_importance:
        return None
    items = sorted(result.feature_importance.items(), key=lambda kv: abs(kv[1]))[-12:]
    names = [k for k, _ in items]
    vals = [abs(v) for _, v in items]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(range(len(names)), vals, color=TEAL)
    ax.set_yticks(range(len(names)), names)
    ax.set_xlabel("Mean |coefficient| across folds")
    ax.set_title("Top baseline features")
    fig.tight_layout()
    return fig
