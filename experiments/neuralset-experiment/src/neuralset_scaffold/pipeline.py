"""End-to-end orchestration: validate -> preprocess -> window -> features -> eval."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import __version__, neuralset_adapter
from .config import Config
from .features import compute_features
from .io import Recording, ValidationReport, load_recording
from .markers import extract_events, validate_events
from .model import EvalResult, evaluate
from .plots import save_all
from .preprocess import preprocess
from .windows import make_windows


@dataclass
class PipelineResult:
    validation: ValidationReport
    events: dict
    windows: dict
    features_shape: tuple[int, int]
    evaluation: EvalResult | None
    artifacts: list[str]
    neuralset: dict

    def as_dict(self) -> dict[str, object]:
        return {
            "scaffold_version": __version__,
            "neuralset_adapter": self.neuralset,
            "validation": self.validation.as_dict(),
            "events": self.events,
            "windows": self.windows,
            "features_shape": list(self.features_shape),
            "evaluation": self.evaluation.as_dict() if self.evaluation else None,
            "artifacts": self.artifacts,
        }


def run_experiment(
    input_path: str | Path,
    cfg: Config,
    out_dir: str | Path,
    *,
    label_map: dict[str, str] | None = None,
    make_plots: bool = True,
) -> PipelineResult:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rec, report = load_recording(input_path, cfg)
    if rec is None or not report.ok:
        result = PipelineResult(
            validation=report,
            events={},
            windows={},
            features_shape=(0, 0),
            evaluation=None,
            artifacts=[],
            neuralset=neuralset_adapter.describe(),
        )
        _write_json(result, out_dir)
        return result

    return _run_from_recording(rec, report, cfg, out_dir, label_map=label_map, make_plots=make_plots)


def _run_from_recording(
    rec: Recording,
    report: ValidationReport,
    cfg: Config,
    out_dir: Path,
    *,
    label_map: dict[str, str] | None,
    make_plots: bool,
) -> PipelineResult:
    raw_events = extract_events(rec.marker_raw, rec.sfreq_hz, rec.session, label_map=label_map)
    ev_problems = validate_events(raw_events, min_per_class=2)
    for p in ev_problems:
        report.warnings.append(f"markers: {p}")

    pre = preprocess(rec, cfg.preprocess)
    windows = make_windows(pre, cfg.windows, label_map=label_map)
    feats = compute_features(windows, cfg.features)

    evaluation: EvalResult | None = None
    eval_error: str | None = None
    if windows.n_windows > 0 and len(set(windows.labels.tolist())) >= 2:
        try:
            evaluation = evaluate(feats, cfg.model)
        except Exception as exc:  # noqa: BLE001 - report, don't crash the run
            eval_error = str(exc)
    else:
        eval_error = "Not enough windows/classes for evaluation."

    artifacts: list[str] = []
    if make_plots and evaluation is not None:
        artifacts = save_all(pre, feats, evaluation, out_dir)

    windows_info = windows.as_dict()
    windows_info["preprocess_steps"] = pre.steps
    windows_info["artifact_fraction_overall"] = round(pre.artifact_fraction, 4)
    if eval_error:
        windows_info["evaluation_error"] = eval_error

    result = PipelineResult(
        validation=report,
        events=raw_events.as_dict(),
        windows=windows_info,
        features_shape=feats.shape,
        evaluation=evaluation,
        artifacts=artifacts,
        neuralset=neuralset_adapter.describe(),
    )
    _write_json(result, out_dir)
    return result


def _write_json(result: PipelineResult, out_dir: Path) -> None:
    (out_dir / "metrics.json").write_text(json.dumps(result.as_dict(), indent=2))
