"""
自动生成 Token 并更新测试脚本
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_test_token import generate_test_token

def update_test_file(file_path, token):
    """更新测试文件中的 Token"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换 Token
        if 'TOKEN = "YOUR_JWT_TOKEN"' in content:
            new_content = content.replace(
                'TOKEN = "YOUR_JWT_TOKEN"',
                f'TOKEN = "{token}"'
            )
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
        else:
            print(f"⚠️  文件中未找到 TOKEN = \"YOUR_JWT_TOKEN\"")
            return False
    except Exception as e:
        print(f"❌ 更新文件失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("自动设置测试 Token")
    print("=" * 60)
    print()
    
    # 生成 Token
    print("1. 生成 JWT Token...")
    token, user_id = generate_test_token()
    print(f"   ✅ Token 已生成")
    print(f"   用户ID: {user_id}")
    print(f"   Token: {token[:50]}...")
    print()
    
    # 更新测试文件
    test_files = [
        "examples/test_chat_history.py",
        "examples/test_chat_history_simple.py"
    ]
    
    print("2. 更新测试文件...")
    for file_path in test_files:
        if os.path.exists(file_path):
            if update_test_file(file_path, token):
                print(f"   ✅ {file_path}")
            else:
                print(f"   ⚠️  {file_path} (已有 Token)")
        else:
            print(f"   ⚠️  {file_path} (文件不存在)")
    
    print()
    print("=" * 60)
    print("✅ 设置完成")
    print("=" * 60)
    print()
    print("现在可以运行测试:")
    print("  python examples/test_chat_history_simple.py")
    print("  python examples/test_chat_history.py")
    print()
