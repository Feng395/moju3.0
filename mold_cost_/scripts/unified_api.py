# -*- coding: utf-8 -*-
"""历史 unified_api 兼容启动壳。"""

from __future__ import annotations

from pathlib import Path
import sys

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from refactor_bootstrap import ensure_src_path

ensure_src_path()
load_dotenv(PROJECT_ROOT / ".env")

try:
    from scripts.config_loader import get_server_config, load_config

    load_config()
    server_config = get_server_config()
    if server_config.get("host"):
        import os

        os.environ.setdefault("CAD_SERVER_HOST", str(server_config["host"]))
    if server_config.get("port"):
        import os

        os.environ.setdefault("CAD_SERVER_PORT", str(server_config["port"]))
    if server_config.get("reload") is not None:
        import os

        os.environ.setdefault("API_RELOAD", str(server_config["reload"]))
    if server_config.get("workers") is not None:
        import os

        os.environ.setdefault("API_WORKERS", str(server_config["workers"]))
except Exception:
    # 中文注释：配置加载失败时退回环境变量默认值，避免兼容入口直接不可启动。
    pass

from mold_cost.interfaces.api.legacy_cad_api import app, run

__all__ = ["app"]


if __name__ == "__main__":
    run("unified_api:app")
