"""Server-side git synchronization for uploaded recordings and reports.

Design goals:
- Use ``git`` (and ``gh`` only for deriving a commit URL) on the server. GitHub
  credentials are never exposed to the frontend.
- The repository ``.gitignore`` excludes neural data and reports on purpose, so
  we ``git add --force`` **only** the explicit list of files produced by an
  accepted upload. We never broadly unignore data.
- Missing credentials or push failures must not lose the local upload: the file
  is already written before any git call, and every git step returns a status
  instead of raising, so the caller can report a partial result.

All subprocess calls are constructed from a fixed argv list (never a shell
string) and never include raw file contents.
"""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class GitSyncResult:
    enabled: bool = True
    committed: bool = False
    pushed: bool = False
    commit_sha: str | None = None
    commit_url: str | None = None
    branch: str | None = None
    message: str = ""
    error: str | None = None
    steps: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def _run(argv: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


class GitSyncService:
    """Encapsulates the commit/push flow so it can be swapped out in tests."""

    def __init__(
        self,
        repo_root: Path,
        *,
        remote: str = "origin",
        branch: str = "master",
        author_name: str = "NeXus NeuroMirror Dashboard",
        author_email: str = "dashboard@nexus-neuromirror.local",
        enabled: bool = True,
        runner=_run,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.remote = remote
        self.branch = branch
        self.author_name = author_name
        self.author_email = author_email
        self.enabled = enabled
        self._run = runner

    # -- helpers -------------------------------------------------------------
    def _rel(self, path: Path) -> str:
        return str(Path(path).resolve().relative_to(self.repo_root.resolve()))

    def remote_url(self) -> str | None:
        proc = self._run(["git", "remote", "get-url", self.remote], self.repo_root)
        if proc.returncode == 0:
            return proc.stdout.strip() or None
        return None

    def _commit_url(self, sha: str) -> str | None:
        url = self.remote_url()
        if not url:
            return None
        # Normalize common GitHub URL shapes into an https commit link.
        u = url.strip()
        if u.startswith("git@github.com:"):
            u = "https://github.com/" + u[len("git@github.com:") :]
        if u.endswith(".git"):
            u = u[: -len(".git")]
        # Handle the agent proxy host by rewriting to github.com if it looks like one.
        if "github.com" not in u and "/JeremyGracey-AI/" in u:
            tail = u.split("/", 3)[-1] if u.count("/") >= 3 else u
            u = "https://github.com/" + tail.lstrip("/")
        if "github.com" in u:
            return f"{u}/commit/{sha}"
        return None

    # -- main flow -----------------------------------------------------------
    def sync_files(self, files: list[Path], message: str) -> GitSyncResult:
        """Force-add the given files, commit, and push. Never raises for git
        errors; returns a structured result instead.
        """
        result = GitSyncResult(enabled=self.enabled, branch=self.branch, message=message)
        if not self.enabled:
            result.message = "Git sync disabled by configuration."
            result.steps.append("skipped: sync disabled")
            return result

        try:
            rels = [self._rel(f) for f in files]
        except ValueError as exc:
            result.error = f"Refusing to add file outside repository: {exc}"
            result.steps.append("error: path outside repo")
            return result

        # Explicit, per-file force add. This is the ONLY place we bypass
        # .gitignore, and only for files this upload produced.
        for rel in rels:
            proc = self._run(["git", "add", "--force", "--", rel], self.repo_root)
            result.steps.append(f"git add --force {rel} (rc={proc.returncode})")
            if proc.returncode != 0:
                result.error = f"git add failed for {rel}: {proc.stderr.strip()}"
                return result

        # Commit with an explicit author identity.
        commit_argv = [
            "git",
            "-c",
            f"user.name={self.author_name}",
            "-c",
            f"user.email={self.author_email}",
            "commit",
            "-m",
            message,
        ]
        proc = self._run(commit_argv, self.repo_root)
        result.steps.append(f"git commit (rc={proc.returncode})")
        if proc.returncode != 0:
            # Nothing to commit is not fatal, but surface it.
            result.error = f"git commit failed: {proc.stderr.strip() or proc.stdout.strip()}"
            return result
        result.committed = True

        sha_proc = self._run(["git", "rev-parse", "HEAD"], self.repo_root)
        if sha_proc.returncode == 0:
            result.commit_sha = sha_proc.stdout.strip()

        # Push. Missing credentials or network failures are reported, not raised.
        push_proc = self._run(
            ["git", "push", self.remote, f"HEAD:{self.branch}"], self.repo_root, timeout=120
        )
        result.steps.append(f"git push (rc={push_proc.returncode})")
        if push_proc.returncode != 0:
            result.error = (
                "Push failed (commit is saved locally). "
                f"{push_proc.stderr.strip() or 'Check server-side GitHub credentials.'}"
            )
            return result
        result.pushed = True
        if result.commit_sha:
            result.commit_url = self._commit_url(result.commit_sha)
        result.message = "Committed and pushed to origin."
        return result

    def repo_status(self) -> dict:
        """Return a small status summary for the repo-sync endpoint."""
        status: dict = {
            "enabled": self.enabled,
            "branch": self.branch,
            "remote": self.remote,
            "remote_url": None,
            "credentials_available": False,
            "ahead": None,
            "note": "",
        }
        url = self.remote_url()
        status["remote_url"] = url
        if not self.enabled:
            status["note"] = "Git sync is disabled by configuration."
            return status
        # A lightweight, read-only check for push capability. `git ls-remote`
        # exercises credentials without mutating anything.
        ls = self._run(["git", "ls-remote", "--heads", self.remote], self.repo_root, timeout=30)
        status["credentials_available"] = ls.returncode == 0
        if ls.returncode != 0:
            status["note"] = (
                "Remote not reachable with current credentials. Uploads will be "
                "saved locally and committed, but push may fail until GitHub "
                "credentials are injected server-side."
            )
        else:
            status["note"] = "Remote reachable; push path available."
        return status
