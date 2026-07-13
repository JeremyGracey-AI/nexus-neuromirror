from __future__ import annotations

from dataclasses import replace

import numpy as np

from neuralset_scaffold.features import compute_features
from neuralset_scaffold.preprocess import Preprocessed
from neuralset_scaffold.windows import make_windows


def _preprocessed(sfreq=200.0, n=2000, onsets=(200, 800, 1400)):
    rng = np.random.default_rng(1)
    data = rng.standard_normal((4, n))
    flags = np.zeros((4, n), dtype=bool)
    marker = np.array([""] * n, dtype=object)
    labels = ["A", "B", "A"]
    for onset, lab in zip(onsets, labels, strict=False):
        marker[onset] = lab
    session = np.array(["s1"] * n, dtype=object)
    return Preprocessed(
        channels=["Fz", "FCz", "Pz", "Oz"],
        data_uv=data,
        sfreq_hz=sfreq,
        artifact_flags=flags,
        marker_raw=marker,
        session=session,
        steps=["test"],
    )


def test_make_windows_basic(cfg):
    pre = _preprocessed()
    ws = make_windows(pre, cfg.windows)
    win_n = int(round(cfg.windows.length_s * pre.sfreq_hz))
    assert ws.n_windows == 3
    assert ws.data_uv.shape == (3, 4, win_n)
    assert list(ws.labels) == ["A", "B", "A"]


def test_make_windows_drops_out_of_bounds(cfg):
    # Onset near the very end cannot fit a full window.
    pre = _preprocessed(onsets=(200, 1999))
    ws = make_windows(pre, cfg.windows)
    assert ws.n_dropped_bounds >= 1
    assert ws.n_windows == 1


def test_make_windows_drops_artifacted(cfg):
    pre = _preprocessed(onsets=(200, 800))
    win_n = int(round(cfg.windows.length_s * pre.sfreq_hz))
    # Flag the entire first window heavily.
    pre.artifact_flags[:, 200:200 + win_n] = True
    strict = replace(cfg.windows, max_artifact_fraction=0.5)
    ws = make_windows(pre, strict)
    assert ws.n_dropped_artifact == 1
    assert ws.n_windows == 1


def test_compute_features_shapes(cfg):
    pre = _preprocessed()
    ws = make_windows(pre, cfg.windows)
    fm = compute_features(ws, cfg.features)
    n_feats = len(cfg.features) * 2 * len(pre.channels)
    assert fm.X.shape == (3, n_feats)
    assert len(fm.feature_names) == n_feats
    assert fm.y.tolist() == ["A", "B", "A"]


def test_compute_features_empty_windowset(cfg):
    pre = _preprocessed(onsets=())
    ws = make_windows(pre, cfg.windows)
    assert ws.n_windows == 0
    fm = compute_features(ws, cfg.features)
    assert fm.X.shape[0] == 0


def test_feature_names_include_abs_and_rel(cfg):
    pre = _preprocessed()
    ws = make_windows(pre, cfg.windows)
    fm = compute_features(ws, cfg.features)
    assert any(name.endswith(":abs") for name in fm.feature_names)
    assert any(name.endswith(":rel") for name in fm.feature_names)
    assert any(name.startswith("Fz:") for name in fm.feature_names)
