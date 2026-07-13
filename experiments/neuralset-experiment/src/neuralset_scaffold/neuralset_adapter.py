"""Optional NeuralSet integration boundary.

This module defines a stable seam where a NeuralSet backend could plug in for
feature extraction or modeling. The scaffold runs fully **without** NeuralSet;
if the dependency is not importable, :func:`is_available` returns ``False`` and
the adapter raises a clear, actionable error instead of guessing at an API.

No specific NeuralSet API is assumed or fabricated here. Wire the real calls
inside :meth:`NeuralSetAdapter.transform` once the dependency is present.
"""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass

from .features import FeatureMatrix
from .windows import WindowSet

_MODULE_NAME = "neuralset"


def is_available() -> bool:
    """True if a NeuralSet backend can be imported in this environment."""
    return importlib.util.find_spec(_MODULE_NAME) is not None


class NeuralSetUnavailableError(RuntimeError):
    """Raised when NeuralSet features are requested but the backend is absent."""


@dataclass
class NeuralSetAdapter:
    """Thin boundary object; instantiate only when :func:`is_available`."""

    module_name: str = _MODULE_NAME

    def __post_init__(self) -> None:
        if not is_available():
            raise NeuralSetUnavailableError(
                "NeuralSet backend not installed. Install the optional extra "
                "(`pip install -e '.[neuralset]'`) or use the built-in spectral "
                "features. The scaffold does not require NeuralSet."
            )
        self._backend = importlib.import_module(self.module_name)

    def backend_version(self) -> str:
        return str(getattr(self._backend, "__version__", "unknown"))

    def transform(self, windows: WindowSet) -> FeatureMatrix:
        """Produce a FeatureMatrix using the NeuralSet backend.

        Intentionally left as an explicit integration point. Implement the real
        NeuralSet calls here (windows.data_uv is (n_windows, n_channels,
        n_samples)); until then this raises so behavior is never silently wrong.
        """
        raise NotImplementedError(
            "NeuralSet transform is a wiring point for a real backend. "
            "Map windows.data_uv -> features here and return a FeatureMatrix."
        )


def describe() -> dict[str, object]:
    """Report adapter status for diagnostics/metrics."""
    available = is_available()
    info: dict[str, object] = {"available": available, "module": _MODULE_NAME}
    if available:
        try:
            info["version"] = NeuralSetAdapter().backend_version()
        except Exception as exc:  # noqa: BLE001
            info["version"] = f"error: {exc}"
    return info
