from __future__ import annotations

from nexus_neuromirror.config import load_config
from nexus_neuromirror.markers import detect_markers


def test_detects_annotations_and_channel_events(synthetic_raw, example_config_path):
    cfg = load_config(example_config_path)
    report = detect_markers(synthetic_raw, cfg.markers)

    assert "Status" in report.candidate_channels
    assert len(report.annotation_events) > 0
    assert len(report.channel_events) > 0
    # Events are sorted by onset.
    onsets = [e.onset_s for e in report.events]
    assert onsets == sorted(onsets)


def test_no_marker_channel_when_absent(example_config_path):
    from nexus_neuromirror.synth import make_synthetic_raw

    cfg = load_config(example_config_path)
    raw = make_synthetic_raw(duration_s=20.0, add_marker_channel=False, add_annotations=False)
    report = detect_markers(raw, cfg.markers)
    assert report.candidate_channels == []
    assert report.n_events == 0
