from __future__ import annotations

import json
from pathlib import Path

from neuralset_scaffold.cli import main
from neuralset_scaffold.pipeline import run_experiment


def test_run_experiment_end_to_end(synth_csv, cfg, tmp_path):
    out = tmp_path / "out"
    result = run_experiment(synth_csv, cfg, out, make_plots=True)
    assert result.validation.ok
    assert result.evaluation is not None
    assert result.evaluation.n_windows > 0
    # Separable above chance but not trivially perfect (synthetic design).
    assert result.evaluation.mean_accuracy > result.evaluation.chance_level
    # metrics.json written.
    metrics = json.loads((out / "metrics.json").read_text())
    assert metrics["validation"]["ok"] is True
    assert metrics["evaluation"]["cv_scheme"].startswith(("leave-one", "group-"))
    # Plots emitted.
    assert result.artifacts
    for name in ("trace.png", "psd.png", "confusion.png"):
        assert (out / name).exists()


def test_run_experiment_no_plots(synth_csv, cfg, tmp_path):
    out = tmp_path / "np"
    result = run_experiment(synth_csv, cfg, out, make_plots=False)
    assert result.artifacts == []
    assert (out / "metrics.json").exists()


def test_run_experiment_invalid_input_reports_not_crashes(tmp_path, cfg):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b,c\n1,2,3\n")
    out = tmp_path / "bad_out"
    result = run_experiment(bad, cfg, out)
    assert not result.validation.ok
    assert result.evaluation is None
    assert (out / "metrics.json").exists()


def test_cli_synth_then_run(tmp_path):
    data = tmp_path / "d.csv"
    rc = main(["synth", "--out", str(data), "--sessions", "2", "--trials", "8"])
    assert rc == 0
    assert data.exists()

    out = tmp_path / "cli_out"
    rc = main(["run", str(data), "--out", str(out), "--no-plots"])
    assert rc == 0
    assert (out / "metrics.json").exists()


def test_cli_validate_ok(synth_csv):
    assert main(["validate", str(synth_csv)]) == 0


def test_cli_validate_failure_exit_1(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("x,y\n1,2\n3,4\n")
    assert main(["validate", str(bad)]) == 1


def test_cli_demo(tmp_path):
    out = tmp_path / "demo"
    rc = main(["demo", "--out", str(out), "--sessions", "2", "--trials", "8", "--no-plots"])
    assert rc == 0
    assert (out / "metrics.json").exists()
    assert (out / "demo_data.csv").exists()


def test_cli_missing_config_exit_2(synth_csv, tmp_path):
    out = tmp_path / "o"
    rc = main(["run", str(synth_csv), "--out", str(out), "--config", "nope.yaml"])
    assert rc == 2


def test_cli_tsv_roundtrip(tmp_path):
    data = tmp_path / "d.tsv"
    rc = main(["synth", "--out", str(data), "--sessions", "2", "--trials", "8"])
    assert rc == 0
    assert "\t" in Path(data).read_text().splitlines()[0]
    assert main(["validate", str(data)]) == 0
