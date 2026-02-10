"""
配置读取测试脚本
用于验证配置是否正确从 .env 文件读取
"""
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from api_gateway.config import settings

print("=" * 60)
print("配置读取测试")
print("=" * 60)

# 1. 检查 .env 文件是否存在
env_file = ".env"
env_exists = os.path.exists(env_file)
print(f"\n1. .env 文件存在: {env_exists}")
if env_exists:
    print(f"   路径: {os.path.abspath(env_file)}")

# 2. 显示当前配置值
print("\n2. 当前配置值:")
print(f"   DB_HOST: {settings.DB_HOST}")
print(f"   DB_PORT: {settings.DB_PORT}")
print(f"   DB_NAME: {settings.DB_NAME}")
print(f"   DB_USER: {settings.DB_USER}")
print(f"   DB_PASSWORD: {'*' * len(settings.DB_PASSWORD)}")  # 隐藏密码
print(f"   NC_AGENT_URL: {settings.NC_AGENT_URL}")
print(f"   FEATURE_REPROCESS_API_URL: {settings.FEATURE_REPROCESS_API_URL}")
print(f"   REDIS_URL: {settings.REDIS_URL}")

# 3. 检查环境变量
print("\n3. 环境变量检查:")
env_vars = [
    "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
    "NC_AGENT_URL", "FEATURE_REPROCESS_API_URL", "REDIS_URL"
]
for var in env_vars:
    env_value = os.getenv(var)
    if env_value:
        if "PASSWORD" in var or "SECRET" in var:
            print(f"   {var}: {'*' * 8} (已设置)")
        else:
            print(f"   {var}: {env_value}")
    else:
        print(f"   {var}: (未设置)")

# 4. 读取 .env 文件内容（如果存在）
if env_exists:
    print("\n4. .env 文件内容预览:")
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()[:20]  # 只显示前20行
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('#'):
                # 隐藏敏感信息
                if any(keyword in line.upper() for keyword in ['PASSWORD', 'SECRET', 'KEY']):
                    key = line.split('=')[0] if '=' in line else line
                    print(f"   {i:2d}. {key}=********")
                else:
                    print(f"   {i:2d}. {line}")

# 5. 验证配置来源
print("\n5. 配置来源分析:")
print("   如果 .env 文件存在且包含配置项，pydantic-settings 会自动读取")
print("   如果配置值与代码中的默认值不同，说明已从 .env 读取")

# 6. 对比默认值
print("\n6. 配置值对比:")
defaults = {
    "DB_HOST": "localhost",
    "DB_PORT": 5432,
    "DB_NAME": "mold_cost_db",
    "DB_USER": "root",
    "NC_AGENT_URL": "http://192.168.0.65:8001",
}

for key, default_value in defaults.items():
    current_value = getattr(settings, key)
    if str(current_value) != str(default_value):
        print(f"   ✅ {key}: 已从配置文件读取 (当前值: {current_value})")
    else:
        print(f"   ⚠️  {key}: 使用默认值 (当前值: {current_value})")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
