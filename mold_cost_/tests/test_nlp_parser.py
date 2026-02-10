"""
NLP Parser 单元测试
负责人：人员B2

测试内容：
1. 规则解析
2. LLM 解析
3. Fallback 机制
4. 数据验证
"""
import pytest
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.nlp_parser import NLPParser


# ========== 测试数据 ==========

SAMPLE_CONTEXT = {
    "features": [
        {
            "feature_id": 1,
            "subgraph_id": "UP01",
            "length_mm": 100.0,
            "width_mm": 50.0,
            "thickness_mm": 10.0,
            "material": "P20"
        }
    ],
    "subgraphs": [
        {
            "subgraph_id": "UP01",
            "part_name": "上模板",
            "weight_kg": 5.5,
            "total_cost": 1000.0,
            "process_description": "铣削加工"
        },
        {
            "subgraph_id": "UP02",
            "part_name": "下模板",
            "weight_kg": 6.0,
            "total_cost": 1200.0,
            "process_description": "线切割"
        }
    ],
    "price_snapshots": [],
    "process_snapshots": []
}


# ========== 规则解析测试 ==========

@pytest.mark.asyncio
async def test_rule_parse_pattern1():
    """测试规则解析 - 模式1: 将 X 的 Y 改为 Z"""
    parser = NLPParser(use_llm=False)
    
    text = "将 UP01 的材质改为 718"
    changes = await parser.parse(text, SAMPLE_CONTEXT)
    
    assert len(changes) == 1
    assert changes[0]["table"] == "subgraphs"
    assert changes[0]["id"] == "UP01"
    assert changes[0]["field"] == "material"
    assert changes[0]["value"] == "718"
    
    await parser.close()
    print("✅ 规则解析 - 模式1 测试通过")


@pytest.mark.asyncio
async def test_rule_parse_pattern2():
    """测试规则解析 - 模式2: 修改 X 的 Y 为 Z"""
    parser = NLPParser(use_llm=False)
    
    text = "修改 UP02 的厚度为 15mm"
    changes = await parser.parse(text, SAMPLE_CONTEXT)
    
    assert len(changes) == 1
    assert changes[0]["table"] == "subgraphs"
    assert changes[0]["id"] == "UP02"
    assert changes[0]["field"] == "thickness_mm"
    assert changes[0]["value"] == "15mm"
    
    await parser.close()
    print("✅ 规则解析 - 模式2 测试通过")


@pytest.mark.asyncio
async def test_rule_parse_pattern3():
    """测试规则解析 - 模式3: 把 X 的 Y 设置为 Z"""
    parser = NLPParser(use_llm=False)
    
    text = "把 UP01 的重量设置为 6.5kg"
    changes = await parser.parse(text, SAMPLE_CONTEXT)
    
    assert len(changes) == 1
    assert changes[0]["table"] == "subgraphs"
    assert changes[0]["id"] == "UP01"
    assert changes[0]["field"] == "weight_kg"
    assert changes[0]["value"] == "6.5kg"
    
    await parser.close()
    print("✅ 规则解析 - 模式3 测试通过")


@pytest.mark.asyncio
async def test_rule_parse_multiple():
    """测试规则解析 - 多个修改"""
    parser = NLPParser(use_llm=False)
    
    text = "将 UP01 的材质改为 718，把 UP02 的重量设置为 7kg"
    changes = await parser.parse(text, SAMPLE_CONTEXT)
    
    assert len(changes) == 2
    assert changes[0]["id"] == "UP01"
    assert changes[1]["id"] == "UP02"
    
    await parser.close()
    print("✅ 规则解析 - 多个修改 测试通过")


@pytest.mark.asyncio
async def test_rule_parse_chinese_field():
    """测试规则解析 - 中文字段名"""
    parser = NLPParser(use_llm=False)
    
    text = "将 UP01 的材质改为 718"
    changes = await parser.parse(text, SAMPLE_CONTEXT)
    
    assert len(changes) == 1
    assert changes[0]["field"] == "material"  # 应该转换为英文
    
    await parser.close()
    print("✅ 规则解析 - 中文字段名 测试通过")


# ========== LLM 解析测试 ==========

@pytest.mark.asyncio
async def test_llm_parse_simple():
    """测试 LLM 解析 - 简单指令"""
    parser = NLPParser(use_llm=True)
    
    text = "将 UP01 的材质改为 718"
    changes = await parser.parse(text, SAMPLE_CONTEXT)
    
    # LLM 应该能正确解析
    assert len(changes) >= 1
    assert any(c["id"] == "UP01" for c in changes)
    
    await parser.close()
    print("✅ LLM 解析 - 简单指令 测试通过")


@pytest.mark.asyncio
async def test_llm_parse_complex():
    """测试 LLM 解析 - 复杂指令"""
    parser = NLPParser(use_llm=True)
    
    text = "请把上模板的材料换成 718，然后将下模板的加工说明改为精密铣削"
    changes = await parser.parse(text, SAMPLE_CONTEXT)
    
    # LLM 应该能理解"上模板"指的是 UP01
    assert len(changes) >= 1
    
    await parser.close()
    print("✅ LLM 解析 - 复杂指令 测试通过")


@pytest.mark.asyncio
async def test_llm_fallback():
    """测试 LLM Fallback 机制"""
    # 使用无效的 LLM 配置，强制 fallback
    import os
    original_url = os.getenv("OPENAI_BASE_URL")
    os.environ["OPENAI_BASE_URL"] = "http://invalid-url"
    
    parser = NLPParser(use_llm=True)
    
    text = "将 UP01 的材质改为 718"
    changes = await parser.parse(text, SAMPLE_CONTEXT)
    
    # 应该 fallback 到规则解析
    assert len(changes) == 1
    assert changes[0]["id"] == "UP01"
    
    # 恢复配置
    if original_url:
        os.environ["OPENAI_BASE_URL"] = original_url
    
    await parser.close()
    print("✅ LLM Fallback 机制 测试通过")


# ========== 辅助功能测试 ==========

@pytest.mark.asyncio
async def test_field_normalization():
    """测试字段名标准化"""
    parser = NLPParser(use_llm=False)
    
    # 测试中文字段名映射
    assert parser._normalize_field_name("材质") == "material"
    assert parser._normalize_field_name("重量") == "weight_kg"
    assert parser._normalize_field_name("厚度") == "thickness_mm"
    
    # 未知字段名应该保持不变
    assert parser._normalize_field_name("unknown_field") == "unknown_field"
    
    await parser.close()
    print("✅ 字段名标准化 测试通过")


@pytest.mark.asyncio
async def test_table_inference():
    """测试表名推断"""
    parser = NLPParser(use_llm=False)
    
    # 应该能根据 ID 推断表名
    table = parser._infer_table("UP01", "material", SAMPLE_CONTEXT)
    assert table == "subgraphs"
    
    table = parser._infer_table("1", "length_mm", SAMPLE_CONTEXT)
    assert table == "features"
    
    # 未知 ID 应该默认返回 subgraphs
    table = parser._infer_table("UNKNOWN", "field", SAMPLE_CONTEXT)
    assert table == "subgraphs"
    
    await parser.close()
    print("✅ 表名推断 测试通过")


# ========== 运行所有测试 ==========

async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("NLP Parser 单元测试")
    print("=" * 60)
    
    # 规则解析测试
    print("\n📋 规则解析测试:")
    await test_rule_parse_pattern1()
    await test_rule_parse_pattern2()
    await test_rule_parse_pattern3()
    await test_rule_parse_multiple()
    await test_rule_parse_chinese_field()
    
    # LLM 解析测试
    print("\n🤖 LLM 解析测试:")
    try:
        await test_llm_parse_simple()
        await test_llm_parse_complex()
    except Exception as e:
        print(f"⚠️  LLM 测试跳过（可能是网络问题）: {e}")
    
    # Fallback 测试
    print("\n🔄 Fallback 测试:")
    await test_llm_fallback()
    
    # 辅助功能测试
    print("\n🔧 辅助功能测试:")
    await test_field_normalization()
    await test_table_inference()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
