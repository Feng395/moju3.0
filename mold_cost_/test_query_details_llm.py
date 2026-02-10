"""
测试 QueryDetailsHandler 的 LLM 格式化功能

使用方法：
    python test_query_details_llm.py
"""
import asyncio
import json
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 🆕 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

from agents.action_handlers.query_details_handler import QueryDetailsHandler
from agents.intent_types import IntentResult


# 模拟的 calculation_steps 数据
SAMPLE_CALCULATION_STEPS = [
    {
        "category": "material",
        "steps": [
            {
                "step": "匹配材料",
                "material": "718",
                "matched_sub_category": "718",
                "unit_price": 15.5,
                "unit": "元/kg",
                "match_note": "精确匹配"
            },
            {
                "step": "获取尺寸数据",
                "length_mm": 200.0,
                "width_mm": 150.0,
                "thickness_mm": 50.0
            },
            {
                "step": "计算重量",
                "weight": 11.775,
                "formula": "0.00000785 * length * width * thickness"
            },
            {
                "step": "计算材料费",
                "material_cost": 182.5125,
                "formula": "weight * unit_price"
            }
        ]
    },
    {
        "category": "heat",
        "steps": [
            {
                "step": "判断是否需要热处理",
                "needs_heat_treatment": True,
                "heat_treatment_cost": 50.0,
                "note": "718材质需要热处理"
            }
        ]
    },
    {
        "category": "wire_base",
        "steps": [
            {
                "code": "L",
                "view": "top_view",
                "instruction": "俯视图线割",
                "cone": "t",
                "original_total_length": 150.0,
                "area_num": 1,
                "added_length": 0.0,
                "tooth_hole_length": 0.0,
                "total_length": 150.0,
                "dimension": 50.0,
                "dimension_name": "thickness_mm",
                "unit_price": 0.0133,
                "base_price": 99.75,
                "multipliers": [
                    {
                        "type": "extra_thick",
                        "multiplier": 1.0,
                        "description": "厚度未超过40mm，无超厚倍率"
                    }
                ],
                "calculation_formula": "150.0 * 50.0 * 0.0133",
                "complete_formula": "150.0 * 50.0 * 0.0133 * 1.0",
                "final_price": 99.75
            },
            {
                "step": "视图汇总（应用cone规则前）",
                "view_totals": {
                    "top_view": 99.75
                }
            },
            {
                "step": "应用视图级别cone规则",
                "cone_details": [
                    {
                        "view": "top_view",
                        "before_cone": 99.75,
                        "after_cone": 149.625,
                        "multiplier": 1.5
                    }
                ]
            },
            {
                "step": "视图汇总（应用cone规则后）",
                "view_totals_after_cone": {
                    "top_view": 149.625
                }
            },
            {
                "step": "最终总价",
                "basic_processing_cost": 149.625
            }
        ]
    }
]


async def test_llm_formatting():
    """测试 LLM 格式化功能"""
    print("=" * 60)
    print("测试 QueryDetailsHandler LLM 格式化功能")
    print("=" * 60)
    
    # 创建 Handler
    handler = QueryDetailsHandler()
    
    # 测试用例
    test_cases = [
        {
            "name": "查询材料费",
            "user_question": "UP01 的材料费怎么算的？",
            "query_type": "material"
        },
        {
            "name": "查询线割费用（带 cone）",
            "user_question": "UP01 的线割费用为什么这么贵？cone 是什么意思？",
            "query_type": "wire_base"
        },
        {
            "name": "查询整体价格",
            "user_question": "UP01 的价格怎么算的？",
            "query_type": None
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"测试用例 {i}: {test_case['name']}")
        print(f"{'=' * 60}")
        print(f"用户问题: {test_case['user_question']}")
        print(f"查询类型: {test_case['query_type']}")
        print()
        
        try:
            # 调用 LLM 格式化
            formatted_message = await handler._format_with_llm(
                subgraph_id="UP01",
                calculation_steps=SAMPLE_CALCULATION_STEPS,
                user_question=test_case['user_question'],
                query_type=test_case['query_type']
            )
            
            print("✅ LLM 格式化成功")
            print()
            print("格式化结果:")
            print("-" * 60)
            print(formatted_message)
            print("-" * 60)
            
        except Exception as e:
            print(f"❌ LLM 格式化失败: {e}")
            print()
            print("降级到规则格式化:")
            print("-" * 60)
            
            # Fallback: 规则格式化
            if test_case['query_type']:
                formatted_message = handler._format_specific_category(
                    "UP01",
                    SAMPLE_CALCULATION_STEPS,
                    test_case['query_type']
                )
            else:
                formatted_message = handler._format_calculation_steps(
                    "UP01",
                    SAMPLE_CALCULATION_STEPS
                )
            
            print(formatted_message)
            print("-" * 60)
    
    # 关闭 HTTP 客户端
    await handler.close()
    
    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


async def test_field_glossary():
    """测试字段说明构建功能"""
    print("\n" + "=" * 60)
    print("测试字段说明构建功能")
    print("=" * 60)
    
    handler = QueryDetailsHandler()
    
    # 构建字段说明
    glossary = handler._build_field_glossary(SAMPLE_CALCULATION_STEPS)
    
    print("\n生成的字段说明:")
    print("-" * 60)
    print(glossary)
    print("-" * 60)
    
    await handler.close()


async def main():
    """主函数"""
    # 检查环境变量
    use_llm = os.getenv("USE_LLM_FOR_QUERY_DETAILS", "true").lower() == "true"
    
    print(f"USE_LLM_FOR_QUERY_DETAILS: {use_llm}")
    print(f"OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL', 'Not set')}")
    print(f"OPENAI_MODEL: {os.getenv('OPENAI_MODEL', 'Not set')}")
    print()
    
    if not use_llm:
        print("⚠️  警告: USE_LLM_FOR_QUERY_DETAILS=false，将使用规则格式化")
        print()
    
    # 测试字段说明构建
    await test_field_glossary()
    
    # 测试 LLM 格式化
    if use_llm:
        await test_llm_formatting()
    else:
        print("\n跳过 LLM 格式化测试（USE_LLM_FOR_QUERY_DETAILS=false）")


if __name__ == "__main__":
    asyncio.run(main())
