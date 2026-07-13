"""Upload safety primitives: filename sanitization, path-traversal rejection,
extension allow-listing, size limits, and SHA-256 checksums.

These functions are deliberately pure and side-effect free so they can be unit
tested in isolation. Raw file *contents* are never logged or echoed anywhere.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import PurePosixPath

from .settings import (
    ALLOWED_EXTENSIONS,
    ANALYZABLE_EXTENSIONS,
    ARCHIVAL_ONLY_EXTENSIONS,
    CATALOG_ONLY_EXTENSIONS,
    FORMAT_LABELS,
)


class UploadValidationError(ValueError):
    """Raised when an upload fails a safety or format check."""


_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_MULTI_DOT = re.compile(r"\.{2,}")


def sanitize_filename(raw_name: str) -> str:
    """Return a safe base filename with no directory components.

    - Strips any path (both POSIX and Windows separators), defeating traversal
      such as ``../../etc/passwd`` or ``..\\..\\secret``.
    - Normalizes Unicode and drops disallowed characters.
    - Collapses repeated dots so ``a..b`` cannot re-introduce traversal.
    - Rejects empty results.
    """
    if raw_name is None:
        raise UploadValidationError("Missing filename.")

    # Normalize Unicode to a canonical form, then drop non-ASCII.
    name = unicodedata.normalize("NFKD", raw_name)
    name = name.encode("ascii", "ignore").decode("ascii")

    # Take only the final path component, handling both separator styles.
    name = name.replace("\\", "/")
    name = PurePosixPath(name).name  # strips directories and leading slashes

    # Remove control chars and disallowed characters.
    name = name.replace("\x00", "")
    name = _SAFE_CHARS.sub("_", name).strip("._")
    name = _MULTI_DOT.sub(".", name)

    if not name or name in {".", ".."}:
        raise UploadValidationError("Filename is empty after sanitization.")
    # Cap the length to keep filesystem paths reasonable.
    if len(name) > 128:
        stem, _, ext = name.rpartition(".")
        name = (stem[:120] + "." + ext) if ext else name[:128]
    return name


def is_path_safe(candidate: str) -> bool:
    """Return True if ``candidate`` has no traversal or absolute components."""
    if not candidate:
        return False
    normalized = candidate.replace("\\", "/")
    if normalized.startswith("/"):
        return False
    parts = PurePosixPath(normalized).parts
    return ".." not in parts and not any(p.startswith("/") for p in parts)


def extension_of(filename: str) -> str:
    """Return the lowercased extension including the leading dot (or '')."""
    return PurePosixPath(filename).suffix.lower()


def classify_extension(ext: str) -> str:
    """Return an analysis-mode string for a (validated) extension."""
    ext = ext.lower()
    if ext in ANALYZABLE_EXTENSIONS:
        return "analyze"
    if ext in CATALOG_ONLY_EXTENSIONS:
        return "catalog-only"
    if ext in ARCHIVAL_ONLY_EXTENSIONS:
        return "archival-only"
    return "unsupported"


def format_label(ext: str) -> str:
    return FORMAT_LABELS.get(ext.lower(), "Unknown")


def validate_extension(filename: str) -> str:
    """Validate the file extension against the allow-list.

    Returns the normalized extension. Raises :class:`UploadValidationError`
    for anything outside the allow-list.
    """
    ext = extension_of(filename)
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise UploadValidationError(
            f"Unsupported file type '{ext or '(none)'}'. Allowed: {allowed}."
        )
    return ext


def validate_size(size_bytes: int, max_bytes: int) -> None:
    """Reject empty or oversized uploads."""
    if size_bytes <= 0:
        raise UploadValidationError("Uploaded file is empty.")
    if size_bytes > max_bytes:
        mb = max_bytes / (1024 * 1024)
        raise UploadValidationError(
            f"File exceeds the {mb:.0f} MB upload limit (deployment proxy caps requests at 10 MB)."
        )


def sha256_of_bytes(data: bytes) -> str:
    """Compute a hex SHA-256 digest of raw bytes without logging contents."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_of_file(path) -> str:
    """Compute a hex SHA-256 digest of a file, streamed in chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
