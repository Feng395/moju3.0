"""Bridge the existing file storage helper into the new domain layer."""


def _load_storage_manager():
    from scripts.cad_chaitu.storage import FileStorageManager as LegacyFileStorageManager

    return LegacyFileStorageManager


class FileStorageManager:
    def __new__(cls, *args, **kwargs):
        return _load_storage_manager()(*args, **kwargs)


__all__ = ["FileStorageManager"]
