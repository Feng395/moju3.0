"""
聊天历史仓储兼容壳。

中文说明：
1. 默认实现已经迁入 `src/mold_cost`。
2. legacy 调用面继续保留原类名，避免旧入口一次性改动过大。
"""

from __future__ import annotations

from refactor_bootstrap import ensure_src_path

ensure_src_path()

from mold_cost.infrastructure.db.repositories.chat_history_repository import (  # noqa: E402
    ChatHistoryRepository as SrcChatHistoryRepository,
)


class ChatHistoryRepository(SrcChatHistoryRepository):
    """兼容旧导入路径的聊天历史仓储外壳。"""

