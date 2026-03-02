"""
测试模块分类日志功能

运行此脚本后，检查 logs/ 目录下是否生成了以下文件：
- app.log（包含所有日志）
- error.log（仅包含错误日志）
- api_gateway.log（仅包含 api_gateway 模块的日志）
- workers.log（仅包含 workers 模块的日志）
- agents.log（仅包含 agents 模块的日志）
- mcp_services.log（仅包含 mcp_services 模块的日志）
- scripts.log（仅包含 scripts 模块的日志）
- shared.log（仅包含 shared 模块的日志）
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.unified_logging import init_logging, get_logger

# 初始化日志系统（启用模块分类）
init_logging(
    level="INFO",
    enable_module_logs=True
)

# 创建不同模块的 logger
api_gateway_logger = get_logger("api_gateway.test")
workers_logger = get_logger("workers.test")
agents_logger = get_logger("agents.test")
mcp_services_logger = get_logger("mcp_services.test")
scripts_logger = get_logger("scripts.test")
shared_logger = get_logger("shared.test")

print("=" * 80)
print("开始测试模块分类日志功能")
print("=" * 80)

# 测试各模块的日志
print("\n1. 测试 API Gateway 日志...")
api_gateway_logger.info("✅ API Gateway 模块日志测试 - INFO")
api_gateway_logger.warning("⚠️  API Gateway 模块日志测试 - WARNING")
api_gateway_logger.error("❌ API Gateway 模块日志测试 - ERROR")

print("\n2. 测试 Workers 日志...")
workers_logger.info("✅ Workers 模块日志测试 - INFO")
workers_logger.warning("⚠️  Workers 模块日志测试 - WARNING")
workers_logger.error("❌ Workers 模块日志测试 - ERROR")

print("\n3. 测试 Agents 日志...")
agents_logger.info("✅ Agents 模块日志测试 - INFO")
agents_logger.warning("⚠️  Agents 模块日志测试 - WARNING")
agents_logger.error("❌ Agents 模块日志测试 - ERROR")

print("\n4. 测试 MCP Services 日志...")
mcp_services_logger.info("✅ MCP Services 模块日志测试 - INFO")
mcp_services_logger.warning("⚠️  MCP Services 模块日志测试 - WARNING")
mcp_services_logger.error("❌ MCP Services 模块日志测试 - ERROR")

print("\n5. 测试 Scripts 日志...")
scripts_logger.info("✅ Scripts 模块日志测试 - INFO")
scripts_logger.warning("⚠️  Scripts 模块日志测试 - WARNING")
scripts_logger.error("❌ Scripts 模块日志测试 - ERROR")

print("\n6. 测试 Shared 日志...")
shared_logger.info("✅ Shared 模块日志测试 - INFO")
shared_logger.warning("⚠️  Shared 模块日志测试 - WARNING")
shared_logger.error("❌ Shared 模块日志测试 - ERROR")

print("\n" + "=" * 80)
print("测试完成！")
print("=" * 80)

# 检查日志文件
log_dir = Path("logs")
if log_dir.exists():
    print("\n📁 生成的日志文件：")
    log_files = sorted(log_dir.glob("*.log"))
    for log_file in log_files:
        size = log_file.stat().st_size
        print(f"  - {log_file.name} ({size} bytes)")
    
    print("\n✅ 请检查以下内容：")
    print("  1. app.log 应包含所有模块的日志")
    print("  2. error.log 应仅包含 ERROR 级别的日志")
    print("  3. api_gateway.log 应仅包含 api_gateway 模块的日志")
    print("  4. workers.log 应仅包含 workers 模块的日志")
    print("  5. agents.log 应仅包含 agents 模块的日志")
    print("  6. mcp_services.log 应仅包含 mcp_services 模块的日志")
    print("  7. scripts.log 应仅包含 scripts 模块的日志")
    print("  8. shared.log 应仅包含 shared 模块的日志")
    
    print("\n🔍 快速验证命令：")
    print("  # 查看 API Gateway 日志")
    print("  cat logs/api_gateway.log")
    print()
    print("  # 查看 Workers 日志")
    print("  cat logs/workers.log")
    print()
    print("  # 查看错误日志")
    print("  cat logs/error.log")
    print()
    print("  # 统计各文件的日志数量")
    print("  wc -l logs/*.log")
else:
    print("\n❌ 日志目录不存在！")

print("\n" + "=" * 80)
