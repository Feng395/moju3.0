"""Compatibility wrapper for the refactored settings module."""

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.core.settings import Settings, get_settings, print_config_summary, settings

__all__ = ["Settings", "get_settings", "print_config_summary", "settings"]
