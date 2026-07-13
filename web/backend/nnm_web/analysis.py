"""EDF analysis integration.

Wraps the existing ``nexus_neuromirror`` package (MNE pipeline) to run the
verifier / report generator on an uploaded EDF and record the results and the
generated artifact paths back into the session metadata.
"""

from __future__ import annotations

from pathlib import Path

from nexus_neuromirror.config import load_config
from nexus_neuromirror.report import generate_report

from .settings import Settings
from .storage import SessionStore


def analyze_edf_session(
    metadata: dict,
    store: SessionStore,
    settings: Settings,
) -> dict:
    """Run the EDF report generator for an ``analyze`` session.

    Mutates and persists ``metadata`` with analysis status, summary metrics,
    warnings/failures, and the list of report artifact repo-relative paths.
    Returns the updated metadata.
    """
    if metadata.get("analysis_mode") != "analyze":
        return metadata

    raw_path = settings.repo_root / metadata["raw_relpath"]
    report_dir = store.report_dir(metadata["session_id"])

    try:
        cfg = load_config(settings.config_path)
        result = generate_report(raw_path, cfg, report_dir)
    except Exception as exc:  # noqa: BLE001 - surface a clean failure to the UI
        metadata["analysis_status"] = "error"
        metadata["hard_failures"] = [f"Analysis failed: {exc}"]
        return store.update_metadata(metadata)

    payload = result.as_dict()
    # Rewrite artifact paths to be repo-relative so the frontend can request
    # them through the artifact-serving endpoint.
    report_relpaths: list[str] = []
    for stem in ("trace", "psd", "markers"):
        for fmt in ("png", "svg"):
            artifact = report_dir / f"{stem}.{fmt}"
            if artifact.exists():
                report_relpaths.append(str(artifact.relative_to(settings.repo_root)))
    diag = report_dir / "diagnostic.json"
    if diag.exists():
        report_relpaths.append(str(diag.relative_to(settings.repo_root)))

    metadata["analysis_status"] = "ok" if result.ok else "failed"
    metadata["analysis"] = _summarize(payload)
    metadata["warnings"] = payload.get("warnings", [])
    metadata["hard_failures"] = payload.get("hard_failures", [])
    metadata["report_relpaths"] = report_relpaths
    return store.update_metadata(metadata)


def _summarize(payload: dict) -> dict:
    """Extract a compact, frontend-friendly summary from the diagnostic payload."""
    rec = payload.get("recording", {})
    markers = payload.get("markers", {})
    return {
        "status": payload.get("status"),
        "config_name": payload.get("config_name"),
        "unit_assumption": payload.get("unit_assumption"),
        "recording": {
            "n_channels": rec.get("n_channels"),
            "channel_names": rec.get("channel_names", []),
            "sfreq_hz": rec.get("sfreq_hz"),
            "duration_s": rec.get("duration_s"),
            "n_samples": rec.get("n_samples"),
            "n_annotations": rec.get("n_annotations"),
            "highpass_hz": rec.get("highpass_hz"),
            "lowpass_hz": rec.get("lowpass_hz"),
            "meas_date": rec.get("meas_date"),
        },
        "expected_channels": payload.get("expected_channels", []),
        "markers": {
            "n_events": markers.get("n_events"),
            "distinct_labels": markers.get("distinct_labels", []),
            "candidate_marker_channels": markers.get("candidate_marker_channels", []),
            "events": markers.get("events", []),
        },
    }
