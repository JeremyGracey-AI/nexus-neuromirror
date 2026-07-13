"""Runtime settings for the NeXus NeuroMirror web backend.

All configuration is read from environment variables at import time so the same
process can be started locally or in a hosted preview with credentials injected
by the operator. Nothing here is exposed to the frontend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _repo_root_default() -> Path:
    # nnm_web/ -> backend/ -> web/ -> <repo root>
    return Path(__file__).resolve().parents[3]


# --- Accepted upload formats -------------------------------------------------
# Extension -> human label. BCD is archival-only and must never be parsed.
# ASCII/CSV and MAT are catalog-only in the MVP. EDF/EDF+ is analyzed.
ANALYZABLE_EXTENSIONS = {".edf"}
CATALOG_ONLY_EXTENSIONS = {".csv", ".txt", ".asc", ".mat"}
ARCHIVAL_ONLY_EXTENSIONS = {".bcd"}

FORMAT_LABELS = {
    ".edf": "EDF/EDF+",
    ".csv": "ASCII/CSV",
    ".txt": "ASCII/CSV",
    ".asc": "ASCII/CSV",
    ".mat": "MATLAB .mat",
    ".bcd": "BCD (archival)",
}

ALLOWED_EXTENSIONS = (
    ANALYZABLE_EXTENSIONS | CATALOG_ONLY_EXTENSIONS | ARCHIVAL_ONLY_EXTENSIONS
)

# Deployment proxy caps requests at 10 MB; keep MVP uploads safely below that.
MAX_UPLOAD_BYTES = int(os.environ.get("NNM_MAX_UPLOAD_BYTES", str(8 * 1024 * 1024)))


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    uploads_subdir: str = "data/uploads"
    reports_subdir: str = "reports/uploads"
    config_path: Path = field(default_factory=lambda: _repo_root_default() / "configs" / "project.example.yaml")
    max_upload_bytes: int = MAX_UPLOAD_BYTES

    # Git sync configuration
    git_remote: str = "origin"
    git_branch: str = "master"
    git_author_name: str = "NeXus NeuroMirror Dashboard"
    git_author_email: str = "dashboard@nexus-neuromirror.local"
    # When false, uploads are saved and cataloged but never committed/pushed.
    git_sync_enabled: bool = True

    @property
    def uploads_dir(self) -> Path:
        return self.repo_root / self.uploads_subdir

    @property
    def reports_dir(self) -> Path:
        return self.repo_root / self.reports_subdir

    @property
    def demo_reports_dir(self) -> Path:
        # Bundled synthetic demo report shipped with the repo. Served read-only
        # so the Overview demo works regardless of the configured reports subdir.
        return self.repo_root / "reports" / "diagnostic_demo"


def load_settings() -> Settings:
    repo_root = Path(os.environ.get("NNM_REPO_ROOT", str(_repo_root_default()))).resolve()
    config_env = os.environ.get("NNM_CONFIG_PATH")
    config_path = Path(config_env).resolve() if config_env else repo_root / "configs" / "project.example.yaml"
    return Settings(
        repo_root=repo_root,
        uploads_subdir=os.environ.get("NNM_UPLOADS_SUBDIR", "data/uploads"),
        reports_subdir=os.environ.get("NNM_REPORTS_SUBDIR", "reports/uploads"),
        config_path=config_path,
        max_upload_bytes=MAX_UPLOAD_BYTES,
        git_remote=os.environ.get("NNM_GIT_REMOTE", "origin"),
        git_branch=os.environ.get("NNM_GIT_BRANCH", "master"),
        git_author_name=os.environ.get("NNM_GIT_AUTHOR_NAME", "NeXus NeuroMirror Dashboard"),
        git_author_email=os.environ.get("NNM_GIT_AUTHOR_EMAIL", "dashboard@nexus-neuromirror.local"),
        git_sync_enabled=os.environ.get("NNM_GIT_SYNC_ENABLED", "1") not in {"0", "false", "False", ""},
    )


SETTINGS = load_settings()
