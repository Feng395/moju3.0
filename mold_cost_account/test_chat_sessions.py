#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天会话API测试脚本
"""

import requests
import json
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"  # 修改为你的用户名
PASSWORD = "admin123"  # 修改为你的密码

# 测试会话ID（需要在数据库中存在）
TEST_SESSION_ID = "test_session_001"
# 测试任务ID（需要在数据库中存在）
TEST_JOB_ID = "test_job_001"


def print_response(title, response):
    """打印响应信息"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"状态码: {response.status_code}")
    print(f"响应内容:")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print(response.text)


def login():
    """登录获取token"""
    print("\n开始登录...")
    url = f"{BASE_URL}/api/login"
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    response = requests.post(url, json=data)
    print_response("登录结果", response)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            token = result.get('token')
            print(f"\n✓ 登录成功，获取到token")
            return token
    
    print("\n✗ 登录失败")
    return None


def test_update_session_name_by_job_id(token, job_id, new_name):
    """测试根据任务ID更新会话名称"""
    print(f"\n\n测试1: 根据任务ID更新会话名称")
    print(f"任务ID: {job_id}")
    print(f"新名称: {new_name}")
    
    url = f"{BASE_URL}/api/chat-sessions/update-name"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "job_id": job_id,
        "name": new_name
    }
    
    response = requests.put(url, json=data, headers=headers)
    print_response("根据任务ID更新会话名称结果", response)
    
    return response.status_code == 200


def test_update_session_name(token, session_id, new_name):
    """测试根据会话ID更新会话名称"""
    print(f"\n\n测试2: 根据会话ID更新会话名称")
    print(f"会话ID: {session_id}")
    print(f"新名称: {new_name}")
    
    url = f"{BASE_URL}/api/chat-sessions/{session_id}/name"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "name": new_name
    }
    
    response = requests.put(url, json=data, headers=headers)
    print_response("根据会话ID更新会话名称结果", response)
    
    return response.status_code == 200


def test_get_session(token, session_id):
    """测试获取会话详情"""
    print(f"\n\n测试3: 获取会话详情")
    print(f"会话ID: {session_id}")
    
    url = f"{BASE_URL}/api/chat-sessions/{session_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(url, headers=headers)
    print_response("获取会话详情结果", response)
    
    return response.status_code == 200


def test_get_sessions_list(token, status=None, limit=10, offset=0):
    """测试获取会话列表"""
    print(f"\n\n测试4: 获取会话列表")
    print(f"状态过滤: {status or '无'}")
    print(f"数量限制: {limit}")
    print(f"偏移量: {offset}")
    
    url = f"{BASE_URL}/api/chat-sessions/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "limit": limit,
        "offset": offset
    }
    if status:
        params["status"] = status
    
    response = requests.get(url, headers=headers, params=params)
    print_response("获取会话列表结果", response)
    
    return response.status_code == 200


def test_invalid_token():
    """测试无效token"""
    print(f"\n\n测试5: 使用无效token")
    
    url = f"{BASE_URL}/api/chat-sessions/{TEST_SESSION_ID}"
    headers = {
        "Authorization": "Bearer invalid_token_here"
    }
    
    response = requests.get(url, headers=headers)
    print_response("无效token测试结果", response)
    
    return response.status_code == 401


def test_empty_name(token, job_id):
    """测试空名称"""
    print(f"\n\n测试6: 更新为空名称（应该失败）")
    
    url = f"{BASE_URL}/api/chat-sessions/update-name"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "job_id": job_id,
        "name": "   "  # 空白字符
    }
    
    response = requests.put(url, json=data, headers=headers)
    print_response("空名称测试结果", response)
    
    return response.status_code == 400


def test_nonexistent_session(token):
    """测试不存在的会话"""
    print(f"\n\n测试7: 访问不存在的任务")
    
    url = f"{BASE_URL}/api/chat-sessions/update-name"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "job_id": "nonexistent_job_id",
        "name": "测试名称"
    }
    
    response = requests.put(url, json=data, headers=headers)
    print_response("不存在任务测试结果", response)
    
    return response.status_code == 404


def test_delete_session_by_job_id(token, job_id):
    """测试根据任务ID删除会话"""
    print(f"\n\n测试8: 根据任务ID删除会话")
    print(f"任务ID: {job_id}")
    
    url = f"{BASE_URL}/api/chat-sessions/delete-by-job"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "job_id": job_id
    }
    
    response = requests.delete(url, json=data, headers=headers)
    print_response("根据任务ID删除会话结果", response)
    
    return response.status_code == 200


def test_delete_session_by_id(token, session_id):
    """测试根据会话ID删除会话"""
    print(f"\n\n测试9: 根据会话ID删除会话")
    print(f"会话ID: {session_id}")
    
    url = f"{BASE_URL}/api/chat-sessions/{session_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.delete(url, headers=headers)
    print_response("根据会话ID删除会话结果", response)
    
    return response.status_code == 200


def main():
    """主测试流程"""
    print("="*60)
    print("聊天会话API测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"服务地址: {BASE_URL}")
    
    # 1. 登录获取token
    token = login()
    if not token:
        print("\n✗ 无法获取token，测试终止")
        return
    
    # 测试结果统计
    results = []
    
    # 2. 测试根据任务ID更新会话名称（推荐）
    results.append(("根据任务ID更新会话名称", test_update_session_name_by_job_id(
        token, TEST_JOB_ID, f"测试会话-{datetime.now().strftime('%H:%M:%S')}"
    )))
    
    # 3. 测试根据会话ID更新会话名称
    results.append(("根据会话ID更新会话名称", test_update_session_name(
        token, TEST_SESSION_ID, f"测试会话2-{datetime.now().strftime('%H:%M:%S')}"
    )))
    
    # 4. 测试获取会话详情
    results.append(("获取会话详情", test_get_session(token, TEST_SESSION_ID)))
    
    # 5. 测试获取会话列表
    results.append(("获取会话列表", test_get_sessions_list(token, status="active", limit=5)))
    
    # 6. 测试无效token
    results.append(("无效token测试", test_invalid_token()))
    
    # 7. 测试空名称
    results.append(("空名称测试", test_empty_name(token, TEST_JOB_ID)))
    
    # 8. 测试不存在的会话
    results.append(("不存在任务测试", test_nonexistent_session(token)))
    
    # 9. 测试删除会话（根据任务ID）
    results.append(("根据任务ID删除会话", test_delete_session_by_job_id(token, "test_job_for_delete")))
    
    # 10. 测试删除会话（根据会话ID）
    results.append(("根据会话ID删除会话", test_delete_session_by_id(token, "test_session_for_delete")))
    
    # 打印测试总结
    print("\n\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
