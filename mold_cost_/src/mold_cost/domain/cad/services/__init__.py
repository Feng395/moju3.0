"""CAD domain services."""

from ....infrastructure.cad.legacy_cad_split_gateway import LegacyCadSplitGateway
from .split_service import LegacyCadSplitService

cad_split_service = LegacyCadSplitService(LegacyCadSplitGateway())

__all__ = ["LegacyCadSplitService", "cad_split_service"]
