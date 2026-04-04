"""Transitional logging facade."""

from __future__ import annotations

from shared.logging_config import get_logger as get_logger
from shared.logging_config import setup_logging as setup_logging
from shared.unified_logging import init_logging as init_logging

try:
    from shared.unified_logging import quick_init_logging as quick_init_logging
except ImportError:  # pragma: no cover
    def quick_init_logging(name: str):
        setup_logging()
        return get_logger(name)
