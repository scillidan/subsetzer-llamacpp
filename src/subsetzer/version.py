"""Version information for subsetzer-llamacpp."""
from __future__ import annotations

__all__ = ["__version__"]

try:
    from importlib.metadata import version

    __version__ = version("subsetzer-llamacpp")
except Exception:
    __version__ = "0.0.0"
