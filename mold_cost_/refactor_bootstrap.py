"""重构过渡期的启动辅助工具。"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_src_path() -> Path:
    """确保 `src` 目录进入 `sys.path`，兼容旧入口导入新包。"""
    project_root = Path(__file__).resolve().parent
    src_path = project_root / "src"
    src_value = str(src_path)
    if src_value not in sys.path:
        sys.path.insert(0, src_value)
    return src_path
