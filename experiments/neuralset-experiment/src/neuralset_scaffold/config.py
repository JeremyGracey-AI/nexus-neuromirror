"""Configuration schema and loader.

Mirrors ``configs/default.yaml``. Loading is tolerant: omitted sections fall
back to documented defaults, while structural mistakes raise ``ConfigError``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CHANNELS = ["Fz", "FCz", "Pz", "Oz"]
DEFAULT_BANDS = {
    "delta": [1.0, 4.0],
    "theta": [4.0, 8.0],
    "alpha": [8.0, 13.0],
    "beta": [13.0, 30.0],
    "gamma": [30.0, 45.0],
}


class ConfigError(ValueError):
    """Raised when a configuration file is malformed."""


@dataclass(frozen=True)
class Columns:
    time: str = "time"
    sample_rate_hz: float = 256.0
    marker: str = "marker"
    session: str = "session"
    # Accepted aliases for channel columns (normalized match, see labels.py).
    channel_aliases: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Preprocess:
    notch_hz: list[float] = field(default_factory=lambda: [50.0])
    bandpass_hz: tuple[float, float] = (1.0, 45.0)
    resample_hz: float = 200.0
    # Artifact flagging thresholds (microvolts). Samples are FLAGGED, never
    # silently removed.
    artifact_amp_uv: float = 150.0
    artifact_grad_uv: float = 75.0


@dataclass(frozen=True)
class Windows:
    length_s: float = 2.0          # must be within [1, 4]
    offset_s: float = 0.0          # start relative to marker onset
    # Reject a window as unusable if more than this fraction of its samples are
    # artifact-flagged (the window is dropped from modeling, with a count).
    max_artifact_fraction: float = 0.5


@dataclass(frozen=True)
class Model:
    kind: str = "logreg"           # "logreg" or "lda"
    n_splits: int = 5
    standardize: bool = True
    random_state: int = 17


@dataclass(frozen=True)
class Config:
    channels: list[str]
    columns: Columns
    preprocess: Preprocess
    windows: Windows
    features: dict[str, list[float]]
    model: Model
    raw: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if len(self.channels) != 4:
            raise ConfigError(f"Expected exactly 4 channels, got {self.channels}.")
        if not (1.0 <= self.windows.length_s <= 4.0):
            raise ConfigError(
                f"windows.length_s must be within [1, 4] s, got {self.windows.length_s}."
            )
        lo, hi = self.preprocess.bandpass_hz
        if not (0 < lo < hi):
            raise ConfigError(f"Invalid bandpass {self.preprocess.bandpass_hz}.")
        if hi >= self.preprocess.resample_hz / 2.0:
            raise ConfigError(
                f"bandpass high {hi} Hz must be below Nyquist "
                f"({self.preprocess.resample_hz / 2.0} Hz)."
            )
        if self.model.kind not in {"logreg", "lda"}:
            raise ConfigError(f"model.kind must be 'logreg' or 'lda', got {self.model.kind}.")


def default_config() -> Config:
    cfg = Config(
        channels=list(DEFAULT_CHANNELS),
        columns=Columns(),
        preprocess=Preprocess(),
        windows=Windows(),
        features=dict(DEFAULT_BANDS),
        model=Model(),
    )
    cfg.validate()
    return cfg


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:  # pragma: no cover
        raise ConfigError(f"Could not parse YAML {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Top-level config in {path} must be a mapping.")

    cols = data.get("columns", {}) or {}
    pre = data.get("preprocess", {}) or {}
    win = data.get("windows", {}) or {}
    mdl = data.get("model", {}) or {}
    bands = data.get("features", {}) or DEFAULT_BANDS

    bandpass = pre.get("bandpass_hz", [1.0, 45.0])
    cfg = Config(
        channels=list(data.get("channels", DEFAULT_CHANNELS)),
        columns=Columns(
            time=str(cols.get("time", "time")),
            sample_rate_hz=float(cols.get("sample_rate_hz", 256.0)),
            marker=str(cols.get("marker", "marker")),
            session=str(cols.get("session", "session")),
            channel_aliases={k: [str(a) for a in v] for k, v in (cols.get("channel_aliases", {}) or {}).items()},
        ),
        preprocess=Preprocess(
            notch_hz=[float(x) for x in pre.get("notch_hz", [50.0])],
            bandpass_hz=(float(bandpass[0]), float(bandpass[1])),
            resample_hz=float(pre.get("resample_hz", 200.0)),
            artifact_amp_uv=float(pre.get("artifact_amp_uv", 150.0)),
            artifact_grad_uv=float(pre.get("artifact_grad_uv", 75.0)),
        ),
        windows=Windows(
            length_s=float(win.get("length_s", 2.0)),
            offset_s=float(win.get("offset_s", 0.0)),
            max_artifact_fraction=float(win.get("max_artifact_fraction", 0.5)),
        ),
        features={k: [float(x) for x in v] for k, v in bands.items()},
        model=Model(
            kind=str(mdl.get("kind", "logreg")),
            n_splits=int(mdl.get("n_splits", 5)),
            standardize=bool(mdl.get("standardize", True)),
            random_state=int(mdl.get("random_state", 17)),
        ),
        raw=data,
    )
    cfg.validate()
    return cfg
