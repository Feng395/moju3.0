"""
测试 PU-BL2 子图ID推断修复

问题: 用户问 "L的线长是多少"，历史中最近提到 PU-BL2，但系统推断成 DIE-02
原因: 正则表达式只匹配 2 位数字，不匹配 PU-BL2 这种字母+数字组合
修复: 扩展正则表达式支持 [A-Z]+\d+ 格式
"""
import re


def test_subgraph_pattern():
    """测试子图ID匹配模式"""
    print("=" * 60)
    print("测试子图ID匹配模式")
    print("=" * 60)
    
    # 🆕 修复后的正则表达式
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
    
    # 🆕 修复后的完整模式：支持字母+数字组合
    subgraph_pattern = rf'({subgraph_prefixes}[-_]?(?:\d{{2}}|[A-Z]+\d+))'
    
    # 测试用例
    test_cases = [
        # 标准格式（2位数字）
        ("UP-01", "UP-01"),
        ("DIE-03", "DIE-03"),
        ("PS-02", "PS-02"),
        ("LP_05", "LP_05"),
        
        # 🆕 特殊格式（字母+数字组合）
        ("PU-BL2", "PU-BL2"),  # ✅ 应该匹配
        ("UP-A1", "UP-A1"),
        ("DIE-X3", "DIE-X3"),
        ("PS-ABC123", "PS-ABC123"),
        
        # 中文环境
        ("PU-BL2是怎么算的？", "PU-BL2"),
        ("DIE-02 怎么算的？", "DIE-02"),
        ("L的线长是多少", None),  # 没有子图ID
    ]
    
    print("\n测试匹配结果：")
    for text, expected in test_cases:
        matches = re.findall(subgraph_pattern, text, re.IGNORECASE)
        result = matches[0].upper() if matches else None
        status = "✅" if result == expected else "❌"
        expected_str = expected if expected else "None"
        result_str = result if result else "None"
        print(f"{status} 输入: {text:30} | 期望: {expected_str:15} | 实际: {result_str}")
    
    print("\n" + "=" * 60)


def test_inference_priority():
    """测试推断优先级"""
    print("\n" + "=" * 60)
    print("测试推断优先级")
    print("=" * 60)
    
    # 模拟历史消息（从旧到新，与数据库查询顺序一致）
    history = [
        {"role": "user", "content": "DIE-03中线割中L的线长是多少"}, # [0] 最早
        {"role": "user", "content": "DIE-02 怎么算的？"},       # [1]
        {"role": "assistant", "content": "DIE-02 的..."},      # [2]
        {"role": "user", "content": "PU-BL2是怎么算的？"},      # [3] ← 应该匹配这个！
        {"role": "assistant", "content": "PU-BL2 的..."},      # [4]
        {"role": "user", "content": "L的线长是多少"},           # [5] 当前问题（最新）
    ]
    
    # 正则表达式
    subgraph_prefixes = r'(?:' + '|'.join([
        r'UP_JIAT', r'PS_JIAT', r'LOW_JIAT',
        r'UP_ITEM', r'PSITEM', r'LOW_ITEM',
        r'DIE2_P', r'PS2_P', r'PPS2_P', r'PH2_P', r'LB2_P',
        r'UP_P', r'UB_P', r'PH_P', r'PU_P', r'PPS_P', r'PS_P', r'DIE_P', r'GU_P', r'LB_P',
        r'TEMP[12]', r'ST[123]',
        r'DIE2', r'PS2', r'PPS2', r'PH2', r'LB2',
        r'STRIP',
        r'PPS', r'DIE', r'CAM', r'BOL',
        r'UP', r'LP', r'PS', r'PH', r'UB', r'PU', r'LB', r'EB', r'EJ', 
        r'CV', r'CJ', r'CB', r'GU', r'RP', r'CP', r'TP', r'BP', r'SP', r'MP', r'PP',
        r'U[12]', r'B[12]',
    ]) + r')'
    
    subgraph_pattern = rf'({subgraph_prefixes}[-_]?(?:\d{{2}}|[A-Z]+\d+))'
    
    # 🔑 关键：reversed(history) 将历史从旧到新变成从新到旧
    # 过滤用户消息
    user_messages = [msg for msg in reversed(history) if msg.get("role") == "user"]
    
    print(f"\n原始历史消息（从旧到新）：")
    for i, msg in enumerate(history):
        role = msg['role']
        content = msg['content']
        print(f"  [{i}] {role:10} {content}")
    
    print(f"\n过滤后的用户消息（从新到旧，reversed）：")
    for i, msg in enumerate(user_messages):
        print(f"  [{i}] {msg['content']}")
    
    # 推断子图ID（只检查最近3条）
    print("\n推断过程（只检查最近3条）：")
    for i, msg in enumerate(user_messages[:3]):
        content = msg.get("content", "")
        matches = re.findall(subgraph_pattern, content, re.IGNORECASE)
        print(f"  [{i}] 尝试匹配: {content:40} | 匹配结果: {matches}")
        
        if matches:
            subgraph_id = matches[0].upper()
            print(f"  ✅ 推断出子图: {subgraph_id} (第{i}条用户消息)")
            print(f"\n✅ 期望结果: PU-BL2")
            print(f"✅ 实际结果: {subgraph_id}")
            print(f"{'✅ 测试通过' if subgraph_id == 'PU-BL2' else '❌ 测试失败'}")
            break
    else:
        print("  ❌ 未找到子图ID")
        print("\n❌ 测试失败：未找到子图ID")
    
    print("=" * 60)


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 60)
    print("测试边界情况")
    print("=" * 60)
    
    subgraph_prefixes = r'(?:' + '|'.join([
        r'UP_JIAT', r'PS_JIAT', r'LOW_JIAT',
        r'UP_ITEM', r'PSITEM', r'LOW_ITEM',
        r'DIE2_P', r'PS2_P', r'PPS2_P', r'PH2_P', r'LB2_P',
        r'UP_P', r'UB_P', r'PH_P', r'PU_P', r'PPS_P', r'PS_P', r'DIE_P', r'GU_P', r'LB_P',
        r'TEMP[12]', r'ST[123]',
        r'DIE2', r'PS2', r'PPS2', r'PH2', r'LB2',
        r'STRIP',
        r'PPS', r'DIE', r'CAM', r'BOL',
        r'UP', r'LP', r'PS', r'PH', r'UB', r'PU', r'LB', r'EB', r'EJ', 
        r'CV', r'CJ', r'CB', r'GU', r'RP', r'CP', r'TP', r'BP', r'SP', r'MP', r'PP',
        r'U[12]', r'B[12]',
    ]) + r')'
    
    subgraph_pattern = rf'({subgraph_prefixes}[-_]?(?:\d{{2}}|[A-Z]+\d+))'
    
    edge_cases = [
        # 单字母后缀
        ("PU-A", None),  # 只有字母，没有数字 → 不匹配
        ("PU-A1", "PU-A1"),  # 字母+数字 → 匹配
        ("PU-AB", None),  # 只有字母 → 不匹配
        ("PU-AB2", "PU-AB2"),  # 字母+数字 → 匹配
        
        # 多字母后缀
        ("PU-BL2", "PU-BL2"),  # ✅ 目标格式
        ("PU-BL23", "PU-BL23"),  # 字母+多位数字
        ("PU-ABC123", "PU-ABC123"),  # 多字母+多位数字
        
        # 分隔符
        ("PU_BL2", "PU_BL2"),  # 下划线
        ("PUBL2", "PUBL2"),  # 无分隔符（可能误匹配）
        
        # 大小写
        ("pu-bl2", "PU-BL2"),  # 小写 → 转大写
        ("Pu-Bl2", "PU-BL2"),  # 混合大小写
        
        # 中文环境
        ("PU-BL2是怎么算的？", "PU-BL2"),
        ("查询PU-BL2的价格", "PU-BL2"),
    ]
    
    print("\n边界情况测试：")
    for text, expected in edge_cases:
        matches = re.findall(subgraph_pattern, text, re.IGNORECASE)
        result = matches[0].upper() if matches else None
        status = "✅" if result == expected else "❌"
        expected_str = expected if expected else "None"
        result_str = result if result else "None"
        print(f"{status} 输入: {text:35} | 期望: {expected_str:15} | 实际: {result_str}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_subgraph_pattern()
    test_inference_priority()
    test_edge_cases()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)
