"""Session storage & catalog.

An upload becomes a *session* stored under:

    data/uploads/YYYY-MM-DD/<session-id>/
        <sanitized-original-name>       # the raw recording
        metadata.json                   # provenance + checksum + analysis state

Derived report artifacts (for EDF) live under:

    reports/uploads/<session-id>/
        diagnostic.json, trace.png/svg, psd.png/svg, markers.png/svg

The catalog is simply the set of metadata.json files on disk — no separate
database, which keeps the prototype stateless and easy to reason about.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .security import classify_extension, format_label
from .settings import Settings


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # -- paths ---------------------------------------------------------------
    def session_dir(self, date: str, session_id: str) -> Path:
        return self.settings.uploads_dir / date / session_id

    def report_dir(self, session_id: str) -> Path:
        return self.settings.reports_dir / session_id

    # -- write ---------------------------------------------------------------
    def create_session(
        self,
        *,
        filename: str,
        data: bytes,
        checksum: str,
    ) -> dict:
        """Write raw bytes + metadata for a new session; return metadata dict.

        The caller is responsible for having already validated and sanitized
        ``filename`` and computed ``checksum``.
        """
        date = _today()
        session_id = new_session_id()
        sdir = self.session_dir(date, session_id)
        sdir.mkdir(parents=True, exist_ok=True)

        raw_path = sdir / filename
        raw_path.write_bytes(data)

        ext = Path(filename).suffix.lower()
        mode = classify_extension(ext)

        metadata = {
            "session_id": session_id,
            "date": date,
            "original_filename": filename,
            "extension": ext,
            "format_label": format_label(ext),
            "analysis_mode": mode,  # analyze | catalog-only | archival-only
            "size_bytes": len(data),
            "sha256": checksum,
            "uploaded_at": _now_iso(),
            "raw_relpath": str(raw_path.relative_to(self.settings.repo_root)),
            "analysis_status": "pending" if mode == "analyze" else "not-applicable",
            "analysis": None,
            "report_relpaths": [],
            "warnings": [],
            "hard_failures": [],
            "git": None,
        }
        self._write_metadata(sdir, metadata)
        return metadata

    def _write_metadata(self, sdir: Path, metadata: dict) -> None:
        (sdir / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=False))

    def update_metadata(self, metadata: dict) -> dict:
        sdir = self.session_dir(metadata["date"], metadata["session_id"])
        self._write_metadata(sdir, metadata)
        return metadata

    # -- read / catalog ------------------------------------------------------
    def _iter_metadata_paths(self):
        root = self.settings.uploads_dir
        if not root.exists():
            return
        for meta in sorted(root.glob("*/*/metadata.json")):
            yield meta

    def list_sessions(self) -> list[dict]:
        sessions: list[dict] = []
        for meta in self._iter_metadata_paths():
            try:
                sessions.append(json.loads(meta.read_text()))
            except (json.JSONDecodeError, OSError):
                continue
        # Newest first.
        sessions.sort(key=lambda m: m.get("uploaded_at", ""), reverse=True)
        return sessions

    def get_session(self, session_id: str) -> dict | None:
        for meta in self._iter_metadata_paths():
            try:
                data = json.loads(meta.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("session_id") == session_id:
                return data
        return None

    def resolve_repo_path(self, relpath: str) -> Path | None:
        """Resolve a repo-relative path safely inside uploads/reports dirs.

        Only paths under the configured uploads or reports directories are
        allowed, defeating traversal via serving endpoints.
        """
        root = self.settings.repo_root.resolve()
        target = (root / relpath).resolve()
        allowed_roots = [
            self.settings.uploads_dir.resolve(),
            self.settings.reports_dir.resolve(),
            self.settings.demo_reports_dir.resolve(),
        ]
        for base in allowed_roots:
            try:
                target.relative_to(base)
            except ValueError:
                continue
            if target.exists() and target.is_file():
                return target
        return None
