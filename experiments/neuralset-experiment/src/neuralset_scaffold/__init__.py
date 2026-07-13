"""NeuralSet experiment scaffold.

A lightweight, reproducible first-experiment pipeline for four-channel
NeXus-10 / BioTrace CSV/TSV exports (channels Fz, FCz, Pz, Oz) with event
markers: validate -> preprocess -> window -> features -> baseline classifier.

This is a research/engineering scaffold. It makes no medical claims and does
not decode consciousness or mental states; it evaluates whether simple spectral
features separate user-defined event labels above chance on your own data.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
