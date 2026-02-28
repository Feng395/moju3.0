#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模具行业语音识别测试脚本
测试术语修正功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from speech_services.core.dict_manager import DictionaryManager


def test_mold_speech_correction():
    """测试模具行业术语修正"""
    
    print("=" * 80)
    print("模具行业语音识别术语修正测试")
    print("=" * 80)
    print()
    
    # 初始化字典管理器
    dict_manager = DictionaryManager()
    
    print(f"✓ 加载字典成功")
    print(f"  总规则数: {dict_manager.stats['total_rules']}")
    print()
    
    # 测试用例（模拟语音识别后可能出现的错误）
    test_cases = [
        {
            "name": "修改工艺 - 线割工艺",
            "input": "将这套的线个慢思割一修2的单家改称0.0018",
            "expected": "将这套的线割慢丝割一修二的单价改成0.0018"
        },
        {
            "name": "修改材质 - 材料编号",
            "input": "将die-03的材质改围CR12MOV",
            "expected": "将DIE-03的材质改为Cr12MoV"
        },
        {
            "name": "批量修改 - 概念词",
            "input": "充头累的零件全部改称慢思割一修1",
            "expected": "冲头类的零件全部改成慢丝割一修一"
        },
        {
            "name": "查询计算 - NC加工",
            "input": "up01的nc开初怎么蒜的",
            "expected": "UP01的NC开粗怎么算的"
        },
        {
            "name": "修改价格 - 材料价格",
            "input": "这套的45号家格不对，改称6块",
            "expected": "这套的45#价格不对，改成6块"
        },
        {
            "name": "修改尺寸 - 零件尺寸",
            "input": "ph2-04这个零件的常度改称150MM",
            "expected": "PH2-04这个零件的长度改成150mm"
        },
        {
            "name": "组合修改 - 材质+工艺",
            "input": "up01改称七一八材质，用慢思割一修1",
            "expected": "UP01改成718材质，用慢丝割一修一"
        },
        {
            "name": "批量零件修改",
            "input": "up01、up02、up03的材质都改称p20",
            "expected": "UP01、UP02、UP03的材质都改成P20"
        },
        {
            "name": "类型筛选修改",
            "input": "下摸板类的零件改称中思割一修1",
            "expected": "下模板类的零件改成中丝割一修一"
        },
        {
            "name": "查询详情 - 水磨",
            "input": "up01的水磨高费用怎么蒜的",
            "expected": "UP01的水磨高费用怎么算的"
        },
        {
            "name": "按重量计算",
            "input": "up01按重量计蒜",
            "expected": "UP01按重量计算"
        },
        {
            "name": "零件类型 - 导柱导套",
            "input": "把导住导头工艺都改称慢思割一修2",
            "expected": "把导柱导套工艺都改成慢丝割一修二"
        }
    ]
    
    # 执行测试
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"测试 {i}: {test['name']}")
        print(f"  输入: {test['input']}")
        
        # 修正文本
        result = dict_manager.fix_text(test['input'], accumulate=False)
        
        print(f"  输出: {result}")
        print(f"  期望: {test['expected']}")
        
        # 显示修正详情
        corrections = dict_manager.get_corrections()
        if corrections:
            print(f"  修正: {len(corrections)} 处")
            for correction in corrections:
                print(f"    - '{correction['wrong']}' → '{correction['correct']}' ({correction['category']})")
        else:
            print(f"  修正: 无")
        
        # 检查结果
        if result == test['expected']:
            print(f"  结果: ✅ 通过")
            passed += 1
        else:
            print(f"  结果: ❌ 失败")
            failed += 1
        
        print()
    
    # 显示统计
    print("=" * 80)
    print("测试统计")
    print("=" * 80)
    print(f"总测试数: {len(test_cases)}")
    print(f"通过: {passed} ({passed/len(test_cases)*100:.1f}%)")
    print(f"失败: {failed} ({failed/len(test_cases)*100:.1f}%)")
    print()
    
    # 显示字典统计
    print("=" * 80)
    print("字典统计")
    print("=" * 80)
    stats = dict_manager.get_stats()
    print(f"总规则数: {stats['total_rules']}")
    print(f"总修正次数: {stats['replacements_made']}")
    print()
    
    categories = dict_manager.list_categories()
    print("分类统计:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} 条规则")
    print()
    
    return passed == len(test_cases)


def test_specific_terms():
    """测试特定术语的修正"""
    
    print("=" * 80)
    print("特定术语修正测试")
    print("=" * 80)
    print()
    
    dict_manager = DictionaryManager()
    
    # 测试线切割工艺术语
    print("1. 线切割工艺术语")
    wire_terms = [
        ("慢思割一修1", "慢丝割一修一"),
        ("快思割一道", "快丝割一刀"),
        ("中思割一修2", "中丝割一修二"),
        ("慢丝割一秀一", "慢丝割一修一"),
    ]
    
    for wrong, correct in wire_terms:
        result = dict_manager.fix_text(wrong, accumulate=False)
        status = "✅" if result == correct else "❌"
        print(f"  {status} '{wrong}' → '{result}' (期望: '{correct}')")
    print()
    
    # 测试材料术语
    print("2. 材料术语")
    material_terms = [
        ("CR12MOV", "Cr12MoV"),
        ("skd11", "SKD11"),
        ("p20", "P20"),
        ("45号", "45#"),
        ("TOOLOX44", "T00L0X44"),
    ]
    
    for wrong, correct in material_terms:
        result = dict_manager.fix_text(wrong, accumulate=False)
        status = "✅" if result == correct else "❌"
        print(f"  {status} '{wrong}' → '{result}' (期望: '{correct}')")
    print()
    
    # 测试零件编号
    print("3. 零件编号")
    part_codes = [
        ("up01", "UP01"),
        ("die-03", "DIE-03"),
        ("lp-02", "LP-02"),
        ("ph2-04", "PH2-04"),
    ]
    
    for wrong, correct in part_codes:
        result = dict_manager.fix_text(wrong, accumulate=False)
        status = "✅" if result == correct else "❌"
        print(f"  {status} '{wrong}' → '{result}' (期望: '{correct}')")
    print()
    
    # 测试修改动作
    print("4. 修改动作")
    action_terms = [
        ("改称", "改成"),
        ("改围", "改为"),
        ("休改", "修改"),
        ("条整", "调整"),
        ("设制", "设置"),
    ]
    
    for wrong, correct in action_terms:
        result = dict_manager.fix_text(wrong, accumulate=False)
        status = "✅" if result == correct else "❌"
        print(f"  {status} '{wrong}' → '{result}' (期望: '{correct}')")
    print()
    
    # 测试查询关键词
    print("5. 查询关键词")
    query_terms = [
        ("怎么蒜", "怎么算"),
        ("祥情", "详情"),
        ("名细", "明细"),
        ("计蒜过程", "计算过程"),
        ("nc", "NC"),
    ]
    
    for wrong, correct in query_terms:
        result = dict_manager.fix_text(wrong, accumulate=False)
        status = "✅" if result == correct else "❌"
        print(f"  {status} '{wrong}' → '{result}' (期望: '{correct}')")
    print()


if __name__ == "__main__":
    print()
    print("🎤 模具行业语音识别优化测试")
    print()
    
    # 运行完整测试
    success = test_mold_speech_correction()
    
    # 运行特定术语测试
    test_specific_terms()
    
    # 显示结果
    if success:
        print("✅ 所有测试通过！")
        sys.exit(0)
    else:
        print("❌ 部分测试失败，请检查字典配置")
        sys.exit(1)
