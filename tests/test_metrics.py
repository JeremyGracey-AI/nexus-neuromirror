from __future__ import annotations

import numpy as np
import pytest

from nexus_neuromirror.metrics import compute_channel_metrics


def test_rms_and_ptp_of_known_sine():
    sfreq = 200.0
    t = np.arange(int(sfreq * 4)) / sfreq
    amp_uv = 50.0
    sig_v = (amp_uv * np.sin(2 * np.pi * 10 * t)) * 1e-6  # volts
    dc_v = np.full_like(t, 20e-6)
    data = np.vstack([sig_v, dc_v])

    metrics = compute_channel_metrics(["sine", "dc"], data)
    by = {m.name: m for m in metrics}

    # RMS of a sine is amplitude / sqrt(2).
    assert by["sine"].rms_uv == pytest.approx(amp_uv / np.sqrt(2), rel=1e-2)
    # Peak-to-peak of a sine is 2 * amplitude.
    assert by["sine"].ptp_uv == pytest.approx(2 * amp_uv, rel=1e-2)
    # DC channel: RMS equals the level, ptp ~ 0.
    assert by["dc"].rms_uv == pytest.approx(20.0, rel=1e-3)
    assert by["dc"].ptp_uv == pytest.approx(0.0, abs=1e-6)


def test_shape_validation():
    with pytest.raises(ValueError):
        compute_channel_metrics(["a"], np.zeros((2, 10)))
    with pytest.raises(ValueError):
        compute_channel_metrics(["a"], np.zeros(10))
