"""Event-marker extraction, validation, and normalization."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Event:
    onset_sample: int
    onset_s: float
    label: str
    session: str

    def as_dict(self) -> dict[str, object]:
        return {
            "onset_sample": self.onset_sample,
            "onset_s": round(self.onset_s, 4),
            "label": self.label,
            "session": self.session,
        }


@dataclass
class EventSet:
    events: list[Event] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def labels(self) -> list[str]:
        return [e.label for e in self.events]

    @property
    def distinct_labels(self) -> list[str]:
        return sorted(set(self.labels))

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for label in self.labels:
            out[label] = out.get(label, 0) + 1
        return out

    def as_dict(self) -> dict[str, object]:
        return {
            "n_events": len(self.events),
            "distinct_labels": self.distinct_labels,
            "counts": self.counts(),
            "warnings": self.warnings,
            "events": [e.as_dict() for e in self.events[:1000]],
        }


def normalize_label(label: str, mapping: dict[str, str] | None = None) -> str:
    """Trim and optionally remap a marker label to a canonical class name."""
    s = str(label).strip()
    if mapping:
        # Case-insensitive remap.
        lower = {k.lower(): v for k, v in mapping.items()}
        if s.lower() in lower:
            return lower[s.lower()]
    return s


def extract_events(
    marker_raw: np.ndarray,
    sfreq_hz: float,
    session: np.ndarray,
    *,
    label_map: dict[str, str] | None = None,
) -> EventSet:
    """Extract discrete onset events from a per-sample marker array.

    An event is emitted at the first sample of each contiguous run of a given
    non-empty label, so both single-row pulses and sustained codes work.
    """
    result = EventSet()
    prev = ""
    for i, raw in enumerate(marker_raw):
        cur = "" if raw is None else str(raw).strip()
        if cur and cur != prev:
            label = normalize_label(cur, label_map)
            sess = str(session[i]) if i < len(session) else "session-1"
            result.events.append(
                Event(onset_sample=i, onset_s=i / sfreq_hz, label=label, session=sess)
            )
        prev = cur
    return result


def validate_events(
    events: EventSet,
    *,
    min_per_class: int = 2,
    allowed_labels: list[str] | None = None,
) -> list[str]:
    """Return a list of validation problems (empty list == ok)."""
    problems: list[str] = []
    counts = events.counts()
    if not counts:
        problems.append("No events found.")
        return problems
    if len(counts) < 2:
        problems.append(
            f"Only one event class present ({list(counts)}); need >= 2 for classification."
        )
    for label, n in counts.items():
        if n < min_per_class:
            problems.append(f"Class '{label}' has {n} events (< {min_per_class}).")
    if allowed_labels is not None:
        unexpected = sorted(set(counts) - set(allowed_labels))
        if unexpected:
            problems.append(f"Unexpected marker labels: {unexpected}.")
    return problems
