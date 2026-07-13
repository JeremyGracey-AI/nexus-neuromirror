"""Label normalization and alias matching.

BioTrace+ / EDF exports use inconsistent channel and marker labels
(``"EEG Fz-A1A2"``, ``"Fz"``, ``"Ch1"``, ...). Normalization strips case and
separators; :func:`core_label` additionally removes a leading ``EEG`` prefix
and trailing reference tokens (``A1A2``, ``LE``, ...) so a small alias list can
match the many surface forms a device might emit without brittle enumeration.
"""

from __future__ import annotations

import re

_SEP = re.compile(r"[^a-z0-9]+")

# Reference / prefix tokens that carry no site information and can be trimmed.
_PREFIXES = ("eeg",)
_REF_SUFFIXES = (
    "a1a2", "a2a1", "m1m2", "m2m1",
    "linkedears", "linkedear", "le",
    "ref", "avg", "cor",
    "a1", "a2", "m1", "m2",
)


def normalize(label: str) -> str:
    """Lowercase a label and remove all non-alphanumeric characters."""
    return _SEP.sub("", label.strip().lower())


def core_label(label: str) -> str:
    """Normalized label with a leading EEG prefix and trailing reference tokens removed.

    ``"EEG Fz-A1A2"`` -> ``"fz"``; ``"Fz"`` -> ``"fz"``; ``"Oz-LE"`` -> ``"oz"``.
    Trimming is conservative: it never empties the string.
    """
    norm = normalize(label)
    for pre in _PREFIXES:
        if norm.startswith(pre) and len(norm) > len(pre):
            norm = norm[len(pre):]
            break
    for suf in _REF_SUFFIXES:
        if norm.endswith(suf) and len(norm) > len(suf):
            norm = norm[: -len(suf)]
            break
    return norm


def match_alias(label: str, aliases: list[str]) -> bool:
    """True if ``label`` matches any alias by normalized or core form."""
    norm = normalize(label)
    core = core_label(label)
    for a in aliases:
        if norm == normalize(a) or core == core_label(a):
            return True
    return False


def find_channel(channel_names: list[str], aliases: list[str]) -> str | None:
    """Return the first channel name in ``channel_names`` matching any alias."""
    for name in channel_names:
        if match_alias(name, aliases):
            return name
    return None


def contains_token(label: str, tokens: list[str]) -> bool:
    """True if any token appears as a normalized substring of the label.

    Used for loose classification (e.g. flagging ``"EOG-L"`` as non-EEG via the
    ``EOG`` token) where an exact alias match is too strict.
    """
    norm = normalize(label)
    return any(normalize(t) in norm for t in tokens if t)
