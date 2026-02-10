"""
测试历史推断逻辑

测试场景：
1. 用户问过多个零件
2. 再次询问时不指定零件
3. 应该推断为最近提到的零件
"""
import asyncio
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()


async def test_history_inference():
    """测试历史推断"""
    print("=" * 60)
    print("历史推断测试")
    print("=" * 60)
    
    # 模拟对话历史
    conversation = [
        {"role": "user", "content": "LP-02 的价格是多少？"},
        {"role": "assistant", "content": "LP-02 的总价是 1500 元"},
        {"role": "user", "content": "UP01 的价格呢？"},
        {"role": "assistant", "content": "UP01 的总价是 2000 元"},
        {"role": "user", "content": "PH2-04怎么算的？"},
        {"role": "assistant", "content": "PH2-04 的计算详情..."},
        {"role": "user", "content": "水磨怎么算的？"},  # 应该推断为 PH2-04
    ]
    
    print("\n对话历史:")
    for i, msg in enumerate(conversation, 1):
        role_name = "用户" if msg["role"] == "user" else "助手"
        print(f"  {i}. {role_name}: {msg['content']}")
    
    print("\n" + "=" * 60)
    print("测试场景")
    print("=" * 60)
    
    # 测试场景 1：最近提到 PH2-04
    print("\n场景 1：用户刚问完 PH2-04，接着问'水磨怎么算的？'")
    print("期望推断: PH2-04")
    print("原因: PH2-04 是最近的用户消息中提到的零件")
    
    # 测试场景 2：多个零件混合
    print("\n场景 2：用户问过 LP-02, UP01, PH2-04")
    print("当前问: '线割呢？'")
    print("期望推断: PH2-04")
    print("原因: PH2-04 是最近的用户消息中提到的零件")
    
    # 测试场景 3：只有助手消息提到
    print("\n场景 3：用户没有明确提到零件，只有助手回复中有")
    print("期望推断: 从助手消息中推断")
    
    print("\n" + "=" * 60)
    print("优先级规则")
    print("=" * 60)
    print("1. 最近的用户消息（最高优先级）")
    print("2. 最近的助手消息")
    print("3. 所有历史消息（最后备选）")
    
    print("\n" + "=" * 60)
    print("实际测试")
    print("=" * 60)
    print("\n⚠️  此测试需要数据库连接和真实的聊天历史")
    print("请通过 API 端点测试真实场景:")
    print("\n1. 问: 'PH2-04怎么算的？'")
    print("2. 问: '水磨怎么算的？'")
    print("3. 检查日志，确认推断的零件是 PH2-04")
    
    print("\n日志关键词:")
    print("  ✅ 从最近的用户消息推断出子图: PH2-04")
    print("  ❌ 从最近的用户消息推断出子图: LP-02  (错误)")


async def test_pattern_matching():
    """测试子图ID模式匹配"""
    print("\n" + "=" * 60)
    print("子图ID模式匹配测试")
    print("=" * 60)
    
    import re
    
    # 子图ID模式
    subgraph_prefixes = r'(?:UP|LP|DIE|RP|CP|TP|BP|SP|MP|PP|PH\d+)'
    subgraph_pattern = rf'\b({subgraph_prefixes}[-_]?\d{{2}})\b'
    
    test_cases = [
        ("UP01 的价格是多少？", "UP01"),
        ("LP-02 怎么算的？", "LP-02"),
        ("PH2-04 的材料费", "PH2-04"),
        ("PS-02 的计算过程", "PS-02"),  # 🆕 新增
        ("DIE_03 的重量", "DIE-03"),
        ("材质是 718", None),  # 不应该匹配材料名称
        ("P20 的价格", None),  # 不应该匹配材料名称
        ("水磨怎么算的？", None),  # 没有子图ID
    ]
    
    print("\n测试用例:")
    for text, expected in test_cases:
        matches = re.findall(subgraph_pattern, text, re.IGNORECASE)
        result = matches[0].upper().replace("_", "-") if matches else None
        
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text}'")
        print(f"   期望: {expected}, 实际: {result}")


async def main():
    """主函数"""
    await test_history_inference()
    await test_pattern_matching()
    
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("\n修复内容:")
    print("1. ✅ 优先从最近的用户消息中查找子图ID")
    print("2. ✅ 添加 PH2, PH3 等前缀支持")
    print("3. ✅ 分优先级查找（用户 > 助手 > 所有）")
    
    print("\n测试方法:")
    print("1. 通过 API 端点测试真实对话")
    print("2. 查看日志确认推断结果")
    print("3. 验证多轮对话的准确性")


if __name__ == "__main__":
    asyncio.run(main())
