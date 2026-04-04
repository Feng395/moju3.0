"""Bridge the existing CAD split database helper into the refactored package."""

from scripts.cad_chaitu.database import DatabaseManager

__all__ = ["DatabaseManager"]
