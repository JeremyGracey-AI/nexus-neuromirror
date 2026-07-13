"""Generate a synthetic EDF for local demos (``make demo``)."""

from __future__ import annotations

import argparse

from .synth import export_synthetic_edf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a synthetic 4-channel EDF for demos.")
    parser.add_argument("--out", default="/tmp/nnm_demo.edf", help="Output EDF path.")
    parser.add_argument("--sfreq", type=float, default=256.0)
    parser.add_argument("--duration", type=float, default=60.0)
    args = parser.parse_args(argv)
    path = export_synthetic_edf(args.out, sfreq=args.sfreq, duration_s=args.duration)
    print(f"Wrote synthetic EDF: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
