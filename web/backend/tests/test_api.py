from __future__ import annotations

import io


def test_health(app_client):
    r = app_client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["max_upload_mb"] == 8.0
    exts = {f["ext"] for f in body["accepted_formats"]}
    assert {".edf", ".csv", ".mat", ".bcd"} <= exts


def test_repo_sync_disabled(app_client):
    r = app_client.get("/api/repo-sync")
    assert r.status_code == 200
    assert r.json()["enabled"] is False


def test_demo_report(app_client):
    r = app_client.get("/api/demo")
    assert r.status_code == 200
    body = r.json()
    assert body["diagnostic"]["status"] == "ok"
    assert "trace_png" in body["artifacts"]


def test_empty_catalog(app_client):
    assert app_client.get("/api/sessions").json()["sessions"] == []


def test_upload_edf_analyzes_and_catalogs(app_client, synthetic_edf):
    with open(synthetic_edf, "rb") as f:
        r = app_client.post("/api/upload", files={"file": ("rec.edf", f, "application/octet-stream")})
    assert r.status_code == 201
    meta = r.json()
    assert meta["analysis_mode"] == "analyze"
    assert meta["analysis_status"] == "ok"
    assert len(meta["sha256"]) == 64
    assert meta["report_relpaths"], "expected report artifacts"
    assert meta["git"]["committed"] is False  # sync disabled in tests

    # Now appears in the catalog and detail.
    sessions = app_client.get("/api/sessions").json()["sessions"]
    assert len(sessions) == 1
    sid = meta["session_id"]
    assert app_client.get(f"/api/sessions/{sid}").status_code == 200


def test_upload_rejects_bad_extension(app_client):
    r = app_client.post(
        "/api/upload", files={"file": ("evil.exe", io.BytesIO(b"MZ..."), "application/octet-stream")}
    )
    assert r.status_code == 400
    assert r.json()["stage"] == "validate"


def test_upload_rejects_traversal_name(app_client, synthetic_edf):
    # A traversal filename is sanitized to a safe base name; upload still succeeds
    # but must be stored with a safe name (no directory escape).
    with open(synthetic_edf, "rb") as f:
        r = app_client.post(
            "/api/upload",
            files={"file": ("../../../etc/evil.edf", f, "application/octet-stream")},
        )
    assert r.status_code == 201
    meta = r.json()
    assert meta["original_filename"] == "evil.edf"
    # The stored basename must be the sanitized name, not an escape sequence.
    assert meta["raw_relpath"].endswith(f"{meta['session_id']}/evil.edf")


def test_upload_rejects_empty_file(app_client):
    r = app_client.post(
        "/api/upload", files={"file": ("empty.edf", io.BytesIO(b""), "application/octet-stream")}
    )
    assert r.status_code == 413
    assert r.json()["stage"] == "size"


def test_upload_bcd_is_archival_only(app_client):
    r = app_client.post(
        "/api/upload", files={"file": ("arch.bcd", io.BytesIO(b"BCD-bytes"), "application/octet-stream")}
    )
    assert r.status_code == 201
    meta = r.json()
    assert meta["analysis_mode"] == "archival-only"
    assert meta["analysis_status"] == "not-applicable"
    assert meta["report_relpaths"] == []


def test_upload_csv_is_catalog_only(app_client):
    r = app_client.post(
        "/api/upload", files={"file": ("data.csv", io.BytesIO(b"t,ch1\n0,1\n"), "text/csv")}
    )
    assert r.status_code == 201
    assert r.json()["analysis_mode"] == "catalog-only"


def test_artifact_serving_and_traversal(app_client, synthetic_edf):
    with open(synthetic_edf, "rb") as f:
        meta = app_client.post(
            "/api/upload", files={"file": ("rec.edf", f, "application/octet-stream")}
        ).json()
    rel = meta["report_relpaths"][0]
    assert app_client.get("/api/artifact", params={"path": rel}).status_code == 200
    # Traversal / outside path is rejected.
    assert app_client.get("/api/artifact", params={"path": "../../etc/passwd"}).status_code == 404


def test_missing_session_404(app_client):
    assert app_client.get("/api/sessions/deadbeef").status_code == 404


def test_demo_artifact_served_from_bundled_dir(app_client):
    """Bundled demo report figures serve even when reports_dir is redirected.

    The demo lives under repo `reports/diagnostic_demo/`, which is outside the
    configurable uploads/reports dirs; it is allowlisted read-only so the
    Overview demo works regardless of NNM_REPORTS_SUBDIR.
    """
    art = app_client.get("/api/demo").json()["artifacts"]
    resp = app_client.get("/api/artifact", params={"path": art["trace_png"]})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/")
    # A sibling source file outside the demo dir must still be rejected.
    assert (
        app_client.get(
            "/api/artifact",
            params={"path": "reports/diagnostic_demo/../../src/nexus_neuromirror/config.py"},
        ).status_code
        == 404
    )
