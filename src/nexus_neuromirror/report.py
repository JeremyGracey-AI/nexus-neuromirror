"""Report generation: JSON summary + PNG/SVG diagnostic figures.

Reads the recording once and reuses the MNE Raw for both metrics and plots.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import Config
from .edf import read_edf
from .metrics import VOLTS_TO_UV
from .verify import VerificationResult, verify_raw
from .viz import (
    plot_marker_timeline,
    plot_multichannel_trace,
    plot_psd,
)

IMAGE_FORMATS = ("png", "svg")


def _save_fig(fig: Any, out_dir: Path, stem: str) -> list[str]:
    written: list[str] = []
    for fmt in IMAGE_FORMATS:
        target = out_dir / f"{stem}.{fmt}"
        fig.savefig(target, format=fmt, bbox_inches="tight")
        written.append(str(target))
    import matplotlib.pyplot as plt

    plt.close(fig)
    return written


def generate_report(path: str | Path, cfg: Config, out_dir: str | Path) -> VerificationResult:
    """Verify a recording and write JSON + figures into ``out_dir``.

    Returns the :class:`VerificationResult` so the CLI can set its exit code.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = read_edf(path)
    result = verify_raw(raw, path, cfg)

    artifacts: list[str] = []

    # Figures use only the matched expected channels for clarity.
    matched = [r.matched_name for r in result.resolutions if r.matched_name]
    if matched:
        picks = [raw.ch_names.index(n) for n in matched]
        data_uv = np.asarray(raw.get_data(picks=picks)) * VOLTS_TO_UV
        sfreq = float(raw.info["sfreq"])

        fig = plot_multichannel_trace(matched, data_uv, sfreq, title="EEG trace")
        artifacts += _save_fig(fig, out_dir, "trace")

        fmax = min(40.0, sfreq / 2.0 - 1.0)
        fig = plot_psd(matched, data_uv, sfreq, fmax=fmax)
        artifacts += _save_fig(fig, out_dir, "psd")

    events = [(e.onset_s, e.label) for e in result.markers.events]
    if events:
        fig = plot_marker_timeline(events, result.info.duration_s)
        artifacts += _save_fig(fig, out_dir, "markers")

    payload = result.as_dict()
    payload["artifacts"] = artifacts
    json_path = out_dir / "diagnostic.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=False))

    return result
