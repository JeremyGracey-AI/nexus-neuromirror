"""Verification orchestration: load a recording, compute a diagnostic report,
and apply the validation gate.

The result separates *hard* failures (which make the CLI exit nonzero) from
*soft* warnings (surfaced but non-fatal), so the same tool serves both a strict
CI gate and an exploratory bring-up check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .config import Config
from .edf import RecordingInfo, extract_info, read_edf
from .labels import contains_token, find_channel
from .markers import MarkerReport, detect_markers
from .metrics import ChannelMetrics, compute_channel_metrics


@dataclass
class ChannelResolution:
    canonical: str
    matched_name: str | None
    metrics: ChannelMetrics | None = None

    @property
    def found(self) -> bool:
        return self.matched_name is not None


@dataclass
class VerificationResult:
    info: RecordingInfo
    config_name: str
    unit_assumption: str
    resolutions: list[ChannelResolution]
    other_channel_metrics: list[ChannelMetrics]
    markers: MarkerReport
    hard_failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.hard_failures

    @property
    def missing_channels(self) -> list[str]:
        return [r.canonical for r in self.resolutions if not r.found]

    @property
    def matched_channels(self) -> list[str]:
        return [r.matched_name for r in self.resolutions if r.matched_name]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.ok else "failed",
            "config_name": self.config_name,
            "unit_assumption": self.unit_assumption,
            "recording": self.info.as_dict(),
            "expected_channels": [
                {
                    "canonical": r.canonical,
                    "matched_name": r.matched_name,
                    "found": r.found,
                    "metrics": r.metrics.as_dict() if r.metrics else None,
                }
                for r in self.resolutions
            ],
            "other_channels": [
                {"name": m.name, "metrics": m.as_dict()} for m in self.other_channel_metrics
            ],
            "markers": self.markers.as_dict(),
            "hard_failures": self.hard_failures,
            "warnings": self.warnings,
        }


def _classify_other_channels(
    all_names: list[str], matched: set[str], cfg: Config
) -> list[str]:
    """Return non-EEG-expected channels that are not obvious ignore/marker channels."""
    others: list[str] = []
    ignore = cfg.channels.ignore_patterns
    marker_aliases = cfg.markers.channel_aliases
    for name in all_names:
        if name in matched:
            continue
        if contains_token(name, ignore):
            continue
        if contains_token(name, marker_aliases):
            continue
        others.append(name)
    return others


def verify_recording(path: str | Path, cfg: Config) -> VerificationResult:
    """Read a recording from disk and run the diagnostic + validation pipeline."""
    raw = read_edf(path)
    return verify_raw(raw, path, cfg)


def verify_raw(raw: Any, path: str | Path, cfg: Config) -> VerificationResult:
    """Run the diagnostic + validation pipeline on an already-loaded MNE Raw.

    Split from :func:`verify_recording` so callers that also need to plot can
    read the file once and reuse the same object.
    """
    info = extract_info(raw, path)

    # Resolve each expected channel through its aliases.
    resolutions: list[ChannelResolution] = []
    matched_names: set[str] = set()
    for ec in cfg.channels.expected:
        found = find_channel(list(raw.ch_names), ec.aliases)
        resolutions.append(ChannelResolution(canonical=ec.canonical, matched_name=found))
        if found:
            matched_names.add(found)

    # Metrics for matched expected channels.
    if matched_names:
        picks = [raw.ch_names.index(n) for n in raw.ch_names if n in matched_names]
        data = np.asarray(raw.get_data(picks=picks))
        picked_names = [raw.ch_names[i] for i in picks]
        by_name = {m.name: m for m in compute_channel_metrics(picked_names, data)}
        for res in resolutions:
            if res.matched_name and res.matched_name in by_name:
                res.metrics = by_name[res.matched_name]

    # Metrics for other (non-ignored, non-marker) channels, for context.
    other_names = _classify_other_channels(list(raw.ch_names), matched_names, cfg)
    other_metrics: list[ChannelMetrics] = []
    if other_names:
        picks = [raw.ch_names.index(n) for n in other_names]
        data = np.asarray(raw.get_data(picks=picks))
        other_metrics = compute_channel_metrics(other_names, data)

    markers = detect_markers(raw, cfg.markers)

    result = VerificationResult(
        info=info,
        config_name=cfg.name,
        unit_assumption=cfg.acquisition.eeg_unit_assumption,
        resolutions=resolutions,
        other_channel_metrics=other_metrics,
        markers=markers,
    )
    _apply_validation(result, cfg)
    return result


def _apply_validation(result: VerificationResult, cfg: Config) -> None:
    v = cfg.validation
    info = result.info

    if info.duration_s < v.min_duration_s:
        result.hard_failures.append(
            f"Recording too short: {info.duration_s:.1f}s < required {v.min_duration_s:.1f}s."
        )

    # Sample-rate checks.
    allowed = cfg.acquisition.allowed_sample_rates_hz
    expected = cfg.acquisition.expected_sample_rates_hz
    if allowed and info.sfreq_hz not in allowed:
        result.hard_failures.append(
            f"Sample rate {info.sfreq_hz:g} Hz not in allowed set {allowed}."
        )
    elif expected and info.sfreq_hz not in expected:
        result.warnings.append(
            f"Sample rate {info.sfreq_hz:g} Hz not in expected set {expected} "
            "(allowed, but confirm acquisition settings)."
        )

    # Missing channels.
    if result.missing_channels:
        msg = f"Missing expected EEG channels: {', '.join(result.missing_channels)}."
        if v.require_all_expected_channels:
            result.hard_failures.append(msg)
        else:
            result.warnings.append(msg)

    # Per-channel signal quality (soft warnings).
    for res in result.resolutions:
        if not res.metrics:
            continue
        m = res.metrics
        if m.rms_uv < v.rms_uv_min:
            result.warnings.append(
                f"{res.canonical} ({res.matched_name}): RMS {m.rms_uv:.2f} uV below "
                f"{v.rms_uv_min} uV — possible disconnected lead."
            )
        elif m.rms_uv > v.rms_uv_max:
            result.warnings.append(
                f"{res.canonical} ({res.matched_name}): RMS {m.rms_uv:.2f} uV above "
                f"{v.rms_uv_max} uV — possible poor contact / noise."
            )
        if m.ptp_uv > v.ptp_uv_max:
            result.warnings.append(
                f"{res.canonical} ({res.matched_name}): peak-to-peak {m.ptp_uv:.0f} uV "
                f"exceeds {v.ptp_uv_max:.0f} uV — possible motion / artifact."
            )

    # Event expectations.
    if cfg.markers.min_expected_events > 0:
        if result.markers.n_events < cfg.markers.min_expected_events:
            result.hard_failures.append(
                f"Found {result.markers.n_events} events, expected at least "
                f"{cfg.markers.min_expected_events}."
            )
