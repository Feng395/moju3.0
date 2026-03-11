#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
板料线集成功能测试脚本
"""

import os
import sys
import asyncio
from pathlib import Path

# 使用统一的配置加载模块
from scripts.config_loader import load_config

# 加载配置
load_config()

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from cad_chaitu.material_line_integrator import MaterialLineIntegrator


def test_material_line_integrator():
    """测试板料线集成器"""
    print("=" * 80)
    print("板料线集成器测试")
    print("=" * 80)
    
    # 创建集成器实例
    integrator = MaterialLineIntegrator(enable=True)
    
    # 测试数据
    test_cases = [
        {
            'dxf_path': 'test_data/sample1.dxf',
            'lwt': {'L': 100.0, 'W': 80.0, 'T': 10.0},
            'sub_code': 'TEST-001'
        },
        {
            'dxf_path': 'test_data/sample2.dxf',
            'lwt': {'L': 200.0, 'W': 150.0, 'T': 20.0},
            'sub_code': 'TEST-002'
        }
    ]
    
    print("\n开始测试...")
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"  文件: {test_case['dxf_path']}")
        print(f"  尺寸: L={test_case['lwt']['L']}, W={test_case['lwt']['W']}, T={test_case['lwt']['T']}")
        print(f"  编号: {test_case['sub_code']}")
        
        if not os.path.exists(test_case['dxf_path']):
            print(f"  ⚠️ 文件不存在，跳过")
            continue
        
        try:
            success = integrator.add_material_lines_to_subgraph(
                dxf_path=test_case['dxf_path'],
                lwt=test_case['lwt'],
                sub_code=test_case['sub_code']
            )
            
            if success:
                print(f"  ✅ 测试通过")
            else:
                print(f"  ❌ 测试失败")
                
        except Exception as e:
            print(f"  ❌ 异常: {e}")
    
    # 打印统计
    print("\n" + "=" * 80)
    integrator.print_stats()
    print("=" * 80)


async def test_full_integration():
    """测试完整集成流程"""
    print("=" * 80)
    print("完整集成流程测试")
    print("=" * 80)
    
    # 检查环境变量
    enable_material_lines = os.getenv('ENABLE_MATERIAL_LINES', 'true').lower() == 'true'
    print(f"\n环境变量 ENABLE_MATERIAL_LINES: {enable_material_lines}")
    
    if not enable_material_lines:
        print("⚠️ 板料线功能已禁用")
        return
    
    # 测试拆图流程（需要有效的job_id和dwg_url）
    try:
        from cad_chaitu import chaitu_process
        
        # 这里需要替换为实际的测试数据
        test_job_id = "TEST_JOB_001"
        test_dwg_url = None  # 从数据库查询
        
        print(f"\n开始拆图流程测试...")
        print(f"  job_id: {test_job_id}")
        
        result = await chaitu_process(
            dwg_url=test_dwg_url,
            job_id=test_job_id
        )
        
        if result['status'] == 'ok':
            print(f"\n✅ 拆图成功")
            print(f"  子图数量: {result['data']['total_count']}")
            print(f"  文件列表: {result['data']['result_files']}")
        else:
            print(f"\n❌ 拆图失败: {result.get('message')}")
            
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()


def test_tolerance_calculation():
    """测试动态容差计算"""
    print("=" * 80)
    print("动态容差计算测试")
    print("=" * 80)
    
    test_dimensions = [10, 50, 100, 200, 500, 1000, 2000]
    
    print("\n尺寸 (mm) | 容差 (mm) | 相对误差")
    print("-" * 50)
    
    for dim in test_dimensions:
        tolerance = MaterialLineIntegrator._calculate_dynamic_tolerance(dim)
        relative = (tolerance / dim) * 100
        print(f"{dim:8.0f}  | {tolerance:8.1f}  | {relative:6.1f}%")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("板料线集成功能测试套件")
    print("=" * 80)
    
    # 测试1: 动态容差计算
    test_tolerance_calculation()
    
    # 测试2: 板料线集成器
    print("\n")
    # test_material_line_integrator()  # 需要测试数据
    
    # 测试3: 完整集成流程
    print("\n")
    # asyncio.run(test_full_integration())  # 需要数据库和MinIO
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
    print("\n提示：")
    print("  - 测试2和测试3需要实际的DXF文件和数据库连接")
    print("  - 请根据实际环境调整测试数据")
    print("  - 使用 ENABLE_MATERIAL_LINES=false 可禁用板料线功能")
