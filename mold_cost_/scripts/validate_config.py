#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置验证脚本
检查所有配置项是否正确设置
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.config import settings
from dotenv import load_dotenv
import os

# 重新加载环境变量
load_dotenv(override=True)

print("=" * 70)
print("配置验证报告")
print("=" * 70)

# 验证结果
issues = []
warnings = []
success = []

# 1. 数据库配置验证
print("\n【数据库配置】")
print(f"  主机: {settings.DB_HOST}")
print(f"  端口: {settings.DB_PORT}")
print(f"  数据库: {settings.DB_NAME}")
print(f"  用户: {settings.DB_USER}")
print(f"  连接池大小: {settings.DB_POOL_SIZE}")

if settings.DB_HOST == "localhost" and settings.DB_NAME == "mold_cost":
    success.append("✅ 数据库配置正确 - 使用本地数据库")
elif settings.DB_HOST == "192.168.1.54" and settings.DB_NAME == "mold_cost_db":
    warnings.append("⚠️  数据库配置 - 使用远程数据库（确认是否正确）")
else:
    warnings.append(f"⚠️  数据库配置 - 使用自定义配置: {settings.DB_HOST}/{settings.DB_NAME}")

# 2. Redis配置验证
print("\n【Redis配置】")
print(f"  URL: {settings.REDIS_URL}")
print(f"  降级模式: {settings.SKIP_REDIS}")

if "localhost" in settings.REDIS_URL or "127.0.0.1" in settings.REDIS_URL:
    success.append("✅ Redis配置正确 - 使用本地Redis")
else:
    warnings.append(f"⚠️  Redis配置 - 使用远程Redis: {settings.REDIS_URL}")

# 3. RabbitMQ配置验证
print("\n【RabbitMQ配置】")
print(f"  主机: {settings.RABBITMQ_HOST}")
print(f"  端口: {settings.RABBITMQ_PORT}")
print(f"  用户: {settings.RABBITMQ_USER}")

if settings.RABBITMQ_HOST == "localhost":
    success.append("✅ RabbitMQ配置正确 - 使用本地RabbitMQ")
else:
    warnings.append(f"⚠️  RabbitMQ配置 - 使用远程RabbitMQ: {settings.RABBITMQ_HOST}")

# 4. MinIO配置验证
print("\n【MinIO配置】")
print(f"  端点: {settings.MINIO_ENDPOINT}")
print(f"  Bucket: {settings.MINIO_BUCKET_FILES}")
print(f"  HTTPS: {settings.MINIO_USE_HTTPS}")

if "localhost" in settings.MINIO_ENDPOINT:
    success.append("✅ MinIO配置正确 - 使用本地MinIO")
else:
    warnings.append(f"⚠️  MinIO配置 - 使用远程MinIO: {settings.MINIO_ENDPOINT}")

# 5. JWT配置验证
print("\n【JWT配置】")
print(f"  算法: {settings.JWT_ALGORITHM}")
print(f"  过期时间: {settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES}分钟")

if settings.JWT_SECRET_KEY == "your-secret-key-change-in-production-2024":
    warnings.append("⚠️  JWT密钥 - 使用默认密钥（生产环境请修改）")
else:
    success.append("✅ JWT密钥已自定义")

# 6. LLM配置验证
print("\n【LLM配置】")
print(f"  启用: {settings.USE_LLM}")
print(f"  模型: {settings.OPENAI_MODEL}")
print(f"  Base URL: {settings.OPENAI_BASE_URL}")

if settings.USE_LLM:
    if settings.OPENAI_API_KEY == "sk-dummy":
        warnings.append("⚠️  LLM配置 - 使用虚拟API Key")
    else:
        success.append("✅ LLM配置正确")

# 7. 外部服务配置验证
print("\n【外部服务配置】")
print(f"  NC Agent: {settings.NC_AGENT_URL}")
print(f"  ODA转换器: {settings.ODA_FILE_CONVERTER_PATH}")

if settings.NC_AGENT_ENABLED:
    success.append("✅ NC Agent已启用")

# 8. 性能配置验证
print("\n【性能配置】")
print(f"  任务并发数: {settings.JOB_PROCESSING_CONCURRENCY}")
print(f"  价格计算并发数: {settings.PRICING_RECALCULATE_CONCURRENCY}")
print(f"  特征识别并发数: {settings.FEATURE_RECOGNITION_MAX_CONCURRENT}")
print(f"  MCP连接池: {settings.MCP_CLIENT_POOL_SIZE}")

success.append("✅ 性能配置已加载")

# 9. 日志配置验证
print("\n【日志配置】")
print(f"  级别: {settings.LOG_LEVEL}")
print(f"  目录: {settings.LOG_DIR}")
print(f"  JSON格式: {settings.ENABLE_JSON_LOG}")

success.append("✅ 日志配置已加载")

# 10. 环境变量完整性检查
print("\n【环境变量检查】")
env_file = project_root / ".env"
if env_file.exists():
    print(f"  .env文件: ✅ 存在")
    success.append("✅ .env文件存在")
else:
    print(f"  .env文件: ❌ 不存在")
    issues.append("❌ .env文件不存在")

# 输出总结
print("\n" + "=" * 70)
print("验证总结")
print("=" * 70)

if success:
    print(f"\n✅ 成功 ({len(success)}项):")
    for item in success:
        print(f"  {item}")

if warnings:
    print(f"\n⚠️  警告 ({len(warnings)}项):")
    for item in warnings:
        print(f"  {item}")

if issues:
    print(f"\n❌ 错误 ({len(issues)}项):")
    for item in issues:
        print(f"  {item}")

print("\n" + "=" * 70)

if issues:
    print("状态: ❌ 配置存在错误，请修复后再启动")
    sys.exit(1)
elif warnings:
    print("状态: ⚠️  配置可用但有警告，建议检查")
    sys.exit(0)
else:
    print("状态: ✅ 配置完全正确")
    sys.exit(0)
