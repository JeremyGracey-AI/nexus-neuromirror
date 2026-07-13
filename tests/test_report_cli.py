from __future__ import annotations

import json

from nexus_neuromirror.cli import main
from nexus_neuromirror.config import load_config
from nexus_neuromirror.report import generate_report


def test_generate_report_writes_artifacts(synthetic_edf, example_config_path, tmp_path):
    cfg = load_config(example_config_path)
    out = tmp_path / "diagnostic"
    result = generate_report(synthetic_edf, cfg, out)
    assert result.ok

    json_path = out / "diagnostic.json"
    assert json_path.is_file()
    payload = json.loads(json_path.read_text())
    assert payload["status"] == "ok"
    assert payload["artifacts"], "expected image artifacts to be listed"

    for stem in ("trace", "psd", "markers"):
        assert (out / f"{stem}.png").is_file()
        assert (out / f"{stem}.svg").is_file()


def test_cli_verify_returns_zero_on_success(synthetic_edf, example_config_path, tmp_path, capsys):
    out = tmp_path / "report"
    rc = main(["verify", str(synthetic_edf), "--config", str(example_config_path), "--out", str(out)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Result    : OK" in captured.out


def test_cli_verify_returns_one_on_hard_failure(example_config_path, tmp_path):
    from nexus_neuromirror.synth import export_synthetic_edf

    short = tmp_path / "short.edf"
    export_synthetic_edf(str(short), duration_s=5.0)
    out = tmp_path / "report"
    rc = main(["verify", str(short), "--config", str(example_config_path), "--out", str(out)])
    assert rc == 1


def test_cli_missing_recording_returns_two(example_config_path, tmp_path):
    out = tmp_path / "report"
    rc = main(["verify", str(tmp_path / "nope.edf"), "--config", str(example_config_path), "--out", str(out)])
    assert rc == 2


def test_cli_bad_config_returns_two(synthetic_edf, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("project:\n  name: x\n")  # missing channels
    out = tmp_path / "report"
    rc = main(["verify", str(synthetic_edf), "--config", str(bad), "--out", str(out)])
    assert rc == 2
