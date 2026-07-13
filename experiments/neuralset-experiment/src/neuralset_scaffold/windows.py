"""Event-aligned windowing (1-4 s) over preprocessed data."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .config import Windows
from .markers import extract_events
from .preprocess import Preprocessed


@dataclass
class WindowSet:
    data_uv: np.ndarray            # (n_windows, n_channels, n_samples)
    labels: np.ndarray             # (n_windows,) str
    sessions: np.ndarray           # (n_windows,) str
    channels: list[str]
    sfreq_hz: float
    length_s: float
    n_dropped_artifact: int = 0
    n_dropped_bounds: int = 0
    dropped_detail: list[str] = field(default_factory=list)

    @property
    def n_windows(self) -> int:
        return self.data_uv.shape[0]

    def as_dict(self) -> dict[str, object]:
        counts: dict[str, int] = {}
        for label in self.labels.tolist():
            counts[label] = counts.get(label, 0) + 1
        return {
            "n_windows": self.n_windows,
            "class_counts": counts,
            "sessions": sorted(set(self.sessions.tolist())),
            "length_s": self.length_s,
            "sfreq_hz": self.sfreq_hz,
            "n_dropped_artifact": self.n_dropped_artifact,
            "n_dropped_bounds": self.n_dropped_bounds,
        }


def make_windows(pre: Preprocessed, cfg: Windows, *, label_map: dict[str, str] | None = None) -> WindowSet:
    """Cut event-aligned windows; drop out-of-bounds and heavily-artifacted ones."""
    events = extract_events(pre.marker_raw, pre.sfreq_hz, pre.session, label_map=label_map)
    win_n = int(round(cfg.length_s * pre.sfreq_hz))
    offset_n = int(round(cfg.offset_s * pre.sfreq_hz))
    total = pre.n_samples

    data_list: list[np.ndarray] = []
    labels: list[str] = []
    sessions: list[str] = []
    n_drop_art = 0
    n_drop_bounds = 0
    detail: list[str] = []

    for ev in events.events:
        start = ev.onset_sample + offset_n
        end = start + win_n
        if start < 0 or end > total:
            n_drop_bounds += 1
            detail.append(f"bounds: {ev.label}@{ev.onset_s:.2f}s")
            continue
        flag_frac = float(pre.artifact_flags[:, start:end].mean())
        if flag_frac > cfg.max_artifact_fraction:
            n_drop_art += 1
            detail.append(f"artifact({flag_frac:.2f}): {ev.label}@{ev.onset_s:.2f}s")
            continue
        data_list.append(pre.data_uv[:, start:end])
        labels.append(ev.label)
        sessions.append(ev.session)

    if data_list:
        data = np.stack(data_list, axis=0)
    else:
        data = np.empty((0, len(pre.channels), win_n))

    return WindowSet(
        data_uv=data,
        labels=np.array(labels, dtype=object),
        sessions=np.array(sessions, dtype=object),
        channels=list(pre.channels),
        sfreq_hz=pre.sfreq_hz,
        length_s=cfg.length_s,
        n_dropped_artifact=n_drop_art,
        n_dropped_bounds=n_drop_bounds,
        dropped_detail=detail,
    )
