from __future__ import annotations

import numpy as np

from neuralset_scaffold.markers import (
    extract_events,
    normalize_label,
    validate_events,
)


def _sessions(n: int, name: str = "s1") -> np.ndarray:
    return np.array([name] * n, dtype=object)


def test_normalize_label_remap_case_insensitive():
    mapping = {"left": "L", "right": "R"}
    assert normalize_label("Left", mapping) == "L"
    assert normalize_label("RIGHT", mapping) == "R"
    assert normalize_label("other", mapping) == "other"


def test_extract_events_single_row_pulses():
    marker = np.array(["A", "", "", "B", "", "A", ""], dtype=object)
    ev = extract_events(marker, sfreq_hz=100.0, session=_sessions(7))
    assert ev.labels == ["A", "B", "A"]
    assert ev.events[0].onset_sample == 0
    assert ev.events[1].onset_sample == 3
    assert ev.events[2].onset_sample == 5


def test_extract_events_sustained_run_is_single_onset():
    marker = np.array(["A", "A", "A", "", "B", "B"], dtype=object)
    ev = extract_events(marker, sfreq_hz=100.0, session=_sessions(6))
    assert ev.labels == ["A", "B"]
    assert ev.events[0].onset_sample == 0
    assert ev.events[1].onset_sample == 4


def test_extract_events_onset_time_and_label_map():
    marker = np.array(["", "left", "", "right"], dtype=object)
    ev = extract_events(
        marker, sfreq_hz=200.0, session=_sessions(4), label_map={"left": "L", "right": "R"}
    )
    assert ev.labels == ["L", "R"]
    assert ev.events[0].onset_s == 1 / 200.0


def test_validate_events_flags_single_class():
    marker = np.array(["A", "", "A", ""], dtype=object)
    ev = extract_events(marker, sfreq_hz=100.0, session=_sessions(4))
    problems = validate_events(ev, min_per_class=2)
    assert any("one event class" in p for p in problems)


def test_validate_events_flags_too_few_per_class():
    marker = np.array(["A", "B", ""], dtype=object)
    ev = extract_events(marker, sfreq_hz=100.0, session=_sessions(3))
    problems = validate_events(ev, min_per_class=2)
    assert any("< 2" in p for p in problems)


def test_validate_events_allowed_labels():
    marker = np.array(["A", "B", "C"], dtype=object)
    ev = extract_events(marker, sfreq_hz=100.0, session=_sessions(3))
    problems = validate_events(ev, min_per_class=1, allowed_labels=["A", "B"])
    assert any("Unexpected" in p and "C" in p for p in problems)


def test_validate_events_ok_when_balanced():
    marker = np.array(["A", "B", "A", "B"], dtype=object)
    ev = extract_events(marker, sfreq_hz=100.0, session=_sessions(4))
    assert validate_events(ev, min_per_class=2) == []
