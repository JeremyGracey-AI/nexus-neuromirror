from __future__ import annotations

import pytest

from nnm_web.security import (
    UploadValidationError,
    classify_extension,
    is_path_safe,
    sanitize_filename,
    sha256_of_bytes,
    validate_extension,
    validate_size,
)


class TestSanitize:
    def test_strips_posix_traversal(self):
        assert sanitize_filename("../../etc/passwd.edf") == "passwd.edf"

    def test_strips_windows_traversal(self):
        assert sanitize_filename("..\\..\\secret.edf") == "secret.edf"

    def test_strips_absolute_path(self):
        assert sanitize_filename("/var/data/rec.edf") == "rec.edf"

    def test_collapses_double_dots(self):
        # "a..b" must not re-introduce traversal
        out = sanitize_filename("a..b.edf")
        assert ".." not in out

    def test_replaces_unsafe_chars(self):
        assert sanitize_filename("My Session (v2).EDF") == "My_Session_v2_.EDF"

    def test_rejects_empty(self):
        with pytest.raises(UploadValidationError):
            sanitize_filename("")

    def test_rejects_only_dots(self):
        with pytest.raises(UploadValidationError):
            sanitize_filename("..")

    def test_length_cap(self):
        name = "x" * 300 + ".edf"
        assert len(sanitize_filename(name)) <= 128


class TestPathSafe:
    def test_rejects_traversal(self):
        assert is_path_safe("../secret") is False

    def test_rejects_absolute(self):
        assert is_path_safe("/etc/passwd") is False

    def test_accepts_normal(self):
        assert is_path_safe("reports/uploads/abc/diagnostic.json") is True


class TestExtension:
    def test_accepts_edf(self):
        assert validate_extension("rec.edf") == ".edf"

    def test_accepts_csv_mat_bcd(self):
        for name, ext in [("a.csv", ".csv"), ("b.mat", ".mat"), ("c.bcd", ".bcd")]:
            assert validate_extension(name) == ext

    def test_rejects_disallowed(self):
        with pytest.raises(UploadValidationError):
            validate_extension("evil.exe")

    def test_rejects_no_extension(self):
        with pytest.raises(UploadValidationError):
            validate_extension("noext")

    def test_classify(self):
        assert classify_extension(".edf") == "analyze"
        assert classify_extension(".csv") == "catalog-only"
        assert classify_extension(".bcd") == "archival-only"


class TestSize:
    def test_rejects_empty(self):
        with pytest.raises(UploadValidationError):
            validate_size(0, 1000)

    def test_rejects_oversize(self):
        with pytest.raises(UploadValidationError):
            validate_size(2000, 1000)

    def test_accepts_within_limit(self):
        validate_size(500, 1000)  # no raise


class TestChecksum:
    def test_known_sha256(self):
        # SHA-256 of b"abc"
        expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        assert sha256_of_bytes(b"abc") == expected

    def test_changes_with_content(self):
        assert sha256_of_bytes(b"a") != sha256_of_bytes(b"b")
