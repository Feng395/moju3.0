"""Legacy pricing search bridge: wire_total_search."""

from __future__ import annotations

from importlib import import_module

_legacy_module = import_module("scripts.search.wire_total_search")


def __getattr__(attr: str):
    return getattr(_legacy_module, attr)


def __dir__():
    return sorted(set(globals()) | set(dir(_legacy_module)))
