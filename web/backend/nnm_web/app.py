"""FastAPI application for the NeXus NeuroMirror dashboard.

Endpoints (all under /api):
    GET  /api/health            -> service + config status
    GET  /api/repo-sync         -> git remote / credential status
    GET  /api/sessions          -> catalog of uploaded sessions
    GET  /api/sessions/{id}     -> single session detail
    POST /api/upload            -> secure multipart upload + analyze + git sync
    GET  /api/demo              -> bundled synthetic demo report (Overview)
    GET  /api/artifact?path=..  -> serve a report/raw artifact safely

The frontend static build (if present) is served at the root.
"""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .analysis import analyze_edf_session
from .gitsync import GitSyncService
from .security import (
    UploadValidationError,
    classify_extension,
    format_label,
    sanitize_filename,
    sha256_of_bytes,
    validate_extension,
    validate_size,
)
from .settings import SETTINGS, ALLOWED_EXTENSIONS, FORMAT_LABELS
from .storage import SessionStore

app = FastAPI(title="NeXus NeuroMirror Dashboard API", version=__version__)

store = SessionStore(SETTINGS)


def _git_service() -> GitSyncService:
    return GitSyncService(
        SETTINGS.repo_root,
        remote=SETTINGS.git_remote,
        branch=SETTINGS.git_branch,
        author_name=SETTINGS.git_author_name,
        author_email=SETTINGS.git_author_email,
        enabled=SETTINGS.git_sync_enabled,
    )


# --- Health & status ---------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    config_ok = SETTINGS.config_path.is_file()
    return {
        "status": "ok",
        "version": __version__,
        "config_path": str(SETTINGS.config_path),
        "config_available": config_ok,
        "max_upload_bytes": SETTINGS.max_upload_bytes,
        "max_upload_mb": round(SETTINGS.max_upload_bytes / (1024 * 1024), 1),
        "accepted_formats": [
            {"ext": ext, "label": FORMAT_LABELS[ext], "mode": classify_extension(ext)}
            for ext in sorted(ALLOWED_EXTENSIONS)
        ],
    }


@app.get("/api/repo-sync")
def repo_sync() -> dict:
    return _git_service().repo_status()


# --- Demo (Overview) ---------------------------------------------------------
@app.get("/api/demo")
def demo() -> dict:
    """Return the bundled synthetic demo diagnostic report for the Overview."""
    demo_json = SETTINGS.repo_root / "reports" / "diagnostic_demo" / "diagnostic.json"
    if not demo_json.is_file():
        raise HTTPException(status_code=404, detail="Demo report not found.")
    payload = json.loads(demo_json.read_text())
    # Expose artifact paths the frontend can request.
    artifacts = {}
    base = "reports/diagnostic_demo"
    for stem in ("trace", "psd", "markers"):
        for fmt in ("png", "svg"):
            rel = f"{base}/{stem}.{fmt}"
            if (SETTINGS.repo_root / rel).is_file():
                artifacts[f"{stem}_{fmt}"] = rel
    return {"diagnostic": payload, "artifacts": artifacts}


# --- Catalog -----------------------------------------------------------------
@app.get("/api/sessions")
def list_sessions() -> dict:
    return {"sessions": store.list_sessions()}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    meta = store.get_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Session not found.")
    return meta


# --- Upload ------------------------------------------------------------------
@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> JSONResponse:
    # 1. Sanitize + validate extension BEFORE reading a large body.
    try:
        safe_name = sanitize_filename(file.filename or "")
        ext = validate_extension(safe_name)
    except UploadValidationError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc), "stage": "validate"})

    # 2. Read the body with a hard size cap (never log contents).
    data = await file.read(SETTINGS.max_upload_bytes + 1)
    try:
        validate_size(len(data), SETTINGS.max_upload_bytes)
    except UploadValidationError as exc:
        return JSONResponse(status_code=413, content={"error": str(exc), "stage": "size"})

    # 3. Checksum + write session.
    checksum = sha256_of_bytes(data)
    metadata = store.create_session(filename=safe_name, data=data, checksum=checksum)

    # 4. Analyze EDF (only). Catalog-only / archival-only are skipped.
    if metadata["analysis_mode"] == "analyze":
        metadata = analyze_edf_session(metadata, store, SETTINGS)

    # 5. Git sync: commit raw + metadata + report artifacts, then push.
    files_to_sync = [
        SETTINGS.repo_root / metadata["raw_relpath"],
        store.session_dir(metadata["date"], metadata["session_id"]) / "metadata.json",
    ]
    for rel in metadata.get("report_relpaths", []):
        files_to_sync.append(SETTINGS.repo_root / rel)

    commit_msg = (
        f"data: add session {metadata['session_id']} "
        f"({metadata['format_label']}, {metadata['analysis_status']})"
    )
    git_result = _git_service().sync_files(files_to_sync, commit_msg)
    metadata["git"] = git_result.as_dict()
    store.update_metadata(metadata)

    return JSONResponse(status_code=201, content=metadata)


# --- Artifact serving --------------------------------------------------------
@app.get("/api/artifact")
def artifact(path: str = Query(..., description="Repo-relative path under uploads/ or reports/")):
    target = store.resolve_repo_path(path)
    if not target:
        raise HTTPException(status_code=404, detail="Artifact not found or not permitted.")
    media_type, _ = mimetypes.guess_type(str(target))
    return FileResponse(str(target), media_type=media_type or "application/octet-stream")


# --- Static frontend (served last so /api takes precedence) ------------------
_FRONTEND_DIST = Path(__file__).resolve().parents[1].parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="static")
