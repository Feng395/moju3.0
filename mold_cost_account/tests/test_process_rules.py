#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工艺规则API测试脚本
"""

import requests
import json

class ProcessRulesTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/process-rules"
        self.headers = {'Content-Type': 'application/json'}
    
    def create_rule(self, rule_data):
        """创建规则"""
        print(f"\n{'='*50}")
        print("测试: 创建工艺规则")
        print('='*50)
        
        try:
            response = requests.post(self.api_url, json=rule_data, headers=self.headers)
            print(f"状态码: {response.status_code}")
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result.get('success'), result.get('data')
        except Exception as e:
            print(f"请求错误: {e}")
            return False, None
    
    def get_rule(self, rule_id):
        """获取单个规则"""
        print(f"\n{'='*50}")
        print(f"测试: 获取规则 {rule_id}")
        print('='*50)
        
        try:
            response = requests.get(f"{self.api_url}/{rule_id}")
            print(f"状态码: {response.status_code}")
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result.get('success'), result.get('data')
        except Exception as e:
            print(f"请求错误: {e}")
            return False, None
    
    def get_rules(self, params=None):
        """获取规则列表"""
        print(f"\n{'='*50}")
        print("测试: 获取规则列表")
        if params:
            print(f"参数: {params}")
        print('='*50)
        
        try:
            response = requests.get(self.api_url, params=params)
            print(f"状态码: {response.status_code}")
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result.get('success'), result.get('data')
        except Exception as e:
            print(f"请求错误: {e}")
            return False, None
    
    def update_rule(self, rule_id, update_data):
        """更新规则"""
        print(f"\n{'='*50}")
        print(f"测试: 更新规则 {rule_id}")
        print('='*50)
        
        try:
            response = requests.put(f"{self.api_url}/{rule_id}", json=update_data, headers=self.headers)
            print(f"状态码: {response.status_code}")
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result.get('success'), result.get('data')
        except Exception as e:
            print(f"请求错误: {e}")
            return False, None
    
    def delete_rule(self, rule_id):
        """删除规则"""
        print(f"\n{'='*50}")
        print(f"测试: 删除规则 {rule_id}")
        print('='*50)
        
        try:
            response = requests.delete(f"{self.api_url}/{rule_id}")
            print(f"状态码: {response.status_code}")
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result.get('success')
        except Exception as e:
            print(f"请求错误: {e}")
            return False
    
    def batch_delete_rules(self, rule_ids):
        """批量删除规则"""
        print(f"\n{'='*50}")
        print(f"测试: 批量删除规则")
        print('='*50)
        
        try:
            response = requests.post(f"{self.api_url}/batch-delete", 
                                    json={'ids': rule_ids}, 
                                    headers=self.headers)
            print(f"状态码: {response.status_code}")
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result.get('success')
        except Exception as e:
            print(f"请求错误: {e}")
            return False
    
    def get_rules_by_version_type(self, version_id, feature_type, active_only=True):
        """根据版本和类型获取规则"""
        print(f"\n{'='*50}")
        print(f"测试: 获取规则 (版本={version_id}, 类型={feature_type})")
        print('='*50)
        
        try:
            params = {
                'version_id': version_id,
                'feature_type': feature_type,
                'active_only': str(active_only).lower()
            }
            response = requests.get(f"{self.api_url}/by-version-type", params=params)
            print(f"状态码: {response.status_code}")
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result.get('success'), result.get('data')
        except Exception as e:
            print(f"请求错误: {e}")
            return False, None
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始工艺规则API测试")
        print("=" * 50)
        
        # 测试数据
        test_rules = [
            {
                "id": "R001",
                "version_id": "v1.0",
                "feature_type": "WIRE",
                "name": "线割规则1",
                "description": "这是一个线割工艺规则",
                "priority": 10,
                "is_active": True,
                "conditions": "length > 100 AND width < 50",
                "output_params": "speed=100,power=80"
            },
            {
                "id": "R002",
                "version_id": "v1.0",
                "feature_type": "NC",
                "name": "数控规则1",
                "description": "这是一个数控工艺规则",
                "priority": 20,
                "is_active": True,
                "conditions": "depth > 10",
                "output_params": "rpm=3000,feed=500"
            },
            {
                "id": "R003",
                "version_id": "v1.1",
                "feature_type": "WIRE",
                "name": "线割规则2",
                "description": "升级版线割规则",
                "priority": 15,
                "is_active": True,
                "conditions": "length > 200",
                "output_params": "speed=120,power=90"
            }
        ]
        
        # 1. 创建规则
        print("\n1️⃣  测试创建规则")
        created_ids = []
        for rule in test_rules:
            success, data = self.create_rule(rule)
            if success:
                created_ids.append(rule['id'])
        
        # 2. 获取单个规则
        print("\n2️⃣  测试获取单个规则")
        if created_ids:
            self.get_rule(created_ids[0])
        
        # 3. 获取规则列表（无筛选）
        print("\n3️⃣  测试获取规则列表（无筛选）")
        self.get_rules()
        
        # 4. 获取规则列表（带筛选）
        print("\n4️⃣  测试获取规则列表（筛选版本v1.0）")
        self.get_rules({'version_id': 'v1.0'})
        
        print("\n5️⃣  测试获取规则列表（筛选类型WIRE）")
        self.get_rules({'feature_type': 'WIRE'})
        
        print("\n6️⃣  测试获取规则列表（名称模糊搜索）")
        self.get_rules({'name': '线割'})
        
        # 7. 分页测试
        print("\n7️⃣  测试分页（第1页，每页2条）")
        self.get_rules({'page': 1, 'page_size': 2})
        
        # 8. 根据版本和类型获取
        print("\n8️⃣  测试根据版本和类型获取规则")
        self.get_rules_by_version_type('v1.0', 'WIRE')
        
        # 9. 更新规则
        print("\n9️⃣  测试更新规则")
        if created_ids:
            update_data = {
                "name": "更新后的线割规则1",
                "priority": 25,
                "description": "这是更新后的描述"
            }
            self.update_rule(created_ids[0], update_data)
        
        # 10. 删除单个规则
        print("\n🔟 测试删除单个规则")
        if len(created_ids) > 0:
            self.delete_rule(created_ids[0])
            created_ids.pop(0)
        
        # 11. 批量删除
        print("\n1️⃣1️⃣  测试批量删除规则")
        if created_ids:
            self.batch_delete_rules(created_ids)
        
        # 12. 验证删除
        print("\n1️⃣2️⃣  验证删除（获取列表应为空）")
        self.get_rules()
        
        print("\n" + "=" * 50)
        print("✅ 测试完成")

def main():
    """主函数"""
    tester = ProcessRulesTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()