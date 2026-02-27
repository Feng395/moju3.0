#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Speech Services 测试脚本
用于验证服务是否正常运行

作者：集成方案
创建日期：2026-02-27
"""

import requests
import sys
import time

BASE_URL = "http://localhost:8888"

def test_health():
    """测试健康检查"""
    print("🔍 测试健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        response.raise_for_status()
        result = response.json()
        print(f"✅ 健康检查通过: {result}")
        return True
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_models():
    """测试模型列表"""
    print("\n🔍 测试模型列表...")
    try:
        response = requests.get(f"{BASE_URL}/api/models", timeout=5)
        response.raise_for_status()
        result = response.json()
        print(f"✅ 模型列表获取成功:")
        print(f"   支持的模型: {result.get('models', [])}")
        print(f"   默认模型: {result.get('default', 'unknown')}")
        print(f"   已加载模型: {result.get('loaded', [])}")
        return True
    except Exception as e:
        print(f"❌ 模型列表获取失败: {e}")
        return False

def test_stats():
    """测试统计信息"""
    print("\n🔍 测试统计信息...")
    try:
        response = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        response.raise_for_status()
        result = response.json()
        print(f"✅ 统计信息获取成功:")
        print(f"   已加载模型: {result.get('loaded_models', [])}")
        if 'dict_stats' in result:
            print(f"   字典规则数: {result['dict_stats'].get('total_rules', 0)}")
        return True
    except Exception as e:
        print(f"❌ 统计信息获取失败: {e}")
        return False

def test_root():
    """测试根路径"""
    print("\n🔍 测试根路径...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        response.raise_for_status()
        result = response.json()
        print(f"✅ 根路径访问成功:")
        print(f"   服务名称: {result.get('name', 'unknown')}")
        print(f"   版本: {result.get('version', 'unknown')}")
        print(f"   状态: {result.get('status', 'unknown')}")
        return True
    except Exception as e:
        print(f"❌ 根路径访问失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("  Speech Services 测试")
    print("=" * 60)
    print(f"\n服务地址: {BASE_URL}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 等待服务启动
    print("⏳ 等待服务启动...")
    time.sleep(2)
    
    # 运行测试
    tests = [
        ("根路径", test_root),
        ("健康检查", test_health),
        ("模型列表", test_models),
        ("统计信息", test_stats),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    # 显示总结
    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！服务运行正常。")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查服务状态。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
