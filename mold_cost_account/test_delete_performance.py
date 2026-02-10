#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试删除接口性能
"""

import time
import requests
import json

# 配置
BASE_URL = "http://localhost:5000/api"
TOKEN = "your_token_here"  # 替换为实际的token

def test_delete_by_job_performance():
    """测试 delete-by-job 接口性能"""
    
    # 准备测试数据
    job_id = "test_job_123"  # 替换为实际的job_id
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "job_id": job_id
    }
    
    print(f"测试删除接口性能...")
    print(f"Job ID: {job_id}")
    print("-" * 60)
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 发送删除请求
        response = requests.delete(
            f"{BASE_URL}/chat-sessions/delete-by-job",
            headers=headers,
            json=data,
            timeout=10
        )
        
        # 记录结束时间
        elapsed = time.time() - start_time
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应时间: {elapsed:.3f} 秒")
        print("-" * 60)
        
        if response.status_code == 200:
            result = response.json()
            print("响应内容:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # 性能评估
            print("\n" + "=" * 60)
            print("性能评估:")
            if elapsed < 0.5:
                print(f"✅ 优秀！响应时间 {elapsed:.3f}秒 < 0.5秒")
            elif elapsed < 1.0:
                print(f"✅ 良好！响应时间 {elapsed:.3f}秒 < 1秒")
            elif elapsed < 2.0:
                print(f"⚠️  一般。响应时间 {elapsed:.3f}秒 < 2秒")
            else:
                print(f"❌ 较慢！响应时间 {elapsed:.3f}秒 >= 2秒")
            print("=" * 60)
        else:
            print(f"错误: {response.text}")
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"❌ 请求超时！耗时: {elapsed:.3f}秒")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ 请求失败: {e}")
        print(f"耗时: {elapsed:.3f}秒")


def test_connection_pool():
    """测试连接池效果 - 多次请求"""
    
    print("\n测试连接池效果（连续5次请求）...")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    times = []
    
    for i in range(5):
        start_time = time.time()
        
        try:
            # 发送一个简单的查询请求
            response = requests.get(
                f"{BASE_URL}/chat-sessions/",
                headers=headers,
                timeout=5
            )
            
            elapsed = time.time() - start_time
            times.append(elapsed)
            
            print(f"请求 {i+1}: {elapsed:.3f}秒 - 状态码: {response.status_code}")
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"请求 {i+1}: 失败 - {e}")
            times.append(elapsed)
    
    print("-" * 60)
    print(f"平均响应时间: {sum(times)/len(times):.3f}秒")
    print(f"最快: {min(times):.3f}秒")
    print(f"最慢: {max(times):.3f}秒")
    print("=" * 60)
    
    if sum(times)/len(times) < 0.2:
        print("✅ 连接池工作正常！平均响应时间很快")
    else:
        print("⚠️  连接池可能未生效或网络较慢")


if __name__ == "__main__":
    print("=" * 60)
    print("删除接口性能测试")
    print("=" * 60)
    print()
    
    # 提示用户配置
    print("⚠️  请先配置以下参数:")
    print(f"   - BASE_URL: {BASE_URL}")
    print(f"   - TOKEN: {'已配置' if TOKEN != 'your_token_here' else '未配置'}")
    print()
    
    if TOKEN == "your_token_here":
        print("❌ 请先在脚本中配置有效的 TOKEN")
        exit(1)
    
    # 运行测试
    try:
        # 测试1: 删除接口性能
        test_delete_by_job_performance()
        
        # 测试2: 连接池效果
        test_connection_pool()
        
    except KeyboardInterrupt:
        print("\n\n测试已取消")
    except Exception as e:
        print(f"\n\n测试失败: {e}")
