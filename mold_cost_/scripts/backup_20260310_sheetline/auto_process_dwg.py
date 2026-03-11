#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动化处理脚本：DWG转DXF → 添加板料线 → 输出到output目录
"""

import os
import sys
import time
import subprocess

def main():
    """主流程"""
    print("=" * 80)
    print("自动化处理流程：DWG → DXF → 添加板料线")
    print("=" * 80)
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 定义路径
    dwg_converter = os.path.join(current_dir, "dwg_to_dxf_converter.py")
    sheetline_processor = os.path.join(current_dir, "dxf_auto_sheetline.py")
    output_dir = os.path.join(current_dir, "output")
    
    # 确保output目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"✅ 创建输出目录: {output_dir}")
    
    # 步骤1：运行DWG转DXF
    print("\n" + "=" * 80)
    print("步骤1：DWG转DXF")
    print("=" * 80)
    
    # 查找当前目录下的DWG文件
    dwg_files = [f for f in os.listdir(current_dir) if f.lower().endswith('.dwg')]
    
    if not dwg_files:
        print("❌ 当前目录没有找到DWG文件")
        print(f"   目录: {current_dir}")
        return False
    
    print(f"找到 {len(dwg_files)} 个DWG文件:")
    for f in dwg_files:
        print(f"   - {f}")
    
    # 转换所有DWG文件
    converted_dxf_files = []
    
    for dwg_file in dwg_files:
        dwg_path = os.path.join(current_dir, dwg_file)
        dxf_file = dwg_file.replace('.dwg', '.dxf').replace('.DWG', '.dxf')
        dxf_path = os.path.join(current_dir, dxf_file)
        
        print(f"\n转换: {dwg_file} → {dxf_file}")
        
        try:
            result = subprocess.run(
                [sys.executable, dwg_converter, dwg_path],
                cwd=current_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300  # 5分钟超时
            )
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("错误输出:", result.stderr)
            
            if result.returncode == 0 and os.path.exists(dxf_path):
                print(f"✅ 转换成功: {dxf_file}")
                converted_dxf_files.append(dxf_path)
            else:
                print(f"❌ 转换失败: {dwg_file}")
        
        except subprocess.TimeoutExpired:
            print(f"❌ 转换超时: {dwg_file}")
        except Exception as e:
            print(f"❌ 转换出错: {e}")
    
    if not converted_dxf_files:
        print("\n❌ 没有成功转换的DXF文件")
        return False
    
    print(f"\n✅ 成功转换 {len(converted_dxf_files)} 个DXF文件")
    
    # 等待1秒，确保文件写入完成
    time.sleep(1)
    
    # 步骤2：运行板料线处理
    print("\n" + "=" * 80)
    print("步骤2：添加板料线")
    print("=" * 80)
    
    success_count = 0
    
    for dxf_path in converted_dxf_files:
        dxf_file = os.path.basename(dxf_path)
        print(f"\n处理: {dxf_file}")
        
        try:
            result = subprocess.run(
                [sys.executable, sheetline_processor, dxf_path],
                cwd=current_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=600  # 10分钟超时
            )
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("错误输出:", result.stderr)
            
            if result.returncode == 0:
                print(f"✅ 处理成功: {dxf_file}")
                success_count += 1
            else:
                print(f"❌ 处理失败: {dxf_file}")
        
        except subprocess.TimeoutExpired:
            print(f"❌ 处理超时: {dxf_file}")
        except Exception as e:
            print(f"❌ 处理出错: {e}")
    
    if success_count == 0:
        print(f"\n❌ 所有文件处理失败")
        return False
    
    print(f"\n✅ 成功处理 {success_count}/{len(converted_dxf_files)} 个文件")
    
    # 步骤3：检查输出文件
    print("\n" + "=" * 80)
    print("步骤3：检查输出文件")
    print("=" * 80)
    
    output_files = [f for f in os.listdir(output_dir) if f.endswith('.dxf')]
    if output_files:
        print(f"✅ 在output目录找到 {len(output_files)} 个DXF文件:")
        for f in output_files:
            file_path = os.path.join(output_dir, f)
            file_size = os.path.getsize(file_path) / 1024  # KB
            print(f"   - {f} ({file_size:.1f} KB)")
    else:
        print("⚠️ output目录中没有找到DXF文件")
    
    print("\n" + "=" * 80)
    print("✅ 自动化处理完成！")
    print("=" * 80)
    return True

if __name__ == "__main__":
    start_time = time.time()
    success = main()
    elapsed_time = time.time() - start_time
    
    if success:
        print(f"\n✅ 总耗时: {elapsed_time:.1f} 秒")
        sys.exit(0)
    else:
        print(f"\n❌ 处理失败，耗时: {elapsed_time:.1f} 秒")
        sys.exit(1)
