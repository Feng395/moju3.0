"""Legacy pricing calculator bridge: judgment."""

from __future__ import annotations

from importlib import import_module

_legacy_module = import_module("scripts.calculate.judgment")


def __getattr__(attr: str):
    return getattr(_legacy_module, attr)


def __dir__():
    return sorted(set(globals()) | set(dir(_legacy_module)))
