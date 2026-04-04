"""NX 相关基础设施适配层。"""

from __future__ import annotations

import os
from pathlib import Path


class NXAdapter:
    """NX 工具路径适配器。"""

    def __init__(self, nx_bin_dir: str | None = None):
        self.nx_bin_dir = Path(nx_bin_dir or os.getenv("NX_BIN_DIR", "")).expanduser()

    @property
    def run_journal_path(self) -> Path:
        """返回 run_journal.exe 路径。"""
        return self.nx_bin_dir / "run_journal.exe"

    def is_available(self) -> bool:
        """检查 NX 运行环境是否可用。"""
        return self.run_journal_path.exists()
