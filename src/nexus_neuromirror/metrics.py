"""Per-channel signal metrics.

Metrics are reported in microvolts. MNE stores EEG internally in volts, so we
scale by 1e6. This is the single place the volts->uV assumption is applied.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

VOLTS_TO_UV = 1e6


@dataclass(frozen=True)
class ChannelMetrics:
    name: str
    rms_uv: float
    ptp_uv: float
    max_abs_uv: float
    mean_uv: float

    def as_dict(self) -> dict[str, float]:
        return {
            "rms_uv": round(self.rms_uv, 4),
            "ptp_uv": round(self.ptp_uv, 4),
            "max_abs_uv": round(self.max_abs_uv, 4),
            "mean_uv": round(self.mean_uv, 4),
        }


def compute_channel_metrics(
    names: list[str], data_volts: np.ndarray
) -> list[ChannelMetrics]:
    """Compute RMS / peak-to-peak / etc. per channel.

    ``data_volts`` has shape ``(n_channels, n_samples)`` in volts.
    """
    if data_volts.ndim != 2:
        raise ValueError("data_volts must be 2-D (channels x samples).")
    if data_volts.shape[0] != len(names):
        raise ValueError("names length must match data rows.")

    uv = data_volts * VOLTS_TO_UV
    out: list[ChannelMetrics] = []
    for i, name in enumerate(names):
        row = uv[i]
        rms = float(np.sqrt(np.mean(np.square(row)))) if row.size else 0.0
        ptp = float(np.ptp(row)) if row.size else 0.0
        max_abs = float(np.max(np.abs(row))) if row.size else 0.0
        mean = float(np.mean(row)) if row.size else 0.0
        out.append(
            ChannelMetrics(name=name, rms_uv=rms, ptp_uv=ptp, max_abs_uv=max_abs, mean_uv=mean)
        )
    return out
