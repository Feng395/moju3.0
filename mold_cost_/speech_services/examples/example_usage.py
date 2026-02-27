#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Speech Services 使用示例
演示如何调用语音识别服务

作者：集成方案
创建日期：2026-02-27
"""

import requests
import sys
from pathlib import Path

# 服务地址
BASE_URL = "http://localhost:8888"

def transcribe_audio_file(audio_file_path, model="small", language="zh"):
    """
    转录音频文件
    
    参数:
        audio_file_path: 音频文件路径
        model: 模型大小（tiny/base/small/medium/large）
        language: 语言代码（zh/en）
    
    返回:
        转录结果字典
    """
    print(f"📝 转录音频文件: {audio_file_path}")
    print(f"   模型: {model}")
    print(f"   语言: {language}")
    print()
    
    # 检查文件是否存在
    audio_path = Path(audio_file_path)
    if not audio_path.exists():
        print(f"❌ 文件不存在: {audio_file_path}")
        return None
    
    try:
        # 准备请求
        with open(audio_path, 'rb') as f:
            files = {'file': (audio_path.name, f, 'audio/wav')}
            data = {
                'model': model,
                'language': language,
                'fix_terms': 'true',
                'learn': 'true',
                'verbose': 'true'
            }
            
            print("⏳ 正在转录...")
            
            # 发送请求
            response = requests.post(
                f"{BASE_URL}/api/transcribe",
                files=files,
                data=data,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 显示结果
            if result.get('success'):
                print("✅ 转录成功！")
                print()
                print("=" * 60)
                print("转录结果:")
                print("=" * 60)
                print(result.get('text', ''))
                print("=" * 60)
                print()
                
                # 显示详细信息
                if 'corrections' in result:
                    corrections = result['corrections']
                    print(f"术语修正: {corrections.get('count', 0)} 处")
                
                if 'stats' in result:
                    stats = result['stats']
                    print(f"文件大小: {stats.get('file_size', 0)} bytes")
                    print(f"字典规则: {stats.get('dict_rules', 0)} 条")
                
                return result
            else:
                print("❌ 转录失败")
                return None
    
    except requests.exceptions.Timeout:
        print("❌ 请求超时，请检查服务是否运行或音频文件是否过大")
        return None
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到服务: {BASE_URL}")
        print("   请确保 Speech Services 正在运行")
        return None
    except Exception as e:
        print(f"❌ 转录失败: {e}")
        return None

def check_service():
    """检查服务是否运行"""
    print("🔍 检查服务状态...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ 服务运行正常")
        print(f"   状态: {result.get('status', 'unknown')}")
        print(f"   已加载模型: {result.get('loaded_models', [])}")
        print()
        return True
    except Exception as e:
        print(f"❌ 服务未运行: {e}")
        print()
        print("请先启动 Speech Services:")
        print("  Windows: start_speech.bat")
        print("  Linux/macOS: ./start_speech.sh")
        print()
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("  Speech Services 使用示例")
    print("=" * 60)
    print()
    
    # 检查服务
    if not check_service():
        return 1
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用方法:")
        print(f"  python {sys.argv[0]} <音频文件路径> [模型] [语言]")
        print()
        print("示例:")
        print(f"  python {sys.argv[0]} test.wav")
        print(f"  python {sys.argv[0]} test.wav small zh")
        print(f"  python {sys.argv[0]} test.wav medium en")
        print()
        print("支持的模型: tiny, base, small, medium, large")
        print("支持的语言: zh (中文), en (英文)")
        return 1
    
    # 获取参数
    audio_file = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "small"
    language = sys.argv[3] if len(sys.argv) > 3 else "zh"
    
    # 转录音频
    result = transcribe_audio_file(audio_file, model, language)
    
    if result:
        print("🎉 转录完成！")
        return 0
    else:
        print("⚠️  转录失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
