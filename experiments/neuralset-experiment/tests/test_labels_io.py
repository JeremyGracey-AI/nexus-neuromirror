from __future__ import annotations

import pandas as pd
import pytest

from neuralset_scaffold.io import ValidationError, load_recording, validate_table
from neuralset_scaffold.labels import core_label, normalize, resolve_column


def test_normalize_strips_separators():
    assert normalize("EEG Fz-A1A2") == "eegfza1a2"
    assert normalize("  Ch1  ") == "ch1"


def test_core_label_trims_prefix_and_reference():
    assert core_label("EEG Fz-A1A2") == "fz"
    assert core_label("Pz-LE") == "pz"
    assert core_label("Fz") == "fz"


def test_resolve_column_direct_and_alias():
    cols = ["time", "EEG Fz-A1A2", "Ch2", "Pz", "Oz", "marker", "session"]
    assert resolve_column(cols, "Fz", ["EEG Fz", "Fz-A1A2", "Ch1"]) == "EEG Fz-A1A2"
    assert resolve_column(cols, "FCz", ["Ch2"]) == "Ch2"
    assert resolve_column(cols, "Cz") is None


def test_validate_table_accepts_synthetic(synth_df, cfg):
    rec, report = validate_table(synth_df, cfg, source="synthetic")
    assert report.ok
    assert rec is not None
    assert rec.data_uv.shape[0] == 4
    assert rec.n_samples == len(synth_df)
    assert set(rec.channels) == {"Fz", "FCz", "Pz", "Oz"}


def test_validate_table_infers_sample_rate(synth_df, cfg):
    _, report = validate_table(synth_df, cfg)
    assert abs(report.sfreq_hz - 256.0) < 1.0


def test_validate_table_missing_channel_fails(synth_df, cfg):
    df = synth_df.drop(columns=["Oz"])
    rec, report = validate_table(df, cfg)
    assert rec is None
    assert not report.ok
    assert any("Oz" in e for e in report.errors)


def test_validate_table_aliased_headers():
    # Header aliases (from the shipped config) must resolve to canonical channels.
    from neuralset_scaffold.config import load_config

    cfg = load_config("configs/default.yaml")
    df = pd.DataFrame(
        {
            "time": [0.0, 0.5, 1.0, 1.5],
            "EEG Fz-A1A2": [1.0, 2.0, 3.0, 4.0],
            "Ch2": [1.0, 2.0, 3.0, 4.0],
            "Pz-LE": [1.0, 2.0, 3.0, 4.0],
            "Oz": [1.0, 2.0, 3.0, 4.0],
            "marker": ["A", "", "B", ""],
            "session": ["s1", "s1", "s1", "s1"],
        }
    )
    rec, report = validate_table(df, cfg)
    assert report.ok, report.errors
    assert rec is not None
    assert rec.data_uv.shape == (4, 4)


def test_marker_normalization_treats_zero_and_nan_as_empty(cfg):
    df = pd.DataFrame(
        {
            "time": [0.0, 0.5, 1.0, 1.5],
            "Fz": [1.0, 2.0, 3.0, 4.0],
            "FCz": [1.0, 2.0, 3.0, 4.0],
            "Pz": [1.0, 2.0, 3.0, 4.0],
            "Oz": [1.0, 2.0, 3.0, 4.0],
            "marker": ["A", "0", "nan", "B"],
            "session": ["s1"] * 4,
        }
    )
    rec, report = validate_table(df, cfg)
    assert report.ok
    assert list(rec.marker_raw) == ["A", "", "", "B"]


def test_load_recording_missing_file(cfg):
    with pytest.raises(ValidationError):
        load_recording("no/such/file.csv", cfg)


def test_load_recording_from_csv(synth_csv, cfg):
    rec, report = load_recording(synth_csv, cfg)
    assert report.ok
    assert rec is not None
    assert rec.data_uv.shape[0] == 4
