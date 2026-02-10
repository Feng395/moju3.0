"""
测试模块导入
验证 scripts/search 和 scripts/calculate 中的所有模块都能正确导入
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_search_modules():
    """测试搜索模块导入"""
    print("测试搜索模块导入...")
    
    try:
        from scripts.search import (
            base_itemcode_search,
            material_search,
            heat_search,
            tooth_hole_search,
            water_mill_search,
            wire_base_search,
            wire_special_search,
            wire_standard_search,
            wire_total_search,
            nc_search,
            total_search,
            search
        )
        print("✓ 所有搜索模块导入成功")
        
        # 验证每个模块都有 MCP_TOOL_META
        modules = [
            ("base_itemcode_search", base_itemcode_search),
            ("material_search", material_search),
            ("heat_search", heat_search),
            ("tooth_hole_search", tooth_hole_search),
            ("water_mill_search", water_mill_search),
            ("wire_base_search", wire_base_search),
            ("wire_special_search", wire_special_search),
            ("wire_standard_search", wire_standard_search),
            ("wire_total_search", wire_total_search),
            ("nc_search", nc_search),
            ("total_search", total_search),
            ("search", search),
        ]
        
        for name, module in modules:
            if hasattr(module, 'MCP_TOOL_META'):
                print(f"  ✓ {name}.MCP_TOOL_META 存在")
            else:
                print(f"  ✗ {name}.MCP_TOOL_META 不存在")
                
        return True
    except Exception as e:
        print(f"✗ 搜索模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_calculate_modules():
    """测试计算模块导入"""
    print("\n测试计算模块导入...")
    
    try:
        from scripts.calculate import (
            price_material,
            price_heat,
            price_weight,
            price_tooth_hole,
            price_wire_base,
            price_wire_special,
            price_wire_standard,
            price_add_auto_material,
            price_water_mill_bevel_cost,
            price_water_mill_chamfer_cost,
            price_water_mill_component,
            price_water_mill_hanging_table,
            price_water_mill_high_cost,
            price_water_mill_long_strip,
            price_water_mill_oil_tank,
            price_water_mill_plate,
            price_water_mill_thread_ends,
            price_water_mill_total,
            price_wire_total,
            price_nc_base,
            price_nc_time,
            price_nc_total,
            price_total
        )
        print("✓ 所有计算模块导入成功")
        
        # 验证每个模块都有 MCP_TOOL_META
        modules = [
            ("price_material", price_material),
            ("price_heat", price_heat),
            ("price_weight", price_weight),
            ("price_tooth_hole", price_tooth_hole),
            ("price_wire_base", price_wire_base),
            ("price_wire_special", price_wire_special),
            ("price_wire_standard", price_wire_standard),
            ("price_add_auto_material", price_add_auto_material),
            ("price_water_mill_bevel_cost", price_water_mill_bevel_cost),
            ("price_water_mill_chamfer_cost", price_water_mill_chamfer_cost),
            ("price_water_mill_component", price_water_mill_component),
            ("price_water_mill_hanging_table", price_water_mill_hanging_table),
            ("price_water_mill_high_cost", price_water_mill_high_cost),
            ("price_water_mill_long_strip", price_water_mill_long_strip),
            ("price_water_mill_oil_tank", price_water_mill_oil_tank),
            ("price_water_mill_plate", price_water_mill_plate),
            ("price_water_mill_thread_ends", price_water_mill_thread_ends),
            ("price_water_mill_total", price_water_mill_total),
            ("price_wire_total", price_wire_total),
            ("price_nc_base", price_nc_base),
            ("price_nc_time", price_nc_time),
            ("price_nc_total", price_nc_total),
            ("price_total", price_total),
        ]
        
        for name, module in modules:
            if hasattr(module, 'MCP_TOOL_META'):
                print(f"  ✓ {name}.MCP_TOOL_META 存在")
            else:
                print(f"  ✗ {name}.MCP_TOOL_META 不存在")
                
        return True
    except Exception as e:
        print(f"✗ 计算模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("模块导入测试")
    print("=" * 60)
    
    search_ok = test_search_modules()
    calculate_ok = test_calculate_modules()
    
    print("\n" + "=" * 60)
    if search_ok and calculate_ok:
        print("✓ 所有模块导入测试通过")
        sys.exit(0)
    else:
        print("✗ 部分模块导入测试失败")
        sys.exit(1)
