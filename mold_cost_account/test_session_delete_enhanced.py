#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强的会话删除功能
"""

import requests
import json
import time
from datetime import datetime

# 配置
BASE_URL = "http://localhost:5000"
USERNAME = "admin"
PASSWORD = "admin123"

def get_auth_token():
    """获取认证令牌"""
    login_url = f"{BASE_URL}/api/auth/login"
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            result = response.json()
            return result.get('data', {}).get('access_token')
        else:
            print(f"登录失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"登录请求失败: {e}")
        return None

def create_test_session(token, job_id, session_id):
    """创建测试会话"""
    url = f"{BASE_URL}/api/chat-sessions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "session_id": session_id,
        "job_id": job_id,
        "name": f"测试会话 - {session_id}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"创建会话 {session_id}: {response.status_code}")
        if response.status_code == 201:
            print(f"  成功: {response.json()}")
            return True
        else:
            print(f"  失败: {response.text}")
            return False
    except Exception as e:
        print(f"创建会话请求失败: {e}")
        return False

def add_test_messages(token, session_id, count=3):
    """添加测试消息"""
    url = f"{BASE_URL}/api/chat-sessions/{session_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    success_count = 0
    for i in range(count):
        data = {
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"测试消息 {i+1} - {datetime.now().isoformat()}"
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 201:
                success_count += 1
            else:
                print(f"  添加消息 {i+1} 失败: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"添加消息 {i+1} 请求失败: {e}")
    
    print(f"成功添加 {success_count}/{count} 条消息到会话 {session_id}")
    return success_count

def get_session_messages(token, session_id):
    """获取会话消息"""
    url = f"{BASE_URL}/api/chat-sessions/{session_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            result = response.json()
            messages = result.get('data', {}).get('messages', [])
            print(f"会话 {session_id} 当前有 {len(messages)} 条消息")
            return messages
        else:
            print(f"获取消息失败: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"获取消息请求失败: {e}")
        return []

def delete_session_by_id(token, session_id):
    """根据会话ID删除会话"""
    url = f"{BASE_URL}/api/chat-sessions/{session_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.delete(url, headers=headers)
        print(f"\n删除会话 {session_id}: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"  成功: {result.get('message', '')}")
            data = result.get('data', {})
            if data:
                print(f"  删除统计:")
                for key, value in data.items():
                    if key not in ['session_id', 'job_id']:
                        print(f"    {key}: {value}")
            return True
        else:
            print(f"  失败: {response.text}")
            return False
    except Exception as e:
        print(f"删除会话请求失败: {e}")
        return False

def delete_session_by_job_id(token, job_id):
    """根据任务ID删除会话"""
    url = f"{BASE_URL}/api/chat-sessions/delete-by-job"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {"job_id": job_id}
    
    try:
        response = requests.delete(url, headers=headers, json=data)
        print(f"\n删除任务 {job_id} 的会话: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"  成功: {result.get('message', '')}")
            data = result.get('data', {})
            if data:
                print(f"  删除统计:")
                for key, value in data.items():
                    if key not in ['session_id', 'job_id']:
                        print(f"    {key}: {value}")
            return True
        else:
            print(f"  失败: {response.text}")
            return False
    except Exception as e:
        print(f"删除会话请求失败: {e}")
        return False

def verify_session_deleted(token, session_id):
    """验证会话是否已删除"""
    url = f"{BASE_URL}/api/chat-sessions/{session_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            print(f"  ✓ 会话 {session_id} 已成功删除")
            return True
        else:
            print(f"  ✗ 会话 {session_id} 仍然存在: {response.status_code}")
            return False
    except Exception as e:
        print(f"验证删除请求失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=== 修复后的会话删除功能测试 ===")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"服务器: {BASE_URL}")
    print("修复内容: 外键约束删除顺序问题")
    
    # 获取认证令牌
    print("\n1. 获取认证令牌...")
    token = get_auth_token()
    if not token:
        print("无法获取认证令牌，测试终止")
        return
    print("  ✓ 认证成功")
    
    # 测试数据
    test_cases = [
        {
            "name": "根据会话ID删除（修复测试）",
            "job_id": "test_job_delete_fix_session_id",
            "session_id": "test_session_delete_fix_id",
            "delete_method": "session_id"
        },
        {
            "name": "根据任务ID删除（修复测试）",
            "job_id": "test_job_delete_fix_job_id",
            "session_id": "test_session_delete_fix_job",
            "delete_method": "job_id"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. 测试: {test_case['name']}")
        job_id = test_case['job_id']
        session_id = test_case['session_id']
        delete_method = test_case['delete_method']
        
        # 创建测试会话
        print(f"  创建测试会话...")
        if not create_test_session(token, job_id, session_id):
            results.append((test_case['name'], False, "创建会话失败"))
            continue
        
        # 添加测试消息
        print(f"  添加测试消息...")
        message_count = add_test_messages(token, session_id, 5)
        if message_count == 0:
            print("  警告: 未能添加任何消息")
        
        # 验证消息存在
        messages = get_session_messages(token, session_id)
        
        # 执行删除
        print(f"  执行删除 (方法: {delete_method})...")
        if delete_method == "session_id":
            delete_success = delete_session_by_id(token, session_id)
        else:
            delete_success = delete_session_by_job_id(token, job_id)
        
        if not delete_success:
            results.append((test_case['name'], False, "删除操作失败"))
            continue
        
        # 验证删除结果
        print(f"  验证删除结果...")
        time.sleep(1)  # 等待一秒确保删除完成
        verify_success = verify_session_deleted(token, session_id)
        
        results.append((test_case['name'], verify_success, "成功" if verify_success else "验证失败"))
    
    # 打印测试总结
    print("\n" + "="*50)
    print("测试总结:")
    print("="*50)
    
    success_count = 0
    for name, success, message in results:
        status = "✓ 成功" if success else "✗ 失败"
        print(f"{status} {name}: {message}")
        if success:
            success_count += 1
    
    print(f"\n总计: {success_count}/{len(results)} 个测试通过")
    
    if success_count == len(results):
        print("🎉 所有测试通过！修复后的会话删除功能工作正常。")
        print("✅ 外键约束删除顺序问题已解决")
    else:
        print("⚠️  部分测试失败，请检查日志。")
        print("💡 如果仍有外键约束错误，请检查数据库外键关系")

if __name__ == "__main__":
    main()