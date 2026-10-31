"""Git ingestion engine: clone, structure scan, and symbol extraction."""

from .clone import CloneError, clone_repo
from .pipeline import run_ingestion
from .structure import scan_structure
from .symbols import extract_symbols

__all__ = [
    "clone_repo",
    "CloneError",
    "scan_structure",
    "extract_symbols",
    "run_ingestion",
]
