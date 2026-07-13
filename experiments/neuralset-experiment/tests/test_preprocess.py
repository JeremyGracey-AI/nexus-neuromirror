from __future__ import annotations

from dataclasses import replace

import numpy as np

from neuralset_scaffold.io import Recording
from neuralset_scaffold.preprocess import preprocess


def _recording(sfreq=256.0, n=2560):
    rng = np.random.default_rng(0)
    data = rng.standard_normal((4, n)) * 5.0
    marker = np.array([""] * n, dtype=object)
    marker[0] = "A"
    marker[n // 2] = "B"
    session = np.array(["s1"] * n, dtype=object)
    return Recording(
        channels=["Fz", "FCz", "Pz", "Oz"],
        data_uv=data,
        sfreq_hz=sfreq,
        marker_raw=marker,
        session=session,
    )


def test_preprocess_resamples_to_target(cfg):
    rec = _recording(sfreq=256.0, n=2560)
    pre = preprocess(rec, cfg.preprocess)
    assert pre.sfreq_hz == cfg.preprocess.resample_hz
    expected = int(round(2560 * cfg.preprocess.resample_hz / 256.0))
    assert pre.n_samples == expected
    assert pre.data_uv.shape[0] == 4


def test_preprocess_is_nondestructive_flags_only(cfg):
    rec = _recording()
    # Inject a large artifact spike into one channel.
    rec.data_uv[0, 100] = 5000.0
    pre = preprocess(rec, cfg.preprocess)
    # Sample count is unchanged by flagging (only resampling changes it).
    assert pre.artifact_flags.shape == pre.data_uv.shape
    assert pre.artifact_flags.any()


def test_preprocess_no_resample_when_rate_matches():
    rec = _recording(sfreq=200.0, n=2000)
    from neuralset_scaffold.config import Preprocess

    pp = Preprocess(resample_hz=200.0)
    pre = preprocess(rec, pp)
    assert pre.n_samples == 2000


def test_preprocess_marker_onsets_preserved_after_resample(cfg):
    rec = _recording()
    pre = preprocess(rec, cfg.preprocess)
    present = {str(m) for m in pre.marker_raw if str(m)}
    assert present == {"A", "B"}


def test_preprocess_records_steps(cfg):
    rec = _recording()
    pre = preprocess(rec, cfg.preprocess)
    joined = " ".join(pre.steps)
    assert "detrend" in joined
    assert "notch" in joined
    assert "bandpass" in joined
    assert "artifact_flag" in joined


def test_preprocess_low_threshold_flags_more(cfg):
    rec = _recording()
    strict = replace(cfg.preprocess, artifact_amp_uv=0.1, artifact_grad_uv=0.1)
    pre = preprocess(rec, strict)
    assert pre.artifact_fraction > 0.0
