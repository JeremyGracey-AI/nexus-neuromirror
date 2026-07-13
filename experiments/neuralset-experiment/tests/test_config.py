from __future__ import annotations

import pytest

from neuralset_scaffold.config import (
    Config,
    ConfigError,
    default_config,
    load_config,
)


def test_default_config_valid():
    cfg = default_config()
    assert cfg.channels == ["Fz", "FCz", "Pz", "Oz"]
    assert set(cfg.features) == {"delta", "theta", "alpha", "beta", "gamma"}
    cfg.validate()  # should not raise


def test_load_config_roundtrip(cfg):
    # The shipped default.yaml should load and match code defaults closely.
    yaml_cfg = load_config("configs/default.yaml")
    assert yaml_cfg.channels == cfg.channels
    assert yaml_cfg.model.kind in {"logreg", "lda"}
    assert yaml_cfg.preprocess.resample_hz == 200.0


def test_validate_rejects_wrong_channel_count(cfg):
    bad = Config(
        channels=["Fz", "FCz", "Pz"],
        columns=cfg.columns,
        preprocess=cfg.preprocess,
        windows=cfg.windows,
        features=cfg.features,
        model=cfg.model,
    )
    with pytest.raises(ConfigError):
        bad.validate()


def test_validate_rejects_out_of_range_window(cfg):
    from dataclasses import replace

    bad = replace(cfg, windows=replace(cfg.windows, length_s=6.0))
    with pytest.raises(ConfigError):
        bad.validate()


def test_validate_rejects_bandpass_above_nyquist(cfg):
    from dataclasses import replace

    bad = replace(cfg, preprocess=replace(cfg.preprocess, bandpass_hz=(1.0, 120.0)))
    with pytest.raises(ConfigError):
        bad.validate()


def test_validate_rejects_unknown_model(cfg):
    from dataclasses import replace

    bad = replace(cfg, model=replace(cfg.model, kind="svm"))
    with pytest.raises(ConfigError):
        bad.validate()


def test_load_config_missing_file():
    with pytest.raises(ConfigError):
        load_config("does/not/exist.yaml")
