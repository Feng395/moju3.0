"""Legacy pricing calculator bridge: price_tooth_hole."""

from __future__ import annotations

from importlib import import_module

_legacy_module = import_module("scripts.calculate.price_tooth_hole")


def __getattr__(attr: str):
    return getattr(_legacy_module, attr)


def __dir__():
    return sorted(set(globals()) | set(dir(_legacy_module)))
