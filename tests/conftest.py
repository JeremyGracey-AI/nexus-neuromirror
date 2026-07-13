from __future__ import annotations

from pathlib import Path

import pytest

from nexus_neuromirror.synth import export_synthetic_edf, make_synthetic_raw

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = REPO_ROOT / "configs" / "project.example.yaml"


@pytest.fixture(scope="session")
def example_config_path() -> Path:
    return EXAMPLE_CONFIG


@pytest.fixture()
def synthetic_raw():
    return make_synthetic_raw(duration_s=40.0)


@pytest.fixture()
def synthetic_edf(tmp_path) -> Path:
    path = tmp_path / "session.edf"
    export_synthetic_edf(str(path), duration_s=40.0)
    return path
