"""Isolated integration test against a real temporary git repo (no network).

This proves that the force-add strategy commits an otherwise-ignored data file
without broadly unignoring the data directory. There is no remote, so push is
expected to fail gracefully while the commit is preserved.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from nnm_web.gitsync import GitSyncService


def _git(argv, cwd):
    return subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, check=True)


@pytest.fixture()
def temp_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["git", "init", "-q"], repo)
    _git(["git", "config", "user.email", "t@t.local"], repo)
    _git(["git", "config", "user.name", "t"], repo)
    # .gitignore excludes the whole data dir, like the real project.
    (repo / ".gitignore").write_text("data/**\n!data/README.md\n*.edf\n")
    (repo / "README.md").write_text("repo")
    _git(["git", "add", "."], repo)
    _git(["git", "commit", "-qm", "init"], repo)
    return repo


def test_force_add_commits_ignored_file(temp_repo):
    data_dir = temp_repo / "data" / "uploads" / "2026-07-13" / "abc"
    data_dir.mkdir(parents=True)
    rec = data_dir / "session.edf"
    rec.write_bytes(b"\x00\x01edf")
    meta = data_dir / "metadata.json"
    meta.write_text("{}")

    svc = GitSyncService(temp_repo, branch="master")
    res = svc.sync_files([rec, meta], "data: add abc")

    # Commit succeeds; push fails (no remote) but commit is preserved.
    assert res.committed is True
    assert res.pushed is False

    tracked = subprocess.run(
        ["git", "ls-files"], cwd=str(temp_repo), capture_output=True, text=True
    ).stdout
    assert "session.edf" in tracked
    assert "metadata.json" in tracked

    # Crucially, an unrelated ignored file was NOT swept in.
    other = temp_repo / "data" / "uploads" / "other.edf"
    other.write_bytes(b"x")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--ignored"],
        cwd=str(temp_repo),
        capture_output=True,
        text=True,
    ).stdout
    assert "other.edf" in status  # present but ignored, not staged
