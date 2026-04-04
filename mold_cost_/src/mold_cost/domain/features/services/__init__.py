"""特征识别领域服务导出。"""

from ....infrastructure.cad.legacy_feature_recognition_gateway import LegacyFeatureRecognitionGateway
from .recognition_service import LegacyFeatureRecognitionService

feature_recognition_service = LegacyFeatureRecognitionService(LegacyFeatureRecognitionGateway())

__all__ = ["LegacyFeatureRecognitionService", "feature_recognition_service"]
