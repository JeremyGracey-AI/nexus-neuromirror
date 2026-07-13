"""Configuration loading for the project YAML.

The schema mirrors ``configs/project.example.yaml``. Loading is tolerant:
missing optional sections fall back to documented defaults so that a minimal
config still works, while structural mistakes raise a clear ``ConfigError``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a configuration file is malformed or inconsistent."""


@dataclass(frozen=True)
class ExpectedChannel:
    canonical: str
    aliases: list[str]


@dataclass(frozen=True)
class Channels:
    expected: list[ExpectedChannel]
    ignore_patterns: list[str] = field(default_factory=list)

    @property
    def canonical_names(self) -> list[str]:
        return [c.canonical for c in self.expected]


@dataclass(frozen=True)
class Markers:
    annotation_aliases: list[str] = field(default_factory=list)
    channel_aliases: list[str] = field(default_factory=list)
    min_expected_events: int = 0


@dataclass(frozen=True)
class Acquisition:
    expected_sample_rates_hz: list[float] = field(default_factory=list)
    allowed_sample_rates_hz: list[float] = field(default_factory=list)
    eeg_unit_assumption: str = "volts (MNE-internal); EDF physical dimension expected uV"


@dataclass(frozen=True)
class Resample:
    target_hz: float = 200.0
    method: str = "fir"


@dataclass(frozen=True)
class Validation:
    min_duration_s: float = 30.0
    rms_uv_min: float = 0.5
    rms_uv_max: float = 150.0
    ptp_uv_max: float = 3000.0
    require_all_expected_channels: bool = True


@dataclass(frozen=True)
class Paths:
    data_dir: str = "data"
    reports_dir: str = "reports"


@dataclass(frozen=True)
class Config:
    name: str
    channels: Channels
    markers: Markers
    acquisition: Acquisition
    resample: Resample
    validation: Validation
    paths: Paths
    model: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


def _as_list(value: Any, ctx: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError(f"Expected a list for '{ctx}', got {type(value).__name__}.")
    return value


def _parse_channels(data: dict[str, Any]) -> Channels:
    expected_raw = _as_list(data.get("expected"), "channels.expected")
    if not expected_raw:
        raise ConfigError("channels.expected must list at least one channel.")
    expected: list[ExpectedChannel] = []
    for i, item in enumerate(expected_raw):
        if not isinstance(item, dict) or "canonical" not in item:
            raise ConfigError(f"channels.expected[{i}] needs a 'canonical' key.")
        canonical = str(item["canonical"])
        aliases = [str(a) for a in _as_list(item.get("aliases", [canonical]), "aliases")]
        if canonical not in aliases:
            aliases = [canonical, *aliases]
        expected.append(ExpectedChannel(canonical=canonical, aliases=aliases))
    ignore = [str(p) for p in _as_list(data.get("ignore_patterns", []), "ignore_patterns")]
    return Channels(expected=expected, ignore_patterns=ignore)


def load_config(path: str | Path) -> Config:
    """Load and validate a project config YAML file."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - passthrough of parser error
        raise ConfigError(f"Could not parse YAML {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Top-level config in {path} must be a mapping.")

    channels_data = data.get("channels")
    if not isinstance(channels_data, dict):
        raise ConfigError("Missing required 'channels' section.")

    markers_data = data.get("markers", {}) or {}
    acq_data = data.get("acquisition", {}) or {}
    resample_data = data.get("resample", {}) or {}
    validation_data = data.get("validation", {}) or {}
    paths_data = data.get("paths", {}) or {}
    project_data = data.get("project", {}) or {}

    return Config(
        name=str(project_data.get("name", path.stem)),
        channels=_parse_channels(channels_data),
        markers=Markers(
            annotation_aliases=[str(a) for a in markers_data.get("annotation_aliases", [])],
            channel_aliases=[str(a) for a in markers_data.get("channel_aliases", [])],
            min_expected_events=int(markers_data.get("min_expected_events", 0)),
        ),
        acquisition=Acquisition(
            expected_sample_rates_hz=[float(x) for x in acq_data.get("expected_sample_rates_hz", [])],
            allowed_sample_rates_hz=[float(x) for x in acq_data.get("allowed_sample_rates_hz", [])],
            eeg_unit_assumption=str(
                acq_data.get(
                    "eeg_unit_assumption",
                    "volts (MNE-internal); EDF physical dimension expected uV",
                )
            ),
        ),
        resample=Resample(
            target_hz=float(resample_data.get("target_hz", 200.0)),
            method=str(resample_data.get("method", "fir")),
        ),
        validation=Validation(
            min_duration_s=float(validation_data.get("min_duration_s", 30.0)),
            rms_uv_min=float(validation_data.get("rms_uv_min", 0.5)),
            rms_uv_max=float(validation_data.get("rms_uv_max", 150.0)),
            ptp_uv_max=float(validation_data.get("ptp_uv_max", 3000.0)),
            require_all_expected_channels=bool(
                validation_data.get("require_all_expected_channels", True)
            ),
        ),
        paths=Paths(
            data_dir=str(paths_data.get("data_dir", "data")),
            reports_dir=str(paths_data.get("reports_dir", "reports")),
        ),
        model=dict(data.get("model", {}) or {}),
        raw=data,
    )
