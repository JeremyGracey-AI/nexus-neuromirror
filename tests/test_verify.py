from __future__ import annotations

from nexus_neuromirror.config import load_config
from nexus_neuromirror.synth import make_synthetic_raw
from nexus_neuromirror.verify import verify_raw


def test_verify_passes_on_good_recording(synthetic_raw, example_config_path):
    cfg = load_config(example_config_path)
    result = verify_raw(synthetic_raw, "synthetic.edf", cfg)
    assert result.ok
    assert result.hard_failures == []
    assert set(result.missing_channels) == set()
    assert result.info.n_channels == 5
    for res in result.resolutions:
        assert res.found and res.metrics is not None


def test_missing_channel_is_hard_failure(example_config_path):
    cfg = load_config(example_config_path)
    raw = make_synthetic_raw(
        duration_s=40.0,
        channel_names=("EEG Fz-A1A2", "EEG FCz-A1A2", "EEG Pz-A1A2"),  # no Oz
        add_marker_channel=False,
    )
    result = verify_raw(raw, "synthetic.edf", cfg)
    assert not result.ok
    assert "Oz" in result.missing_channels
    assert any("Missing expected" in f for f in result.hard_failures)


def test_short_recording_is_hard_failure(example_config_path):
    cfg = load_config(example_config_path)
    raw = make_synthetic_raw(duration_s=5.0)
    result = verify_raw(raw, "synthetic.edf", cfg)
    assert not result.ok
    assert any("too short" in f for f in result.hard_failures)


def test_disconnected_lead_warns(example_config_path):
    import numpy as np

    cfg = load_config(example_config_path)
    raw = make_synthetic_raw(duration_s=40.0)
    # Zero out the Fz channel to simulate a disconnected lead.
    data = raw.get_data()
    data[0] = 0.0
    raw._data = data
    result = verify_raw(raw, "synthetic.edf", cfg)
    assert any("below" in w and "Fz" in w for w in result.warnings)
    assert np.all(raw.get_data()[0] == 0.0)


def test_as_dict_is_json_serializable(synthetic_raw, example_config_path):
    import json

    cfg = load_config(example_config_path)
    result = verify_raw(synthetic_raw, "synthetic.edf", cfg)
    payload = result.as_dict()
    json.dumps(payload)  # must not raise
    assert payload["status"] == "ok"
