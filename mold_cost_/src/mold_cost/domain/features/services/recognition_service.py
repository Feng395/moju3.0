"""特征识别领域桥接服务。"""

from __future__ import annotations


class LegacyFeatureRecognitionService:
    """桥接现有特征识别能力。

    当前项目的特征识别由 CAD 编排统一驱动，
    这里先提供领域层落点，后续再拆出独立服务实现。
    """

    async def recognize(self, context: dict) -> dict:
        raise RuntimeError("当前项目的特征识别仍由 CAD 编排统一驱动")


feature_recognition_service = LegacyFeatureRecognitionService()
