"""Event/marker detection from EDF+ annotations and candidate marker channels."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .config import Markers
from .labels import contains_token, match_alias


@dataclass(frozen=True)
class MarkerEvent:
    onset_s: float
    label: str
    source: str  # "annotation" or channel name

    def as_dict(self) -> dict[str, object]:
        return {"onset_s": round(self.onset_s, 4), "label": self.label, "source": self.source}


@dataclass
class MarkerReport:
    annotation_events: list[MarkerEvent] = field(default_factory=list)
    channel_events: list[MarkerEvent] = field(default_factory=list)
    candidate_channels: list[str] = field(default_factory=list)

    @property
    def events(self) -> list[MarkerEvent]:
        return sorted(
            [*self.annotation_events, *self.channel_events], key=lambda e: e.onset_s
        )

    @property
    def n_events(self) -> int:
        return len(self.annotation_events) + len(self.channel_events)

    @property
    def distinct_labels(self) -> list[str]:
        return sorted({e.label for e in self.events})

    def as_dict(self) -> dict[str, object]:
        return {
            "n_events": self.n_events,
            "n_annotation_events": len(self.annotation_events),
            "n_channel_events": len(self.channel_events),
            "candidate_marker_channels": self.candidate_channels,
            "distinct_labels": self.distinct_labels,
            "events": [e.as_dict() for e in self.events[:500]],
        }


def _annotation_events(raw, cfg: Markers) -> list[MarkerEvent]:
    events: list[MarkerEvent] = []
    annotations = getattr(raw, "annotations", None)
    if annotations is None:
        return events
    for onset, desc in zip(annotations.onset, annotations.description, strict=False):
        label = str(desc)
        # Keep every annotation, but note whether it looks like a task marker.
        events.append(MarkerEvent(onset_s=float(onset), label=label, source="annotation"))
    # If aliases are configured, prefer those that look like real markers, but
    # never drop everything: annotations are informative even when unlabeled.
    if cfg.annotation_aliases:
        filtered = [e for e in events if contains_token(e.label, cfg.annotation_aliases)]
        if filtered:
            return filtered
    return events


def _candidate_marker_channels(ch_names: list[str], cfg: Markers) -> list[str]:
    out: list[str] = []
    for name in ch_names:
        if match_alias(name, cfg.channel_aliases) or contains_token(name, cfg.channel_aliases):
            out.append(name)
    return out


def _channel_events(raw, channel: str) -> list[MarkerEvent]:
    """Extract step changes on an integer-like marker/status channel."""
    idx = raw.ch_names.index(channel)
    data = np.asarray(raw.get_data(picks=[idx])[0])
    sfreq = float(raw.info["sfreq"])
    # Treat as a discrete code channel: emit an event whenever the value changes
    # to a nonzero code.
    codes = np.rint(data).astype(np.int64)
    events: list[MarkerEvent] = []
    prev = 0
    for i, code in enumerate(codes):
        if code != prev and code != 0:
            events.append(
                MarkerEvent(onset_s=i / sfreq, label=f"code:{int(code)}", source=channel)
            )
        prev = code
    return events


def detect_markers(raw, cfg: Markers) -> MarkerReport:
    """Detect markers from annotations and any candidate marker channel."""
    report = MarkerReport()
    report.annotation_events = _annotation_events(raw, cfg)
    report.candidate_channels = _candidate_marker_channels(list(raw.ch_names), cfg)
    for ch in report.candidate_channels:
        report.channel_events.extend(_channel_events(raw, ch))
    return report
