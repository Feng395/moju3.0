"""
检查 NC Agent 配置
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

print("=" * 60)
print("NC Agent 配置检查")
print("=" * 60)
print()

# 检查 NC_AGENT_URL
nc_url = os.getenv("NC_AGENT_URL")
print(f"NC_AGENT_URL: {nc_url}")

if nc_url:
    print("✓ NC Agent URL 已配置")
else:
    print("✗ NC Agent URL 未配置")
    print()
    print("请在 .env 文件中添加：")
    print("NC_AGENT_URL=http://nc-agent:8001")
    print()
    sys.exit(1)

print()
print("=" * 60)
print("配置检查完成")
print("=" * 60)
