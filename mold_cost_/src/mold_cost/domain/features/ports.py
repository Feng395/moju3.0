"""特征识别领域端口定义。"""

from __future__ import annotations

from typing import Protocol


class FeatureRecognitionService(Protocol):
    async def recognize(self, context: dict) -> dict: ...
