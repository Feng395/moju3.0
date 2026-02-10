"""
测试子图推断功能

验证正则表达式是否能正确匹配 PH2-04 等格式
"""
import re


def test_regex_patterns():
    """测试不同的正则表达式模式"""
    print("=" * 60)
    print("测试子图ID正则表达式")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        ("PH2-04 宽度改为200", "PH2-04"),
        ("PH2-04长度改为200", "PH2-04"),
        ("材质改为Cr12mov", None),
        ("材质改为45#", None),
        ("UP01 的价格", "UP01"),
        ("LP-02 详情", "LP-02"),
        ("DIE-03 怎么算的", "DIE-03"),
        ("那线割费呢？", None),
        ("CR12 材料", None),  # 材料名，不应匹配
        ("P20 钢材", None),   # 材料名，不应匹配
        ("718 材质", None),   # 材料名，不应匹配
        ("NAK80", None),      # 材料名，不应匹配
    ]
    
    # 当前使用的模式（data_modification_handler.py）
    subgraph_prefixes = r'(?:UP|LP|DIE|RP|CP|TP|BP|SP|MP|PP|PH\d?|PS|DP|EP|FP|GP|HP|IP|JP|KP|NP|OP|QP|TP|VP|WP|XP|YP|ZP)'
    pattern = rf'\b({subgraph_prefixes}[-_]?\d{{2}})\b'
    
    print(f"\n📋 使用模式: {pattern}\n")
    
    passed = 0
    failed = 0
    
    for text, expected in test_cases:
        matches = re.findall(pattern, text, re.IGNORECASE)
        actual = matches[0].upper().replace("_", "-") if matches else None
        
        if actual == expected:
            print(f"✅ '{text}' -> {actual}")
            passed += 1
        else:
            print(f"❌ '{text}' -> 期望: {expected}, 实际: {actual}")
            failed += 1
    
    print(f"\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


def test_history_inference_logic():
    """测试历史推断逻辑"""
    print("\n" + "=" * 60)
    print("测试历史推断逻辑")
    print("=" * 60)
    
    # 模拟历史消息
    history = [
        {"role": "user", "content": "PH2-04 宽度改为200"},
        {"role": "assistant", "content": "已将 PH2-04 的宽度修改为 200，请确认"},
        {"role": "user", "content": "材质改为Cr12mov"},
    ]
    
    print("\n📚 历史消息:")
    for i, msg in enumerate(history):
        print(f"  [{i}] {msg['role']}: {msg['content']}")
    
    # 推断子图ID
    subgraph_prefixes = r'(?:UP|LP|DIE|RP|CP|TP|BP|SP|MP|PP|PH\d?|PS|DP|EP|FP|GP|HP|IP|JP|KP|NP|OP|QP|TP|VP|WP|XP|YP|ZP)'
    pattern = rf'\b({subgraph_prefixes}[-_]?\d{{2}})\b'
    
    inferred_subgraph = None
    for msg in reversed(history[:-1]):  # 不包括最后一条（当前消息）
        content = msg.get("content", "")
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        if matches:
            inferred_subgraph = matches[0].upper().replace("_", "-")
            print(f"\n✅ 从历史推断出子图: {inferred_subgraph}")
            print(f"   来源消息: {content}")
            break
    
    if not inferred_subgraph:
        print(f"\n❌ 未能从历史推断出子图")
        return False
    
    # 验证当前消息是否包含子图ID
    current_message = history[-1]["content"]
    current_matches = re.findall(pattern, current_message, re.IGNORECASE)
    
    if current_matches:
        print(f"\n⚠️  当前消息包含子图ID: {current_matches[0]}")
        print(f"   不需要推断")
    else:
        print(f"\n✅ 当前消息不包含子图ID，使用推断的: {inferred_subgraph}")
    
    return True


def test_material_name_exclusion():
    """测试材料名称排除"""
    print("\n" + "=" * 60)
    print("测试材料名称排除")
    print("=" * 60)
    
    # 材料名称（不应该被匹配为子图ID）
    material_names = [
        "CR12",
        "Cr12mov",
        "P20",
        "718",
        "NAK80",
        "45#",
        "S136",
        "H13",
    ]
    
    subgraph_prefixes = r'(?:UP|LP|DIE|RP|CP|TP|BP|SP|MP|PP|PH\d?|PS|DP|EP|FP|GP|HP|IP|JP|KP|NP|OP|QP|TP|VP|WP|XP|YP|ZP)'
    pattern = rf'\b({subgraph_prefixes}[-_]?\d{{2}})\b'
    
    print(f"\n📋 测试材料名称:")
    all_passed = True
    
    for material in material_names:
        matches = re.findall(pattern, material, re.IGNORECASE)
        if matches:
            print(f"❌ '{material}' 被错误匹配为: {matches}")
            all_passed = False
        else:
            print(f"✅ '{material}' 未被匹配（正确）")
    
    return all_passed


if __name__ == "__main__":
    print("\n🧪 开始测试子图推断功能\n")
    
    test1 = test_regex_patterns()
    test2 = test_history_inference_logic()
    test3 = test_material_name_exclusion()
    
    print("\n" + "=" * 60)
    print("总体测试结果")
    print("=" * 60)
    print(f"正则表达式测试: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"历史推断逻辑测试: {'✅ 通过' if test2 else '❌ 失败'}")
    print(f"材料名称排除测试: {'✅ 通过' if test3 else '❌ 失败'}")
    
    if test1 and test2 and test3:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败，请检查")
