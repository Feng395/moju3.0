"""
批量修改功能测试脚本
测试工艺代码映射和批量修改功能

运行方式:
    cd moldCost
    python examples/test_batch_modification.py
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.process_code_mapping import (
    resolve_process_code,
    resolve_category,
    extract_process_from_text
)


def test_resolve_process_code():
    """测试工艺代码解析"""
    print("\n" + "="*60)
    print("测试1: 工艺代码解析 (resolve_process_code)")
    print("="*60)
    
    test_cases = [
        "慢丝割一修三",
        "慢丝割一修二",
        "慢丝割一修一",
        "慢丝割一刀",
        "中丝割一修一",
        "快丝割一刀",
        "线割割一修一",
        "割一修三",
        "割一刀",
        "45#",
        "CR12",
        "SKD11",
        "P20",
        "未知工艺"
    ]
    
    for text in test_cases:
        result = resolve_process_code(text)
        print(f"\n输入: {text}")
        print(f"输出: {result}")


def test_resolve_category():
    """测试类别映射"""
    print("\n" + "="*60)
    print("测试2: 类别映射 (resolve_category)")
    print("="*60)
    
    test_cases = [
        "线割",
        "热处理",
        "材料",
        "标准",
        "未知类别"
    ]
    
    for text in test_cases:
        result = resolve_category(text)
        print(f"\n输入: {text}")
        print(f"输出: {result}")


def test_extract_process_from_text():
    """测试从文本提取工艺"""
    print("\n" + "="*60)
    print("测试3: 从文本提取工艺 (extract_process_from_text)")
    print("="*60)
    
    test_cases = [
        "将这套的线割割一修一的单价改成0.0018",
        "慢丝割一修一的价格改为0.002",
        "快丝割一刀的单价是多少",
        "中丝割一修一改为0.0025",
        "45#价格改成6块",
        "CR12的价格改为11.8",
        "将SKD11的单价修改为15",
        "这个零件没有工艺信息"
    ]
    
    for text in test_cases:
        result = extract_process_from_text(text)
        print(f"\n输入: {text}")
        print(f"输出: {result}")


def test_batch_modification_scenario():
    """测试批量修改场景"""
    print("\n" + "="*60)
    print("测试4: 批量修改场景模拟")
    print("="*60)
    
    # 场景1: 线割工艺价格修改
    print("\n【场景1: 线割工艺价格修改】")
    user_input = "将这套的线割割一修一的单价改成0.0018"
    
    print(f"用户输入: {user_input}")
    
    process_code = extract_process_from_text(user_input)
    
    if process_code:
        print(f"\n✅ 工艺代码解析成功:")
        print(f"   category: {process_code.get('category')}")
        print(f"   sub_category: {process_code.get('sub_category')}")
        print(f"   note: {process_code.get('note')}")
        
        change = {
            "table": "job_price_snapshots",
            "filter": {
                "category": process_code.get("category"),
                "sub_category": process_code.get("sub_category")
            },
            "field": "price",
            "value": "0.0018",
            "original_text": user_input
        }
        
        print(f"\n✅ 生成的修改指令:")
        import json
        print(json.dumps(change, indent=2, ensure_ascii=False))
    else:
        print("\n❌ 无法解析工艺代码")
    
    # 场景2: 材质价格修改
    print("\n\n【场景2: 材质价格修改】")
    user_input2 = "45#价格改成6块"
    
    print(f"用户输入: {user_input2}")
    
    material_code = extract_process_from_text(user_input2)
    
    if material_code:
        print(f"\n✅ 材质代码解析成功:")
        print(f"   category: {material_code.get('category')}")
        print(f"   sub_category: {material_code.get('sub_category')}")
        print(f"   note: {material_code.get('note')}")
        
        change2 = {
            "table": "job_price_snapshots",
            "filter": {
                "category": material_code.get("category"),
                "sub_category": material_code.get("sub_category")
            },
            "field": "price",
            "value": "6",
            "original_text": user_input2
        }
        
        print(f"\n✅ 生成的修改指令:")
        import json
        print(json.dumps(change2, indent=2, ensure_ascii=False))
    else:
        print("\n❌ 无法解析材质代码")


if __name__ == "__main__":
    print("\n" + "🧪 批量修改功能测试".center(60, "="))
    
    try:
        test_resolve_process_code()
        test_resolve_category()
        test_extract_process_from_text()
        test_batch_modification_scenario()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成")
        print("="*60 + "\n")
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
