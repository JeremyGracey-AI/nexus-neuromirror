"""Column-label normalization and alias matching for CSV/TSV headers."""

from __future__ import annotations

import re

_SEP = re.compile(r"[^a-z0-9]+")
_PREFIXES = ("eeg",)
_REF_SUFFIXES = ("a1a2", "a2a1", "m1m2", "le", "ref", "a1", "a2", "m1", "m2")


def normalize(label: str) -> str:
    return _SEP.sub("", str(label).strip().lower())


def core_label(label: str) -> str:
    """Normalized label with an EEG prefix and reference suffix trimmed."""
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


def resolve_column(
    columns: list[str], canonical: str, aliases: list[str] | None = None
) -> str | None:
    """Find the header in ``columns`` matching ``canonical`` or an alias."""
    candidates = [canonical, *(aliases or [])]
    cand_norm = {normalize(c) for c in candidates}
    cand_core = {core_label(c) for c in candidates}
    for col in columns:
        if normalize(col) in cand_norm or core_label(col) in cand_core:
            return col
    return None
