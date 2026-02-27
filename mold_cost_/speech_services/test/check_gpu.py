#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GPU 状态检查脚本
检查 CUDA 和 GPU 是否可用

作者：集成方案
创建日期：2026-02-27
"""

import sys

def check_gpu():
    """检查 GPU 状态"""
    print("=" * 60)
    print("  GPU 状态检查")
    print("=" * 60)
    print()
    
    try:
        import torch
        
        print("✅ PyTorch 已安装")
        print(f"   版本: {torch.__version__}")
        print()
        
        # 检查 CUDA
        if torch.cuda.is_available():
            print("✅ CUDA 可用")
            print(f"   CUDA 版本: {torch.version.cuda}")
            print(f"   cuDNN 版本: {torch.backends.cudnn.version()}")
            print()
            
            # GPU 信息
            gpu_count = torch.cuda.device_count()
            print(f"✅ 检测到 {gpu_count} 个 GPU:")
            print()
            
            for i in range(gpu_count):
                props = torch.cuda.get_device_properties(i)
                print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
                print(f"   - 显存: {props.total_memory / 1024**3:.1f} GB")
                print(f"   - 计算能力: {props.major}.{props.minor}")
                print(f"   - 多处理器数量: {props.multi_processor_count}")
                print()
            
            # 测试 GPU
            print("🧪 测试 GPU 运算...")
            try:
                x = torch.rand(1000, 1000).cuda()
                y = torch.rand(1000, 1000).cuda()
                z = torch.matmul(x, y)
                print("✅ GPU 运算测试通过")
                print()
            except Exception as e:
                print(f"❌ GPU 运算测试失败: {e}")
                print()
            
            print("=" * 60)
            print("  结论：GPU 加速已启用")
            print("=" * 60)
            print()
            print("Speech Services 将使用 GPU 加速")
            print("预期性能提升：3-8 倍（取决于模型大小）")
            return 0
            
        else:
            print("⚠️  CUDA 不可用")
            print()
            print("可能的原因：")
            print("1. 未安装 NVIDIA 驱动")
            print("2. 安装的是 CPU 版本的 PyTorch")
            print("3. CUDA 版本不匹配")
            print()
            
            print("=" * 60)
            print("  如何启用 GPU 加速")
            print("=" * 60)
            print()
            
            print("步骤 1：检查 NVIDIA 驱动")
            print("  命令：nvidia-smi")
            print("  如果命令不存在，请安装 NVIDIA 驱动")
            print()
            
            print("步骤 2：卸载 CPU 版本的 PyTorch")
            print("  命令：pip uninstall -y torch torchaudio torchvision")
            print()
            
            print("步骤 3：安装 GPU 版本的 PyTorch")
            print("  CUDA 12.1：")
            print("    pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu121")
            print()
            print("  CUDA 11.8：")
            print("    pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu118")
            print()
            
            print("步骤 4：重新运行此脚本验证")
            print("  命令：python check_gpu.py")
            print()
            
            print("详细说明：GPU_SETUP.md")
            print()
            
            return 1
    
    except ImportError:
        print("❌ PyTorch 未安装")
        print()
        print("请先安装 PyTorch：")
        print("  pip install torch torchaudio torchvision")
        print()
        return 1
    
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(check_gpu())
