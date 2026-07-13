"""Command-line interface.

Subcommands:
    synth     Generate a synthetic demo CSV/TSV.
    validate  Validate a CSV/TSV recording and its markers.
    run       Full experiment: validate -> preprocess -> window -> features -> eval.
    demo      Generate synthetic data and run the experiment in one step.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, neuralset_adapter
from .config import ConfigError, default_config, load_config
from .io import ValidationError, load_recording
from .pipeline import run_experiment
from .synth import write_synthetic


def _load_cfg(path: str | None):
    if path is None:
        return default_config()
    return load_config(path)


def _cmd_synth(args: argparse.Namespace) -> int:
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    write_synthetic(
        args.out,
        n_sessions=args.sessions,
        trials_per_class=args.trials,
        sfreq_hz=args.sfreq,
        seed=args.seed,
    )
    print(f"Wrote synthetic recording: {args.out}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    rec, report = load_recording(args.input, cfg)
    print(json.dumps(report.as_dict(), indent=2))
    return 0 if report.ok else 1


def _cmd_run(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    result = run_experiment(args.input, cfg, args.out, make_plots=not args.no_plots)
    _print_summary(result, args.out)
    return 0 if result.validation.ok else 1


def _cmd_demo(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data_path = out / "demo_data.csv"
    write_synthetic(str(data_path), n_sessions=args.sessions, trials_per_class=args.trials, seed=args.seed)
    print(f"Synthetic data: {data_path}")
    result = run_experiment(data_path, cfg, out, make_plots=not args.no_plots)
    _print_summary(result, args.out)
    return 0 if result.validation.ok else 1


def _print_summary(result, out_dir: str) -> None:
    v = result.validation
    print(f"Validation : {'OK' if v.ok else 'FAILED'} "
          f"(sfreq {v.sfreq_hz:.2f} Hz, {v.n_samples} samples)")
    if v.errors:
        print("  errors:")
        for e in v.errors:
            print(f"    ! {e}")
    if v.warnings:
        print("  warnings:")
        for w in v.warnings:
            print(f"    - {w}")
    if result.events:
        print(f"Events     : {result.events.get('n_events')} "
              f"classes={result.events.get('distinct_labels')} "
              f"counts={result.events.get('counts')}")
    if result.windows:
        print(f"Windows    : {result.windows.get('n_windows')} "
              f"(dropped: bounds={result.windows.get('n_dropped_bounds')}, "
              f"artifact={result.windows.get('n_dropped_artifact')})")
        print(f"Features   : {result.features_shape}")
    ev = result.evaluation
    if ev is not None:
        print(f"CV scheme  : {ev.cv_scheme}")
        print(f"Accuracy   : {ev.mean_accuracy:.3f} +/- {ev.std_accuracy:.3f} "
              f"(chance {ev.chance_level:.3f})")
        print(f"Balanced   : {ev.mean_balanced_accuracy:.3f}   F1-macro: {ev.mean_f1_macro:.3f}")
    elif result.windows.get("evaluation_error"):
        print(f"Evaluation : skipped ({result.windows['evaluation_error']})")
    ns = result.neuralset
    print(f"NeuralSet  : available={ns.get('available')}")
    print(f"Outputs    : {Path(out_dir) / 'metrics.json'}")
    if result.artifacts:
        print(f"Plots      : {len(result.artifacts)} files in {out_dir}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="neuralset-scaffold",
        description="Four-channel EEG first-experiment scaffold (NeXus-10/BioTrace CSV/TSV).",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("synth", help="Generate synthetic demo data.")
    ps.add_argument("--out", required=True)
    ps.add_argument("--sessions", type=int, default=3)
    ps.add_argument("--trials", type=int, default=20, help="Trials per class per session.")
    ps.add_argument("--sfreq", type=float, default=256.0)
    ps.add_argument("--seed", type=int, default=17)
    ps.set_defaults(func=_cmd_synth)

    pv = sub.add_parser("validate", help="Validate a CSV/TSV recording.")
    pv.add_argument("input")
    pv.add_argument("--config", default=None)
    pv.set_defaults(func=_cmd_validate)

    pr = sub.add_parser("run", help="Run the full experiment on a recording.")
    pr.add_argument("input")
    pr.add_argument("--config", default=None)
    pr.add_argument("--out", required=True)
    pr.add_argument("--no-plots", action="store_true")
    pr.set_defaults(func=_cmd_run)

    pd = sub.add_parser("demo", help="Generate synthetic data and run end-to-end.")
    pd.add_argument("--out", default="outputs/demo")
    pd.add_argument("--config", default=None)
    pd.add_argument("--sessions", type=int, default=3)
    pd.add_argument("--trials", type=int, default=20)
    pd.add_argument("--seed", type=int, default=17)
    pd.add_argument("--no-plots", action="store_true")
    pd.set_defaults(func=_cmd_demo)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (ConfigError, ValidationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except neuralset_adapter.NeuralSetUnavailableError as exc:
        print(f"NeuralSet error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
