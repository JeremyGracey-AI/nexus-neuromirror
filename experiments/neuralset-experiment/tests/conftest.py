"""Shared fixtures: synthetic data + default config (no private files needed)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from neuralset_scaffold.config import default_config
from neuralset_scaffold.synth import generate_synthetic


@pytest.fixture
def cfg():
    return default_config()


@pytest.fixture
def synth_df() -> pd.DataFrame:
    # Small but non-trivial: 2 sessions, enough trials for session-aware CV.
    return generate_synthetic(n_sessions=2, trials_per_class=8, seed=17)


@pytest.fixture
def synth_csv(tmp_path: Path, synth_df: pd.DataFrame) -> Path:
    path = tmp_path / "rec.csv"
    synth_df.to_csv(path, index=False)
    return path
