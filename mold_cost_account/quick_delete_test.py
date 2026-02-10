#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速删除功能测试 - 验证外键约束修复
"""

import requests
import json
from datetime import datetime

# 配置
BASE_URL = "http://localhost:5000"
USERNAME = "admin"
PASSWORD = "admin123"

def get_auth_token():
    """获取认证令牌"""
    login_url = f"{BASE_URL}/api/auth/login"
    login_data = {"username": USERNAME, "password": PASSWORD}
    
    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            result = response.json()
            return result.get('data', {}).get('access_token')
        else:
            print(f"登录失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"登录请求失败: {e}")
        return None

def test_delete_by_job_id(token):
    """测试根据任务ID删除 - 这是出现错误的接口"""
    print("\n🧪 测试根据任务ID删除会话...")
    
    # 创建测试会话
    create_url = f"{BASE_URL}/api/chat-sessions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    test_job_id = f"quick_test_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    test_session_id = f"quick_test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    create_data = {
        "session_id": test_session_id,
        "job_id": test_job_id,
        "name": "快速测试会话"
    }
    
    try:
        # 创建会话
        print(f"  创建测试会话: {test_session_id}")
        create_response = requests.post(create_url, headers=headers, json=create_data)
        if create_response.status_code != 201:
            print(f"  ❌ 创建会话失败: {create_response.status_code}")
            return False
        
        print(f"  ✅ 会话创建成功")
        
        # 删除会话
        delete_url = f"{BASE_URL}/api/chat-sessions/delete-by-job"
        delete_data = {"job_id": test_job_id}
        
        print(f"  执行删除操作...")
        delete_response = requests.delete(delete_url, headers=headers, json=delete_data)
        
        print(f"  删除响应状态: {delete_response.status_code}")
        
        if delete_response.status_code == 200:
            result = delete_response.json()
            print(f"  ✅ 删除成功: {result.get('message', '')}")
            
            # 显示删除统计
            data = result.get('data', {})
            if 'total_deleted' in data:
                print(f"  📊 总删除记录数: {data['total_deleted']}")
            
            return True
        else:
            print(f"  ❌ 删除失败: {delete_response.status_code}")
            try:
                error_info = delete_response.json()
                print(f"  错误信息: {error_info.get('message', 'Unknown error')}")
            except:
                print(f"  错误响应: {delete_response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ 测试过程中出现异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 快速删除功能测试")
    print("=" * 50)
    print(f"目标: 验证外键约束删除顺序修复")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"服务器: {BASE_URL}")
    
    # 获取认证令牌
    print("\n1. 获取认证令牌...")
    token = get_auth_token()
    if not token:
        print("❌ 无法获取认证令牌，测试终止")
        return
    print("✅ 认证成功")
    
    # 执行删除测试
    print("\n2. 执行删除测试...")
    success = test_delete_by_job_id(token)
    
    # 输出结果
    print("\n" + "=" * 50)
    print("📋 测试结果:")
    if success:
        print("🎉 测试通过！外键约束删除顺序修复成功")
        print("✅ /chat-sessions/delete-by-job 接口工作正常")
    else:
        print("❌ 测试失败！可能仍存在外键约束问题")
        print("💡 建议检查删除顺序和数据库外键关系")
    
    print("\n📚 相关文档:")
    print("- DELETE_ORDER_FIX.md - 修复详情")
    print("- SESSION_DELETE_SUMMARY.md - 功能总结")

if __name__ == "__main__":
    main()