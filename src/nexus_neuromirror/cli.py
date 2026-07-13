"""Command-line interface for NeXus NeuroMirror.

Usage:
    nexus-neuromirror verify path/to/session.edf \
        --config configs/project.example.yaml --out reports/diagnostic
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, load_config
from .edf import EdfLoadError
from .report import generate_report
from .verify import VerificationResult


def _print_summary(result: VerificationResult) -> None:
    info = result.info
    print(f"Recording : {info.path}")
    print(f"Config    : {result.config_name}")
    print(f"Channels  : {info.n_channels}  |  sfreq: {info.sfreq_hz:g} Hz  |  "
          f"duration: {info.duration_s:.1f} s")
    print(f"Units     : {result.unit_assumption}")
    print("Expected EEG channels:")
    for r in result.resolutions:
        if r.found and r.metrics:
            m = r.metrics
            print(f"  [ok]   {r.canonical:<4} -> {r.matched_name:<16} "
                  f"RMS {m.rms_uv:7.2f} uV  p2p {m.ptp_uv:9.1f} uV")
        else:
            print(f"  [MISS] {r.canonical:<4} -> (not found)")
    mk = result.markers
    print(f"Markers   : {mk.n_events} events "
          f"(annotations: {len(mk.annotation_events)}, "
          f"channel: {len(mk.channel_events)}); "
          f"candidate channels: {mk.candidate_channels or 'none'}")
    if result.warnings:
        print("Warnings:")
        for w in result.warnings:
            print(f"  - {w}")
    if result.hard_failures:
        print("Hard failures:")
        for f in result.hard_failures:
            print(f"  ! {f}")
    print(f"Result    : {'OK' if result.ok else 'FAILED'}")


def _cmd_verify(args: argparse.Namespace) -> int:
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    if not Path(args.recording).is_file():
        print(f"Recording not found: {args.recording}", file=sys.stderr)
        return 2
    try:
        result = generate_report(args.recording, cfg, args.out)
    except EdfLoadError as exc:
        print(f"Could not load recording: {exc}", file=sys.stderr)
        return 2
    _print_summary(result)
    print(f"Report    : {Path(args.out) / 'diagnostic.json'}")
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nexus-neuromirror",
        description="Diagnostic verifier for NeXus-10 + BioTrace+ EDF recordings.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="Verify and diagnose an EDF/EDF+ recording.")
    verify.add_argument("recording", help="Path to the EDF/EDF+ recording.")
    verify.add_argument("--config", required=True, help="Path to project config YAML.")
    verify.add_argument("--out", required=True, help="Output directory for report artifacts.")
    verify.set_defaults(func=_cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
