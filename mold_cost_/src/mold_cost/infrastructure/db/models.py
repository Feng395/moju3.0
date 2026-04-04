"""Bridge existing ORM models into the refactored package."""

from __future__ import annotations

from .session import Base
from shared.models import *  # noqa: F401,F403
