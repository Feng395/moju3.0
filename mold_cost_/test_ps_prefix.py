"""
测试 PS 前缀支持

验证 PS-01, PS-02 等零件ID可以正确识别
"""
import re


def test_ps_prefix():
    """测试所有前缀识别"""
    print("=" * 60)
    print("子图ID前缀识别测试")
    print("=" * 60)
    
    # 正则表达式（与实际代码一致）
    subgraph_prefixes = r'(?:' + '|'.join([
        # 带后缀的（最长，优先匹配）
        r'UP_JIAT', r'PS_JIAT', r'LOW_JIAT',
        r'UP_ITEM', r'PSITEM', r'LOW_ITEM',
        r'DIE2_P', r'PS2_P', r'PPS2_P', r'PH2_P', r'LB2_P',
        r'UP_P', r'UB_P', r'PH_P', r'PU_P', r'PPS_P', r'PS_P', r'DIE_P', r'GU_P', r'LB_P',
        
        # 带数字的前缀
        r'TEMP[12]', r'ST[123]',
        r'DIE2', r'PS2', r'PPS2', r'PH2', r'LB2',
        
        # 特殊前缀
        r'STRIP',
        
        # 三字母
        r'PPS', r'DIE', r'CAM', r'BOL',
        
        # 双字母
        r'UP', r'LP', r'PS', r'PH', r'UB', r'PU', r'LB', r'EB', r'EJ', 
        r'CV', r'CJ', r'CB', r'GU', r'RP', r'CP', r'TP', r'BP', r'SP', r'MP', r'PP',
        
        # 单字母+数字
        r'U[12]', r'B[12]',
    ]) + r')'
    # 注意：不使用 \b 因为在中文环境下不工作
    subgraph_pattern = rf'({subgraph_prefixes}[-_]?\d{{2}})'
    
    # 测试用例（按类别）
    test_cases = [
        # 单字母+数字
        ("U1-01 的价格", "U1-01", "✅ U1 识别"),
        ("U2-04 怎么算", "U2-04", "✅ U2 识别"),
        ("B1-02 的材料费", "B1-02", "✅ B1 识别"),
        ("B2-03 的重量", "B2-03", "✅ B2 识别"),
        
        # 双字母
        ("UP01 的价格", "UP01", "✅ UP 识别"),
        ("LP-02 怎么算", "LP-02", "✅ LP 识别"),
        ("PS-02的计算过程", "PS-02", "✅ PS 识别"),
        ("PH-01 的材料费", "PH-01", "✅ PH 识别"),
        ("UB_05 的重量", "UB_05", "✅ UB 识别"),
        
        # 三字母
        ("PPS01 的价格", "PPS01", "✅ PPS 识别"),
        ("DIE-02 怎么算", "DIE-02", "✅ DIE 识别"),
        ("CAM03 的材料费", "CAM03", "✅ CAM 识别"),
        
        # 带数字的
        ("PH2-04 的材料费", "PH2-04", "✅ PH2 识别"),
        ("DIE2-01 怎么算", "DIE2-01", "✅ DIE2 识别"),
        ("ST1-05 的价格", "ST1-05", "✅ ST1 识别"),
        ("TEMP1-02 的重量", "TEMP1-02", "✅ TEMP1 识别"),
        
        # 带后缀_P
        ("UP_P-01 的价格", "UP_P-01", "✅ UP_P 识别"),
        ("PS_P-02 怎么算", "PS_P-02", "✅ PS_P 识别"),
        ("DIE2_P-03 的材料费", "DIE2_P-03", "✅ DIE2_P 识别"),
        
        # 带后缀_JIAT
        ("UP_JIAT-01 的价格", "UP_JIAT-01", "✅ UP_JIAT 识别"),
        ("PS_JIAT-02 怎么算", "PS_JIAT-02", "✅ PS_JIAT 识别"),
        ("LOW_JIAT-03 的材料费", "LOW_JIAT-03", "✅ LOW_JIAT 识别"),
        
        # 带后缀_ITEM
        ("UP_ITEM-01 的价格", "UP_ITEM-01", "✅ UP_ITEM 识别"),
        ("PSITEM-02 怎么算", "PSITEM-02", "✅ PSITEM 识别"),
        ("LOW_ITEM-03 的材料费", "LOW_ITEM-03", "✅ LOW_ITEM 识别"),
        
        # 特殊
        ("STRIP-01 的价格", "STRIP-01", "✅ STRIP 识别"),
        
        # 不应该匹配的
        ("P20 的价格", None, "❌ P20 不匹配（材料名称）"),
        ("718 材质", None, "❌ 718 不匹配（材料名称）"),
        ("CR12 的价格", None, "❌ CR12 不匹配（材料名称）"),
    ]
    
    print("\n测试结果:")
    passed = 0
    failed = 0
    
    for text, expected, description in test_cases:
        matches = re.findall(subgraph_pattern, text, re.IGNORECASE)
        # 保持原始格式，只转大写，不替换下划线
        result = matches[0].upper() if matches else None
        
        if result == expected:
            status = "✅ 通过"
            passed += 1
        else:
            status = "❌ 失败"
            failed += 1
        
        print(f"\n{status} - {description}")
        print(f"  输入: '{text}'")
        print(f"  期望: {expected}")
        print(f"  实际: {result}")
    
    print("\n" + "=" * 60)
    print(f"测试总结: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


def test_real_scenario():
    """测试真实场景"""
    print("\n" + "=" * 60)
    print("真实场景模拟")
    print("=" * 60)
    
    # 模拟对话
    conversation = [
        "PS-02的计算过程是什么？",
        "PS-02 的总成本是 1708.20 元，整个计算过程...",
        "L是什么？",  # 应该能从历史中推断出 PS-02
    ]
    
    print("\n对话历史:")
    for i, msg in enumerate(conversation, 1):
        print(f"  {i}. {msg[:50]}...")
    
    # 测试推断（使用完整的正则表达式）
    subgraph_prefixes = r'(?:' + '|'.join([
        # 带后缀的（最长，优先匹配）
        r'UP_JIAT', r'PS_JIAT', r'LOW_JIAT',
        r'UP_ITEM', r'PSITEM', r'LOW_ITEM',
        r'DIE2_P', r'PS2_P', r'PPS2_P', r'PH2_P', r'LB2_P',
        r'UP_P', r'UB_P', r'PH_P', r'PU_P', r'PPS_P', r'PS_P', r'DIE_P', r'GU_P', r'LB_P',
        
        # 带数字的前缀
        r'TEMP[12]', r'ST[123]',
        r'DIE2', r'PS2', r'PPS2', r'PH2', r'LB2',
        
        # 特殊前缀
        r'STRIP',
        
        # 三字母
        r'PPS', r'DIE', r'CAM', r'BOL',
        
        # 双字母
        r'UP', r'LP', r'PS', r'PH', r'UB', r'PU', r'LB', r'EB', r'EJ', 
        r'CV', r'CJ', r'CB', r'GU', r'RP', r'CP', r'TP', r'BP', r'SP', r'MP', r'PP',
        
        # 单字母+数字
        r'U[12]', r'B[12]',
    ]) + r')'
    # 注意：不使用 \b 因为在中文环境下不工作
    subgraph_pattern = rf'({subgraph_prefixes}[-_]?\d{{2}})'
    
    print("\n推断测试:")
    for msg in reversed(conversation):
        matches = re.findall(subgraph_pattern, msg, re.IGNORECASE)
        if matches:
            # 保持原始格式，只转大写
            subgraph_id = matches[0].upper()
            print(f"  ✅ 从消息中找到: {subgraph_id}")
            print(f"     来源: '{msg[:50]}...'")
            break
    else:
        print("  ❌ 未找到子图ID")
    
    print("\n期望结果: PS-02")
    print("说明: 用户问'L是什么？'时，应该能从历史中推断出是在问 PS-02 的 L工序")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("PS 前缀支持测试")
    print("=" * 60)
    
    # 测试 1：基础识别
    success = test_ps_prefix()
    
    # 测试 2：真实场景
    test_real_scenario()
    
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    
    if success:
        print("\n✅ 所有测试通过！")
        print("\n现在支持的前缀类别:")
        print("  - 单字母+数字: U1, U2, B1, B2")
        print("  - 双字母: UP, LP, PS, PH, UB, PU, LB, EB, EJ, CV, CJ, CB, GU, ...")
        print("  - 三字母: PPS, DIE, CAM, BOL")
        print("  - 带数字: DIE2, PS2, PPS2, PH2, LB2, ST1, ST2, ST3, TEMP1, TEMP2")
        print("  - 带后缀_P: UP_P, PS_P, DIE_P, DIE2_P, ...")
        print("  - 带后缀_JIAT: UP_JIAT, PS_JIAT, LOW_JIAT")
        print("  - 带后缀_ITEM: UP_ITEM, PSITEM, LOW_ITEM")
        print("  - 特殊: STRIP")
        print("\n总计: 55+ 种前缀格式")
        
        print("\n下一步:")
        print("  1. 通过 API 测试真实场景")
        print("  2. 验证历史推断功能")
        print("  3. 查看日志确认识别结果")
    else:
        print("\n❌ 部分测试失败，请检查正则表达式")
    
    print("\n相关文档:")
    print("  - SUBGRAPH_ID_PATTERNS.md - 子图ID模式说明（已更新）")
    print("  - HISTORY_INFERENCE_FIX.md - 历史推断修复说明（已更新）")


if __name__ == "__main__":
    main()
