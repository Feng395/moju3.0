"""脚本侧数据库兼容仓储出口。"""

from __future__ import annotations

from ..asyncpg import db

# 中文注释：脚本层统一从 infrastructure 获取 db，避免再反向依赖 api_gateway 兼容层。
__all__ = ["db"]
