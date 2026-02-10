"""
测试水磨字段更新实施结果

测试内容：
1. 小水磨字段是否在 field_glossary 中
2. 大水磨字段是否在 field_glossary 中
3. 水磨字段翻译是否正确
4. 水磨结果字段是否正确
5. important_groups 是否包含水磨分组
"""
import sys


def test_small_water_mill_fields():
    """测试小水磨字段是否在 field_glossary 中"""
    print("=" * 60)
    print("测试 1: 小水磨字段说明")
    print("=" * 60)
    
    from agents.action_handlers.query_details_handler import QueryDetailsHandler
    
    handler = QueryDetailsHandler()
    
    # 测试数据（包含小水磨相关字段）
    test_steps = [
        {
            "category": "water_mill_thread_ends",
            "steps": [{
                "step": "计算线头费",
                "thread_ends_count": 4,
                "thread_ends_cost": 20.0
            }]
        },
        {
            "category": "water_mill_hanging_table",
            "steps": [{
                "step": "计算挂台费",
                "hanging_table_count": 2,
                "hanging_table_cost": 10.0
            }]
        },
        {
            "category": "water_mill_chamfer",
            "steps": [{
                "step": "计算倒角费",
                "chamfer_type": "c1_c2",
                "total_chamfer_cost": 15.0
            }]
        },
        {
            "category": "water_mill_bevel",
            "steps": [{
                "step": "计算斜面费",
                "bevel_value": 8.0,
                "total_bevel_cost": 25.0
            }]
        },
        {
            "category": "water_mill_oil_tank",
            "steps": [{
                "step": "计算油槽费",
                "oil_tank_count": 3,
                "oil_tank_cost": 18.0
            }]
        },
        {
            "category": "water_mill_high_cost",
            "steps": [{
                "step": "计算高度费",
                "thickness_diff": 5.0,
                "high_cost": 12.0
            }]
        }
    ]
    
    glossary = handler._build_field_glossary(test_steps)
    
    # 验证关键字段
    required_fields = [
        ("thread_ends_count", "线头数量"),
        ("thread_ends_cost", "线头费用"),
        ("hanging_table_count", "挂台数量"),
        ("hanging_table_cost", "挂台费用"),
        ("chamfer_type", "倒角类型"),
        ("total_chamfer_cost", "倒角总费用"),
        ("bevel_value", "斜面值"),
        ("total_bevel_cost", "斜面总费用"),
        ("oil_tank_count", "油槽数量"),
        ("oil_tank_cost", "油槽费用"),
        ("thickness_diff", "厚度差异"),
        ("high_cost", "高度费用"),
    ]
    
    success = True
    found_count = 0
    
    for field_key, field_name in required_fields:
        if field_key in glossary or field_name in glossary:
            print(f"✅ {field_key} ({field_name}) 已添加")
            found_count += 1
        else:
            print(f"❌ {field_key} ({field_name}) 未找到")
            success = False
    
    print(f"\n小水磨字段覆盖率: {found_count}/{len(required_fields)}")
    
    if found_count >= len(required_fields) * 0.8:
        print("✅ 小水磨字段说明测试通过")
    else:
        print("❌ 小水磨字段说明测试失败")
        success = False
    
    return success


def test_large_water_mill_fields():
    """测试大水磨字段是否在 field_glossary 中"""
    print("\n" + "=" * 60)
    print("测试 2: 大水磨字段说明")
    print("=" * 60)
    
    from agents.action_handlers.query_details_handler import QueryDetailsHandler
    
    handler = QueryDetailsHandler()
    
    # 测试数据（包含大水磨相关字段）
    test_steps = [
        {
            "category": "water_mill_plate",
            "steps": [{
                "step": "计算板费",
                "area": 150000.0,
                "divisor": 1290,
                "plate_cost": 17.44
            }]
        },
        {
            "category": "water_mill_long_strip",
            "steps": [{
                "step": "计算长条费",
                "max_length": 450.0,
                "range": "[300, 500)",
                "long_strip_cost": 1.0
            }]
        },
        {
            "category": "water_mill_component",
            "steps": [{
                "step": "计算零件费",
                "grinding": 6,
                "max_length_width": 180.0,
                "component_cost": 30.0
            }]
        }
    ]
    
    glossary = handler._build_field_glossary(test_steps)
    
    # 验证关键字段
    required_fields = [
        ("area", "面积"),
        ("divisor", "除数"),
        ("plate_cost", "板费用"),
        ("max_length", "最长边"),
        ("range", "价格区间"),
        ("long_strip_cost", "长条费用"),
        ("grinding", "研磨面数"),
        ("max_length_width", "长宽最大值"),
        ("component_cost", "零件费用"),
    ]
    
    success = True
    found_count = 0
    
    for field_key, field_name in required_fields:
        if field_key in glossary or field_name in glossary:
            print(f"✅ {field_key} ({field_name}) 已添加")
            found_count += 1
        else:
            print(f"❌ {field_key} ({field_name}) 未找到")
            success = False
    
    print(f"\n大水磨字段覆盖率: {found_count}/{len(required_fields)}")
    
    if found_count >= len(required_fields) * 0.8:
        print("✅ 大水磨字段说明测试通过")
    else:
        print("❌ 大水磨字段说明测试失败")
        success = False
    
    return success


def test_water_mill_translations():
    """测试水磨字段翻译是否正确"""
    print("\n" + "=" * 60)
    print("测试 3: 水磨字段翻译")
    print("=" * 60)
    
    from agents.action_handlers.query_details_handler import QueryDetailsHandler
    
    handler = QueryDetailsHandler()
    
    # 测试翻译
    test_translations = {
        # 小水磨
        'thread_ends_count': '线头数量',
        'thread_ends_cost': '线头费用(元)',
        'hanging_table_count': '挂台数量',
        'hanging_table_cost': '挂台费用(元)',
        'chamfer_type': '倒角类型',
        'total_chamfer_cost': '倒角总费用(元)',
        'bevel_value': '斜面值',
        'total_bevel_cost': '斜面总费用(元)',
        'oil_tank_count': '油槽数量',
        'oil_tank_cost': '油槽费用(元)',
        'thickness_diff': '厚度差异(mm)',
        'high_cost': '高度费用(元)',
        # 大水磨
        'area': '面积(mm²)',
        'plate_cost': '板费用(元)',
        'long_strip_cost': '长条费用(小时/件)',
        'grinding': '研磨面数',
        'component_cost': '零件费用(元)',
    }
    
    success = True
    passed = 0
    
    for key, expected in test_translations.items():
        actual = handler._translate_key(key)
        if actual == expected:
            print(f"✅ {key} → {actual}")
            passed += 1
        else:
            print(f"❌ {key} → {actual} (期望: {expected})")
            success = False
    
    print(f"\n翻译准确率: {passed}/{len(test_translations)}")
    
    return success


def test_water_mill_result_fields():
    """测试水磨结果字段是否正确"""
    print("\n" + "=" * 60)
    print("测试 4: 水磨结果字段")
    print("=" * 60)
    
    from agents.action_handlers.query_details_handler import QueryDetailsHandler
    
    handler = QueryDetailsHandler()
    
    # 测试结果字段
    test_result_fields = [
        'thread_ends_cost',
        'hanging_table_cost',
        'total_chamfer_cost',
        'total_bevel_cost',
        'oil_tank_cost',
        'high_cost',
        'plate_cost',
        'long_strip_cost',
        'component_cost',
    ]
    
    success = True
    passed = 0
    
    for field in test_result_fields:
        test_step = {field: 100.0, "formula": "test"}
        result_key = handler._find_result_key(test_step)
        
        if result_key == field:
            print(f"✅ {field} 是结果字段")
            passed += 1
        else:
            print(f"❌ {field} 不是结果字段")
            success = False
    
    print(f"\n结果字段准确率: {passed}/{len(test_result_fields)}")
    
    return success


def test_water_mill_important_groups():
    """测试 important_groups 是否包含水磨分组"""
    print("\n" + "=" * 60)
    print("测试 5: important_groups 水磨分组")
    print("=" * 60)
    
    from agents.action_handlers.query_details_handler import QueryDetailsHandler
    
    handler = QueryDetailsHandler()
    
    # 测试数据（包含水磨字段）
    test_steps = [
        {
            "category": "water_mill_thread_ends",
            "steps": [{
                "step": "测试",
                "thread_ends_count": 4,
                "thread_ends_cost": 20.0,
                "plate_cost": 15.0,
                "grinding": 6
            }]
        }
    ]
    
    glossary = handler._build_field_glossary(test_steps)
    
    # 检查是否包含"水磨相关"分组
    if "水磨相关" in glossary:
        print("✅ important_groups 包含'水磨相关'分组")
        
        # 检查分组中是否包含关键字段
        expected_fields = [
            "thread_ends_count", "thread_ends_cost",
            "plate_cost", "grinding"
        ]
        
        found = 0
        for field in expected_fields:
            if field in glossary:
                found += 1
        
        if found >= len(expected_fields) * 0.8:
            print(f"✅ 水磨分组包含关键字段 ({found}/{len(expected_fields)})")
            return True
        else:
            print(f"❌ 水磨分组缺少关键字段 ({found}/{len(expected_fields)})")
            return False
    else:
        print("❌ important_groups 未包含'水磨相关'分组")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("开始测试水磨字段更新实施结果")
    print("=" * 60)
    
    results = []
    
    # 测试 1: 小水磨字段
    try:
        results.append(("小水磨字段", test_small_water_mill_fields()))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("小水磨字段", False))
    
    # 测试 2: 大水磨字段
    try:
        results.append(("大水磨字段", test_large_water_mill_fields()))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("大水磨字段", False))
    
    # 测试 3: 字段翻译
    try:
        results.append(("字段翻译", test_water_mill_translations()))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("字段翻译", False))
    
    # 测试 4: 结果字段
    try:
        results.append(("结果字段", test_water_mill_result_fields()))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("结果字段", False))
    
    # 测试 5: important_groups
    try:
        results.append(("important_groups", test_water_mill_important_groups()))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("important_groups", False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
        print("=" * 60)
        print("\n实施总结：")
        print("- 新增 27 个水磨字段说明（小水磨15个 + 大水磨10个 + 通用2个）")
        print("- 扩展 27 个水磨字段翻译")
        print("- 扩展 9 个水磨结果字段")
        print("- 新增'水磨相关' important_groups 分组")
        print("\n详细文档：")
        print("- WATER_MILL_UPDATE_PLAN.md")
        print("- CALCULATION_STEPS_V3_DIFF_ANALYSIS.md")
    else:
        print("❌ 部分测试失败，请检查实施")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
