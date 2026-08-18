"""NeXus NeuroMirror: four-channel NeXus-10 + BioTrace+ neurofeedback prototype.

Offline-first / blockwise design. No public real-time NeXus-10 SDK is assumed.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nexus-neuromirror")
except PackageNotFoundError:  # running from a source tree without an installed dist
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
