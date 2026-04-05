"""Bridge the existing CAD split database helper into the refactored package."""


def _load_database_manager():
    # 中文说明：通过延迟加载隔离旧 CAD 数据库模块，避免 import 时触发重型初始化。
    from scripts.cad_chaitu.database import DatabaseManager as LegacyDatabaseManager

    return LegacyDatabaseManager


class DatabaseManager:
    def __new__(cls, *args, **kwargs):
        # 中文说明：对外保持同名类接口，内部再实例化 legacy manager。
        return _load_database_manager()(*args, **kwargs)


__all__ = ["DatabaseManager"]
