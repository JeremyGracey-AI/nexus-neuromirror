"""CSV/TSV loading and validation for four-channel recordings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Config
from .labels import resolve_column


class ValidationError(ValueError):
    """Raised when a recording cannot be used at all (hard failure)."""


@dataclass
class Recording:
    """A validated four-channel recording in microvolts."""

    channels: list[str]                 # canonical order, e.g. Fz, FCz, Pz, Oz
    data_uv: np.ndarray                 # shape (4, n_samples), float64
    sfreq_hz: float
    marker_raw: np.ndarray              # per-sample marker labels ("" = none)
    session: np.ndarray                 # per-sample session id (string)
    source: str = ""

    @property
    def n_samples(self) -> int:
        return self.data_uv.shape[1]

    @property
    def duration_s(self) -> float:
        return self.n_samples / self.sfreq_hz

    @property
    def sessions(self) -> list[str]:
        return sorted(set(self.session.tolist()))


@dataclass
class ValidationReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    resolved_columns: dict[str, str] = field(default_factory=dict)
    sfreq_hz: float = 0.0
    n_samples: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "resolved_columns": self.resolved_columns,
            "sfreq_hz": self.sfreq_hz,
            "n_samples": self.n_samples,
        }


def _read_delimited(path: Path) -> pd.DataFrame:
    sep = "\t" if path.suffix.lower() in {".tsv", ".tab"} else ","
    try:
        df = pd.read_csv(path, sep=sep)
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"Could not read {path}: {exc}") from exc
    if df.shape[1] == 1 and sep == ",":
        # Possibly a mislabeled TSV; retry with tab.
        try:
            df = pd.read_csv(path, sep="\t")
        except Exception:  # noqa: BLE001
            pass
    return df


def _infer_sfreq(df: pd.DataFrame, time_col: str | None, fallback: float) -> tuple[float, str | None]:
    if time_col is None or time_col not in df.columns:
        return fallback, None
    t = pd.to_numeric(df[time_col], errors="coerce").to_numpy(dtype=float)
    diffs = np.diff(t)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if diffs.size == 0:
        return fallback, "time column present but unusable; using configured sample rate"
    dt = float(np.median(diffs))
    if dt <= 0:
        return fallback, "non-positive time step; using configured sample rate"
    return 1.0 / dt, None


def validate_table(df: pd.DataFrame, cfg: Config, source: str = "") -> tuple[Recording | None, ValidationReport]:
    """Validate a loaded table against the config. Returns (recording, report)."""
    report = ValidationReport(ok=True)
    columns = list(df.columns)

    # Resolve the four channel columns.
    resolved: dict[str, str] = {}
    for ch in cfg.channels:
        aliases = cfg.columns.channel_aliases.get(ch, [])
        col = resolve_column(columns, ch, aliases)
        if col is None:
            report.errors.append(f"Missing required channel column: {ch}")
        else:
            resolved[ch] = col
    report.resolved_columns = resolved

    # Time / sample rate.
    time_col = resolve_column(columns, cfg.columns.time)
    sfreq, sf_warn = _infer_sfreq(df, time_col, cfg.columns.sample_rate_hz)
    if sf_warn:
        report.warnings.append(sf_warn)
    if time_col is not None:
        cfg_sf = cfg.columns.sample_rate_hz
        if cfg_sf > 0 and abs(sfreq - cfg_sf) / cfg_sf > 0.05:
            report.warnings.append(
                f"Inferred sample rate {sfreq:.2f} Hz differs >5% from configured "
                f"{cfg_sf:g} Hz; using inferred rate."
            )
    report.sfreq_hz = sfreq
    report.n_samples = int(len(df))

    if len(df) < 2:
        report.errors.append("Recording has fewer than 2 samples.")

    # If channels are missing we cannot build a Recording.
    if len(resolved) < len(cfg.channels):
        report.ok = False
        return None, report

    # Build channel matrix; check numeric + finite.
    rows = []
    for ch in cfg.channels:
        series = pd.to_numeric(df[resolved[ch]], errors="coerce").to_numpy(dtype=float)
        n_nan = int(np.count_nonzero(~np.isfinite(series)))
        if n_nan == series.size:
            report.errors.append(f"Channel {ch} has no numeric samples.")
        elif n_nan > 0:
            report.warnings.append(
                f"Channel {ch}: {n_nan} non-numeric/NaN samples; interpolated for analysis."
            )
            series = _interpolate_nans(series)
        rows.append(series)
    data = np.vstack(rows) if rows else np.empty((0, 0))

    # Markers.
    marker_col = resolve_column(columns, cfg.columns.marker)
    if marker_col is None:
        report.warnings.append(
            f"No marker column '{cfg.columns.marker}' found; recording has no events."
        )
        marker_raw = np.array([""] * len(df), dtype=object)
    else:
        marker_raw = _normalize_marker_series(df[marker_col])

    # Sessions.
    session_col = resolve_column(columns, cfg.columns.session)
    if session_col is None:
        session = np.array(["session-1"] * len(df), dtype=object)
        report.warnings.append("No session column found; treating all rows as 'session-1'.")
    else:
        session = df[session_col].astype(str).to_numpy()

    if report.errors:
        report.ok = False
        return None, report

    rec = Recording(
        channels=list(cfg.channels),
        data_uv=data.astype(np.float64),
        sfreq_hz=float(sfreq),
        marker_raw=marker_raw,
        session=session,
        source=source,
    )
    return rec, report


def _interpolate_nans(x: np.ndarray) -> np.ndarray:
    mask = ~np.isfinite(x)
    if not mask.any():
        return x
    idx = np.arange(x.size)
    good = idx[~mask]
    if good.size == 0:
        return np.zeros_like(x)
    x = x.copy()
    x[mask] = np.interp(idx[mask], good, x[good])
    return x


def _normalize_marker_series(series: pd.Series) -> np.ndarray:
    out = []
    for v in series.tolist():
        if v is None:
            out.append("")
            continue
        if isinstance(v, float) and np.isnan(v):
            out.append("")
            continue
        s = str(v).strip()
        if s.lower() in {"", "nan", "0", "none", "na"}:
            out.append("")
        else:
            out.append(s)
    return np.array(out, dtype=object)


def load_recording(path: str | Path, cfg: Config) -> tuple[Recording | None, ValidationReport]:
    """Load a CSV/TSV file and validate it against the config."""
    path = Path(path)
    if not path.is_file():
        raise ValidationError(f"Input file not found: {path}")
    df = _read_delimited(path)
    return validate_table(df, cfg, source=str(path))
