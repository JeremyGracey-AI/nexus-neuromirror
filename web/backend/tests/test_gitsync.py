from __future__ import annotations

from pathlib import Path

from nnm_web.gitsync import GitSyncService


class FakeRunner:
    """Records argv calls and returns scripted results."""

    def __init__(self, results):
        self.calls = []
        self._results = results

    def __call__(self, argv, cwd, timeout=60):
        self.calls.append(argv)

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        r = R()
        key = " ".join(argv[:3])
        for match, (rc, out, err) in self._results.items():
            if match in " ".join(argv):
                r.returncode, r.stdout, r.stderr = rc, out, err
                break
        return r


def _mk(tmp_path, results, enabled=True):
    return GitSyncService(tmp_path, enabled=enabled, runner=FakeRunner(results))


def test_disabled_sync_is_noop(tmp_path):
    svc = _mk(tmp_path, {}, enabled=False)
    f = tmp_path / "x.edf"
    f.write_text("data")
    res = svc.sync_files([f], "msg")
    assert res.committed is False
    assert res.pushed is False
    assert "disabled" in res.message.lower()


def test_force_add_is_used_per_file(tmp_path):
    f = tmp_path / "rec.edf"
    f.write_text("data")
    runner = FakeRunner(
        {
            "add --force": (0, "", ""),
            "commit": (0, "", ""),
            "rev-parse": (0, "deadbeef", ""),
            "push": (0, "", ""),
            "remote get-url": (0, "https://github.com/JeremyGracey-AI/nexus-neuromirror.git", ""),
        }
    )
    svc = GitSyncService(tmp_path, runner=runner)
    res = svc.sync_files([f], "add session")
    assert res.committed and res.pushed
    # Verify a force add was issued and never a bare 'git add -A'.
    add_calls = [c for c in runner.calls if c[:2] == ["git", "add"]]
    assert add_calls, "expected a git add call"
    assert all("--force" in c for c in add_calls)
    assert all("-A" not in c and "." not in c[2:] for c in add_calls)


def test_push_failure_preserves_commit(tmp_path):
    f = tmp_path / "rec.edf"
    f.write_text("data")
    runner = FakeRunner(
        {
            "add --force": (0, "", ""),
            "commit": (0, "", ""),
            "rev-parse": (0, "abc123", ""),
            "push": (128, "", "fatal: could not read Username"),
        }
    )
    svc = GitSyncService(tmp_path, runner=runner)
    res = svc.sync_files([f], "add session")
    assert res.committed is True
    assert res.pushed is False
    assert res.error and "locally" in res.error.lower()


def test_commit_url_built_from_remote(tmp_path):
    runner = FakeRunner(
        {"remote get-url": (0, "https://github.com/JeremyGracey-AI/nexus-neuromirror.git", "")}
    )
    svc = GitSyncService(tmp_path, runner=runner)
    url = svc._commit_url("abc123")
    assert url == "https://github.com/JeremyGracey-AI/nexus-neuromirror/commit/abc123"


def test_refuses_file_outside_repo(tmp_path):
    outside = tmp_path.parent / "outside.edf"
    outside.write_text("x")
    svc = GitSyncService(tmp_path / "repo", runner=FakeRunner({}))
    (tmp_path / "repo").mkdir()
    res = svc.sync_files([outside], "msg")
    assert res.error and "outside repository" in res.error
