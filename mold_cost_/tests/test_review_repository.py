"""
ReviewRepository 单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from api_gateway.repositories.review_repository import ReviewRepository
from shared.models import Feature, JobPriceSnapshot, JobProcessSnapshot, Subgraph
from decimal import Decimal
from datetime import datetime
import uuid


@pytest.fixture
def review_repo():
    """创建 ReviewRepository 实例"""
    return ReviewRepository()


@pytest.fixture
def mock_db_session():
    """创建模拟数据库会话"""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_job_id():
    """示例任务ID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_feature():
    """示例 Feature 对象"""
    feature = MagicMock(spec=Feature)
    feature.feature_id = 1
    feature.subgraph_id = "UP01"
    feature.job_id = uuid.uuid4()
    feature.version = 1
    feature.length_mm = Decimal("100.50")
    feature.width_mm = Decimal("50.25")
    feature.thickness_mm = Decimal("10.00")
    feature.quantity = 1
    feature.heat_treatment = "淬火"
    feature.volume_mm3 = Decimal("50000.00")
    feature.calculated_weight_kg = Decimal("0.39")
    feature.top_view_wire_length = None
    feature.front_view_wire_length = None
    feature.side_view_wire_length = None
    feature.has_auto_material = True
    feature.needs_heat_treatment = True
    feature.boring_length_mm = None
    feature.processing_instructions = {"note": "test"}
    feature.is_complete = True
    feature.missing_params = []
    feature.abnormal_situation = {}
    feature.created_by = "test_user"
    feature.created_at = datetime.utcnow()
    feature.metadata = {}
    return feature


class TestReviewRepository:
    """ReviewRepository 测试类"""
    
    @pytest.mark.asyncio
    async def test_feature_to_dict(self, review_repo, sample_feature):
        """测试 Feature 对象转字典"""
        result = review_repo._feature_to_dict(sample_feature)
        
        assert result["feature_id"] == 1
        assert result["subgraph_id"] == "UP01"
        assert result["length_mm"] == 100.50
        assert result["width_mm"] == 50.25
        assert result["thickness_mm"] == 10.00
        assert result["has_auto_material"] is True
        assert result["needs_heat_treatment"] is True
        assert isinstance(result["created_at"], str)
    
    @pytest.mark.asyncio
    async def test_get_features(self, review_repo, mock_db_session, sample_job_id, sample_feature):
        """测试查询 features"""
        # 模拟数据库查询结果
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_feature]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        
        # 重要：execute 需要返回一个 awaitable，但结果是同步的
        async def mock_execute(*args, **kwargs):
            return mock_result
        
        mock_db_session.execute = mock_execute
        
        # 执行查询
        features = await review_repo.get_features(mock_db_session, sample_job_id)
        
        # 验证结果
        assert len(features) == 1
        assert features[0]["feature_id"] == 1
        assert features[0]["subgraph_id"] == "UP01"
    
    @pytest.mark.asyncio
    async def test_update_features(self, review_repo, mock_db_session, sample_job_id):
        """测试更新 features"""
        features_data = [
            {
                "feature_id": 1,
                "subgraph_id": "UP01",
                "thickness_mm": 15.00,
                "material": "P20"
            }
        ]
        
        # 执行更新
        await review_repo.update_features(mock_db_session, sample_job_id, features_data)
        
        # 验证执行了更新
        assert mock_db_session.execute.called
    
    @pytest.mark.asyncio
    async def test_get_all_review_data(self, review_repo, mock_db_session, sample_job_id, sample_feature):
        """测试批量查询所有数据"""
        # 为每个表创建不同的 mock 对象
        mock_price_snapshot = MagicMock()
        mock_price_snapshot.snapshot_id = 1
        mock_price_snapshot.job_id = uuid.uuid4()
        mock_price_snapshot.original_price_id = "price-1"
        mock_price_snapshot.version_id = "v1"
        mock_price_snapshot.feature_type = "material"
        mock_price_snapshot.name = "材料费"
        mock_price_snapshot.description = "测试"
        mock_price_snapshot.unit_price = Decimal("50.0")
        mock_price_snapshot.unit = "kg"
        mock_price_snapshot.param_conditions = {}
        mock_price_snapshot.priority = 1
        mock_price_snapshot.is_modified = False
        mock_price_snapshot.modified_by = None
        mock_price_snapshot.modified_at = None
        mock_price_snapshot.modification_reason = None
        mock_price_snapshot.snapshot_created_at = datetime.utcnow()
        mock_price_snapshot.meta_data = {}
        
        mock_process_snapshot = MagicMock()
        mock_process_snapshot.snapshot_id = 1
        mock_process_snapshot.job_id = uuid.uuid4()
        mock_process_snapshot.original_rule_id = "rule-1"
        mock_process_snapshot.version_id = "v1"
        mock_process_snapshot.feature_type = "machining"
        mock_process_snapshot.name = "粗加工"
        mock_process_snapshot.description = "测试"
        mock_process_snapshot.conditions = {}
        mock_process_snapshot.output_params = {}
        mock_process_snapshot.priority = 1
        mock_process_snapshot.is_modified = False
        mock_process_snapshot.modified_by = None
        mock_process_snapshot.modified_at = None
        mock_process_snapshot.modification_reason = None
        mock_process_snapshot.snapshot_created_at = datetime.utcnow()
        mock_process_snapshot.meta_data = {}
        
        mock_subgraph = MagicMock()
        mock_subgraph.subgraph_id = "UP01"
        mock_subgraph.job_id = uuid.uuid4()
        mock_subgraph.part_name = "上模"
        mock_subgraph.part_code = "P001"
        mock_subgraph.material = "P20"
        mock_subgraph.subgraph_file_url = "http://example.com/file"
        mock_subgraph.weight_kg = Decimal("10.5")
        mock_subgraph.material_unit_price = Decimal("50.0")
        mock_subgraph.material_cost = Decimal("525.0")
        mock_subgraph.heat_treatment_unit_price = Decimal("100.0")
        mock_subgraph.heat_treatment_cost = Decimal("100.0")
        mock_subgraph.process_description = "测试工艺"
        mock_subgraph.nc_roughing_time = Decimal("2.5")
        mock_subgraph.nc_milling_time = Decimal("1.5")
        mock_subgraph.drilling_time = Decimal("0.5")
        mock_subgraph.milling_machine_time = Decimal("1.0")
        mock_subgraph.large_grinding_time = Decimal("0.5")
        mock_subgraph.small_grinding_count = 2
        mock_subgraph.edm_time = Decimal("1.0")
        mock_subgraph.engraving_time = Decimal("0.5")
        mock_subgraph.slow_wire_length = Decimal("100.0")
        mock_subgraph.slow_wire_side_length = Decimal("50.0")
        mock_subgraph.mid_wire_length = Decimal("80.0")
        mock_subgraph.fast_wire_length = Decimal("120.0")
        mock_subgraph.separate_item = "特殊项"
        mock_subgraph.total_cost = Decimal("1000.0")
        mock_subgraph.wire_process_note = "线割说明"
        mock_subgraph.nc_roughing_cost = Decimal("100.0")
        mock_subgraph.nc_milling_cost = Decimal("80.0")
        mock_subgraph.drilling_cost = Decimal("20.0")
        mock_subgraph.milling_machine_cost = Decimal("50.0")
        mock_subgraph.large_grinding_cost = Decimal("30.0")
        mock_subgraph.small_grinding_cost = Decimal("20.0")
        mock_subgraph.slow_wire_cost = Decimal("150.0")
        mock_subgraph.slow_wire_side_cost = Decimal("75.0")
        mock_subgraph.mid_wire_cost = Decimal("120.0")
        mock_subgraph.fast_wire_cost = Decimal("180.0")
        mock_subgraph.edm_cost = Decimal("100.0")
        mock_subgraph.engraving_cost = Decimal("50.0")
        mock_subgraph.separate_item_cost = Decimal("25.0")
        mock_subgraph.processing_cost_total = Decimal("1000.0")
        mock_subgraph.applied_snapshot_ids = []
        mock_subgraph.rule_reason = "规则说明"
        mock_subgraph.override_by_user = False
        mock_subgraph.cost_calculation_method = "standard"
        mock_subgraph.has_sheet_line = False
        mock_subgraph.sheet_area_mm2 = None
        mock_subgraph.sheet_perimeter_mm = None
        mock_subgraph.sheet_line_data = None
        mock_subgraph.has_single_nc_calc = False
        mock_subgraph.single_prt_file = None
        mock_subgraph.process_changed = False
        mock_subgraph.original_process = None
        mock_subgraph.prt_3d_file = None
        mock_subgraph.recalc_count = 0
        mock_subgraph.last_recalc_at = None
        mock_subgraph.last_recalc_by = None
        mock_subgraph.status = "completed"
        mock_subgraph.created_at = datetime.utcnow()
        mock_subgraph.updated_at = datetime.utcnow()
        mock_subgraph.meta_data = {}
        
        # 创建一个计数器来返回不同的 mock 对象
        call_count = [0]
        
        async def mock_execute(*args, **kwargs):
            mock_scalars = MagicMock()
            # 根据调用次数返回不同的对象
            if call_count[0] == 0:  # features
                mock_scalars.all.return_value = [sample_feature]
            elif call_count[0] == 1:  # price_snapshots
                mock_scalars.all.return_value = [mock_price_snapshot]
            elif call_count[0] == 2:  # process_snapshots
                mock_scalars.all.return_value = [mock_process_snapshot]
            else:  # subgraphs
                mock_scalars.all.return_value = [mock_subgraph]
            
            call_count[0] += 1
            
            mock_result = MagicMock()
            mock_result.scalars.return_value = mock_scalars
            return mock_result
        
        mock_db_session.execute = mock_execute
        
        # 执行批量查询
        data = await review_repo.get_all_review_data(mock_db_session, sample_job_id)
        
        # 验证结果
        assert "features" in data
        assert "price_snapshots" in data
        assert "process_snapshots" in data
        assert "subgraphs" in data
        assert len(data["features"]) == 1
        assert len(data["price_snapshots"]) == 1
        assert len(data["process_snapshots"]) == 1
        assert len(data["subgraphs"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
