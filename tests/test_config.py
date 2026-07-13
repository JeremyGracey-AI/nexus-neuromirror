from __future__ import annotations

import pytest

from nexus_neuromirror.config import ConfigError, load_config


def test_load_example_config(example_config_path):
    cfg = load_config(example_config_path)
    assert cfg.channels.canonical_names == ["Fz", "FCz", "Pz", "Oz"]
    assert cfg.resample.target_hz == 200.0
    assert 256 in cfg.acquisition.expected_sample_rates_hz
    assert cfg.validation.require_all_expected_channels is True
    assert cfg.model["adaptation"] == "blockwise"


def test_canonical_added_to_aliases(example_config_path):
    cfg = load_config(example_config_path)
    fz = next(c for c in cfg.channels.expected if c.canonical == "Fz")
    assert "Fz" in fz.aliases


def test_missing_file_raises():
    with pytest.raises(ConfigError):
        load_config("/nonexistent/does-not-exist.yaml")


def test_missing_channels_section_raises(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("project:\n  name: x\n")
    with pytest.raises(ConfigError):
        load_config(p)


def test_defaults_applied_for_minimal_config(tmp_path):
    p = tmp_path / "min.yaml"
    p.write_text(
        "channels:\n"
        "  expected:\n"
        "    - canonical: Fz\n"
        "      aliases: [Fz]\n"
    )
    cfg = load_config(p)
    assert cfg.resample.target_hz == 200.0
    assert cfg.validation.min_duration_s == 30.0
    assert cfg.paths.data_dir == "data"
