"""
测试 P2 实施结果

验证：
1. 水磨相关 Category 是否添加
2. LLM Prompt 是否包含复杂数据结构说明
3. LLM Prompt 是否包含单位和精度说明
4. LLM Prompt 是否包含视图与尺寸对应关系说明
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.action_handlers.query_details_handler import QueryDetailsHandler


def test_water_mill_categories():
    """测试水磨相关 Category"""
    handler = QueryDetailsHandler()
    
    # 水磨相关 Category
    water_mill_categories = [
        ("water_mill_thread_ends", "水磨螺纹端"),
        ("water_mill_hanging_table", "水磨挂台"),
        ("water_mill_bevel", "水磨斜面"),
        ("water_mill_oil_tank", "水磨油槽"),
        ("water_mill_high_cost", "水磨高费用"),
        ("water_mill_plate", "水磨板"),
        ("water_mill_component", "水磨零件"),
        ("water_mill_grinding", "水磨磨削"),
    ]
    
    # 测试每个 Category
    for category, chinese_name in water_mill_categories:
        test_steps = [
            {
                "category": category,
                "steps": [{
                    "step": "测试步骤",
                    "formula": "100 * 2",
                    "cost": 200.0
                }]
            }
        ]
        
        result = handler._format_calculation_steps("TEST01", test_steps)
        
        assert chinese_name in result, \
            f"❌ {category} ({chinese_name}) 未在 category_map 中\n结果: {result}"
    
    print(f"✅ 水磨 Category 测试通过（8个 Category）")


def test_llm_prompt_enhancements():
    """测试 LLM Prompt 增强"""
    handler = QueryDetailsHandler()
    
    # 创建测试数据（包含复杂结构）
    test_steps = [
        {
            "category": "nc_milling",
            "steps": [{
                "step": "统计各类工时",
                "details": [
                    {"code": "精铣", "value": "60"},
                    {"code": "M", "value": "30"}
                ],
                "summary": {
                    "jing_xi_hours": 1.0,
                    "kai_cu_hours": 0.0,
                    "drill_hours": 0.5
                }
            }]
        }
    ]
    
    # 构建字段说明（这会触发 Prompt 构建逻辑）
    glossary = handler._build_field_glossary(test_steps)
    
    # 验证字段说明包含复杂结构的字段
    assert "details" in glossary or "summary" in glossary, \
        "❌ 字段说明未包含复杂数据结构字段"
    
    print("✅ LLM Prompt 增强测试通过（字段说明包含复杂结构）")


def test_prompt_content():
    """测试 Prompt 内容（通过代码审查）"""
    import inspect
    
    handler = QueryDetailsHandler()
    
    # 获取 _format_with_llm 方法的源代码
    source = inspect.getsource(handler._format_with_llm)
    
    # 验证 Prompt 包含关键内容
    checks = [
        ("复杂数据结构说明", "复杂数据结构说明"),
        ("数组类型", "数组类型"),
        ("对象类型", "对象类型"),
        ("单位和精度说明", "单位和精度说明"),
        ("单位", "单位"),
        ("精度", "精度"),
        ("视图与尺寸对应关系", "视图与尺寸对应关系"),
        ("top_view", "top_view"),
        ("thickness_mm", "thickness_mm"),
    ]
    
    for name, keyword in checks:
        assert keyword in source, f"❌ Prompt 未包含 {name}（关键词: {keyword}）"
    
    print("✅ Prompt 内容测试通过（包含所有增强内容）")


def test_category_count():
    """测试 Category 总数"""
    handler = QueryDetailsHandler()
    
    # 测试所有 Category（包括 P0, P1, P2）
    all_categories = [
        # P0 之前
        "weight", "material", "heat", "wire_base", "wire_special",
        "nc_base", "nc_roughing", "nc_milling", "nc_drilling",
        "water_mill_high", "water_mill_long_strip", "water_mill_chamfer",
        "add_auto_material", "standard",
        # P0
        "tooth_hole_time", "wire_standard", "total", "wire_speci",
        # P2
        "water_mill_thread_ends", "water_mill_hanging_table", "water_mill_bevel",
        "water_mill_oil_tank", "water_mill_high_cost", "water_mill_plate",
        "water_mill_component", "water_mill_grinding",
    ]
    
    # 测试格式化
    success_count = 0
    for category in all_categories:
        test_steps = [
            {
                "category": category,
                "steps": [{
                    "step": "测试",
                    "formula": "1 + 1",
                    "result": 2
                }]
            }
        ]
        
        try:
            result = handler._format_calculation_steps("TEST01", test_steps)
            if len(result) > 0:
                success_count += 1
        except Exception as e:
            print(f"⚠️  {category} 格式化失败: {e}")
    
    print(f"✅ Category 总数测试通过（{success_count}/{len(all_categories)} 个 Category 可用）")
    
    # 至少应该支持 26 个 Category
    assert success_count >= 26, f"❌ Category 数量不足: {success_count} < 26"


def main():
    """运行所有测试"""
    print("=" * 60)
    print("开始测试 P2 实施结果")
    print("=" * 60)
    
    try:
        test_water_mill_categories()
        test_llm_prompt_enhancements()
        test_prompt_content()
        test_category_count()
        
        print("\n" + "=" * 60)
        print("✅ 所有 P2 测试通过！")
        print("=" * 60)
        print("\nP2 实施总结：")
        print("  - 新增 8 个水磨相关 Category")
        print("  - 在 LLM Prompt 中添加复杂数据结构说明")
        print("  - 在 LLM Prompt 中添加单位和精度说明")
        print("  - 在 LLM Prompt 中强调视图与尺寸对应关系")
        print("  - 总计支持 26+ 个 Category")
        print("\n详细文档：")
        print("  - QUERY_DETAILS_IMPLEMENTATION_SUMMARY.md")
        print("  - QUERY_DETAILS_P0_P1_COMPLETE.md")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
