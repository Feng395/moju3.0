"""Bridge the existing ODA-backed converter into the new infrastructure layer."""


def _load_converter():
    from scripts.cad_chaitu.converter import DWGConverter as LegacyDWGConverter

    return LegacyDWGConverter


class DWGConverter:
    def __new__(cls, *args, **kwargs):
        return _load_converter()(*args, **kwargs)


__all__ = ["DWGConverter"]
