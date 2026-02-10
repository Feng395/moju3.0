"""
测试工艺修改功能修复
验证：
1. Subgraph 模型包含 wire_process 字段
2. 验证器不再检查 process_snapshots 表
3. 工艺修改解析正常工作
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.models import Subgraph
from shared.validators.modification_validator import ModificationValidator
from agents.nlp_parser import NLPParser
import inspect


def test_subgraph_model():
    """测试 Subgraph 模型是否包含 wire_process 字段"""
    print("=" * 60)
    print("测试 1: Subgraph 模型字段检查")
    print("=" * 60)
    
    # 获取所有列
    columns = [col.name for col in Subgraph.__table__.columns]
    
    print(f"📋 Subgraph 模型字段数量: {len(columns)}")
    
    # 检查关键字段
    required_fields = ['wire_process', 'wire_process_note']
    
    for field in required_fields:
        if field in columns:
            print(f"✅ {field}: 存在")
        else:
            print(f"❌ {field}: 缺失")
    
    print()


def test_validator_tables():
    """测试验证器支持的表"""
    print("=" * 60)
    print("测试 2: 验证器支持的表")
    print("=" * 60)
    
    tables = list(ModificationValidator.TABLE_ID_FIELDS.keys())
    print(f"📋 支持的表: {', '.join(tables)}")
    
    if 'process_snapshots' in tables:
        print("❌ 错误: 仍然支持 process_snapshots 表")
    else:
        print("✅ 正确: 已移除 process_snapshots 表")
    
    if 'subgraphs' in tables:
        print("✅ 正确: 支持 subgraphs 表")
    else:
        print("❌ 错误: 缺少 subgraphs 表")
    
    print()


def test_validator_allowed_fields():
    """测试验证器允许的字段"""
    print("=" * 60)
    print("测试 3: 验证器允许的字段")
    print("=" * 60)
    
    if 'subgraphs' in ModificationValidator.ALLOWED_FIELDS:
        allowed = ModificationValidator.ALLOWED_FIELDS['subgraphs']
        print(f"📋 subgraphs 表允许修改的字段: {len(allowed)} 个")
        
        required_fields = ['wire_process', 'wire_process_note']
        for field in required_fields:
            if field in allowed:
                print(f"✅ {field}: 允许修改")
            else:
                print(f"❌ {field}: 不允许修改")
    else:
        print("❌ 错误: 验证器中没有 subgraphs 表配置")
    
    print()


def test_nlp_parser_prompt():
    """测试 NLP Parser 的 Prompt 是否正确"""
    print("=" * 60)
    print("测试 4: NLP Parser Prompt 检查")
    print("=" * 60)
    
    # 获取 _build_prompt 方法的源代码
    parser = NLPParser(use_llm=False)
    source = inspect.getsource(parser._build_prompt)
    
    # 检查是否提到不使用 process_snapshots
    if 'process_snapshots' in source:
        if '不要使用 process_snapshots' in source or '已移除' in source:
            print("✅ Prompt 中正确说明了不使用 process_snapshots")
        else:
            print("⚠️  Prompt 中提到了 process_snapshots，但没有说明不使用")
    else:
        print("✅ Prompt 中没有提到 process_snapshots")
    
    # 检查是否说明工艺信息在 subgraphs 表中
    if 'subgraphs' in source and 'wire_process' in source:
        print("✅ Prompt 中说明了工艺信息在 subgraphs 表中")
    else:
        print("⚠️  Prompt 中没有明确说明工艺信息的位置")
    
    print()


def test_modification_validation():
    """测试修改验证"""
    print("=" * 60)
    print("测试 5: 修改验证")
    print("=" * 60)
    
    # 模拟数据
    current_data = {
        "subgraphs": [
            {
                "subgraph_id": "sg_001",
                "part_name": "上夹板",
                "wire_process": None,
                "wire_process_note": None
            }
        ]
    }
    
    # 测试工艺修改
    changes = [
        {
            "table": "subgraphs",
            "id": "sg_001",
            "field": "wire_process",
            "value": "fast_and_one"
        },
        {
            "table": "subgraphs",
            "id": "sg_001",
            "field": "wire_process_note",
            "value": "快丝割一刀"
        }
    ]
    
    result = ModificationValidator.validate_changes(changes, current_data)
    
    if result.is_valid:
        print("✅ 工艺修改验证通过")
        if result.warnings:
            print(f"⚠️  警告: {', '.join(result.warnings)}")
    else:
        print(f"❌ 工艺修改验证失败: {result.error_message}")
    
    print()


def test_process_snapshots_rejection():
    """测试是否拒绝 process_snapshots 表的修改"""
    print("=" * 60)
    print("测试 6: 拒绝 process_snapshots 表修改")
    print("=" * 60)
    
    current_data = {
        "process_snapshots": [
            {"snapshot_id": "ps_001", "name": "test"}
        ]
    }
    
    changes = [
        {
            "table": "process_snapshots",
            "id": "ps_001",
            "field": "name",
            "value": "new_name"
        }
    ]
    
    result = ModificationValidator.validate_changes(changes, current_data)
    
    if not result.is_valid:
        print("✅ 正确拒绝了 process_snapshots 表的修改")
        print(f"   错误信息: {result.error_message}")
    else:
        print("❌ 错误: 仍然允许修改 process_snapshots 表")
    
    print()


if __name__ == "__main__":
    print("\n🧪 工艺修改功能修复验证")
    print("=" * 60)
    print()
    
    try:
        test_subgraph_model()
        test_validator_tables()
        test_validator_allowed_fields()
        test_nlp_parser_prompt()
        test_modification_validation()
        test_process_snapshots_rejection()
        
        print("=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
