#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DWG到DXF转换工具
支持多种转换方式：ODA File Converter、ezdxf等
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

# 导入路径配置
try:
    from path_config import get_oda_converter_path
    ODA_CONVERTER_PATH = get_oda_converter_path()
    print(f"✓ 已加载 path_config 配置")
except ImportError as e:
    # 如果无法导入配置文件，使用默认路径
    ODA_CONVERTER_PATH = r"D:\my_project\ODAFileConverter.exe"
    print(f"⚠️ 警告: 无法导入 path_config ({e})，使用默认 ODA 路径")
except Exception as e:
    # 其他错误
    ODA_CONVERTER_PATH = r"D:\my_project\ODAFileConverter.exe"
    print(f"⚠️ 警告: 加载 path_config 时出错 ({e})，使用默认 ODA 路径")

def convert_with_oda(dwg_path, dxf_path=None):
    """
    使用ODA File Converter转换DWG到DXF
    """
    try:
        if not os.path.exists(ODA_CONVERTER_PATH):
            print(f"❌ ODA File Converter未找到: {ODA_CONVERTER_PATH}")
            return False
        
        if dxf_path is None:
            dxf_path = dwg_path.replace('.dwg', '.dxf').replace('.DWG', '.dxf')
        
        # 创建临时目录用于ODA转换
        temp_dir = tempfile.mkdtemp()
        temp_input_dir = os.path.join(temp_dir, "input")
        temp_output_dir = os.path.join(temp_dir, "output")
        os.makedirs(temp_input_dir, exist_ok=True)
        os.makedirs(temp_output_dir, exist_ok=True)
        
        # 复制DWG文件到临时输入目录
        dwg_filename = os.path.basename(dwg_path)
        temp_dwg_path = os.path.join(temp_input_dir, dwg_filename)
        shutil.copy2(dwg_path, temp_dwg_path)
        
        print(f"🔄 使用ODA File Converter转换: {dwg_path}")
        print(f"   输入目录: {temp_input_dir}")
        print(f"   输出目录: {temp_output_dir}")
        
        # 构建ODA命令
        # ODA File Converter命令格式：
        # ODAFileConverter.exe "input_folder" "output_folder" "ACAD2018" "DXF" "0" "1" "*.dwg"
        cmd = [
            ODA_CONVERTER_PATH,
            temp_input_dir,      # 输入文件夹
            temp_output_dir,     # 输出文件夹
            "ACAD2018",          # 输出版本
            "DXF",               # 输出格式
            "0",                 # 递归子目录 (0=否, 1=是)
            "1",                 # 审计和恢复 (0=否, 1=是)
            "*.dwg"              # 文件过滤器
        ]
        
        # 执行转换
        print("   执行转换命令...")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
        
        if result.returncode == 0:
            # 查找转换后的DXF文件
            dxf_filename = dwg_filename.replace('.dwg', '.dxf').replace('.DWG', '.dxf')
            temp_dxf_path = os.path.join(temp_output_dir, dxf_filename)
            
            if os.path.exists(temp_dxf_path):
                # 复制到目标位置
                shutil.copy2(temp_dxf_path, dxf_path)
                print(f"✅ 转换成功: {dxf_path}")
                
                # 清理临时文件
                shutil.rmtree(temp_dir, ignore_errors=True)
                return True
            else:
                print(f"❌ 转换后的DXF文件未找到: {temp_dxf_path}")
        else:
            print(f"❌ ODA转换失败:")
            print(f"   返回码: {result.returncode}")
            print(f"   错误输出: {result.stderr}")
        
        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False
        
    except Exception as e:
        print(f"❌ ODA转换过程出错: {e}")
        return False

def convert_dwg_to_dxf_with_ezdxf(dwg_path, dxf_path=None):
    """
    使用ezdxf尝试转换DWG到DXF（备用方案）
    """
    try:
        import ezdxf
        
        if dxf_path is None:
            dxf_path = dwg_path.replace('.dwg', '.dxf').replace('.DWG', '.dxf')
        
        print(f"🔄 尝试使用ezdxf读取DWG文件: {dwg_path}")
        
        # ezdxf从版本0.16开始支持读取DWG文件（有限支持）
        doc = ezdxf.readfile(dwg_path)
        
        print(f"💾 保存为DXF文件: {dxf_path}")
        doc.saveas(dxf_path)
        
        print("✅ ezdxf转换成功！")
        return True
        
    except Exception as e:
        print(f"❌ ezdxf转换失败: {e}")
        return False

def suggest_alternatives():
    """提供其他转换方案建议"""
    print("\n🔧 其他转换方案：")
    print("1. AutoCAD: 打开DWG → 另存为DXF")
    print("2. 在线转换: https://cloudconvert.com/dwg-to-dxf")
    print("3. LibreCAD: 免费CAD软件，支持DWG导入")
    print("4. FreeCAD: 开源CAD软件")
    print("5. DWG TrueView: Autodesk免费查看器，可转换格式")

def main():
    if len(sys.argv) < 2:
        print("DWG到DXF转换工具")
        print("=" * 50)
        print("使用方法:")
        print("  python dwg_to_dxf_converter.py <dwg_file_path>")
        print("  python dwg_to_dxf_converter.py <dwg_file_path> <output_dxf_path>")
        print("\n示例:")
        print("  python dwg_to_dxf_converter.py drawing.dwg")
        print("  python dwg_to_dxf_converter.py drawing.dwg output.dxf")
        print(f"\n当前ODA路径: {ODA_CONVERTER_PATH}")
        print(f"ODA存在: {'✅' if os.path.exists(ODA_CONVERTER_PATH) else '❌'}")
        return
    
    dwg_file = sys.argv[1]
    dxf_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 检查DWG文件是否存在
    if not os.path.exists(dwg_file):
        print(f"❌ 错误: DWG文件不存在: {dwg_file}")
        return
    
    print("DWG到DXF转换工具")
    print("=" * 50)
    print(f"输入文件: {dwg_file}")
    if dxf_file:
        print(f"输出文件: {dxf_file}")
    else:
        dxf_file = dwg_file.replace('.dwg', '.dxf').replace('.DWG', '.dxf')
        print(f"输出文件: {dxf_file} (自动生成)")
    
    # 优先尝试ODA File Converter
    if os.path.exists(ODA_CONVERTER_PATH):
        print("\n🚀 使用ODA File Converter转换...")
        success = convert_with_oda(dwg_file, dxf_file)
        if success:
            print(f"\n🎉 转换完成！可以使用以下命令处理DXF文件:")
            print(f"python run_dxf_processor.py \"{dxf_file}\"")
            return
    else:
        print(f"\n⚠️  ODA File Converter未找到: {ODA_CONVERTER_PATH}")
    
    # 备用方案：尝试ezdxf
    print("\n🔄 尝试备用方案 (ezdxf)...")
    success = convert_dwg_to_dxf_with_ezdxf(dwg_file, dxf_file)
    
    if success:
        print(f"\n🎉 转换完成！可以使用以下命令处理DXF文件:")
        print(f"python run_dxf_processor.py \"{dxf_file}\"")
    else:
        suggest_alternatives()

if __name__ == "__main__":
    main()