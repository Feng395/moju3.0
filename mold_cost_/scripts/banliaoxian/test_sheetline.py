#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板料线自动生成测试脚本
用于测试 dxf_auto_sheetline.py 的功能
"""

import os
import sys
import time
from pathlib import Path

# 添加当前目录到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def print_banner(text):
    """打印横幅"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def print_banner(text):
    """打印横幅"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def print_stage(stage_num, total_stages, title):
    """打印阶段标题"""
    print("\n" + "─" * 80)
    print(f"📍 阶段 {stage_num}/{total_stages}: {title}")
    print("─" * 80)

def print_substage(title):
    """打印子阶段"""
    print(f"\n  ▸ {title}")

def print_info(message, indent=2):
    """打印信息"""
    print(" " * indent + message)

def print_success(message, indent=2):
    """打印成功信息"""
    print(" " * indent + f"✅ {message}")

def print_warning(message, indent=2):
    """打印警告信息"""
    print(" " * indent + f"⚠️  {message}")

def print_error(message, indent=2):
    """打印错误信息"""
    print(" " * indent + f"❌ {message}")

def test_sheetline_generation(dxf_file: str, use_triple_condition: bool = True, multi_part_mode: bool = True):
    """
    测试板料线生成功能
    
    Args:
        dxf_file: DXF 文件路径
        use_triple_condition: 是否使用三重条件系统（True）或精密L/W/T提取器（False）
        multi_part_mode: 是否启用多零件模式
    """
    print_banner("板料线自动生成测试")
    
    total_stages = 6
    current_stage = 0
    
    # ========== 阶段 1: 文件检查 ==========
    current_stage += 1
    print_stage(current_stage, total_stages, "文件检查")
    
    print_info(f"输入文件: {dxf_file}")
    
    if not os.path.exists(dxf_file):
        print_error(f"DXF 文件不存在: {dxf_file}")
        return False
    
    file_size_kb = os.path.getsize(dxf_file) / 1024
    print_success(f"文件存在，大小: {file_size_kb:.1f} KB")
    
    # ========== 阶段 2: 配置初始化 ==========
    current_stage += 1
    print_stage(current_stage, total_stages, "配置初始化")
    
    # 配置输出目录
    try:
        from path_config import DEFAULT_OUTPUT_DIR, DEFAULT_LOG_DIR
        output_dir = DEFAULT_OUTPUT_DIR
        log_dir = DEFAULT_LOG_DIR
        print_success(f"使用配置的输出目录")
        print_info(f"输出目录: {output_dir}", 4)
        print_info(f"日志目录: {log_dir}", 4)
    except ImportError:
        output_dir = os.path.join(current_dir, "output", "banliaoxian")
        log_dir = os.path.join(current_dir, "logs", "banliaoxian")
        print_warning(f"使用默认输出目录")
        print_info(f"输出目录: {output_dir}", 4)
        print_info(f"日志目录: {log_dir}", 4)
    
    # 创建输出目录
    print_substage("创建输出目录")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    print_success("输出目录已创建", 4)
    
    # JSON 0,0 坐标文件目录
    json_0_0_dir = os.path.join(output_dir, "json_0_0")
    os.makedirs(json_0_0_dir, exist_ok=True)
    print_success("JSON 目录已创建", 4)
    
    # ========== 阶段 3: 导入处理模块 ==========
    current_stage += 1
    print_stage(current_stage, total_stages, "导入处理模块")
    
    try:
        print_info("正在导入 dxf_auto_sheetline 模块...")
        from dxf_auto_sheetline import process_single_dxf_with_triple_integration, set_processing_mode
        print_success("模块导入成功")
        
        # 设置处理模式
        print_substage("设置处理模式")
        mode = 'triple_condition' if use_triple_condition else 'precision_lwt'
        set_processing_mode(mode)
        
        mode_name = '三重条件系统' if use_triple_condition else '精密L/W/T提取器'
        part_mode_name = '多零件模式' if multi_part_mode else '单零件模式'
        
        print_success(f"处理模式: {mode_name}", 4)
        print_success(f"零件模式: {part_mode_name}", 4)
        
        if use_triple_condition:
            print_info("预期识别: ~173 个零件", 4)
        else:
            print_info("预期识别: ~76 个零件", 4)
        
    except ImportError as e:
        print_error(f"无法导入处理函数: {e}")
        return False
    
    # ========== 阶段 4: 执行板料线生成 ==========
    current_stage += 1
    print_stage(current_stage, total_stages, "执行板料线生成")
    
    print_info("开始处理 DXF 文件...")
    print_info(f"文件: {os.path.basename(dxf_file)}", 4)
    print_info(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", 4)
    
    start_time = time.time()
    
    try:
        success = process_single_dxf_with_triple_integration(
            dxf_file_path=dxf_file,
            output_dir=output_dir,
            log_file_dir=log_dir,
            csv_path=None,  # 不使用 CSV
            json_0_0_dir=json_0_0_dir,
            use_triple_condition=use_triple_condition,
            multi_part_mode=multi_part_mode
        )
        
        elapsed_time = time.time() - start_time
        
        # ========== 阶段 5: 结果验证 ==========
        current_stage += 1
        print_stage(current_stage, total_stages, "结果验证")
        
        if success:
            print_success(f"处理成功！耗时: {elapsed_time:.1f} 秒")
            
            # 检查输出文件
            print_substage("检查输出文件")
            output_file = os.path.join(output_dir, os.path.basename(dxf_file))
            
            if os.path.exists(output_file):
                output_size_kb = os.path.getsize(output_file) / 1024
                size_increase = output_size_kb - file_size_kb
                size_increase_percent = (size_increase / file_size_kb) * 100
                
                print_success(f"输出文件已生成", 4)
                print_info(f"路径: {output_file}", 6)
                print_info(f"大小: {output_size_kb:.1f} KB (增加 {size_increase:.1f} KB, +{size_increase_percent:.1f}%)", 6)
            else:
                print_warning(f"输出文件未找到: {output_file}", 4)
            
            # 检查日志文件
            print_substage("检查日志文件")
            log_file = os.path.join(log_dir, os.path.basename(dxf_file).replace('.dxf', '.log'))
            if os.path.exists(log_file):
                log_size_kb = os.path.getsize(log_file) / 1024
                print_success(f"日志文件已生成", 4)
                print_info(f"路径: {log_file}", 6)
                print_info(f"大小: {log_size_kb:.1f} KB", 6)
            
            # 检查 JSON 文件
            print_substage("检查 JSON 文件")
            json_files = [f for f in os.listdir(json_0_0_dir) if f.endswith('.json')]
            if json_files:
                print_success(f"生成了 {len(json_files)} 个 JSON 文件", 4)
                for json_file in json_files[:3]:  # 只显示前3个
                    print_info(f"• {json_file}", 6)
                if len(json_files) > 3:
                    print_info(f"... 还有 {len(json_files) - 3} 个文件", 6)
            else:
                print_info("未生成 JSON 文件", 4)
            
            # ========== 阶段 6: 总结 ==========
            current_stage += 1
            print_stage(current_stage, total_stages, "处理总结")
            
            print_success("所有阶段完成")
            print_info(f"总耗时: {elapsed_time:.1f} 秒", 4)
            print_info(f"平均速度: {file_size_kb / elapsed_time:.1f} KB/s", 4)
            
            print_banner("✅ 测试成功完成")
            return True
        else:
            print_error(f"处理失败，耗时: {elapsed_time:.1f} 秒")
            
            # 检查失败文件
            print_substage("检查失败文件")
            fail_dir = os.path.join(output_dir, "fail_file")
            if os.path.exists(fail_dir):
                fail_files = os.listdir(fail_dir)
                if fail_files:
                    print_warning(f"发现 {len(fail_files)} 个失败文件", 4)
                    for fail_file in fail_files[:3]:
                        print_info(f"• {fail_file}", 6)
            
            print_banner("❌ 测试失败")
            return False
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        
        print_error(f"处理出错，耗时: {elapsed_time:.1f} 秒")
        print_error(f"错误类型: {type(e).__name__}", 4)
        print_error(f"错误信息: {str(e)}", 4)
        
        print_substage("错误堆栈")
        import traceback
        traceback.print_exc()
        
        print_banner("❌ 测试异常终止")
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='板料线自动生成测试工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用当前目录的 ceshitu.dxf 文件（三重条件系统，多零件模式）
  python test_sheetline.py ceshitu.dxf
  
  # 使用精密L/W/T提取器
  python test_sheetline.py ceshitu.dxf --mode precision
  
  # 单零件模式
  python test_sheetline.py ceshitu.dxf --single-part
  
  # 使用完整路径
  python test_sheetline.py "D:\\path\\to\\file.dxf"
        """
    )
    
    parser.add_argument('dxf_file', help='DXF 文件路径')
    parser.add_argument('--mode', choices=['triple', 'precision'], default='triple',
                       help='处理模式: triple=三重条件系统(默认), precision=精密L/W/T提取器')
    parser.add_argument('--single-part', action='store_true',
                       help='使用单零件模式（默认为多零件模式）')
    parser.add_argument('--debug', action='store_true',
                       help='调试模式（不调用 sys.exit，方便调试器使用）')
    
    args = parser.parse_args()
    
    # 处理文件路径
    dxf_file = args.dxf_file
    
    # 如果是相对路径，尝试在当前目录查找
    if not os.path.isabs(dxf_file):
        dxf_file = os.path.join(current_dir, dxf_file)
    
    # 运行测试
    use_triple = (args.mode == 'triple')
    multi_part = not args.single_part
    
    success = test_sheetline_generation(dxf_file, use_triple, multi_part)
    
    # 调试模式下不调用 sys.exit，直接返回
    if args.debug:
        return 0 if success else 1
    else:
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
