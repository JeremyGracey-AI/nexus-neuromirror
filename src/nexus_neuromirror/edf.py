"""EDF / EDF+ loading via MNE with light metadata extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import mne


class EdfLoadError(RuntimeError):
    """Raised when an EDF/EDF+ file cannot be read."""


@dataclass(frozen=True)
class RecordingInfo:
    path: str
    n_channels: int
    channel_names: list[str]
    sfreq_hz: float
    n_samples: int
    duration_s: float
    n_annotations: int
    highpass_hz: float | None
    lowpass_hz: float | None
    meas_date: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "n_channels": self.n_channels,
            "channel_names": self.channel_names,
            "sfreq_hz": self.sfreq_hz,
            "n_samples": self.n_samples,
            "duration_s": round(self.duration_s, 4),
            "n_annotations": self.n_annotations,
            "highpass_hz": self.highpass_hz,
            "lowpass_hz": self.lowpass_hz,
            "meas_date": self.meas_date,
        }


def read_edf(path: str | Path, *, preload: bool = True) -> mne.io.BaseRaw:
    """Read an EDF/EDF+ file, returning an MNE Raw object.

    Non-EDF but MNE-readable formats (e.g. FIF) are accepted as a convenience
    for testing; unreadable files raise :class:`EdfLoadError`.
    """
    path = Path(path)
    if not path.is_file():
        raise EdfLoadError(f"Recording not found: {path}")
    suffix = path.suffix.lower()
    try:
        if suffix in {".edf", ".bdf"}:
            reader = mne.io.read_raw_edf if suffix == ".edf" else mne.io.read_raw_bdf
            raw = reader(path, preload=preload, verbose="ERROR")
        else:
            raw = mne.io.read_raw(path, preload=preload, verbose="ERROR")
    except Exception as exc:  # noqa: BLE001 - surface a single clean error type
        raise EdfLoadError(f"Failed to read {path}: {exc}") from exc
    return raw


def extract_info(raw: mne.io.BaseRaw, path: str | Path) -> RecordingInfo:
    """Pull a compact, JSON-friendly summary from an MNE Raw object."""
    info = raw.info
    meas_date = info.get("meas_date")
    return RecordingInfo(
        path=str(path),
        n_channels=len(raw.ch_names),
        channel_names=list(raw.ch_names),
        sfreq_hz=float(info["sfreq"]),
        n_samples=int(raw.n_times),
        duration_s=float(raw.n_times) / float(info["sfreq"]),
        n_annotations=len(raw.annotations) if raw.annotations is not None else 0,
        highpass_hz=float(info["highpass"]) if info.get("highpass") is not None else None,
        lowpass_hz=float(info["lowpass"]) if info.get("lowpass") is not None else None,
        meas_date=meas_date.isoformat() if meas_date is not None else None,
    )
