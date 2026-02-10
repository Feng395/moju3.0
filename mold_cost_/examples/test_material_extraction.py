"""
测试材质提取功能（大小写不敏感）

运行方式:
    cd moldCost
    python examples/test_material_extraction.py
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.process_code_mapping import extract_process_from_text


def test_material_extraction():
    """测试材质提取（大小写不敏感）"""
    print("\n" + "="*60)
    print("测试: 材质提取（大小写不敏感）")
    print("="*60)
    
    test_cases = [
        # 标准大写
        "材料CR12的价格改为5",
        "45#价格改成6块",
        "SKD11的单价修改为15",
        
        # 小写
        "材料cr12的价格改为5",
        "材料Cr12的价格改为5",
        
        # 混合大小写
        "sKd11的单价修改为15",
        "SkH-51价格改为20",
        
        # 其他材质
        "P20的价格改为8",
        "p20的价格改为8",
        "DC53价格改为12",
        "dc53价格改为12",
    ]
    
    for text in test_cases:
        result = extract_process_from_text(text)
        print(f"\n输入: {text}")
        if result:
            print(f"✅ 输出: {result}")
        else:
            print(f"❌ 未找到匹配")


if __name__ == "__main__":
    print("\n" + "🧪 材质提取测试".center(60, "="))
    
    try:
        test_material_extraction()
        
        print("\n" + "="*60)
        print("✅ 测试完成")
        print("="*60 + "\n")
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
