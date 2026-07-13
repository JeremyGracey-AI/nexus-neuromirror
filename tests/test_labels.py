from __future__ import annotations

import pytest

from nexus_neuromirror.labels import (
    contains_token,
    core_label,
    find_channel,
    match_alias,
    normalize,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("EEG Fz-A1A2", "fz"),
        ("Fz", "fz"),
        ("Oz-LE", "oz"),
        ("EEG Pz-A1A2", "pz"),
        ("FCz", "fcz"),
        ("EEG FCz-A1A2", "fcz"),
    ],
)
def test_core_label(raw, expected):
    assert core_label(raw) == expected


def test_fz_does_not_match_fcz():
    # The classic confusion: Fz must not swallow FCz.
    assert core_label("EEG FCz-A1A2") == "fcz"
    assert not match_alias("EEG FCz-A1A2", ["Fz"])
    assert match_alias("EEG FCz-A1A2", ["FCz"])


def test_find_channel_with_aliases():
    names = ["EEG Fz-A1A2", "EEG FCz-A1A2", "EEG Pz-A1A2", "EEG Oz-A1A2", "Status"]
    assert find_channel(names, ["Fz", "EEG Fz"]) == "EEG Fz-A1A2"
    assert find_channel(names, ["Oz"]) == "EEG Oz-A1A2"
    assert find_channel(names, ["T7"]) is None


def test_normalize_strips_separators():
    assert normalize("STI 014") == "sti014"
    assert normalize("Fz-A1A2") == "fza1a2"


def test_contains_token():
    assert contains_token("EOG-L", ["EOG", "ECG"])
    assert not contains_token("EEG Fz-A1A2", ["EOG", "ECG"])
