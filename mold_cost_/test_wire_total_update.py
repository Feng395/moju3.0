"""
测试 wire_total 更新实施结果

测试内容：
1. wire_total Category 是否在 category_map 中
2. wire_total 相关字段是否在 field_glossary 中
3. 字段翻译是否正确
4. IntentRecognizer 是否支持 wire_total query_type
"""
import sys
import inspect


def test_wire_total_category():
    """测试 wire_total Category 是否正确添加"""
    print("=" * 60)
    print("测试 1: wire_total Category 支持")
    print("=" * 60)
    
    from agents.action_handlers.query_details_handler import QueryDetailsHandler
    
    handler = QueryDetailsHandler()
    
    # 测试数据（使用 result_keys 中的字段）
    test_steps = [
        {
            "category": "wire_total",
            "steps": [{
                "step": "计算线割总价",
                "formula": "180.0 * 2",
                "wire_cost_base": 360.0,  # 这是 result_key
                "wire_cost_per_unit": 180.0,
                "wire_length": 1500.0
            }]
        }
    ]
    
    # 测试 _format_calculation_steps
    result1 = handler._format_calculation_steps("TEST01", test_steps)
    
    # 测试 _format_specific_category
    result2 = handler._format_specific_category("TEST01", test_steps, "wire_total")
    
    # 验证
    success = True
    
    if "线割总价计算" not in result1:
        print("❌ _format_calculation_steps 中未找到 wire_total")
        print(f"结果: {result1[:200]}")
        success = False
    else:
        print("✅ _format_calculation_steps 支持 wire_total")
    
    if "线割总价计算" not in result2:
        print("❌ _format_specific_category 中未找到 wire_total")
        print(f"结果: {result2[:200]}")
        success = False
    else:
        print("✅ _format_specific_category 支持 wire_total")
    
    if "360.0" in result1 or "360.0" in result2:
        print("✅ wire_total 字段值正确显示")
    else:
        print("❌ wire_total 字段值未显示")
        success = False
    
    return success


def test_wire_total_fields():
    """测试 wire_total 相关字段是否在 field_glossary 中"""
    print("\n" + "=" * 60)
    print("测试 2: wire_total 字段说明")
    print("=" * 60)
    
    from agents.action_handlers.query_details_handler import QueryDetailsHandler
    
    handler = QueryDetailsHandler()
    
    # 测试数据（包含 wire_total 相关字段）
    test_steps = [
        {
            "category": "wire_total",
            "steps": [{
                "step": "测试",
                "wire_cost_base": 80.0,
                "wire_cost_per_unit": 180.0,
                "wire_length": 1500.0,
                "slow_wire_length": 800.0,
                "mid_wire_length": 500.0,
                "fast_wire_length": 200.0,
                "material_unit_price": 25.0,
                "heat_treatment_unit_price": 15.0,
                "weight_kg": 12.5,
                "material_cost_total": 312.5,
                "heat_treatment_cost_total": 187.5,
                "matched_material": "45#",
                "density": 0.00000785
            }]
        }
    ]
    
    glossary = handler._build_field_glossary(test_steps)
    
    # 验证关键字段
    required_fields = [
        ("wire_cost_base", "线割基础费用"),
        ("wire_cost_per_unit", "线割单价"),
        ("wire_length", "线割总长度"),
        ("material_cost_total", "材料费总价"),
        ("heat_treatment_cost_total", "热处理费总价"),
        ("matched_material", "匹配到的材料名称"),
        ("density", "密度值")
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
    
    print(f"\n字段覆盖率: {found_count}/{len(required_fields)}")
    
    if found_count >= len(required_fields) * 0.8:  # 至少80%覆盖
        print("✅ 字段说明测试通过")
    else:
        print("❌ 字段说明测试失败")
        success = False
    
    return success


def test_field_translations():
    """测试字段翻译是否正确"""
    print("\n" + "=" * 60)
    print("测试 3: 字段翻译")
    print("=" * 60)
    
    from agents.action_handlers.query_details_handler import QueryDetailsHandler
    
    handler = QueryDetailsHandler()
    
    # 测试翻译
    test_translations = {
        'wire_cost_base': '线割基础费用(元)',
        'wire_cost_per_unit': '线割单价(元)',
        'wire_length': '线割总长度(mm)',
        'material_cost_total': '材料费总价(元)',
        'heat_treatment_cost_total': '热处理费总价(元)',
        'matched_material': '匹配到的材料名称',
        'density': '密度值',
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


def test_intent_recognizer_wire_total():
    """测试 IntentRecognizer 是否支持 wire_total"""
    print("\n" + "=" * 60)
    print("测试 4: IntentRecognizer 支持 wire_total")
    print("=" * 60)
    
    from agents.intent_recognizer import IntentRecognizer
    
    recognizer = IntentRecognizer()
    
    # 检查 _build_llm_prompt 方法的源代码
    source = inspect.getsource(recognizer._build_llm_prompt)
    
    success = True
    
    # 检查是否包含 wire_total
    if "wire_total" in source:
        print("✅ IntentRecognizer Prompt 包含 wire_total")
    else:
        print("❌ IntentRecognizer Prompt 未包含 wire_total")
        success = False
    
    # 检查是否有示例说明
    if "线割总价" in source or "线割总费用" in source:
        print("✅ IntentRecognizer 包含 wire_total 示例")
    else:
        print("❌ IntentRecognizer 未包含 wire_total 示例")
        success = False
    
    return success


def main():
    """运行所有测试"""
    print("=" * 60)
    print("开始测试 wire_total 更新实施结果")
    print("=" * 60)
    
    results = []
    
    # 测试 1: Category 支持
    try:
        results.append(("Category 支持", test_wire_total_category()))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("Category 支持", False))
    
    # 测试 2: 字段说明
    try:
        results.append(("字段说明", test_wire_total_fields()))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("字段说明", False))
    
    # 测试 3: 字段翻译
    try:
        results.append(("字段翻译", test_field_translations()))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("字段翻译", False))
    
    # 测试 4: IntentRecognizer
    try:
        results.append(("IntentRecognizer", test_intent_recognizer_wire_total()))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("IntentRecognizer", False))
    
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
        print("- 新增 1 个 Category (wire_total)")
        print("- 新增 13 个字段说明（wire_total + 密度相关）")
        print("- 扩展 13 个字段翻译")
        print("- 扩展 4 个结果字段")
        print("- 更新 IntentRecognizer 支持 wire_total query_type")
        print("\n详细文档：")
        print("- UPDATE_PLAN.md")
        print("- CALCULATION_STEPS_DIFF_ANALYSIS.md")
    else:
        print("❌ 部分测试失败，请检查实施")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
