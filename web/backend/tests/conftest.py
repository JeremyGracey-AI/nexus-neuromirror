from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture()
def synthetic_edf(tmp_path) -> Path:
    """Write a small synthetic EDF using the existing package generator."""
    from nexus_neuromirror.synth import export_synthetic_edf

    path = tmp_path / "session.edf"
    export_synthetic_edf(str(path), duration_s=40.0)
    return path


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    """A TestClient bound to a temporary repo layout with git sync disabled.

    We point the uploads/reports dirs into a temp copy of the repo so the real
    repository is never touched by tests, and disable git sync.
    """
    # Use the real repo root (for configs + demo) but redirect writable dirs.
    monkeypatch.setenv("NNM_REPO_ROOT", str(REPO_ROOT))
    monkeypatch.setenv("NNM_UPLOADS_SUBDIR", os.path.relpath(tmp_path / "uploads", REPO_ROOT))
    monkeypatch.setenv("NNM_REPORTS_SUBDIR", os.path.relpath(tmp_path / "reports", REPO_ROOT))
    monkeypatch.setenv("NNM_GIT_SYNC_ENABLED", "0")

    import nnm_web.settings as settings_mod

    importlib.reload(settings_mod)
    import nnm_web.storage as storage_mod

    importlib.reload(storage_mod)
    import nnm_web.analysis as analysis_mod

    importlib.reload(analysis_mod)
    import nnm_web.app as app_mod

    importlib.reload(app_mod)

    from fastapi.testclient import TestClient

    return TestClient(app_mod.app)
